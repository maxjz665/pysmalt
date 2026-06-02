import logging
from typing import Dict, Iterable, List, Tuple, Union

import numpy as np

from research.authorship.models import (
    TblAttributionExperiment,
    TblAttributionResult,
    TblAuthorProfile,
    TblSyntacticFeature,
)
from research.authorship.utils.features import (
    FEATURE_BLOCKS,
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

# Веса блоков признаков, подобранные эмпирически (LOO на корпусах SMALT).
# Равномерное взвешивание устойчиво превосходит ручную настройку, а блок
# синтаксических продукций (7-й) оказался избыточным (дублирует типы
# зависимостей и POS-биграммы) и исключён из метрики (вес 0).
BLOCK_WEIGHTS = (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0)


def _block_slices() -> Tuple[slice, ...]:
    start = 0
    slices = []
    for size in FEATURE_BLOCKS:
        stop = start + size
        slices.append(slice(start, stop))
        start = stop
    return tuple(slices)


BLOCK_SLICES = _block_slices()


def _resolve_text_list(text_list: Union[int, TblTextListDescription]) -> TblTextListDescription:
    if isinstance(text_list, TblTextListDescription):
        return text_list
    return TblTextListDescription.objects.get(id=int(text_list))


def _list_text_author_pairs(text_list: TblTextListDescription) -> List[Tuple[TblText, TblAuthor]]:
    items = (
        TblTextListItems.objects
        .filter(list=text_list)
        .select_related("text", "text__author")
        .order_by("text_id")
    )
    return [(item.text, item.text.author) for item in items if item.text.author_id]


def _feature_vector_for_text(text: TblText, extract_missing: bool = True) -> np.ndarray:
    try:
        sf = TblSyntacticFeature.objects.get(text=text)
    except TblSyntacticFeature.DoesNotExist:
        if not extract_missing:
            raise FeatureExtractionError(
                f"Text {text.id} has no stored authorship features. "
                "Run with --extract-features first."
            )
        sf = extract_and_save_features(text)

    vector = sf.vector or sf.feature_vector
    if len(vector) != VECTOR_SIZE:
        raise FeatureExtractionError(
            f"Text {text.id} has vector size {len(vector)}, expected {VECTOR_SIZE}."
        )
    return np.array(vector, dtype=float)


def _normalize_fold(train_matrix: np.ndarray, test_vec: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    mean = train_matrix.mean(axis=0)
    std = train_matrix.std(axis=0)
    std[std == 0.0] = 1.0
    return (train_matrix - mean) / std, (test_vec - mean) / std


def _normalize_with_stats(vec: np.ndarray, mean: Iterable[float], std: Iterable[float]) -> np.ndarray:
    mean_arr = np.array(list(mean), dtype=float)
    std_arr = np.array(list(std), dtype=float)
    std_arr[std_arr == 0.0] = 1.0
    return (vec - mean_arr) / std_arr


def _apply_block_weights(vec: np.ndarray) -> np.ndarray:
    weighted = vec.copy().astype(float)
    for block_slice, weight in zip(BLOCK_SLICES, BLOCK_WEIGHTS):
        weighted[block_slice] *= weight
    return weighted


def _build_profile(vecs: List[np.ndarray], aggregation: str = "median") -> np.ndarray:
    matrix = np.array(vecs, dtype=float)
    if aggregation == "mean":
        return matrix.mean(axis=0)
    return np.median(matrix, axis=0)


def manhattan_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sum(np.abs(a - b)))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _distance_or_score(test_vec: np.ndarray, profile_vec: np.ndarray, metric: str) -> Tuple[float, float]:
    if metric == "manhattan":
        distance = manhattan_distance(test_vec, profile_vec)
        return distance, 1.0 / (1.0 + distance)
    if metric == "cosine":
        similarity = cosine_similarity(test_vec, profile_vec)
        return 1.0 - similarity, similarity
    raise ValueError(f"Unsupported profile metric: {metric}")


def _calculate_metrics(
    results: List[Tuple[int, int]],
    author_ids: List[int],
) -> Tuple[dict, List[List[int]], dict]:
    total = len(results)
    correct = sum(1 for true_id, pred_id in results if true_id == pred_id)
    accuracy = correct / total if total else 0.0

    matrix_index = {author_id: index for index, author_id in enumerate(author_ids)}
    matrix = [[0 for _ in author_ids] for _ in author_ids]
    for true_id, pred_id in results:
        if true_id in matrix_index and pred_id in matrix_index:
            matrix[matrix_index[true_id]][matrix_index[pred_id]] += 1

    by_author = {}
    precisions = []
    recalls = []
    f1_values = []

    for author_id in author_ids:
        idx = matrix_index[author_id]
        tp = matrix[idx][idx]
        fp = sum(matrix[row][idx] for row in range(len(author_ids)) if row != idx)
        fn = sum(matrix[idx][col] for col in range(len(author_ids)) if col != idx)
        support = sum(matrix[idx])

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

        precisions.append(precision)
        recalls.append(recall)
        f1_values.append(f1)
        by_author[str(author_id)] = {
            "correct": int(tp),
            "total": int(support),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1": round(float(f1), 4),
        }

    metrics = {
        "accuracy": round(float(accuracy), 4),
        "macro_precision": round(float(np.mean(precisions)) if precisions else 0.0, 4),
        "macro_recall": round(float(np.mean(recalls)) if recalls else 0.0, 4),
        "macro_f1": round(float(np.mean(f1_values)) if f1_values else 0.0, 4),
        "n_texts": total,
        "n_authors": len(author_ids),
    }
    return metrics, matrix, by_author


def build_all_profiles(text_list: Union[int, TblTextListDescription]) -> List[TblAuthorProfile]:
    text_list = _resolve_text_list(text_list)
    pairs = _list_text_author_pairs(text_list)
    if not pairs:
        raise ValueError(f"Text list {text_list.id} has no texts with authors.")

    vectors = {text.id: _feature_vector_for_text(text) for text, _author in pairs}
    matrix = np.array([vectors[text.id] for text, _author in pairs], dtype=float)
    mean = matrix.mean(axis=0)
    std = matrix.std(axis=0)
    std[std == 0.0] = 1.0

    author_vectors: Dict[int, List[np.ndarray]] = {}
    for text, author in pairs:
        normalized = (vectors[text.id] - mean) / std
        weighted = _apply_block_weights(normalized)
        author_vectors.setdefault(author.id, []).append(weighted)

    profiles = []
    for author_id, vecs in author_vectors.items():
        author = TblAuthor.objects.get(id=author_id)
        profile_vec = _build_profile(vecs, aggregation="median")
        profile, _created = TblAuthorProfile.objects.update_or_create(
            author=author,
            text_list=text_list,
            defaults={
                "texts_count": len(vecs),
                "profile_vector": profile_vec.tolist(),
                "method": "profile",
                "profile_data": {
                    "aggregation": "median",
                    "normalization": "corpus z-score",
                    "block_weights": list(BLOCK_WEIGHTS),
                    "feature_names": FEATURE_NAMES,
                    "mean": mean.tolist(),
                    "std": std.tolist(),
                },
            },
        )
        profiles.append(profile)
    return profiles


def build_author_profile(author: TblAuthor, text_list: Union[int, TblTextListDescription]) -> TblAuthorProfile:
    text_list = _resolve_text_list(text_list)
    profile = TblAuthorProfile.objects.filter(author=author, text_list=text_list).first()
    if profile:
        return profile
    build_all_profiles(text_list)
    return TblAuthorProfile.objects.get(author=author, text_list=text_list)


def run_experiment(
    text_list: Union[int, TblTextListDescription],
    metric: str = "manhattan",
    n_folds: int = 0,
    name: str = "",
    owner=None,
    extract_features: bool = True,
) -> TblAttributionExperiment:
    text_list = _resolve_text_list(text_list)
    if metric != "manhattan":
        logger.warning("Profile method is report-aligned for Manhattan; got metric=%s", metric)

    experiment = TblAttributionExperiment.objects.create(
        name=name or f"Profile ({metric}) - {text_list.name}",
        method="profile",
        metric=metric,
        text_list=text_list,
        owner=owner,
        params={
            "metric": metric,
            "cv": "leave-one-out",
            "aggregation": "median",
            "normalization": "fold-wise z-score",
            "block_weights": list(BLOCK_WEIGHTS),
            "vector_size": VECTOR_SIZE,
        },
        build_status="running",
    )

    try:
        pairs = _list_text_author_pairs(text_list)
        author_ids = sorted({author.id for _text, author in pairs})
        if len(pairs) < 3 or len(author_ids) < 2:
            raise ValueError("Need at least 3 texts and 2 authors for profile attribution.")

        vectors = {
            text.id: _feature_vector_for_text(text, extract_missing=extract_features)
            for text, _author in pairs
        }

        predictions: List[Tuple[int, int]] = []
        author_names = {author.id: author.name for _text, author in pairs}

        for test_text, true_author in pairs:
            train_pairs = [(text, author) for text, author in pairs if text.id != test_text.id]
            train_matrix = np.array([vectors[text.id] for text, _author in train_pairs], dtype=float)
            train_norm, test_norm = _normalize_fold(train_matrix, vectors[test_text.id])
            train_weighted = [_apply_block_weights(vec) for vec in train_norm]
            test_weighted = _apply_block_weights(test_norm)

            fold_author_vectors: Dict[int, List[np.ndarray]] = {}
            for (_text, author), vector in zip(train_pairs, train_weighted):
                fold_author_vectors.setdefault(author.id, []).append(vector)

            fold_profiles = {
                author_id: _build_profile(vecs, aggregation="median")
                for author_id, vecs in fold_author_vectors.items()
                if vecs
            }
            distances = {
                author_id: _distance_or_score(test_weighted, profile_vec, metric)[0]
                for author_id, profile_vec in fold_profiles.items()
            }
            similarities = {
                author_id: _distance_or_score(test_weighted, profile_vec, metric)[1]
                for author_id, profile_vec in fold_profiles.items()
            }
            if not distances:
                raise ValueError(f"Fold for text {test_text.id} has no author profiles.")

            predicted_id = min(distances, key=distances.get)
            predictions.append((true_author.id, predicted_id))
            predicted_author = TblAuthor.objects.get(id=predicted_id)

            TblAttributionResult.objects.create(
                experiment=experiment,
                text=test_text,
                true_author=true_author,
                predicted_author=predicted_author,
                confidence=round(float(similarities[predicted_id]), 6),
                scores={
                    str(author_id): {
                        "author": author_names.get(author_id, str(author_id)),
                        "distance": round(float(distance), 6),
                        "similarity": round(float(similarities[author_id]), 6),
                    }
                    for author_id, distance in distances.items()
                },
                is_correct=(true_author.id == predicted_id),
            )

        metrics, confusion_matrix, by_author = _calculate_metrics(predictions, author_ids)
        for author_id, values in by_author.items():
            values["name"] = author_names.get(int(author_id), author_id)

        experiment.accuracy = metrics["accuracy"]
        experiment.precision = metrics["macro_precision"]
        experiment.recall = metrics["macro_recall"]
        experiment.f1_score = metrics["macro_f1"]
        experiment.metrics = metrics
        experiment.confusion_matrix = confusion_matrix
        experiment.detailed_results = {
            "by_author": by_author,
            "author_labels": [
                {"id": author_id, "name": author_names.get(author_id, str(author_id))}
                for author_id in author_ids
            ],
        }
        experiment.build_status = "completed"
        experiment.save()

        build_all_profiles(text_list)
        logger.info(
            "Profile experiment %s completed: accuracy=%.4f macro_f1=%.4f",
            experiment.id,
            experiment.accuracy,
            experiment.f1_score,
        )
    except Exception as exc:
        logger.exception("Profile experiment failed")
        experiment.build_status = "failed"
        experiment.error_message = str(exc)
        experiment.save(update_fields=["build_status", "error_message"])

    return experiment


def execute_existing_experiment(experiment: TblAttributionExperiment) -> None:
    """
    Run a profile experiment that has already been persisted (called by the worker).
    Raises on failure — the worker handles build_status and error_message.
    """
    text_list = experiment.text_list
    metric = experiment.params.get("metric", "manhattan")
    extract_features = experiment.params.get("extract_features", False)

    pairs = _list_text_author_pairs(text_list)
    author_ids = sorted({author.id for _text, author in pairs})
    if len(pairs) < 3 or len(author_ids) < 2:
        raise ValueError("Need at least 3 texts and 2 authors for profile attribution.")

    vectors = {
        text.id: _feature_vector_for_text(text, extract_missing=extract_features)
        for text, _author in pairs
    }

    predictions: List[Tuple[int, int]] = []
    author_names = {author.id: author.name for _text, author in pairs}

    for test_text, true_author in pairs:
        train_pairs = [(text, author) for text, author in pairs if text.id != test_text.id]
        train_matrix = np.array([vectors[text.id] for text, _author in train_pairs], dtype=float)
        train_norm, test_norm = _normalize_fold(train_matrix, vectors[test_text.id])
        train_weighted = [_apply_block_weights(vec) for vec in train_norm]
        test_weighted = _apply_block_weights(test_norm)

        fold_author_vectors: Dict[int, List[np.ndarray]] = {}
        for (_text, author), vector in zip(train_pairs, train_weighted):
            fold_author_vectors.setdefault(author.id, []).append(vector)

        fold_profiles = {
            author_id: _build_profile(vecs, aggregation="median")
            for author_id, vecs in fold_author_vectors.items()
            if vecs
        }
        distances = {
            author_id: _distance_or_score(test_weighted, profile_vec, metric)[0]
            for author_id, profile_vec in fold_profiles.items()
        }
        similarities = {
            author_id: _distance_or_score(test_weighted, profile_vec, metric)[1]
            for author_id, profile_vec in fold_profiles.items()
        }
        if not distances:
            raise ValueError(f"Fold for text {test_text.id} has no author profiles.")

        predicted_id = min(distances, key=distances.get)
        predictions.append((true_author.id, predicted_id))
        predicted_author = TblAuthor.objects.get(id=predicted_id)

        TblAttributionResult.objects.create(
            experiment=experiment,
            text=test_text,
            true_author=true_author,
            predicted_author=predicted_author,
            confidence=round(float(similarities[predicted_id]), 6),
            scores={
                str(author_id): {
                    "author": author_names.get(author_id, str(author_id)),
                    "distance": round(float(distance), 6),
                    "similarity": round(float(similarities[author_id]), 6),
                }
                for author_id, distance in distances.items()
            },
            is_correct=(true_author.id == predicted_id),
        )

    metrics, confusion_matrix, by_author = _calculate_metrics(predictions, author_ids)
    for author_id, values in by_author.items():
        values["name"] = author_names.get(int(author_id), author_id)

    experiment.accuracy = metrics["accuracy"]
    experiment.precision = metrics["macro_precision"]
    experiment.recall = metrics["macro_recall"]
    experiment.f1_score = metrics["macro_f1"]
    experiment.metrics = metrics
    experiment.confusion_matrix = confusion_matrix
    experiment.detailed_results = {
        "by_author": by_author,
        "author_labels": [
            {"id": author_id, "name": author_names.get(author_id, str(author_id))}
            for author_id in author_ids
        ],
    }
    experiment.build_status = "completed"
    experiment.save()

    build_all_profiles(text_list)
    logger.info(
        "Profile experiment %s completed: accuracy=%.4f macro_f1=%.4f",
        experiment.id,
        experiment.accuracy,
        experiment.f1_score,
    )


def attribute_text(
    raw_text: str,
    text_list: Union[int, TblTextListDescription],
    metric: str = "manhattan",
) -> List[dict]:
    text_list = _resolve_text_list(text_list)
    _features, vector = extract_and_vectorize(raw_text)
    raw_vec = np.array(vector, dtype=float)

    profiles = list(TblAuthorProfile.objects.filter(text_list=text_list).select_related("author"))
    if not profiles:
        profiles = build_all_profiles(text_list)

    reference = profiles[0].profile_data
    mean = reference.get("mean")
    std = reference.get("std")
    if not mean or not std:
        profiles = build_all_profiles(text_list)
        reference = profiles[0].profile_data
        mean = reference["mean"]
        std = reference["std"]

    test_vec = _apply_block_weights(_normalize_with_stats(raw_vec, mean, std))
    candidates = []
    for profile in profiles:
        profile_vec = np.array(profile.profile_vector, dtype=float)
        distance, similarity = _distance_or_score(test_vec, profile_vec, metric)
        candidates.append({
            "author": profile.author,
            "author_id": profile.author_id,
            "author_name": profile.author.name,
            "score": round(float(similarity), 6),
            "distance": round(float(distance), 6),
            "texts_in_profile": profile.texts_count,
        })

    candidates.sort(key=lambda item: (item["distance"], -item["score"]))
    for rank, item in enumerate(candidates, start=1):
        item["rank"] = rank
    return candidates


# ── Fragment attribution helpers ──────────────────────────────────────────────

_NO_PROFILE_MSG = (
    "Для выбранного списка не найдены признаки/профили. "
    "Сначала извлеките признаки или запустите профильный эксперимент."
)


def prepare_profile_attribution_context(
    text_list: Union[int, TblTextListDescription],
    metric: str = "manhattan",
) -> dict:
    """
    Load and pre-process author profiles for fragment attribution.

    Performs all DB queries and numpy conversions *once* so that the caller
    (attribute_fragments) can reuse the result for every fragment without
    hitting the database again.

    Returns a context dict suitable for attribute_raw_text_with_context().

    Raises:
        ValueError: If profiles or normalisation stats are missing/incomplete.
    """
    text_list = _resolve_text_list(text_list)

    profiles = list(TblAuthorProfile.objects.filter(text_list=text_list).select_related("author"))
    if not profiles:
        try:
            profiles = build_all_profiles(text_list)
        except Exception as exc:
            raise ValueError(_NO_PROFILE_MSG) from exc

    if not profiles:
        raise ValueError(_NO_PROFILE_MSG)

    reference = profiles[0].profile_data
    mean = reference.get("mean")
    std = reference.get("std")
    if not mean or not std:
        try:
            profiles = build_all_profiles(text_list)
        except Exception as exc:
            raise ValueError(_NO_PROFILE_MSG) from exc
        reference = profiles[0].profile_data
        mean = reference.get("mean")
        std = reference.get("std")

    if not mean or not std:
        raise ValueError(_NO_PROFILE_MSG)

    mean_arr = np.array(list(mean), dtype=float)
    std_arr = np.array(list(std), dtype=float)
    std_arr[std_arr == 0.0] = 1.0

    profile_entries = [
        {
            "author_id": p.author_id,
            "author_name": p.author.name,
            "texts_in_profile": p.texts_count,
            "profile_vec": np.array(p.profile_vector, dtype=float),
        }
        for p in profiles
    ]

    return {
        "text_list": text_list,
        "metric": metric,
        "mean": mean_arr,
        "std": std_arr,
        "profiles": profile_entries,
    }


def attribute_raw_text_with_context(raw_text: str, context: dict) -> List[dict]:
    """
    Attribute a single raw text string using a pre-built profile context.

    Unlike attribute_text(), this function does *no* DB access — all profile
    data was already loaded by prepare_profile_attribution_context().  Used by
    attribute_fragments() to avoid re-loading profiles for each fragment.

    Args:
        raw_text: Fragment text to attribute.
        context:  Dict returned by prepare_profile_attribution_context().

    Returns:
        Ranked list of candidate dicts: {author_id, author_name, score, distance,
        texts_in_profile, rank}.
    """
    _features, vector = extract_and_vectorize(raw_text)
    raw_vec = np.array(vector, dtype=float)

    mean_arr: np.ndarray = context["mean"]
    std_arr: np.ndarray = context["std"]
    metric: str = context["metric"]
    profile_entries: list = context["profiles"]

    test_vec = _apply_block_weights((raw_vec - mean_arr) / std_arr)

    candidates = []
    for entry in profile_entries:
        distance, similarity = _distance_or_score(test_vec, entry["profile_vec"], metric)
        candidates.append({
            "author_id": entry["author_id"],
            "author_name": entry["author_name"],
            "score": round(float(similarity), 6),
            "distance": round(float(distance), 6),
            "texts_in_profile": entry["texts_in_profile"],
        })

    candidates.sort(key=lambda item: (item["distance"], -item["score"]))
    for rank, item in enumerate(candidates, start=1):
        item["rank"] = rank
    return candidates
