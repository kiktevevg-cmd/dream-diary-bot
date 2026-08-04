import pytest

from app.utils.stop_words import ESOTERIC_STOP_WORDS
from app.utils.validators import (
    extract_json_from_text,
    find_stop_words,
    validate_interpretation,
)

VALID_JSON = """{
  "key_images": ["лес", "мост", "вода"],
  "emotional_focus": "тревога",
  "interpretation": "Сон с лесом и мостом может отражать внутренний переход и неопределённость в жизни. Образ воды часто связан с эмоциональным состоянием. Тревога во сне может указывать на неосознанные переживания, связанные с предстоящими изменениями.",
  "associations_question": "Что для вас означает мост в повседневной жизни?",
  "reflection_question": "Какие изменения сейчас происходят в вашей жизни?",
  "potential_triggers": ["стресс на работе", "отношения", "переезд"],
  "tags": ["переход", "тревога", "изменения"]
}"""

ESOTERIC_JSON = """{
  "key_images": ["ангел", "свет"],
  "emotional_focus": "спокойствие",
  "interpretation": "Ангел во сне — это знак свыше, предсказывающий кармическое возмездие и духовное развитие.",
  "associations_question": "Что означает ангел?",
  "reflection_question": "Какова ваша судьба?",
  "potential_triggers": ["карма"],
  "tags": ["духовность", "ангел"]
}"""


class TestExtractJson:
    def test_plain_json(self):
        result = extract_json_from_text(VALID_JSON)
        assert result is not None
        assert "key_images" in result

    def test_markdown_wrapped(self):
        wrapped = f"```json\n{VALID_JSON}\n```"
        result = extract_json_from_text(wrapped)
        assert result is not None
        assert result["emotional_focus"] == "тревога"

    def test_invalid_json(self):
        assert extract_json_from_text("not json at all") is None


class TestStopWords:
    def test_clean_text(self):
        assert find_stop_words("психологический анализ сна") == []

    def test_esoteric_text(self):
        words = find_stop_words("Это карма и знак свыше")
        assert "карма" in words
        assert "знак свыше" in words

    def test_all_stop_words_are_lowercase(self):
        for word in ESOTERIC_STOP_WORDS:
            assert word == word.lower()


class TestValidateInterpretation:
    def test_valid_interpretation(self):
        result = validate_interpretation(VALID_JSON)
        assert result.is_valid
        assert result.data is not None
        assert result.data.emotional_focus == "тревога"
        assert len(result.data.key_images) == 3

    def test_esoteric_rejected(self):
        result = validate_interpretation(ESOTERIC_JSON)
        assert not result.is_valid
        assert len(result.found_stop_words) > 0

    def test_missing_fields(self):
        incomplete = '{"key_images": ["лес"]}'
        result = validate_interpretation(incomplete)
        assert not result.is_valid
        assert any("Missing fields" in e for e in result.errors)

    def test_invalid_json(self):
        result = validate_interpretation("hello world")
        assert not result.is_valid
        assert "Invalid JSON" in result.errors[0]
