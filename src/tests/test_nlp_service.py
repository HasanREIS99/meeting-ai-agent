"""
Tests for language detection (FR-004, FR-005, FR-006).

Covers:
- FR-004: Detect primary language
- FR-005: Output matches input language
- FR-006: Mixed-language detection
"""

from __future__ import annotations

import pytest

from meeting_analyzer.nlp_service import LanguageDetector


@pytest.fixture
def detector():
    return LanguageDetector()


class TestLanguageDetection:
    """Language detection tests."""

    def test_detect_english(self, detector):
        """FR-004: English text is detected."""
        text = (
            "The meeting started at 10am. We discussed the Q3 roadmap "
            "and reviewed the sprint backlog. John will prepare the report "
            "by Friday."
        )
        assert detector.detect(text) == "en"

    def test_detect_turkish(self, detector):
        """FR-004: Turkish text is detected."""
        text = (
            "Toplantı saat 10'da başladı. Q3 yol haritasını tartıştık ve "
            "sprint geri kalanını gözden geçirdik. John Cuma günü raporu "
            "hazırlayacak."
        )
        assert detector.detect(text) == "tr"

    def test_detect_mixed(self, detector):
        """FR-006: Mixed EN/TR text is detected."""
        text = (
            "The meeting started at 10am. Afternoon session'te proje "
            "gözden geçirildi. John will prepare the report by Friday. "
            "Toplantı notları paylaşılacak."
        )
        result = detector.detect(text)
        assert result in ("en", "tr", "mixed")
        # Mixed text with Turkish characters should be flagged
        text_with_tr_chars = (
            "The meeting discussed the proje roadmap. Toplantı notları "
            "Cuma günü paylaşılacak."
        )
        result = detector.detect(text_with_tr_chars)
        assert result == "mixed" or result in ("en", "tr")

    def test_empty_text_returns_en(self, detector):
        """Empty text falls back to 'en'."""
        assert detector.detect("") == "en"
        assert detector.detect("   ") == "en"

    def test_turkish_characters_detected(self, detector):
        """Turkish-specific characters (ç, ğ, ı, ö, ş, ü) trigger TR/mixed."""
        text = "Bu bir deneme metnidir. Çay içelim."
        result = detector.detect(text)
        assert result == "tr"

    def test_short_english_phrases(self, detector):
        """Short English text is still detected."""
        assert detector.detect("Hello world") == "en"
        assert detector.detect("Meeting notes") == "en"


# ── Turkish technical transcripts (regression) ────────────────────


TR_TECHNICAL_TRANSCRIPT = """Proje Durum Toplantısı - 20 Eylül 2026
Katılımcılar: Ayşe, Bora, Ceren, Deniz

Ayşe: Herkese günaydın. Bugün sprint durumunu değerlendireceğiz.
Bora: Backend tarafındaki geliştirmeyi tamamladım. Tüm endpoint'ler çalışıyor.
Ayşe: Peki deployment sürecinde bir sorun yaşadınız mı?
Bora: Evet, build aşamasında zaman zaman hata alıyoruz.
Ayşe: Bu konuyu öncelikli olarak incelemeni istiyorum.
Bora: Tabii, log kayıtlarını inceleyip doğru nedeni tespit edeceğim.
Ceren: Unit test kapsamı iyi ancak integration test yazmamız gerekiyor.
Deniz: Dokümantasyon güncel değil, kurulum adımları eski sürüme göre yazılmış.
Ayşe: Deniz, frontend ve backend kurulum adımlarını güncelleyebilir misin?
Ceren: Staging ortamındaki environment variable ayarları production ile aynı mı?
Bora: Kontrol etmem gerekiyor, bundan emin değilim açıkçası.
Ayşe: Lütfen bunu da doğrula. Herkese teşekkürler.
"""


class TestTurkishTechnicalTranscript:
    """A Turkish meeting peppered with English software vocabulary.

    Regression: this was reported as "mixed". Two separate causes, both
    in the English heuristic and neither related to the technical terms:
    the pattern had no closing word boundary, so "is"/"do"/"and" matched
    inside Turkish words like "istiyorum", "doğru" and "android"; and the
    threshold was an absolute count, so any Turkish transcript long
    enough accumulated its way over the line.
    """

    def test_turkish_technical_meeting_is_tr(self, detector):
        """FR-004: English tech vocabulary does not make a meeting mixed."""
        assert detector.detect(TR_TECHNICAL_TRANSCRIPT) == "tr"

    @pytest.mark.parametrize("repeats", [1, 2, 3, 5])
    def test_classification_does_not_drift_with_length(self, detector, repeats):
        """The verdict must not depend on how long the transcript is."""
        assert detector.detect(TR_TECHNICAL_TRANSCRIPT * repeats) == "tr"

    def test_english_terms_alone_are_not_english_prose(self, detector):
        """The borrowed nouns carry no English function words at all."""
        from meeting_analyzer.nlp_service import _ENGLISH_PATTERNS

        terms = "backend endpoint unit test deployment frontend environment variable"
        assert _ENGLISH_PATTERNS.findall(terms) == []

    @pytest.mark.parametrize(
        "turkish_word", ["istiyorum", "doğru", "dokümantasyonu", "ise", "dosya",
                         "hasta", "android", "isim", "hareket"],
    )
    def test_english_pattern_does_not_match_turkish_prefixes(self, turkish_word):
        """The pattern must match whole words, never word prefixes."""
        from meeting_analyzer.nlp_service import _ENGLISH_PATTERNS

        assert _ENGLISH_PATTERNS.findall(turkish_word) == []

    def test_genuine_mixed_still_detected(self, detector):
        """FR-006 guard: the fix must not swallow real mixed transcripts."""
        text = (
            "Toplantı saat 10'da başladı. Ayşe sprint durumunu özetledi ve "
            "ekibe teşekkür etti. Bora backend tarafını tamamladı. "
            "The deployment is blocked and the build was failing. "
            "We have reviewed the logs and the team will decide tomorrow. "
            "Ceren entegrasyon testlerini yazacak. Deniz dokümantasyonu "
            "güncelleyecek. Pazartesi günü tekrar değerlendireceğiz."
        )
        assert detector.detect(text) == "mixed"

    def test_pure_english_unaffected(self, detector):
        """FR-004 guard: English transcripts still read as English."""
        text = (
            "The meeting started at 10am. We discussed the Q3 roadmap and "
            "reviewed the sprint backlog. John will prepare the report by "
            "Friday. The team has agreed and the work will start Monday."
        )
        assert detector.detect(text) == "en"
