import json
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.utils.stop_words import ESOTERIC_STOP_WORDS

REQUIRED_FIELDS = [
    "key_images",
    "emotional_focus",
    "interpretation",
    "associations_question",
    "reflection_question",
    "potential_triggers",
    "tags",
]


class DreamInterpretation(BaseModel):
    key_images: list[str] = Field(..., min_length=1)
    emotional_focus: str
    interpretation: str = Field(..., min_length=50)
    associations_question: str
    reflection_question: str
    potential_triggers: list[str] = Field(..., min_length=1)
    tags: list[str] = Field(..., min_length=1)

    @field_validator("key_images", "potential_triggers", "tags", mode="before")
    @classmethod
    def ensure_list(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [v]
        return v


class ValidationResult(BaseModel):
    is_valid: bool
    data: DreamInterpretation | None = None
    errors: list[str] = Field(default_factory=list)
    found_stop_words: list[str] = Field(default_factory=list)


def extract_json_from_text(text: str) -> dict[str, Any] | None:
    """Extract JSON object from LLM response, handling markdown code blocks."""
    text = text.strip()
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
    return None


def find_stop_words(text: str) -> list[str]:
    text_lower = text.lower()
    return [word for word in ESOTERIC_STOP_WORDS if word in text_lower]


def validate_interpretation(raw_response: str) -> ValidationResult:
    errors: list[str] = []
    found_stop_words: list[str] = []

    data = extract_json_from_text(raw_response)
    if data is None:
        return ValidationResult(is_valid=False, errors=["Invalid JSON response"])

    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        errors.append(f"Missing fields: {', '.join(missing)}")

    all_text = json.dumps(data, ensure_ascii=False)
    found_stop_words = find_stop_words(all_text)
    if found_stop_words:
        errors.append(f"Esoteric terms found: {', '.join(found_stop_words)}")

    if errors:
        return ValidationResult(
            is_valid=False,
            errors=errors,
            found_stop_words=found_stop_words,
        )

    try:
        interpretation = DreamInterpretation(**data)
    except Exception as e:
        return ValidationResult(is_valid=False, errors=[str(e)])

    return ValidationResult(is_valid=True, data=interpretation)
