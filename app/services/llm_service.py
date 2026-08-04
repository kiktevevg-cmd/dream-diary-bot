import asyncio

import httpx

from app.core.config import settings
from app.services.prompts import FALLBACK_INTERPRETATION, REINFORCEMENT_PROMPT, SYSTEM_PROMPT
from app.utils.logger import get_logger
from app.utils.validators import DreamInterpretation, validate_interpretation

logger = get_logger(__name__)


class LLMServiceError(Exception):
    pass


class LLMService:
    def __init__(self) -> None:
        self.api_key = settings.llm_api_key
        self.api_base = settings.llm_api_base.rstrip("/")
        self.model = settings.llm_model
        self.timeout = settings.llm_timeout
        self.max_retries = settings.llm_max_retries

    async def _call_llm(self, messages: list[dict[str, str]], *, json_mode: bool = True) -> str:
        if not self.api_key:
            raise LLMServiceError("KIMI_API_KEY не задан")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.post(
                        f"{self.api_base}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    if response.status_code == 400 and json_mode:
                        logger.warning("llm_json_mode_unsupported", model=self.model)
                        return await self._call_llm(messages, json_mode=False)

                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                except httpx.HTTPStatusError as e:
                    body = e.response.text[:500] if e.response else ""
                    logger.warning(
                        "llm_request_failed",
                        attempt=attempt + 1,
                        status=e.response.status_code if e.response else None,
                        error=str(e),
                        body=body,
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        raise LLMServiceError(
                            f"Kimi API error: {e.response.status_code if e.response else 'unknown'}"
                        ) from e
                except (httpx.HTTPError, KeyError, IndexError) as e:
                    logger.warning("llm_request_failed", attempt=attempt + 1, error=str(e))
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        raise LLMServiceError(f"LLM request failed after {self.max_retries} attempts") from e

        raise LLMServiceError("LLM request failed")

    async def interpret_dream(self, dream_text: str) -> DreamInterpretation:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Проанализируй следующий сон:\n\n{dream_text}"},
        ]

        for attempt in range(self.max_retries):
            try:
                raw_response = await self._call_llm(messages)
                validation = validate_interpretation(raw_response)

                if validation.is_valid and validation.data:
                    logger.info("dream_interpreted", attempt=attempt + 1)
                    return validation.data

                logger.warning(
                    "interpretation_validation_failed",
                    attempt=attempt + 1,
                    errors=validation.errors,
                    stop_words=validation.found_stop_words,
                )

                if validation.found_stop_words:
                    messages.append({"role": "assistant", "content": raw_response})
                    messages.append({"role": "user", "content": REINFORCEMENT_PROMPT})
                else:
                    messages.append({"role": "assistant", "content": raw_response})
                    messages.append({
                        "role": "user",
                        "content": "Ответ не соответствует формату. Верни строго JSON со всеми полями.",
                    })

            except LLMServiceError:
                raise

        logger.error("interpretation_fallback_used")
        return DreamInterpretation(**FALLBACK_INTERPRETATION)


llm_service = LLMService()
