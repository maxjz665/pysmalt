"""
Алгоритм определения авторства на основе
статистического сравнения синтаксических профилей.

Автор модуля: М. А. Ежов

Метод:
  1. Для каждого автора строится синтаксический профиль —
     медианный вектор признаков по всем его текстам (робастная агрегация).
  2. Внутри кросс-валидации вектора нормализуются по обучающему фолду
     (без утечки данных из тестового текста).
  3. К нормализованным векторам применяются веса блоков признаков.
  4. Неизвестный текст сравнивается с профилями авторов
     через метрики сходства (косинусное, Манхэттенское,
     дивергенция Кульбака–Лейблера).
  5. Автор с наибольшим сходством считается наиболее вероятным.

Отличие от ML-метода: здесь нет обучения модели. Профиль —
это прямая статистическая характеристика, прозрачная и
интерпретируемая.
"""
import logging
import math
from typing import List, Dict, Tuple, Optional

import numpy as np

from research.authorship.models import (
    TblSyntacticFeature, TblAuthorProfile,
    TblAttributionExperiment, TblAttributionResult
)
from research.authorship.utils.features import (
    extract_and_vectorize, build_feature_vector,
    extract_and_save_features, FEATURE_NAMES, VECTOR_SIZE,
    POS_TAGS, DEP_TYPES,
    POS_BIGRAMS_VOCAB, SYNTACTIC_PRODUCTIONS_VOCAB, FUNCTION_WORDS_VOCAB,
)
from text_app.models.tbl_text import TblText
from text_app.models.tbl_author import TblAuthor
from text_app.models.tbl_textlist import TblTextListDescription

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────
#  Блоки признаков и их веса
# ────────────────────────────────────────────────────────────

_N_SCALAR = 4
_N_POS = len(POS_TAGS)
_N_DEP = len(DEP_TYPES)
_N_CLAUSE = 4
_N_DEPTH = 15
_N_POSBI = len(POS_BIGRAMS_VOCAB)
_N_PROD = len(SYNTACTIC_PRODUCTIONS_VOCAB)
_N_FW = len(FUNCTION_WORDS_VOCAB)

_s0 = 0
_s1 = _s0 + _N_SCALAR
_s2 = _s1 + _N_POS
_s3 = _s2 + _N_DEP
_s4 = _s3 + _N_CLAUSE
_s5 = _s4 + _N_DEPTH
_s6 = _s5 + _N_POSBI
_s7 = _s6 + _N_PROD
_s8 = _s7 + _N_FW  # == VECTOR_SIZE

_BLOCK_SLICES = (
    slice(_s0, _s1),  # [0]  scalar
    slice(_s1, _s2),  # [1]  POS unigrams
    slice(_s2, _s3),  # [2]  dependency relations
    slice(_s3, _s4),  # [3]  clause types
    slice(_s4, _s5),  # [4]  tree depth distribution
    slice(_s5, _s6),  # [5]  POS bigrams
    slice(_s6, _s7),  # [6]  syntactic productions (head-dep-child)
    slice(_s7, _s8),  # [7]  function words
)

# Веса блоков признаков.
# Выше у чисто-синтаксических блоков (зависимости, продукции).
# Ниже у скалярных метрик, которые сильно зависят от длины текста.
_BLOCK_WEIGHTS = (0.35, 1.0, 1.2, 0.9, 0.8, 1.0, 1.3, 1.0)


# ────────────────────────────────────────────────────────────
#  Вспомогательные функции: нормализация и взвешивание
# ────────────────────────────────────────────────────────────

def _apply_block_weights(vec: np.ndarray) -> np.ndarray:
    """Apply per-block weights to a feature vector."""
    out = vec.copy().astype(float)
    for w, sl in zip(_BLOCK_WEIGHTS, _BLOCK_SLICES):
        out[sl] *= w
    return out


