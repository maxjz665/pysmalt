"""
Алгоритм определения авторства на основе
машинного обучения (классификация по синтаксическим признакам).

Автор модуля: Р. Ю. Севрюков

Метод:
  1. Из текстов извлекаются синтаксические признаки
     (тот же вектор из 77 компонент, что и в профильном методе).
  2. Признаки нормализуются (StandardScaler).
  3. Обучается классификатор (SVM с RBF-ядром или Random Forest).
  4. Неизвестный текст классифицируется обученной моделью.

Отличие от профильного метода: модель сама определяет
оптимальные границы между классами в пространстве признаков,
а не опирается на фиксированную метрику расстояния.
Feature importance позволяет определить, какие синтаксические
черты оказались наиболее дискриминативными.
"""
import logging
import pickle
from typing import List, Dict, Optional, Tuple

import numpy as np
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import cross_val_predict, StratifiedKFold, LeaveOneOut
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix, classification_report)
from sklearn.pipeline import Pipeline

from research.authorship.models import (
    TblSyntacticFeature, TblAttributionExperiment, TblAttributionResult
)
from research.authorship.utils.features import (
    extract_and_vectorize, extract_and_save_features,
    FEATURE_NAMES, VECTOR_SIZE
)
from text_app.models.tbl_text import TblText
from text_app.models.tbl_author import TblAuthor
from text_app.models.tbl_textlist import TblTextListDescription

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────
#  Построение обучающей выборки
# ────────────────────────────────────────────────────────────

def _prepare_dataset(text_list: TblTextListDescription) -> Tuple[np.ndarray, np.ndarray, list, list]:
    """
    Формирует матрицу признаков X и вектор меток y
    из текстов заданного списка.

    Returns:
        X: матрица (n_samples, 77)
        y: массив меток авторов
        text_ids: список id текстов (в том же порядке)
        author_names: список имён авторов (для LabelEncoder)
    """
    from text_app.models.tbl_textlist import TblTextListItems

    items = TblTextListItems.objects.filter(
        list=text_list
    ).select_related('text', 'text__author')

    X_list = []
    y_list = []
    text_ids = []
    author_map = {}  # author_id -> author_name

    for item in items:
        text_obj = item.text
        author = text_obj.author
        if author is None:
            continue

        # Получаем или извлекаем признаки
        try:
            sf = TblSyntacticFeature.objects.get(text=text_obj)
        except TblSyntacticFeature.DoesNotExist:
            sf = extract_and_save_features(text_obj)

        X_list.append(sf.feature_vector)
        y_list.append(author.id)
        text_ids.append(text_obj.id)
        author_map[author.id] = author.name

    X = np.array(X_list, dtype=float)
    y = np.array(y_list)

    return X, y, text_ids, author_map


# ────────────────────────────────────────────────────────────
#  Обучение классификатора
# ────────────────────────────────────────────────────────────

def train_svm(X: np.ndarray, y: np.ndarray,
              C: float = 1.0, gamma: str = 'scale',
              kernel: str = 'rbf') -> Pipeline:
    """
    Обучает SVM-классификатор.

    Args:
        X: матрица признаков
        y: метки классов
        C: параметр регуляризации
        gamma: параметр ядра
        kernel: тип ядра ('rbf', 'linear', 'poly')

    Returns:
        Pipeline: обученный пайплайн (scaler + classifier)
    """
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', SVC(
            C=C, gamma=gamma, kernel=kernel,
            probability=True,  # для predict_proba
            random_state=42,
            decision_function_shape='ovr'
        ))
    ])
    pipeline.fit(X, y)
    return pipeline


def train_random_forest(X: np.ndarray, y: np.ndarray,
                        n_estimators: int = 100,
                        max_depth: int = 10) -> Pipeline:
    """
    Обучает Random Forest классификатор.

    Args:
        X: матрица признаков
        y: метки классов
        n_estimators: количество деревьев
        max_depth: максимальная глубина деревьев

    Returns:
        Pipeline: обученный пайплайн (scaler + classifier)
    """
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            n_jobs=-1
        ))
    ])
    pipeline.fit(X, y)
    return pipeline


