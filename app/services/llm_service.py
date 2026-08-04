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

    def _build_payload(self, messages: list[dict[str, str]], *, json_mode: bool) -> dict:
        payload: dict = {
            "model": self.model,
            "messages": messages,
        }
        # kimi-k2.6 думает по умолчанию — это долго и часто упирается в таймаут
        if self.model.startswith("kimi-k2"):
            payload["thinking"] = {"type": "disabled"}
        # kimi-k3 всегда думает; уменьшаем глубину рассуждения
        if self.model.startswith("kimi-k3"):
            payload["reasoning_effort"] = "low"
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        return payload

    @staticmethod
    def _extract_content(data: dict) -> str:
        message = data["choices"][0]["message"]
        content = message.get("content")
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        content = content or message.get("reasoning_content") or ""
        return content.strip() if isinstance(content, str) else ""

    async def _call_llm(self, messages: list[dict[str, str]], *, json_mode: bool = True) -> str:
        if not self.api_key:
            raise LLMServiceError("KIMI_API_KEY не задан")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = self._build_payload(messages, json_mode=json_mode)
        timeout = httpx.Timeout(self.timeout, connect=20.0)
        last_error = "unknown"

        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    logger.info(
                        "llm_request_start",
                        attempt=attempt + 1,
                        model=self.model,
                        api_base=self.api_base,
                        json_mode=json_mode,
                    )
                    response = await client.post(
                        f"{self.api_base}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    body = response.text[:800]
                    if response.status_code == 400 and json_mode and "json" in body.lower():
                        logger.warning("llm_json_mode_unsupported", model=self.model, body=body)
                        return await self._call_llm(messages, json_mode=False)

                    if response.status_code >= 400:
                        logger.warning(
                            "llm_http_error",
                            attempt=attempt + 1,
                            status=response.status_code,
                            model=self.model,
                            api_base=self.api_base,
                            body=body,
                        )
                        if response.status_code in {401, 403}:
                            raise LLMServiceError("Неверный KIMI_API_KEY или нет доступа к модели")
                        if response.status_code == 404:
                            raise LLMServiceError(
                                f"Модель {self.model} недоступна. Укажите LLM_MODEL=kimi-k2.6"
                            )
                        last_error = f"{response.status_code} — {body[:200]}"
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(1 + attempt)
                            continue
                        raise LLMServiceError(f"Kimi API error: {last_error}")

                    content = self._extract_content(response.json())
                    if not content:
                        raise LLMServiceError("Kimi API вернул пустой ответ")
                    logger.info("llm_request_ok", attempt=attempt + 1, chars=len(content))
                    return content

                except LLMServiceError:
                    raise
                except httpx.TimeoutException as e:
                    last_error = f"timeout after {self.timeout}s ({type(e).__name__})"
                    logger.warning(
                        "llm_timeout",
                        attempt=attempt + 1,
                        model=self.model,
                        api_base=self.api_base,
                        timeout=self.timeout,
                    )
                except httpx.HTTPError as e:
                    last_error = f"{type(e).__name__}: {e}"
                    logger.warning(
                        "llm_network_error",
                        attempt=attempt + 1,
                        model=self.model,
                        api_base=self.api_base,
                        error=last_error,
                    )
                except (KeyError, IndexError, TypeError, ValueError) as e:
                    last_error = f"bad response: {e}"
                    logger.warning("llm_parse_error", attempt=attempt + 1, error=str(e))

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1 + attempt)

        raise LLMServiceError(
            f"LLM request failed after {self.max_retries} attempts: {last_error}. "
            f"model={self.model}, base={self.api_base}"
        )

    async def interpret_dream(self, dream_text: str) -> DreamInterpretation:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Проанализируй следующий сон:\n\n{dream_text}"},
        ]
        # Ревалидация ответа — отдельно от сетевых ретраев
        validation_attempts = 3

        for attempt in range(validation_attempts):
            try:
                raw_response = await self._call_llm(messages)
            except LLMServiceError:
                raise

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

            messages.append({"role": "assistant", "content": raw_response})
            if validation.found_stop_words:
                messages.append({"role": "user", "content": REINFORCEMENT_PROMPT})
            else:
                messages.append({
                    "role": "user",
                    "content": "Ответ не соответствует формату. Верни строго JSON со всеми полями.",
                })

        logger.error("interpretation_fallback_used")
        return DreamInterpretation(**FALLBACK_INTERPRETATION)


llm_service = LLMService()
