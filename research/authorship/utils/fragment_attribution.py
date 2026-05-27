"""
Fragment attribution: split raw text into fragments and attribute each one
using the existing profile method.

No ML, no TblText records, purely in-memory analysis.

Optimisation: author profiles (mean/std normalization stats and profile
vectors) are loaded from the DB *once* per attribute_fragments() call and
reused for every fragment, avoiding redundant DB queries.
"""
import re
from typing import Callable, List, Tuple

_MAX_FRAGMENTS_DEFAULT = 100


def attribute_fragments(
    raw_text: str,
    text_list,
    mode: str = "word_window",
    window_words: int = 300,
    step_words: int = 150,
    min_words_warn: int = 150,
    metric: str = "manhattan",
    max_fragments: int = _MAX_FRAGMENTS_DEFAULT,
) -> List[dict]:
    """
    Split raw_text into fragments and attribute each using the profile method.

    Author profiles are loaded from the DB **once** for the entire call and
    reused for every fragment — no per-fragment DB queries.

    Trailing partial windows (word_window mode) are always included and
    marked reliable=False when shorter than min_words_warn, so the user sees
    that the full text was processed.

    Args:
        raw_text:       Source text to split and attribute.
        text_list:      TblTextListDescription instance or id — defines the
                        author profiles to compare against.
        mode:           "word_window" (sliding window) or "paragraphs".
        window_words:   Window size in words (word_window mode).
        step_words:     Step size in words (word_window mode).
        min_words_warn: Fragments shorter than this are marked reliable=False.
        metric:         "manhattan" or "cosine".
        max_fragments:  Hard upper limit; raises ValueError if exceeded so that
                        the user knows to increase window/step instead of
                        silently generating a partial result.

    Returns:
        List of dicts, one per fragment:
            index             int   (1-based)
            start_word        int   word offset (0-based) for word_window;
                                    paragraph index for paragraphs
            end_word          int   exclusive end
            preview           str   first 120 chars + "…"
            word_count        int
            predicted_author  str   name of top candidate, or "—"
            scores            list  of {author, distance, score} — top-3
            reliable          bool  (word_count >= min_words_warn)
            warning           str   empty if reliable

    Raises:
        ValueError: On invalid inputs, too many fragments, or missing profiles.
    """
    # ── Validation ────────────────────────────────────────────
    if not raw_text or not raw_text.strip():
        raise ValueError("Text must not be empty.")
    if window_words < 1:
        raise ValueError("window_words must be >= 1.")
    if step_words < 1:
        raise ValueError("step_words must be >= 1.")
    if min_words_warn < 1:
        raise ValueError("min_words_warn must be >= 1.")
    if max_fragments < 1:
        raise ValueError("max_fragments must be >= 1.")
    if mode not in ("word_window", "paragraphs"):
        raise ValueError(f"Unknown mode: {mode!r}. Use 'word_window' or 'paragraphs'.")

    # ── Split into segments (no attribution yet) ───────────────
    # Splitting is cheap; we check max_fragments *before* the expensive
    # profile context load and Natasha/spacy parsing.
    segments = _split_into_segments(raw_text, mode, window_words, step_words)

    if len(segments) > max_fragments:
        raise ValueError(
            f"Слишком много фрагментов ({len(segments)}). "
            f"Увеличьте размер окна или шаг "
            f"(текущий лимит: {max_fragments})."
        )

    if not segments:
        return []

    # ── Load profile context ONCE ─────────────────────────────
    from research.authorship.utils.profile_method import (
        prepare_profile_attribution_context,
        attribute_raw_text_with_context,
    )
    # prepare_profile_attribution_context raises ValueError with a user-friendly
    # message when profiles or stats are missing — let it propagate as-is.
    ctx = prepare_profile_attribution_context(text_list, metric)

    # ── Attribute each fragment using the pre-built context ────
    results = []
    for index, (start, end, fragment_text) in enumerate(segments, start=1):
        result = _make_fragment_result_with_context(
            index=index,
            start_word=start,
            end_word=end,
            fragment_text=fragment_text,
            ctx=ctx,
            attribute_fn=attribute_raw_text_with_context,
            min_words_warn=min_words_warn,
        )
        results.append(result)
    return results


# ── Splitting helpers ──────────────────────────────────────────────────────────

def _split_into_segments(
    raw_text: str,
    mode: str,
    window_words: int,
    step_words: int,
) -> List[Tuple[int, int, str]]:
    """Dispatch to the appropriate splitter. Returns (start, end, text) tuples."""
    if mode == "paragraphs":
        return _split_paragraphs(raw_text)
    return _split_word_window(raw_text, window_words, step_words)


def _split_paragraphs(raw_text: str) -> List[Tuple[int, int, str]]:
    """Split by blank lines; skip empty paragraphs."""
    segments: List[Tuple[int, int, str]] = []
    para_num = 0
    for paragraph in re.split(r'\n{2,}', raw_text):
        stripped = paragraph.strip()
        if stripped:
            segments.append((para_num, para_num + 1, stripped))
            para_num += 1
    return segments


def _split_word_window(
    raw_text: str,
    window_words: int,
    step_words: int,
) -> List[Tuple[int, int, str]]:
    """
    Sliding word-window tokenization.

    All windows including the trailing partial window are returned.
    Short trailing fragments will be marked unreliable by the caller so the
    user can see that the full text was analysed.
    """
    words = raw_text.split()
    if not words:
        return []

    # Entire text fits in a single window
    if len(words) <= window_words:
        return [(0, len(words), " ".join(words))]

    segments: List[Tuple[int, int, str]] = []
    start = 0
    while start < len(words):
        end = min(start + window_words, len(words))
        segments.append((start, end, " ".join(words[start:end])))
        start += step_words
    return segments


# ── Attribution helper ─────────────────────────────────────────────────────────

def _make_fragment_result_with_context(
    index: int,
    start_word: int,
    end_word: int,
    fragment_text: str,
    ctx: dict,
    attribute_fn: Callable,
    min_words_warn: int,
) -> dict:
    """
    Attribute a single fragment using a pre-built profile context dict.

    Does *not* access the DB — all profile data is already in ctx.
    """
    word_count = len(fragment_text.split())
    reliable = word_count >= min_words_warn
    warning = "Фрагмент короткий, результат может быть неустойчивым." if not reliable else ""
    preview = fragment_text[:120] + ("…" if len(fragment_text) > 120 else "")

    candidates = attribute_fn(fragment_text, ctx)
    top = candidates[0] if candidates else None

    return {
        "index": index,
        "start_word": start_word,
        "end_word": end_word,
        "preview": preview,
        "word_count": word_count,
        "predicted_author": top["author_name"] if top else "—",
        "scores": [
            {
                "author": c["author_name"],
                "distance": round(c["distance"], 4),
                "score": round(c["score"], 4),
            }
            for c in candidates[:3]
        ],
        "reliable": reliable,
        "warning": warning,
    }