# ────────────────────────────────────────────────────────────
#  Атрибуция текста
# ────────────────────────────────────────────────────────────

def attribute_text(raw_text: str,
                   experiment: TblAttributionExperiment) -> List[Dict]:
    """
    Определяет автора текста с помощью обученной ML-модели.

    Args:
        raw_text: текст неизвестного авторства
        experiment: эксперимент с обученной моделью

    Returns:
        list[dict]: список кандидатов с вероятностями
    """
    if not experiment.trained_model:
        raise ValueError("Модель не обучена")

    pipeline = pickle.loads(experiment.trained_model)
    author_map = experiment.params.get('author_map', {})

    # Извлекаем признаки
    features, vector = extract_and_vectorize(raw_text)
    X = np.array([vector])

    # Предсказание
    predicted_id = pipeline.predict(X)[0]
    probabilities = pipeline.predict_proba(X)[0]
    classes = pipeline.classes_

    results = []
    for cls, prob in zip(classes, probabilities):
        author_name = author_map.get(str(cls), f"Author #{cls}")
        results.append({
            'author_id': int(cls),
            'author_name': author_name,
            'score': round(float(prob), 6),
        })

    results.sort(key=lambda x: x['score'], reverse=True)
    for i, r in enumerate(results):
        r['rank'] = i + 1

    return results


def get_feature_importance(experiment: TblAttributionExperiment) -> List[Dict]:
    """
    Возвращает важность признаков (только для Random Forest).

    Returns:
        list[dict]: [{name, importance}, ...], отсортированный по убыванию
    """
    if not experiment.trained_model:
        return []

    pipeline = pickle.loads(experiment.trained_model)
    classifier = pipeline.named_steps['classifier']

    if not hasattr(classifier, 'feature_importances_'):
        return []

    importances = classifier.feature_importances_
    result = []
    for name, imp in zip(FEATURE_NAMES, importances):
        result.append({'name': name, 'importance': round(float(imp), 6)})

    result.sort(key=lambda x: x['importance'], reverse=True)
    return result


# ────────────────────────────────────────────────────────────
#  Эксперимент с кросс-валидацией
# ────────────────────────────────────────────────────────────

