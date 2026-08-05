import asyncio
import json

import httpx

from app.core.config import settings
from app.services.prompts import DIALOGUE_SYSTEM_PROMPT, REINFORCEMENT_PROMPT, SYSTEM_PROMPT
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
            "stream": True,
            "max_tokens": 3500,
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

    async def _read_stream(self, response: httpx.Response) -> str:
        chunks: list[str] = []
        async for line in response.aiter_lines():
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if not data or data == "[DONE]":
                continue
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = payload.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            piece = delta.get("content") or delta.get("reasoning_content") or ""
            if piece:
                chunks.append(piece)
        return "".join(chunks).strip()

    async def _call_llm(self, messages: list[dict[str, str]], *, json_mode: bool = True) -> str:
        if not self.api_key:
            raise LLMServiceError("KIMI_API_KEY не задан")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        payload = self._build_payload(messages, json_mode=json_mode)
        # При stream read-timeout — пауза между чанками, а не вся генерация целиком
        timeout = httpx.Timeout(connect=20.0, read=self.timeout, write=30.0, pool=30.0)
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
                        stream=True,
                        timeout=self.timeout,
                    )
                    async with client.stream(
                        "POST",
                        f"{self.api_base}/chat/completions",
                        headers=headers,
                        json=payload,
                    ) as response:
                        if response.status_code == 400 and json_mode:
                            body = (await response.aread()).decode("utf-8", errors="replace")[:800]
                            if "json" in body.lower() or "response_format" in body.lower():
                                logger.warning("llm_json_mode_unsupported", model=self.model, body=body)
                                return await self._call_llm(messages, json_mode=False)
                            last_error = f"400 — {body[:200]}"
                            logger.warning("llm_http_error", status=400, body=body)
                            if attempt < self.max_retries - 1:
                                await asyncio.sleep(1 + attempt)
                                continue
                            raise LLMServiceError(f"Kimi API error: {last_error}")

                        if response.status_code >= 400:
                            body = (await response.aread()).decode("utf-8", errors="replace")[:800]
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

                        content = await self._read_stream(response)

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
        validation_attempts = 2

        for attempt in range(validation_attempts):
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
                raw_preview=raw_response[:500],
            )

            messages.append({"role": "assistant", "content": raw_response})
            if validation.found_stop_words:
                messages.append({"role": "user", "content": REINFORCEMENT_PROMPT})
            else:
                messages.append({
                    "role": "user",
                    "content": (
                        "Ответ не соответствует формату. Верни строго JSON со всеми полями: "
                        "intro, key_images, key_images_analysis[{image, analysis}], emotional_focus, "
                        "potential_triggers[{title, description}], self_analysis_questions, "
                        "closing_observation, reflection_question, tags. "
                        "Без markdown и пояснений вне JSON. Пиши компактнее."
                    ),
                })

        logger.error("interpretation_fallback_used")
        raise LLMServiceError(
            "Kimi вернул ответ, но он не прошёл проверку формата. "
            "Попробуйте переформулировать сон или повторить позже."
        )

    async def continue_dialogue(
        self,
        *,
        dream_text: str,
        interpretation: dict,
        history: list[dict[str, str]],
        user_message: str,
        skip_question: bool = False,
    ) -> str:
        reserved = interpretation.get("self_analysis_questions") or []
        context = (
            f"Текст сна:\n{dream_text}\n\n"
            f"Первичная интерпретация (JSON):\n{interpretation}\n\n"
            f"Запасные вопросы для самоанализа: {reserved}\n"
        )
        if skip_question:
            context += (
                "\nПользователь нажал «Пропустить»: не настаивай на текущем вопросе, "
                "кратко признай это и предложи другой угол или следующий вопрос.\n"
            )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": DIALOGUE_SYSTEM_PROMPT},
            {"role": "user", "content": context},
            {"role": "assistant", "content": "Контекст принял. Продолжаем разбор в диалоге."},
        ]
        for item in history[-20:]:
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})

        # Для диалога JSON-режим не нужен
        return await self._call_llm(messages, json_mode=False)


llm_service = LLMService()
