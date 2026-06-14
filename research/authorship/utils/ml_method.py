import logging
import pickle
import warnings
from typing import Dict, List, Tuple, Union

import numpy as np

from research.authorship.models import TblAttributionExperiment, TblAttributionResult, TblSyntacticFeature
from research.authorship.utils.features import (
    FEATURE_NAMES,
    VECTOR_SIZE,
    FeatureExtractionError,
    extract_and_save_features,
    extract_and_vectorize,
)
from text_app.models.tbl_author import TblAuthor
from text_app.models.tbl_text import TblText
from text_app.models.tbl_textlist import TblTextListDescription, TblTextListItems

logger = logging.getLogger(__name__)

SVM_PARAM_GRID = {
    "selector__k": [50, 100, "all"],
    "classifier__C": [0.1, 1.0, 10.0],
    "classifier__gamma": ["scale", 0.1],
    "classifier__kernel": ["rbf", "linear"],
}

# Альтернативный классификатор — Random Forest. Сетка соответствует
# табл. «Сетка гиперпараметров GridSearchCV (Random Forest)» отчёта.
RF_PARAM_GRID = {
    "selector__k": [50, 100, "all"],
    "classifier__n_estimators": [100, 300],
    "classifier__max_depth": [5, 10, None],
}


def _classifier_meta(classifier_type: str):
    """Возвращает (описание пайплайна, сетку гиперпараметров, метку) по типу классификатора."""
    if classifier_type == "rf":
        return (
            "StandardScaler -> SelectKBest(f_classif) -> RandomForestClassifier",
            RF_PARAM_GRID,
            "RF",
        )
    return "StandardScaler -> SelectKBest(f_classif) -> SVC", SVM_PARAM_GRID, "SVC"


def _load_sklearn():
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.feature_selection import SelectKBest, f_classif
        from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
        from sklearn.model_selection import GridSearchCV, LeaveOneOut, StratifiedKFold
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.svm import SVC
    except Exception as exc:
        raise RuntimeError(
            "scikit-learn is required for the ML authorship method. "
            "Install requirements.txt and rerun the command."
        ) from exc

    return {
        "SelectKBest": SelectKBest,
        "f_classif": f_classif,
        "accuracy_score": accuracy_score,
        "confusion_matrix": confusion_matrix,
        "f1_score": f1_score,
        "precision_score": precision_score,
        "recall_score": recall_score,
        "GridSearchCV": GridSearchCV,
        "LeaveOneOut": LeaveOneOut,
        "Pipeline": Pipeline,
        "StandardScaler": StandardScaler,
        "StratifiedKFold": StratifiedKFold,
        "SVC": SVC,
        "RandomForestClassifier": RandomForestClassifier,
    }


def _resolve_text_list(text_list: Union[int, TblTextListDescription]) -> TblTextListDescription:
    if isinstance(text_list, TblTextListDescription):
        return text_list
    return TblTextListDescription.objects.get(id=int(text_list))


def _feature_vector_for_text(text: TblText) -> np.ndarray:
    try:
        sf = TblSyntacticFeature.objects.get(text=text)
    except TblSyntacticFeature.DoesNotExist:
        sf = extract_and_save_features(text)

    vector = sf.vector or sf.feature_vector
    if len(vector) != VECTOR_SIZE:
        raise FeatureExtractionError(
            f"Text {text.id} has vector size {len(vector)}, expected {VECTOR_SIZE}."
        )
    return np.array(vector, dtype=float)


def _prepare_dataset(text_list: TblTextListDescription) -> Tuple[np.ndarray, np.ndarray, List[int], Dict[int, str]]:
    items = (
        TblTextListItems.objects
        .filter(list=text_list)
        .select_related("text", "text__author")
        .order_by("text_id")
    )

    vectors = []
    labels = []
    text_ids = []
    author_map: Dict[int, str] = {}

    for item in items:
        if not item.text.author_id:
            continue
        vectors.append(_feature_vector_for_text(item.text))
        labels.append(item.text.author_id)
        text_ids.append(item.text_id)
        author_map[item.text.author_id] = item.text.author.name

    return np.array(vectors, dtype=float), np.array(labels, dtype=int), text_ids, author_map


def _make_svm_pipeline(sk):
    return sk["Pipeline"]([
        ("scaler", sk["StandardScaler"]()),
        ("selector", sk["SelectKBest"](score_func=sk["f_classif"], k="all")),
        ("classifier", sk["SVC"](probability=True, random_state=42)),
    ])


