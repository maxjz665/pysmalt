"""
Алгоритм определения авторства на основе
статистического сравнения синтаксических профилей.

Автор модуля: М. А. Ежов

Метод:
  1. Для каждого автора строится синтаксический профиль —
     усреднённый вектор признаков по всем его текстам.
  2. Неизвестный текст сравнивается с профилями авторов
     через метрики сходства (косинусное, Манхэттенское,
     дивергенция Кульбака–Лейблера).
  3. Автор с наибольшим сходством считается наиболее вероятным.

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
    extract_and_save_features, FEATURE_NAMES, VECTOR_SIZE
)
from text_app.models.tbl_text import TblText
from text_app.models.tbl_author import TblAuthor
from text_app.models.tbl_textlist import TblTextListDescription

logger = logging.getLogger(__name__)


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

    Профиль = среднее арифметическое векторов признаков всех текстов
    автора в данном списке.

    Args:
        author: объект автора
        text_list: список текстов

    Returns:
        TblAuthorProfile: сохранённый профиль
    """
    # Получаем тексты автора из списка
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
        # Получаем или вычисляем признаки
        try:
            sf = TblSyntacticFeature.objects.get(text=text_obj)
        except TblSyntacticFeature.DoesNotExist:
            sf = extract_and_save_features(text_obj)
        vectors.append(np.array(sf.feature_vector))

    if not vectors:
        raise ValueError(f"Нет текстов автора {author.name} в списке {text_list.name}")

    # Усреднение
    mean_vector = np.mean(vectors, axis=0)
    std_vector = np.std(vectors, axis=0)

    profile, _ = TblAuthorProfile.objects.update_or_create(
        author=author,
        text_list=text_list,
        defaults={
            'texts_count': len(vectors),
            'profile_vector': mean_vector.tolist(),
            'profile_data': {
                'std_vector': std_vector.tolist(),
                'texts_count': len(vectors),
                'feature_names': FEATURE_NAMES,
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
    # Извлекаем признаки неизвестного текста
    features, vector = extract_and_vectorize(raw_text)
    vec = np.array(vector)

    # Загружаем профили
    profiles = TblAuthorProfile.objects.filter(text_list=text_list)
    if not profiles.exists():
        profiles = build_all_profiles(text_list)

    results = []
    for profile in profiles:
        pvec = profile.get_profile_vector_np()

        if metric == 'cosine':
            score = cosine_similarity(vec, pvec)
        elif metric == 'manhattan':
            # Инвертируем: чем меньше расстояние, тем больше сходство
            dist = manhattan_distance(vec, pvec)
            score = 1.0 / (1.0 + dist)
        elif metric == 'kl':
            # Для KL берём только распределительные части вектора (с позиции 4)
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

    # Сортируем по убыванию сходства
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
    с кросс-валидацией (leave-one-out или k-fold).

    На каждом фолде один текст исключается, профили строятся
    по оставшимся текстам, затем исключённый текст атрибутируется.

    Args:
        text_list: список текстов для эксперимента
        metric: метрика сходства
        n_folds: количество фолдов (0 = leave-one-out)
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
        params={'metric': metric, 'n_folds': n_folds},
        build_status='running',
    )

    # Получаем все тексты с авторами
    items = TblTextListItems.objects.filter(list=text_list).select_related('text', 'text__author')
    texts_with_authors = [(item.text, item.text.author)
                          for item in items
                          if item.text.author is not None]

    if len(texts_with_authors) < 3:
        experiment.build_status = 'error: недостаточно текстов'
        experiment.save()
        return experiment

    # Извлекаем признаки для всех текстов
    all_features = {}
    for text_obj, author in texts_with_authors:
        try:
            sf = TblSyntacticFeature.objects.get(text=text_obj)
        except TblSyntacticFeature.DoesNotExist:
            sf = extract_and_save_features(text_obj)
        all_features[text_obj.id] = np.array(sf.feature_vector)

    # Leave-one-out кросс-валидация
    correct = 0
    total = 0
    author_results = {}  # author_id -> {correct, total}

    for test_text, true_author in texts_with_authors:
        test_vec = all_features.get(test_text.id)
        if test_vec is None:
            continue

        # Строим профили без тестового текста
        train_texts = [(t, a) for t, a in texts_with_authors if t.id != test_text.id]
        author_vectors = {}
        for t, a in train_texts:
            author_vectors.setdefault(a.id, []).append(all_features[t.id])

        # Усредняем профили
        scores = {}
        for author_id, vecs in author_vectors.items():
            mean_vec = np.mean(vecs, axis=0)
            if metric == 'cosine':
                scores[author_id] = cosine_similarity(test_vec, mean_vec)
            elif metric == 'manhattan':
                d = manhattan_distance(test_vec, mean_vec)
                scores[author_id] = 1.0 / (1.0 + d)
            elif metric == 'kl':
                d = symmetric_kl(test_vec[4:], mean_vec[4:])
                scores[author_id] = 1.0 / (1.0 + d)

        # Предсказание
        predicted_id = max(scores, key=scores.get) if scores else None
        is_correct = predicted_id == true_author.id

        if is_correct:
            correct += 1
        total += 1

        # Статистика по авторам
        aid = true_author.id
        if aid not in author_results:
            author_results[aid] = {'correct': 0, 'total': 0, 'name': true_author.name}
        author_results[aid]['total'] += 1
        if is_correct:
            author_results[aid]['correct'] += 1

        # Сохраняем результат
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

    # Подсчёт метрик
    accuracy = correct / total if total > 0 else 0

    # Precision / Recall / F1 (macro-averaged)
    precisions = []
    recalls = []
    for aid, data in author_results.items():
        # TP = правильно предсказано для этого автора
        tp = data['correct']
        # FP = другие тексты ошибочно приписаны этому автору
        fp = TblAttributionResult.objects.filter(
            experiment=experiment,
            predicted_author_id=aid,
            is_correct=False
        ).count()
        # FN = тексты этого автора приписаны другим
        fn = data['total'] - tp

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        precisions.append(precision)
        recalls.append(recall)
        data['precision'] = round(precision, 4)
        data['recall'] = round(recall, 4)

    macro_precision = np.mean(precisions) if precisions else 0
    macro_recall = np.mean(recalls) if recalls else 0
    macro_f1 = (2 * macro_precision * macro_recall / (macro_precision + macro_recall)
                if (macro_precision + macro_recall) > 0 else 0)

    experiment.accuracy = round(accuracy, 4)
    experiment.precision = round(float(macro_precision), 4)
    experiment.recall = round(float(macro_recall), 4)
    experiment.f1_score = round(float(macro_f1), 4)
    experiment.detailed_results = author_results
    experiment.build_status = 'completed'
    experiment.save()

    logger.info(f"Эксперимент {experiment.name}: accuracy={accuracy:.2%}, F1={macro_f1:.2%}")
    return experiment
