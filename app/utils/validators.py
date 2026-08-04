import json
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.utils.stop_words import ESOTERIC_STOP_WORDS, ESOTERIC_WORD_BOUNDARIES

REQUIRED_FIELDS = [
    "intro",
    "key_images",
    "key_images_analysis",
    "emotional_focus",
    "potential_triggers",
    "self_analysis_questions",
    "closing_observation",
    "reflection_question",
    "tags",
]


class ImageAnalysis(BaseModel):
    image: str = Field(..., min_length=1)
    analysis: str = Field(..., min_length=40)


class TriggerItem(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=20)


class DreamInterpretation(BaseModel):
    intro: str = Field(..., min_length=20)
    key_images: list[str] = Field(..., min_length=1)
    key_images_analysis: list[ImageAnalysis] = Field(..., min_length=1)
    emotional_focus: str
    potential_triggers: list[TriggerItem] = Field(..., min_length=1)
    self_analysis_questions: list[str] = Field(..., min_length=3)
    closing_observation: str = Field(..., min_length=40)
    reflection_question: str = Field(..., min_length=10)
    tags: list[str] = Field(..., min_length=1)

    @field_validator("key_images", "self_analysis_questions", "tags", mode="before")
    @classmethod
    def ensure_str_list(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [v]
        return v

    @field_validator("key_images_analysis", mode="before")
    @classmethod
    def normalize_image_analysis(cls, v: Any) -> list[dict[str, str]]:
        if not isinstance(v, list):
            return v
        normalized: list[dict[str, str]] = []
        for item in v:
            if isinstance(item, str):
                normalized.append({"image": item, "analysis": item})
            elif isinstance(item, dict):
                normalized.append(item)
            else:
                normalized.append({"image": str(item), "analysis": str(item)})
        return normalized

    @field_validator("potential_triggers", mode="before")
    @classmethod
    def normalize_triggers(cls, v: Any) -> list[dict[str, str]]:
        if not isinstance(v, list):
            return v
        normalized: list[dict[str, str]] = []
        for item in v:
            if isinstance(item, str):
                normalized.append({"title": item, "description": item})
            elif isinstance(item, dict):
                if "title" in item and "description" not in item:
                    item = {**item, "description": item.get("title", "")}
                normalized.append(item)
            else:
                normalized.append({"title": str(item), "description": str(item)})
        return normalized

    @model_validator(mode="after")
    def fill_key_images_from_analysis(self) -> "DreamInterpretation":
        if not self.key_images and self.key_images_analysis:
            self.key_images = [item.image for item in self.key_images_analysis]
        return self

    def trigger_titles(self) -> list[str]:
        return [t.title for t in self.potential_triggers]


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
    found = [word for word in ESOTERIC_STOP_WORDS if word in text_lower]
    for word in ESOTERIC_WORD_BOUNDARIES:
        if re.search(rf"(?<![а-яёa-z]){re.escape(word)}(?![а-яёa-z])", text_lower):
            found.append(word)
    return found


def _analysis_text(data: dict[str, Any]) -> str:
    parts: list[str] = [
        str(data.get("intro", "")),
        str(data.get("emotional_focus", "")),
        str(data.get("closing_observation", "")),
        str(data.get("reflection_question", "")),
    ]
    for item in data.get("key_images_analysis") or []:
        if isinstance(item, dict):
            parts.append(str(item.get("analysis", "")))
        else:
            parts.append(str(item))
    for item in data.get("potential_triggers") or []:
        if isinstance(item, dict):
            parts.append(str(item.get("title", "")))
            parts.append(str(item.get("description", "")))
        else:
            parts.append(str(item))
    for question in data.get("self_analysis_questions") or []:
        parts.append(str(question))
    return "\n".join(parts)


def validate_interpretation(raw_response: str) -> ValidationResult:
    errors: list[str] = []

    data = extract_json_from_text(raw_response)
    if data is None:
        return ValidationResult(is_valid=False, errors=["Invalid JSON response"])

    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        errors.append(f"Missing fields: {', '.join(missing)}")

    found_stop_words = find_stop_words(_analysis_text(data))
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