def _normalize_fold(train_matrix: np.ndarray,
                    test_vec: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Z-score normalization using train-fold statistics only (no leakage).
    Features with std == 0 are left unchanged (divided by 1.0).
    """
    mean = train_matrix.mean(axis=0)
    std = train_matrix.std(axis=0)
    std[std == 0.0] = 1.0
    return (train_matrix - mean) / std, (test_vec - mean) / std


def _build_profile(vecs: List[np.ndarray], aggregation: str = 'median') -> np.ndarray:
    """Build author profile via median (robust) or mean aggregation."""
    arr = np.array(vecs)
    if aggregation == 'median':
        return np.median(arr, axis=0)
    return np.mean(arr, axis=0)


# ────────────────────────────────────────────────────────────
#  Метрики сходства
# ────────────────────────────────────────────────────────────

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Косинусное сходство двух векторов.

    cos(a, b) = (a · b) / (||a|| × ||b||)

    Возвращает значение от -1 до 1, где 1 — полное совпадение.
    """
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def manhattan_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    Манхэттенское расстояние (L1-норма разности).

    d(a, b) = Σ |a_i - b_i|
    """
    return float(np.sum(np.abs(a - b)))


def kl_divergence(p: np.ndarray, q: np.ndarray, epsilon: float = 1e-10) -> float:
    """
    Дивергенция Кульбака–Лейблера.

    KL(P || Q) = Σ p_i × log(p_i / q_i)

    Используется сглаживание epsilon для избежания деления на ноль.
    """
    p = np.clip(p, epsilon, None)
    q = np.clip(q, epsilon, None)
    # Нормализуем для корректности (на случай если не нормализовано)
    p = p / p.sum()
    q = q / q.sum()
    return float(np.sum(p * np.log(p / q)))


def symmetric_kl(p: np.ndarray, q: np.ndarray) -> float:
    """
    Симметричная KL-дивергенция (расстояние Джеффриса).

    J(P, Q) = (KL(P||Q) + KL(Q||P)) / 2
    """
    return (kl_divergence(p, q) + kl_divergence(q, p)) / 2


# ────────────────────────────────────────────────────────────
#  Построение профиля автора
# ────────────────────────────────────────────────────────────

def build_author_profile(author: TblAuthor,
                         text_list: TblTextListDescription) -> TblAuthorProfile:
    """
    Строит синтаксический профиль автора на основе текстов из списка.

    Профиль = медиана векторов признаков всех текстов автора
    (робастная агрегация, устойчивая к выбросам).

    Args:
        author: объект автора
        text_list: список текстов

    Returns:
        TblAuthorProfile: сохранённый профиль
    """
    from text_app.models.tbl_textlist import TblTextListItems
    text_ids = TblTextListItems.objects.filter(
        list=text_list
    ).values_list('text_id', flat=True)

    texts = TblText.objects.filter(
        id__in=text_ids,
        author=author
    )

    vectors = []
    for text_obj in texts:
        try:
            sf = TblSyntacticFeature.objects.get(text=text_obj)
        except TblSyntacticFeature.DoesNotExist:
            sf = extract_and_save_features(text_obj)
        vectors.append(np.array(sf.feature_vector))

    if not vectors:
        raise ValueError(f"Нет текстов автора {author.name} в списке {text_list.name}")

    arr = np.array(vectors)
    median_vector = np.median(arr, axis=0)
    std_vector = np.std(arr, axis=0)

    profile, _ = TblAuthorProfile.objects.update_or_create(
        author=author,
        text_list=text_list,
        defaults={
            'texts_count': len(vectors),
            'profile_vector': median_vector.tolist(),
            'profile_data': {
                'std_vector': std_vector.tolist(),
                'texts_count': len(vectors),
                'feature_names': FEATURE_NAMES,
                'aggregation': 'median',
            }
        }
    )
    return profile


def build_all_profiles(text_list: TblTextListDescription) -> List[TblAuthorProfile]:
    """
    Строит профили для всех авторов в списке текстов.
    """
    from text_app.models.tbl_textlist import TblTextListItems
    text_ids = TblTextListItems.objects.filter(
        list=text_list
    ).values_list('text_id', flat=True)

    author_ids = TblText.objects.filter(
        id__in=text_ids,
        author__isnull=False
    ).values_list('author_id', flat=True).distinct()

    authors = TblAuthor.objects.filter(id__in=author_ids)

    profiles = []
    for author in authors:
        try:
            profile = build_author_profile(author, text_list)
            profiles.append(profile)
            logger.info(f"Профиль автора {author.name}: {profile.texts_count} текстов")
        except ValueError as e:
            logger.warning(str(e))

    return profiles


# ────────────────────────────────────────────────────────────
#  Атрибуция текста
# ────────────────────────────────────────────────────────────

def attribute_text(raw_text: str,
                   text_list: TblTextListDescription,
                   metric: str = 'cosine') -> List[Dict]:
    """
    Определяет наиболее вероятного автора текста
    методом сравнения синтаксических профилей.

    Args:
        raw_text: текст неизвестного авторства
        text_list: список текстов с профилями авторов
        metric: метрика ('cosine', 'manhattan', 'kl')

    Returns:
        list[dict]: список кандидатов, отсортированный по убыванию сходства
            [{'author': TblAuthor, 'score': float, 'rank': int}, ...]
    """
    features, vector = extract_and_vectorize(raw_text)
    vec = _apply_block_weights(np.array(vector))

    profiles = TblAuthorProfile.objects.filter(text_list=text_list)
    if not profiles.exists():
        profiles = build_all_profiles(text_list)

    results = []
    for profile in profiles:
        pvec = _apply_block_weights(profile.get_profile_vector_np())

        if metric == 'cosine':
            score = cosine_similarity(vec, pvec)
        elif metric == 'manhattan':
            dist = manhattan_distance(vec, pvec)
            score = 1.0 / (1.0 + dist)
        elif metric == 'kl':
            p_dist = vec[4:]
            q_dist = pvec[4:]
            dist = symmetric_kl(p_dist, q_dist)
            score = 1.0 / (1.0 + dist)
        else:
            raise ValueError(f"Неизвестная метрика: {metric}")

        results.append({
            'author': profile.author,
            'author_name': profile.author.name,
            'score': round(score, 6),
            'texts_in_profile': profile.texts_count,
        })

    results.sort(key=lambda x: x['score'], reverse=True)
    for i, r in enumerate(results):
        r['rank'] = i + 1

    return results


# ────────────────────────────────────────────────────────────
#  Эксперимент с кросс-валидацией
# ────────────────────────────────────────────────────────────

def run_experiment(text_list: TblTextListDescription,
                   metric: str = 'cosine',
                   n_folds: int = 5,
                   name: str = '',
                   owner=None) -> TblAttributionExperiment:
    """
    Запускает эксперимент по определению авторства
    с leave-one-out кросс-валидацией.

    Улучшения по сравнению с базовой версией:
    - fold-wise z-score нормализация (без утечки данных тестового текста)
    - взвешивание блоков признаков после нормализации
    - медианная агрегация профилей авторов (устойчива к выбросам)
    - корректный macro-F1 (среднее по классам, не F(P̄, R̄))

    Args:
        text_list: список текстов для эксперимента
        metric: метрика сходства ('cosine', 'manhattan', 'kl')
        n_folds: зарезервировано для совместимости (используется LOO)
        name: название эксперимента
        owner: пользователь-владелец

    Returns:
        TblAttributionExperiment: результаты эксперимента
    """
    from text_app.models.tbl_textlist import TblTextListItems

    experiment = TblAttributionExperiment.objects.create(
        name=name or f"Profile ({metric}) - {text_list.name}",
        method='profile',
        text_list=text_list,
        owner=owner,
        params={'metric': metric, 'n_folds': n_folds,
                'aggregation': 'median', 'normalization': 'fold-wise'},
        build_status='running',
    )

    items = TblTextListItems.objects.filter(list=text_list).select_related('text', 'text__author')
    texts_with_authors = [(item.text, item.text.author)
                          for item in items
                          if item.text.author is not None]

    if len(texts_with_authors) < 3:
        experiment.build_status = 'error: недостаточно текстов'
        experiment.save()
        return experiment

    # Собираем сырые векторы признаков для всех текстов
    all_features = {}
    for text_obj, author in texts_with_authors:
        try:
            sf = TblSyntacticFeature.objects.get(text=text_obj)
        except TblSyntacticFeature.DoesNotExist:
            sf = extract_and_save_features(text_obj)
        all_features[text_obj.id] = np.array(sf.feature_vector, dtype=float)

    # Leave-one-out кросс-валидация
    correct = 0
    total = 0
    author_results = {}  # author_id -> {correct, total, name}

    for test_text, true_author in texts_with_authors:
        test_raw = all_features.get(test_text.id)
        if test_raw is None:
            continue

        # Разделяем обучающий и тестовый фолды
        train_pairs = [(t, a) for t, a in texts_with_authors if t.id != test_text.id]
        train_raw = np.array([all_features[t.id] for t, a in train_pairs], dtype=float)

        # Fold-wise нормализация (статистики только по обучающим данным)
        train_norm, test_norm = _normalize_fold(train_raw, test_raw)

        # Взвешивание блоков признаков
        train_weighted = np.array([_apply_block_weights(v) for v in train_norm])
        test_weighted = _apply_block_weights(test_norm)

        # Медианные профили авторов из нормализованных взвешенных векторов
        author_vecs: Dict[int, List[np.ndarray]] = {}
        for (t, a), wv in zip(train_pairs, train_weighted):
            author_vecs.setdefault(a.id, []).append(wv)

        profiles = {aid: _build_profile(vecs, 'median')
                    for aid, vecs in author_vecs.items()}

        # Оценка сходства с каждым профилем
        scores: Dict[int, float] = {}
        for author_id, profile_vec in profiles.items():
            if metric == 'cosine':
                scores[author_id] = cosine_similarity(test_weighted, profile_vec)
            elif metric == 'manhattan':
                d = manhattan_distance(test_weighted, profile_vec)
                scores[author_id] = 1.0 / (1.0 + d)
            elif metric == 'kl':
                # KL применяется к распределительной части вектора (с позиции 4)
                d = symmetric_kl(test_weighted[4:], profile_vec[4:])
                scores[author_id] = 1.0 / (1.0 + d)

        predicted_id = max(scores, key=scores.get) if scores else None
        is_correct = (predicted_id == true_author.id)

        if is_correct:
            correct += 1
        total += 1

        aid = true_author.id
        if aid not in author_results:
            author_results[aid] = {'correct': 0, 'total': 0, 'name': true_author.name}
        author_results[aid]['total'] += 1
        if is_correct:
            author_results[aid]['correct'] += 1

        predicted_author = TblAuthor.objects.get(id=predicted_id) if predicted_id else None
        TblAttributionResult.objects.create(
            experiment=experiment,
            text=test_text,
            true_author=true_author,
            predicted_author=predicted_author,
            confidence=scores.get(predicted_id, 0) if predicted_id else 0,
            scores={str(k): round(v, 6) for k, v in scores.items()},
            is_correct=is_correct,
        )

    # ── Метрики ────────────────────────────────────────────
    accuracy = correct / total if total > 0 else 0

    # Precision и Recall по классам (авторам)
    per_class_f1 = []
    precisions = []
    recalls = []

    for aid, data in author_results.items():
        tp = data['correct']
        fp = TblAttributionResult.objects.filter(
            experiment=experiment,
            predicted_author_id=aid,
            is_correct=False
        ).count()
        fn = data['total'] - tp

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)
              if (precision + recall) > 0 else 0.0)

        data['precision'] = round(precision, 4)
        data['recall'] = round(recall, 4)
        data['f1'] = round(f1, 4)

        precisions.append(precision)
        recalls.append(recall)
        per_class_f1.append(f1)

    macro_precision = float(np.mean(precisions)) if precisions else 0.0
    macro_recall = float(np.mean(recalls)) if recalls else 0.0
    # Корректный macro-F1: среднее по классам, а не F(P̄, R̄)
    macro_f1 = float(np.mean(per_class_f1)) if per_class_f1 else 0.0

    experiment.accuracy = round(accuracy, 4)
    experiment.precision = round(macro_precision, 4)
    experiment.recall = round(macro_recall, 4)
    experiment.f1_score = round(macro_f1, 4)
    experiment.detailed_results = author_results
    experiment.build_status = 'completed'
    experiment.save()

    logger.info(f"Эксперимент {experiment.name}: accuracy={accuracy:.2%}, F1={macro_f1:.2%}")
    return experiment
