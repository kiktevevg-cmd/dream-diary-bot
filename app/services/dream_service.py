from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.redis_client import cache_recent_dream
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

        await crud.close_active_dialogues(session, user_id)
        dream = await crud.create_dream(session, user_id, dream_text, transcript)
        await session.commit()

        try:
            interpretation = await llm_service.interpret_dream(dream_text)
            interpretation_dict = interpretation.model_dump()

            await crud.update_dream_interpretation(session, dream.id, interpretation_dict)
            formatted_preview = interpretation.closing_observation
            await crud.add_dream_message(
                session,
                dream.id,
                user_id,
                "user",
                dream_text,
            )
            await crud.add_dream_message(
                session,
                dream.id,
                user_id,
                "assistant",
                formatted_preview,
            )
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

    async def continue_dialogue(
        self,
        session: AsyncSession,
        user_id: int,
        user_message: str,
        *,
        skip_question: bool = False,
    ) -> str:
        dream = await crud.get_active_dream(session, user_id)
        if not dream or not dream.interpretation:
            raise ValueError("Нет активного разбора сна. Нажмите «Новый сон» и опишите сон.")

        history_rows = await crud.get_dream_messages(session, dream.id)
        history = [{"role": row.role, "content": row.content} for row in history_rows]
        dream_text = crud.decrypt_dream_text(dream)

        reply = await llm_service.continue_dialogue(
            dream_text=dream_text,
            interpretation=dream.interpretation,
            history=history,
            user_message=user_message,
            skip_question=skip_question,
        )

        await crud.add_dream_message(session, dream.id, user_id, "user", user_message)
        await crud.add_dream_message(session, dream.id, user_id, "assistant", reply)
        await session.commit()
        return reply

    async def finish_dialogue(self, session: AsyncSession, user_id: int) -> str:
        dream = await crud.get_active_dream(session, user_id)
        if not dream:
            return "Сейчас нет активного разбора. Нажмите «Новый сон», чтобы начать."

        messages = await crud.get_dream_messages(session, dream.id)
        user_bits = [m.content[:120] for m in messages if m.role == "user"][1:4]
        summary_parts = []
        if dream.interpretation:
            summary_parts.append(dream.interpretation.get("closing_observation") or "")
        if user_bits:
            summary_parts.append("В диалоге: " + " | ".join(user_bits))
        summary = "\n".join(p for p in summary_parts if p).strip() or "Разбор завершён."

        await crud.close_dream_dialogue(session, dream.id, user_id, summary=summary)
        await session.commit()
        return (
            "Разбор этого сна завершён. Краткие заметки сохранены в истории.\n"
            "Когда будете готовы — нажмите «Новый сон»."
        )

    async def start_new_dream(self, session: AsyncSession, user_id: int) -> None:
        await crud.close_active_dialogues(session, user_id)
        await session.commit()

    async def save_insight(
        self,
        session: AsyncSession,
        user_id: int,
        note: str,
        dream_id: int | None = None,
    ) -> bool:
        active = await crud.get_active_dream(session, user_id)
        target_dream_id = dream_id or (active.id if active else None)
        await crud.create_insight(session, user_id, note.strip(), dream_id=target_dream_id)
        if target_dream_id:
            await crud.set_dream_note(session, target_dream_id, user_id, note.strip())
        await session.commit()
        return True


dream_service = DreamService()
