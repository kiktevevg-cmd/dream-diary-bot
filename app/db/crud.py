from datetime import datetime, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_text, encrypt_text
from app.db.models import Dream, DreamMessage, Feedback, Insight, User


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        if username and user.username != username:
            user.username = username
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        return user

    user = User(telegram_id=telegram_id, username=username, first_name=first_name)
    session.add(user)
    await session.flush()
    return user


async def create_dream(
    session: AsyncSession,
    user_id: int,
    text: str,
    transcript: str | None = None,
) -> Dream:
    dream = Dream(
        user_id=user_id,
        text=encrypt_text(text),
        transcript=encrypt_text(transcript) if transcript else None,
        is_analyzed=False,
    )
    session.add(dream)
    await session.flush()
    return dream


async def update_dream_interpretation(
    session: AsyncSession,
    dream_id: int,
    interpretation: dict,
) -> Dream | None:
    result = await session.execute(select(Dream).where(Dream.id == dream_id))
    dream = result.scalar_one_or_none()
    if not dream:
        return None

    dream.interpretation = interpretation
    dream.emotional_focus = interpretation.get("emotional_focus")
    dream.tags = interpretation.get("tags", [])
    triggers = interpretation.get("potential_triggers", [])
    dream.potential_triggers = [
        t.get("title", str(t)) if isinstance(t, dict) else str(t) for t in triggers
    ]
    dream.is_analyzed = True
    dream.dialogue_status = "active"
    dream.processed_at = datetime.now(timezone.utc)
    await session.flush()
    return dream


async def get_active_dream(session: AsyncSession, user_id: int) -> Dream | None:
    result = await session.execute(
        select(Dream)
        .where(Dream.user_id == user_id, Dream.dialogue_status == "active")
        .order_by(Dream.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def close_active_dialogues(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        update(Dream)
        .where(Dream.user_id == user_id, Dream.dialogue_status == "active")
        .values(dialogue_status="closed")
    )


async def close_dream_dialogue(
    session: AsyncSession,
    dream_id: int,
    user_id: int,
    summary: str | None = None,
) -> bool:
    values: dict = {"dialogue_status": "closed"}
    if summary:
        values["dialogue_summary"] = summary
    result = await session.execute(
        update(Dream).where(Dream.id == dream_id, Dream.user_id == user_id).values(**values)
    )
    return result.rowcount > 0


async def add_dream_message(
    session: AsyncSession,
    dream_id: int,
    user_id: int,
    role: str,
    content: str,
) -> DreamMessage:
    message = DreamMessage(dream_id=dream_id, user_id=user_id, role=role, content=content)
    session.add(message)
    await session.flush()
    return message


async def get_dream_messages(
    session: AsyncSession,
    dream_id: int,
    limit: int = 40,
) -> list[DreamMessage]:
    result = await session.execute(
        select(DreamMessage)
        .where(DreamMessage.dream_id == dream_id)
        .order_by(DreamMessage.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_insight(
    session: AsyncSession,
    user_id: int,
    text: str,
    dream_id: int | None = None,
) -> Insight:
    insight = Insight(user_id=user_id, dream_id=dream_id, text=text)
    session.add(insight)
    await session.flush()
    return insight


async def get_user_insights(session: AsyncSession, user_id: int, limit: int = 20) -> list[Insight]:
    result = await session.execute(
        select(Insight)
        .where(Insight.user_id == user_id)
        .order_by(Insight.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_dream_by_id(session: AsyncSession, dream_id: int, user_id: int) -> Dream | None:
    result = await session.execute(
        select(Dream).where(Dream.id == dream_id, Dream.user_id == user_id)
    )
    return result.scalar_one_or_none()


def decrypt_dream_text(dream: Dream) -> str:
    return decrypt_text(dream.text)


def decrypt_dream_transcript(dream: Dream) -> str | None:
    return decrypt_text(dream.transcript) if dream.transcript else None


async def get_user_dreams(session: AsyncSession, user_id: int, limit: int = 10) -> list[Dream]:
    result = await session.execute(
        select(Dream)
        .where(Dream.user_id == user_id, Dream.is_analyzed.is_(True))
        .order_by(Dream.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def set_dream_rating(session: AsyncSession, dream_id: int, user_id: int, rating: int) -> bool:
    result = await session.execute(
        update(Dream)
        .where(Dream.id == dream_id, Dream.user_id == user_id)
        .values(accuracy_rating=rating)
    )
    return result.rowcount > 0


async def add_dream_tag(session: AsyncSession, dream_id: int, user_id: int, tag: str) -> bool:
    dream = await get_dream_by_id(session, dream_id, user_id)
    if not dream:
        return False
    tags = list(dream.tags or [])
    if tag not in tags:
        tags.append(tag)
        dream.tags = tags
        await session.flush()
    return True


async def set_dream_note(session: AsyncSession, dream_id: int, user_id: int, note: str) -> bool:
    result = await session.execute(
        update(Dream)
        .where(Dream.id == dream_id, Dream.user_id == user_id)
        .values(user_note=note)
    )
    return result.rowcount > 0


async def add_feedback(
    session: AsyncSession,
    dream_id: int,
    user_id: int,
    rating: int,
    comment: str | None = None,
) -> Feedback:
    feedback = Feedback(dream_id=dream_id, user_id=user_id, rating=rating, comment=comment)
    session.add(feedback)
    await session.flush()
    return feedback


async def get_emotional_stats(session: AsyncSession, user_id: int) -> list[tuple[str, int]]:
    result = await session.execute(
        select(Dream.emotional_focus, func.count(Dream.id))
        .where(Dream.user_id == user_id, Dream.is_analyzed.is_(True), Dream.emotional_focus.isnot(None))
        .group_by(Dream.emotional_focus)
        .order_by(func.count(Dream.id).desc())
    )
    return [(row[0], row[1]) for row in result.all()]


async def get_tag_stats(session: AsyncSession, user_id: int) -> list[tuple[str, int]]:
    dreams = await get_user_dreams(session, user_id, limit=100)
    tag_counts: dict[str, int] = {}
    for dream in dreams:
        for tag in dream.tags or []:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    return sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)


async def get_recurring_images(session: AsyncSession, user_id: int) -> list[tuple[str, int]]:
    dreams = await get_user_dreams(session, user_id, limit=100)
    image_counts: dict[str, int] = {}
    for dream in dreams:
        if dream.interpretation:
            for image in dream.interpretation.get("key_images", []):
                image_counts[image] = image_counts.get(image, 0) + 1
    recurring = [(img, cnt) for img, cnt in image_counts.items() if cnt > 1]
    return sorted(recurring, key=lambda x: x[1], reverse=True)


async def clear_user_history(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(delete(Dream).where(Dream.user_id == user_id))
    return result.rowcount


async def delete_user_data(session: AsyncSession, user_id: int) -> None:
    await session.execute(delete(Insight).where(Insight.user_id == user_id))
    await session.execute(delete(DreamMessage).where(DreamMessage.user_id == user_id))
    await session.execute(delete(Feedback).where(Feedback.user_id == user_id))
    await session.execute(delete(Dream).where(Dream.user_id == user_id))
    await session.execute(delete(User).where(User.id == user_id))


async def update_user_settings(session: AsyncSession, user_id: int, settings: dict) -> None:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        current = user.settings or {}
        current.update(settings)
        user.settings = current
        await session.flush()


async def get_unprocessed_dreams(session: AsyncSession, limit: int = 10) -> list[Dream]:
    result = await session.execute(
        select(Dream).where(Dream.is_analyzed.is_(False)).limit(limit)
    )
    return list(result.scalars().all())
