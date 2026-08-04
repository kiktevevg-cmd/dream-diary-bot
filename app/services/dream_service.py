from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.redis_client import cache_recent_dream, invalidate_dream_cache
from app.services.llm_service import LLMServiceError, llm_service
from app.utils.logger import get_logger
from app.utils.validators import DreamInterpretation

logger = get_logger(__name__)

MAX_DREAM_LENGTH = 4000


class DreamService:
    async def process_dream(
        self,
        session: AsyncSession,
        user_id: int,
        dream_text: str,
        transcript: str | None = None,
    ) -> tuple[int, DreamInterpretation]:
        if len(dream_text) > MAX_DREAM_LENGTH:
            raise ValueError(f"Текст сна не должен превышать {MAX_DREAM_LENGTH} символов")

        dream = await crud.create_dream(session, user_id, dream_text, transcript)
        await session.commit()

        try:
            interpretation = await llm_service.interpret_dream(dream_text)
            interpretation_dict = interpretation.model_dump()

            await crud.update_dream_interpretation(session, dream.id, interpretation_dict)
            await session.commit()

            await cache_recent_dream(user_id, {
                "id": dream.id,
                "emotional_focus": interpretation.emotional_focus,
                "tags": interpretation.tags,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

            return dream.id, interpretation

        except LLMServiceError as e:
            logger.error("dream_processing_failed", dream_id=dream.id, error=str(e))
            await session.commit()
            raise

    async def rate_dream(
        self,
        session: AsyncSession,
        dream_id: int,
        user_id: int,
        rating: int,
    ) -> bool:
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        success = await crud.set_dream_rating(session, dream_id, user_id, rating)
        if success:
            await crud.add_feedback(session, dream_id, user_id, rating)
            await session.commit()
        return success

    async def add_user_tag(
        self,
        session: AsyncSession,
        dream_id: int,
        user_id: int,
        tag: str,
    ) -> bool:
        success = await crud.add_dream_tag(session, dream_id, user_id, tag.strip())
        if success:
            await session.commit()
            await invalidate_dream_cache(user_id)
        return success

    async def save_insight(
        self,
        session: AsyncSession,
        dream_id: int,
        user_id: int,
        note: str,
    ) -> bool:
        success = await crud.set_dream_note(session, dream_id, user_id, note)
        if success:
            await session.commit()
        return success


dream_service = DreamService()