def _make_rf_pipeline(sk):
    return sk["Pipeline"]([
        ("scaler", sk["StandardScaler"]()),
        ("selector", sk["SelectKBest"](score_func=sk["f_classif"], k="all")),
        ("classifier", sk["RandomForestClassifier"](random_state=42)),
    ])


def _make_pipeline(sk, classifier_type: str):
    return _make_rf_pipeline(sk) if classifier_type == "rf" else _make_svm_pipeline(sk)


def _can_grid_search(y_train: np.ndarray) -> bool:
    _, counts = np.unique(y_train, return_counts=True)
    return len(counts) >= 2 and int(counts.min()) >= 2


def _fit_estimator(sk, X_train: np.ndarray, y_train: np.ndarray, classifier_type: str = "svm"):
    pipeline = _make_pipeline(sk, classifier_type)
    param_grid = RF_PARAM_GRID if classifier_type == "rf" else SVM_PARAM_GRID
    if _can_grid_search(y_train):
        _, counts = np.unique(y_train, return_counts=True)
        inner_splits = min(3, int(counts.min()))
        search = sk["GridSearchCV"](
            pipeline,
            param_grid,
            cv=sk["StratifiedKFold"](n_splits=inner_splits, shuffle=True, random_state=42),
            scoring="f1_macro",
            n_jobs=1,
            refit=True,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            warnings.simplefilter("ignore", category=RuntimeWarning)
            search.fit(X_train, y_train)
        return search.best_estimator_, search.best_params_

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        warnings.simplefilter("ignore", category=RuntimeWarning)
        pipeline.fit(X_train, y_train)
    return pipeline, {"fallback": "no inner grid search; too few samples per class"}


def _prediction_scores(estimator, X_test: np.ndarray) -> Tuple[int, Dict[int, float], float]:
    prediction = int(estimator.predict(X_test)[0])
    scores: Dict[int, float] = {}
    confidence = 1.0
    if hasattr(estimator, "predict_proba"):
        probabilities = estimator.predict_proba(X_test)[0]
        classes = estimator.classes_
        scores = {int(cls): float(prob) for cls, prob in zip(classes, probabilities)}
        confidence = float(scores.get(prediction, 0.0))
    return prediction, scores, confidence


def run_experiment(
    text_list: Union[int, TblTextListDescription],
    classifier_type: str = "svm",
    name: str = "",
    owner=None,
    **classifier_params,
) -> TblAttributionExperiment:
    text_list = _resolve_text_list(text_list)
    pipeline_desc, param_grid, clf_label = _classifier_meta(classifier_type)
    experiment = TblAttributionExperiment.objects.create(
        name=name or f"ML {clf_label} - {text_list.name}",
        method="ml",
        metric="f1_macro",
        text_list=text_list,
        owner=owner,
        params={
            "pipeline": pipeline_desc,
            "outer_cv": "leave-one-out",
            "param_grid": param_grid,
            "classifier_type": classifier_type,
            "vector_size": VECTOR_SIZE,
        },
        build_status="running",
    )

    try:
        if classifier_type not in ("svm", "rf"):
            raise ValueError("classifier_type must be 'svm' or 'rf'.")

        sk = _load_sklearn()
        X, y, text_ids, author_map = _prepare_dataset(text_list)
        unique_authors = np.unique(y)
        if len(X) < 3 or len(unique_authors) < 2:
            raise ValueError("Need at least 3 texts and 2 authors for ML attribution.")

        y_pred = []
        best_params_by_fold = []
        for train_idx, test_idx in sk["LeaveOneOut"]().split(X, y):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train = y[train_idx]
            estimator, best_params = _fit_estimator(sk, X_train, y_train, classifier_type)
            prediction, fold_scores, confidence = _prediction_scores(estimator, X_test)
            y_pred.append(prediction)
            best_params_by_fold.append(best_params)

            true_label = int(y[test_idx][0])
            text = TblText.objects.get(id=text_ids[test_idx[0]])
            TblAttributionResult.objects.create(
                experiment=experiment,
                text=text,
                true_author=TblAuthor.objects.get(id=true_label),
                predicted_author=TblAuthor.objects.get(id=prediction),
                confidence=round(confidence, 6),
                scores={str(k): round(v, 6) for k, v in fold_scores.items()},
                is_correct=(true_label == prediction),
            )

        y_pred_arr = np.array(y_pred, dtype=int)
        labels = sorted(int(author_id) for author_id in unique_authors)
        accuracy = sk["accuracy_score"](y, y_pred_arr)
        precision = sk["precision_score"](y, y_pred_arr, labels=labels, average="macro", zero_division=0)
        recall = sk["recall_score"](y, y_pred_arr, labels=labels, average="macro", zero_division=0)
        macro_f1 = sk["f1_score"](y, y_pred_arr, labels=labels, average="macro", zero_division=0)
        cm = sk["confusion_matrix"](y, y_pred_arr, labels=labels)

        final_estimator, best_params = _fit_estimator(sk, X, y, classifier_type)

        by_author = {}
        for author_id in labels:
            mask = y == author_id
            total = int(mask.sum())
            correct = int(((y == author_id) & (y_pred_arr == author_id)).sum())
            by_author[str(author_id)] = {
                "name": author_map.get(author_id, str(author_id)),
                "correct": correct,
                "total": total,
                "accuracy": round(correct / total if total else 0.0, 4),
            }

        metrics = {
            "accuracy": round(float(accuracy), 4),
            "macro_precision": round(float(precision), 4),
            "macro_recall": round(float(recall), 4),
            "macro_f1": round(float(macro_f1), 4),
            "n_texts": int(len(X)),
            "n_authors": int(len(labels)),
        }
        experiment.accuracy = metrics["accuracy"]
        experiment.precision = metrics["macro_precision"]
        experiment.recall = metrics["macro_recall"]
        experiment.f1_score = metrics["macro_f1"]
        experiment.metrics = metrics
        experiment.confusion_matrix = cm.tolist()
        experiment.detailed_results = {
            "by_author": by_author,
            "author_labels": [
                {"id": author_id, "name": author_map.get(author_id, str(author_id))}
                for author_id in labels
            ],
            "best_params": best_params,
            "fold_params_sample": best_params_by_fold[:5],
        }
        experiment.params["author_map"] = {str(k): v for k, v in author_map.items()}
        experiment.params["best_params"] = best_params
        experiment.trained_model = pickle.dumps(final_estimator)
        experiment.build_status = "completed"
        experiment.save()
        logger.info(
            "ML experiment %s completed: accuracy=%.4f macro_f1=%.4f",
            experiment.id,
            experiment.accuracy,
            experiment.f1_score,
        )
    except Exception as exc:
        logger.exception("ML experiment failed")
        experiment.build_status = "failed"
        experiment.error_message = str(exc)
        experiment.save(update_fields=["build_status", "error_message"])

    return experiment


def execute_existing_experiment(experiment: TblAttributionExperiment) -> None:
    """
    Run an ML experiment that has already been persisted (called by the worker).
    Raises on failure — the worker handles build_status and error_message.
    """
    classifier_type = experiment.params.get("classifier_type", "svm")
    if experiment.method == 'ml' and classifier_type not in ("svm", "rf"):
        raise ValueError("classifier_type must be 'svm' or 'rf'.")

    sk = _load_sklearn()
    X, y, text_ids, author_map = _prepare_dataset(experiment.text_list)
    unique_authors = np.unique(y)
    if len(X) < 3 or len(unique_authors) < 2:
        raise ValueError("Need at least 3 texts and 2 authors for ML attribution.")

    y_pred = []
    best_params_by_fold = []
    for train_idx, test_idx in sk["LeaveOneOut"]().split(X, y):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train = y[train_idx]
        estimator, best_params = _fit_estimator(sk, X_train, y_train, classifier_type)
        prediction, fold_scores, confidence = _prediction_scores(estimator, X_test)
        y_pred.append(prediction)
        best_params_by_fold.append(best_params)

        true_label = int(y[test_idx][0])
        text = TblText.objects.get(id=text_ids[test_idx[0]])
        TblAttributionResult.objects.create(
            experiment=experiment,
            text=text,
            true_author=TblAuthor.objects.get(id=true_label),
            predicted_author=TblAuthor.objects.get(id=prediction),
            confidence=round(confidence, 6),
            scores={str(k): round(v, 6) for k, v in fold_scores.items()},
            is_correct=(true_label == prediction),
        )

    y_pred_arr = np.array(y_pred, dtype=int)
    labels = sorted(int(author_id) for author_id in unique_authors)
    accuracy = sk["accuracy_score"](y, y_pred_arr)
    precision = sk["precision_score"](y, y_pred_arr, labels=labels, average="macro", zero_division=0)
    recall = sk["recall_score"](y, y_pred_arr, labels=labels, average="macro", zero_division=0)
    macro_f1 = sk["f1_score"](y, y_pred_arr, labels=labels, average="macro", zero_division=0)
    cm = sk["confusion_matrix"](y, y_pred_arr, labels=labels)

    final_estimator, best_params = _fit_estimator(sk, X, y, classifier_type)

    by_author = {}
    for author_id in labels:
        mask = y == author_id
        total = int(mask.sum())
        correct = int(((y == author_id) & (y_pred_arr == author_id)).sum())
        by_author[str(author_id)] = {
            "name": author_map.get(author_id, str(author_id)),
            "correct": correct,
            "total": total,
            "accuracy": round(correct / total if total else 0.0, 4),
        }

    metrics = {
        "accuracy": round(float(accuracy), 4),
        "macro_precision": round(float(precision), 4),
        "macro_recall": round(float(recall), 4),
        "macro_f1": round(float(macro_f1), 4),
        "n_texts": int(len(X)),
        "n_authors": int(len(labels)),
    }
    experiment.accuracy = metrics["accuracy"]
    experiment.precision = metrics["macro_precision"]
    experiment.recall = metrics["macro_recall"]
    experiment.f1_score = metrics["macro_f1"]
    experiment.metrics = metrics
    experiment.confusion_matrix = cm.tolist()
    experiment.detailed_results = {
        "by_author": by_author,
        "author_labels": [
            {"id": author_id, "name": author_map.get(author_id, str(author_id))}
            for author_id in labels
        ],
        "best_params": best_params,
        "fold_params_sample": best_params_by_fold[:5],
    }
    experiment.params["author_map"] = {str(k): v for k, v in author_map.items()}
    experiment.params["best_params"] = best_params
    experiment.trained_model = pickle.dumps(final_estimator)
    experiment.build_status = "completed"
    experiment.save()
    logger.info(
        "ML experiment %s completed: accuracy=%.4f macro_f1=%.4f",
        experiment.id,
        experiment.accuracy,
        experiment.f1_score,
    )


def attribute_text(raw_text: str, experiment: TblAttributionExperiment) -> List[dict]:
    if not experiment.trained_model:
        raise ValueError("The selected ML experiment has no trained model.")

    estimator = pickle.loads(experiment.trained_model)
    author_map = experiment.params.get("author_map", {})
    _features, vector = extract_and_vectorize(raw_text)
    X = np.array([vector], dtype=float)

    if not hasattr(estimator, "predict_proba"):
        prediction = int(estimator.predict(X)[0])
        return [{
            "rank": 1,
            "author_id": prediction,
            "author_name": author_map.get(str(prediction), str(prediction)),
            "score": 1.0,
        }]

    probabilities = estimator.predict_proba(X)[0]
    candidates = []
    for cls, probability in zip(estimator.classes_, probabilities):
        author_id = int(cls)
        candidates.append({
            "author_id": author_id,
            "author_name": author_map.get(str(author_id), str(author_id)),
            "score": round(float(probability), 6),
        })

    candidates.sort(key=lambda item: item["score"], reverse=True)
    for rank, item in enumerate(candidates, start=1):
        item["rank"] = rank
    return candidates


def get_feature_importance(experiment: TblAttributionExperiment, top_n: int = 20) -> List[dict]:
    """
    Наиболее дискриминативные признаки завершённого ML-эксперимента.

    - Random Forest: встроенные ``feature_importances_`` (среднее снижение
      примеси), отображённые обратно на исходные имена признаков через маску
      SelectKBest.
    - SVM: F-баллы ANOVA из SelectKBest (``scores_``) как прокси
      дискриминативности, поскольку RBF-SVC не даёт пофичерных весов.

    Возвращает список ``{"feature", "importance"}``, отсортированный по
    убыванию важности (не более ``top_n`` элементов).
    """
    if not experiment or not experiment.trained_model:
        return []
    try:
        estimator = pickle.loads(experiment.trained_model)
        selector = estimator.named_steps.get("selector")
        classifier = estimator.named_steps.get("classifier")
    except Exception:
        return []

    pairs: List[dict] = []
    if classifier is not None and hasattr(classifier, "feature_importances_"):
        importances = classifier.feature_importances_
        if selector is not None and hasattr(selector, "get_support"):
            indices = selector.get_support(indices=True)
        else:
            indices = list(range(len(importances)))
        for idx, value in zip(indices, importances):
            name = FEATURE_NAMES[idx] if idx < len(FEATURE_NAMES) else str(idx)
            pairs.append({"feature": name, "importance": round(float(value), 6)})
    elif selector is not None and hasattr(selector, "scores_"):
        for idx, value in enumerate(selector.scores_):
            name = FEATURE_NAMES[idx] if idx < len(FEATURE_NAMES) else str(idx)
            pairs.append({"feature": name, "importance": round(float(np.nan_to_num(value)), 6)})
    else:
        return []

    pairs.sort(key=lambda item: item["importance"], reverse=True)
    return pairs[:top_n]
