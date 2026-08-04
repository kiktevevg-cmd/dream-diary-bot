import tempfile

from openai import AsyncOpenAI

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VoiceServiceError(Exception):
    pass


class VoiceService:
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        self.model = settings.whisper_model

    @property
    def client(self) -> AsyncOpenAI:
        if not settings.whisper_api_key:
            raise VoiceServiceError(
                "Голосовые сообщения недоступны: задайте WHISPER_API_KEY (OpenAI Whisper). "
                "Kimi API не поддерживает распознавание речи."
            )
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=settings.whisper_api_key,
                base_url=settings.whisper_api_base,
            )
        return self._client

    async def transcribe(self, audio_bytes: bytes, filename: str = "voice.ogg") -> str:
        try:
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            with open(tmp_path, "rb") as audio_file:
                response = await self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language="ru",
                )

            logger.info("voice_transcribed", length=len(response.text))
            return response.text

        except Exception as e:
            logger.error("voice_transcription_failed", error=str(e))
            raise VoiceServiceError("Не удалось распознать голосовое сообщение") from e


voice_service = VoiceService()
