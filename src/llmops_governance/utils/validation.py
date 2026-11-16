"""Label validation and normalization for Banking77 intent classification.

Provides utilities to clean noisy LLM outputs, normalize labels to a
canonical form, validate against the Banking77 label set, and fuzzy-match
predictions that are close but not exact.
"""

from __future__ import annotations

import difflib
import re
import string
from typing import Final

from llmops_governance.core.constants import BANKING77_LABEL_SET, BANKING77_LABELS

__all__ = [
    "extract_label_from_response",
    "find_closest_label",
    "normalize_label",
    "validate_label",
]

_BANKING77_SET: Final[frozenset[str]] = BANKING77_LABEL_SET

# ── Pre-compiled regexes ──────────────────────────────────────────────────
_RE_NUMBERED_PREFIX = re.compile(r"^\d+[\.\)\-]\s*")
_RE_INTENT_PREFIX = re.compile(
    r"^(?:intent|label|category|class|answer|output)\s*[:=\-]\s*",
    re.IGNORECASE,
)
_RE_THE_INTENT_IS = re.compile(
    r"^(?:the\s+)?(?:intent|label|category|predicted\s+intent)\s+(?:is|was|should\s+be)\s+",
    re.IGNORECASE,
)
_RE_QUOTES = re.compile(r"[\"'`" "'']")
_RE_PUNCTUATION_EXCEPT_UNDERSCORE = re.compile(
    rf"[{re.escape(string.punctuation.replace('_', ''))}]"
)


def normalize_label(label: str) -> str:
    """Normalize a predicted label to its canonical form.

    The normalization pipeline:
    1. Strip leading / trailing whitespace.
    2. Remove surrounding quotes and backticks.
    3. Remove common LLM artifacts (``"Intent: "``, numbered prefixes, etc.).
    4. Lowercase.
    5. Replace whitespace / hyphens with underscores.
    6. Remove all punctuation except underscores.
    7. Collapse consecutive underscores and strip leading / trailing ones.

    Args:
        label: Raw predicted label string from an LLM or classifier.

    Returns:
        Cleaned, lowercased, underscore-separated label string.
    """
    text = label.strip()

    # Remove surrounding quotes / backticks
    text = _RE_QUOTES.sub("", text)
    text = text.strip()

    # Strip common prefixes like "Intent: ", "1. ", "1) "
    text = _RE_NUMBERED_PREFIX.sub("", text)
    text = _RE_INTENT_PREFIX.sub("", text)
    text = _RE_THE_INTENT_IS.sub("", text)
    text = text.strip()

    # Lowercase
    text = text.lower()

    # Replace whitespace and hyphens with underscores
    text = re.sub(r"[\s\-]+", "_", text)

    # Remove all punctuation except underscores
    text = _RE_PUNCTUATION_EXCEPT_UNDERSCORE.sub("", text)

    # Collapse underscores and strip boundary underscores
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def validate_label(
    label: str,
    valid_labels: list[str] | None = None,
) -> bool:
    """Check whether *label* (after normalisation) is a valid Banking77 intent.

    Args:
        label: The label to validate (will be normalised first).
        valid_labels: Optional override for the valid label set.  If ``None``,
            the default :data:`BANKING77_LABELS` set is used.

    Returns:
        ``True`` if the normalised label is in the valid set, ``False``
        otherwise.
    """
    normalised = normalize_label(label)
    allowed = frozenset(valid_labels) if valid_labels is not None else _BANKING77_SET
    return normalised in allowed


def find_closest_label(
    prediction: str,
    valid_labels: list[str] | None = None,
    threshold: float = 0.8,
) -> str | None:
    """Find the closest valid label for a potentially misspelled prediction.

    Uses :func:`difflib.get_close_matches` with the given *threshold*
    (``cutoff`` parameter).

    Args:
        prediction: The (possibly noisy) predicted label.  Normalised
            internally before matching.
        valid_labels: Optional override for the valid label set.
        threshold: Minimum similarity ratio in ``[0, 1]``.  Defaults to
            0.8.

    Returns:
        The closest matching label, or ``None`` if no match meets the
        threshold.
    """
    normalised = normalize_label(prediction)
    candidates = list(valid_labels) if valid_labels is not None else BANKING77_LABELS

    # Exact match short-circuit
    if normalised in frozenset(candidates):
        return normalised

    matches = difflib.get_close_matches(
        normalised,
        candidates,
        n=1,
        cutoff=threshold,
    )
    return matches[0] if matches else None


def extract_label_from_response(response: str) -> str:
    """Extract an intent label from a potentially noisy LLM response.

    Handles common response formats produced by language models:

    * Plain label: ``"card_arrival"``
    * Prefixed:    ``"Intent: card_arrival"``
    * Sentence:    ``"The intent is card_arrival."``
    * Numbered:    ``"1. card_arrival"``
    * Quoted:      ``'"card_arrival"'``
    * Multi-line:  picks the first non-empty line that looks like a label.

    Args:
        response: Raw text output from an LLM.

    Returns:
        A normalised label string extracted from the response.  May not
        be a valid Banking77 label—call :func:`validate_label` or
        :func:`find_closest_label` afterwards.
    """
    text = response.strip()

    # If the response has multiple lines, try each line and pick the first
    # one that validates, otherwise fall back to the first non-empty line.
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if len(lines) > 1:
        # Prefer the first line that directly validates
        for line in lines:
            candidate = normalize_label(line)
            if candidate in _BANKING77_SET:
                return candidate
        # Fall back to normalising the first line
        text = lines[0]

    return normalize_label(text)
