from app.utils.stop_words import ESOTERIC_STOP_WORDS
from app.utils.validators import (
    extract_json_from_text,
    find_stop_words,
    validate_interpretation,
)

VALID_JSON = """{
  "intro": "Спасибо, что поделились. Разберём сон с позиции психологии личности, без сонников и мистики.",
  "key_images": ["лес", "мост", "вода"],
  "key_images_analysis": [
    {
      "image": "лес",
      "analysis": "Лес часто отражает пространство неизвестного и внутреннего поиска. Он может указывать на этап, где привычные ориентиры ослабевают, и психика просит замедлиться и прислушаться к себе."
    },
    {
      "image": "мост",
      "analysis": "Мост может символизировать переход между состояниями или ролями. Важно, чувствовали ли вы уверенность при переходе или сомнение — это подсказка о текущем жизненном выборе."
    },
    {
      "image": "вода",
      "analysis": "Вода связана с эмоциональной сферой. Её состояние во сне часто зеркалит то, насколько доступны и прожиты чувства в бодрствовании."
    }
  ],
  "emotional_focus": "тревога",
  "potential_triggers": [
    {
      "title": "Переходный период",
      "description": "Возможно, вы находитесь между знакомым и новым, и психика фиксирует неопределённость этого промежутка."
    },
    {
      "title": "Непрожитые эмоции",
      "description": "Тревога во сне может указывать на чувства, которые днём откладываются из-за занятости или контроля."
    }
  ],
  "self_analysis_questions": [
    "Какие чувства были доминирующими во сне?",
    "Что для вас лично означает мост?",
    "Где в жизни сейчас ощущается переход?",
    "Какие эмоции вы обычно откладываете на потом?"
  ],
  "closing_observation": "Сон не столько пугает неизвестностью, сколько приглашает признать переход как часть вашего пути и дать эмоциям место рядом с решениями.",
  "reflection_question": "Что изменилось бы, если бы вы отнеслись к текущей неопределённости не как к угрозе, а как к пространству выбора?",
  "tags": ["переход", "тревога", "эмоции"]
}"""

ESOTERIC_JSON = """{
  "intro": "Сон несёт знак свыше.",
  "key_images": ["ангел", "свет"],
  "key_images_analysis": [
    {
      "image": "ангел",
      "analysis": "Ангел во сне — это знак свыше, предсказывающий кармическое возмездие и духовное развитие."
    }
  ],
  "emotional_focus": "спокойствие",
  "potential_triggers": [
    {"title": "Карма", "description": "Это проявление кармы и судьбы."}
  ],
  "self_analysis_questions": [
    "Что означает ангел?",
    "Какова ваша судьба?",
    "Готовы ли вы к пророчеству?"
  ],
  "closing_observation": "Вас ждёт предсказание и духовное развитие через знак свыше.",
  "reflection_question": "Примите ли вы послание свыше?",
  "tags": ["духовность", "ангел"]
}"""

RELIGIOUS_IMAGE_PSYCHOLOGICAL_JSON = """{
  "intro": "Спасибо за доверие. Разберём образы психологически, без мистики и сонников.",
  "key_images": ["ангел", "церковь", "свет"],
  "key_images_analysis": [
    {
      "image": "ангел",
      "analysis": "Образ ангела может отражать потребность в защите, поддержке или внутренней опоре. В психологии это часто проекция ресурса заботы, а не послание извне."
    },
    {
      "image": "церковь",
      "analysis": "Церковь как образ может символизировать поиск смысла, безопасности и принадлежности к ценностям, важным для вашей идентичности."
    }
  ],
  "emotional_focus": "тревога",
  "potential_triggers": [
    {
      "title": "Поиск поддержки",
      "description": "Сон может указывать на период, когда особенно нужна эмоциональная опора и ясность границ."
    },
    {
      "title": "Неопределённость",
      "description": "Тревога связана с отсутствием понятной опоры в текущих решениях или отношениях."
    }
  ],
  "self_analysis_questions": [
    "С чем у вас ассоциируется образ ангела?",
    "Где в жизни вам сейчас нужна поддержка?",
    "Какие ценности сейчас особенно важны?",
    "Что даёт вам ощущение безопасности?"
  ],
  "closing_observation": "Сон поднимает тему внутренней опоры: психика ищет не внешнее чудо, а устойчивый способ заботиться о себе в период неопределённости.",
  "reflection_question": "Что могло бы стать вашей надёжной опорой уже сейчас, без ожидания внешней помощи?",
  "tags": ["защита", "опора", "тревога"]
}"""


class TestExtractJson:
    def test_plain_json(self):
        result = extract_json_from_text(VALID_JSON)
        assert result is not None
        assert "key_images_analysis" in result

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

    def test_false_positives_substrings(self):
        assert find_stop_words("мне надо идти на край") == []
        assert find_stop_words("богатый опыт анализа") == []

    def test_all_stop_words_are_lowercase(self):
        for word in ESOTERIC_STOP_WORDS:
            assert word == word.lower()


class TestValidateInterpretation:
    def test_valid_interpretation(self):
        result = validate_interpretation(VALID_JSON)
        assert result.is_valid, result.errors
        assert result.data is not None
        assert result.data.emotional_focus == "тревога"
        assert len(result.data.key_images_analysis) == 3
        assert result.data.trigger_titles()[0] == "Переходный период"

    def test_esoteric_rejected(self):
        result = validate_interpretation(ESOTERIC_JSON)
        assert not result.is_valid
        assert len(result.found_stop_words) > 0

    def test_religious_images_with_psychological_analysis_allowed(self):
        result = validate_interpretation(RELIGIOUS_IMAGE_PSYCHOLOGICAL_JSON)
        assert result.is_valid, result.errors
        assert "ангел" in result.data.key_images

    def test_missing_fields(self):
        incomplete = '{"key_images": ["лес"]}'
        result = validate_interpretation(incomplete)
        assert not result.is_valid
        assert any("Missing fields" in e for e in result.errors)

    def test_invalid_json(self):
        result = validate_interpretation("hello world")
        assert not result.is_valid
        assert "Invalid JSON" in result.errors[0]