def run_experiment(text_list: TblTextListDescription,
                   classifier_type: str = 'svm',
                   name: str = '',
                   owner=None,
                   **classifier_params) -> TblAttributionExperiment:
    """
    Запускает эксперимент по определению авторства
    с кросс-валидацией и обучением модели.

    Args:
        text_list: список текстов для эксперимента
        classifier_type: 'svm' или 'rf' (random forest)
        name: название эксперимента
        owner: пользователь-владелец
        **classifier_params: параметры классификатора

    Returns:
        TblAttributionExperiment: результаты эксперимента
    """
    experiment = TblAttributionExperiment.objects.create(
        name=name or f"ML ({classifier_type}) - {text_list.name}",
        method='ml',
        text_list=text_list,
        owner=owner,
        params={
            'classifier_type': classifier_type,
            'classifier_params': classifier_params,
        },
        build_status='running',
    )

    try:
        # Подготовка данных
        X, y, text_ids, author_map = _prepare_dataset(text_list)

        if len(X) < 3:
            experiment.build_status = 'error: недостаточно текстов'
            experiment.save()
            return experiment

        unique_authors = np.unique(y)
        if len(unique_authors) < 2:
            experiment.build_status = 'error: недостаточно авторов'
            experiment.save()
            return experiment

        # Сохраняем маппинг авторов
        experiment.params['author_map'] = {str(k): v for k, v in author_map.items()}
        experiment.params['n_samples'] = len(X)
        experiment.params['n_authors'] = len(unique_authors)
        experiment.params['vector_size'] = VECTOR_SIZE

        # Кросс-валидация
        # Если текстов мало — leave-one-out, иначе StratifiedKFold
        min_samples_per_class = min(np.bincount(
            LabelEncoder().fit_transform(y)
        ))

        if min_samples_per_class < 3:
            cv = LeaveOneOut()
        else:
            n_splits = min(5, min_samples_per_class)
            cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

        # Создаём пайплайн
        if classifier_type == 'svm':
            pipeline = Pipeline([
                ('scaler', StandardScaler()),
                ('classifier', SVC(
                    C=classifier_params.get('C', 1.0),
                    gamma=classifier_params.get('gamma', 'scale'),
                    kernel=classifier_params.get('kernel', 'rbf'),
                    probability=True,
                    random_state=42,
                ))
            ])
        elif classifier_type == 'rf':
            pipeline = Pipeline([
                ('scaler', StandardScaler()),
                ('classifier', RandomForestClassifier(
                    n_estimators=classifier_params.get('n_estimators', 100),
                    max_depth=classifier_params.get('max_depth', 10),
                    random_state=42,
                    n_jobs=-1,
                ))
            ])
        else:
            raise ValueError(f"Неизвестный тип классификатора: {classifier_type}")

        # Предсказания по кросс-валидации
        y_pred = cross_val_predict(pipeline, X, y, cv=cv)

        # Метрики
        accuracy = accuracy_score(y, y_pred)
        precision = precision_score(y, y_pred, average='macro', zero_division=0)
        recall = recall_score(y, y_pred, average='macro', zero_division=0)
        f1 = f1_score(y, y_pred, average='macro', zero_division=0)
        cm = confusion_matrix(y, y_pred)

        # Обучаем финальную модель на всех данных
        pipeline.fit(X, y)

        # Сохраняем результаты по каждому тексту
        for i, (text_id, true_label, pred_label) in enumerate(zip(text_ids, y, y_pred)):
            text_obj = TblText.objects.get(id=text_id)
            true_author = TblAuthor.objects.get(id=true_label)
            pred_author = TblAuthor.objects.get(id=pred_label)

            TblAttributionResult.objects.create(
                experiment=experiment,
                text=text_obj,
                true_author=true_author,
                predicted_author=pred_author,
                confidence=1.0 if true_label == pred_label else 0.0,
                scores={},
                is_correct=(true_label == pred_label),
            )

        # Подробные результаты по авторам
        detailed = {}
        for author_id, author_name in author_map.items():
            mask = (y == int(author_id))
            if mask.sum() == 0:
                continue
            author_correct = ((y == int(author_id)) & (y_pred == int(author_id))).sum()
            author_total = mask.sum()
            detailed[author_id] = {
                'name': author_name,
                'correct': int(author_correct),
                'total': int(author_total),
                'accuracy': round(float(author_correct / author_total), 4),
            }

        # Feature importance (для RF)
        feature_imp = []
        if classifier_type == 'rf':
            clf = pipeline.named_steps['classifier']
            for fname, imp in zip(FEATURE_NAMES, clf.feature_importances_):
                feature_imp.append({'name': fname, 'importance': round(float(imp), 6)})
            feature_imp.sort(key=lambda x: x['importance'], reverse=True)

        experiment.accuracy = round(accuracy, 4)
        experiment.precision = round(precision, 4)
        experiment.recall = round(recall, 4)
        experiment.f1_score = round(f1, 4)
        experiment.confusion_matrix = cm.tolist()
        experiment.detailed_results = {
            'by_author': detailed,
            'feature_importance': feature_imp[:20],
            'classification_report': classification_report(
                y, y_pred,
                target_names=[author_map.get(str(c), str(c)) for c in np.unique(y)],
                output_dict=True,
                zero_division=0
            ),
        }
        experiment.trained_model = pickle.dumps(pipeline)
        experiment.build_status = 'completed'
        experiment.save()

        logger.info(f"Эксперимент {experiment.name}: accuracy={accuracy:.2%}, F1={f1:.2%}")

    except Exception as e:
        logger.exception("Ошибка при выполнении эксперимента")
        experiment.build_status = f'error: {str(e)}'
        experiment.save()

    return experiment
