from datetime import datetime

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.config import settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(10), default="ru")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    dreams: Mapped[list["Dream"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    feedback: Mapped[list["Feedback"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    messages: Mapped[list["DreamMessage"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    insights: Mapped[list["Insight"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Dream(Base):
    __tablename__ = "dreams"
    __table_args__ = (
        Index("idx_dreams_user_created", "user_id", "created_at"),
        Index("idx_dreams_user_emotional", "user_id", "emotional_focus"),
        Index("idx_dreams_user_dialogue", "user_id", "dialogue_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    transcript: Mapped[str | None] = mapped_column(Text)
    interpretation: Mapped[dict | None] = mapped_column(JSONB)
    emotional_focus: Mapped[str | None] = mapped_column(String(50))
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    potential_triggers: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    accuracy_rating: Mapped[int | None] = mapped_column(Integer)
    user_note: Mapped[str | None] = mapped_column(Text)
    dialogue_status: Mapped[str | None] = mapped_column(String(20), default=None)
    dialogue_summary: Mapped[str | None] = mapped_column(Text)
    is_analyzed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="dreams")
    feedback: Mapped[list["Feedback"]] = relationship(back_populates="dream", cascade="all, delete-orphan")
    messages: Mapped[list["DreamMessage"]] = relationship(back_populates="dream", cascade="all, delete-orphan")
    insights: Mapped[list["Insight"]] = relationship(back_populates="dream", cascade="all, delete-orphan")


class DreamMessage(Base):
    __tablename__ = "dream_messages"
    __table_args__ = (
        Index("idx_dream_messages_dream_created", "dream_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dream_id: Mapped[int] = mapped_column(Integer, ForeignKey("dreams.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dream: Mapped["Dream"] = relationship(back_populates="messages")
    user: Mapped["User"] = relationship(back_populates="messages")


class Insight(Base):
    __tablename__ = "insights"
    __table_args__ = (
        Index("idx_insights_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    dream_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("dreams.id", ondelete="SET NULL"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="insights")
    dream: Mapped["Dream | None"] = relationship(back_populates="insights")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dream_id: Mapped[int] = mapped_column(Integer, ForeignKey("dreams.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="feedback")
    dream: Mapped["Dream"] = relationship(back_populates="feedback")


engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    connect_args={"timeout": 10},
)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()
