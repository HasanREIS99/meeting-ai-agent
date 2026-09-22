"""
Language detection service (FR-004, FR-005, FR-006).

Detects the primary language of a transcript (English, Turkish, or mixed)
using the ``langdetect`` library. Falls back to simple heuristics if the
library is unavailable.
"""

from __future__ import annotations

import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)

# Heuristic patterns for Turkish vs English detection
_TURKISH_PATTERN = re.compile(
    r"[çğıöşüÇĞİÖŞÜ]"  # Turkish-specific characters
)
# Closed on BOTH sides: an opening \b alone matches word *prefixes*, so
# "is" hit Turkish "istiyorum" and "do" hit "doğru"/"dokümantasyonu",
# which was enough to call a wholly Turkish transcript "mixed".
_ENGLISH_PATTERNS = re.compile(
    r"\b(?:the|and|is|are|was|were|have|has|had|will|would|could|should"
    r"|do|does|did)\b"
)
_WORD_PATTERN = re.compile(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+")

# English function words as a share of all words, above which the text is
# taken to carry English prose rather than the odd English loanword.
_ENGLISH_MIN_SHARE = 0.05
_ENGLISH_MIN_HITS = 2


class LanguageDetector:
    """Detects the dominant language of text content."""

    def detect(self, text: str) -> str:
        """Detect the primary language of *text*.

        Args:
            text: Transcript text (already decoded from bytes).

        Returns:
            One of 'en', 'tr', or 'mixed'.
        """
        if not text.strip():
            return "en"  # safe default

        # Try langdetect first (more accurate than regex)
        try:
            from langdetect import detect, LangDetectException, lang_detect_exception
        except ImportError:
            logger.debug("langdetect not available, using regex fallback")
            return self._detect_regex(text)

        try:
            lang = detect(text)
        except LangDetectException as exc:
            logger.warning("Language detection failed: %s, using fallback", exc)
            return self._detect_regex(text)

        # langdetect returns 'en' or 'tr' for these languages
        if lang in ("en",):
            # Double-check for Turkish content
            tr_ratio = self._turkish_ratio(text)
            if tr_ratio > 0.3:
                return "mixed" if self._has_english(text) else "tr"
            return "en"
        elif lang in ("tr",):
            # Double-check for English content
            if self._has_english(text):
                return "mixed"
            return "tr"
        else:
            # Fallback: check if it's predominantly Turkish or English
            if self._turkish_ratio(text) > 0.5:
                return "tr"
            return "en"

    @staticmethod
    def _detect_regex(text: str) -> str:
        """Fallback detection using simple regex patterns."""
        tr_matches = len(_TURKISH_PATTERN.findall(text))
        en_matches = len(_ENGLISH_PATTERNS.findall(text))

        if tr_matches > 5 and en_matches == 0:
            return "tr"
        if en_matches > 3 and tr_matches == 0:
            return "en"
        if tr_matches > 0 and en_matches > 0:
            return "mixed"
        if tr_matches > en_matches:
            return "tr"
        return "en"

    @staticmethod
    def _turkish_ratio(text: str) -> float:
        """Ratio of Turkish-specific characters to total alphabetic chars."""
        turkish_chars = len(_TURKISH_PATTERN.findall(text))
        alpha_chars = len(re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]", text))
        if alpha_chars == 0:
            return 0.0
        return turkish_chars / alpha_chars

    @staticmethod
    def _has_english(text: str) -> bool:
        """Whether *text* carries English prose, not just English words.

        Measured as a share of all words rather than as an absolute
        count. A fixed ceiling scales with document length, so a long
        enough Turkish transcript crosses it on incidental matches alone
        and gets reported as "mixed" however Turkish it actually is.

        Note this counts English *function* words. Technical vocabulary
        that Turkish speakers use untranslated -- backend, endpoint,
        deployment -- is deliberately not evidence of English prose.
        """
        hits = len(_ENGLISH_PATTERNS.findall(text))
        if hits < _ENGLISH_MIN_HITS:
            return False

        words = len(_WORD_PATTERN.findall(text))
        if words == 0:
            return False

        return hits / words >= _ENGLISH_MIN_SHARE
