from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud


class AnalyticsService:
    async def get_emotional_dynamics(self, session: AsyncSession, user_id: int) -> str:
        stats = await crud.get_emotional_stats(session, user_id)
        if not stats:
            return "📊 Пока недостаточно данных для статистики. Запишите несколько снов!"

        total = sum(count for _, count in stats)
        lines = ["📊 <b>Динамика эмоционального фона</b>\n"]

        for emotion, count in stats:
            pct = round(count / total * 100)
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            lines.append(f"{emotion}: {bar} {pct}% ({count})")

        return "\n".join(lines)

    async def get_tag_frequency(self, session: AsyncSession, user_id: int) -> str:
        tags = await crud.get_tag_stats(session, user_id)
        if not tags:
            return ""

        lines = ["\n🏷 <b>Частые теги</b>\n"]
        for tag, count in tags[:10]:
            lines.append(f"• {tag} — {count}")
        return "\n".join(lines)

    async def get_insights(self, session: AsyncSession, user_id: int) -> str:
        recurring = await crud.get_recurring_images(session, user_id)
        emotions = await crud.get_emotional_stats(session, user_id)
        tags = await crud.get_tag_stats(session, user_id)

        if not recurring and not emotions:
            return "🔍 Пока недостаточно данных для выявления паттернов. Продолжайте записывать сны!"

        lines = ["🔍 <b>Инсайты и паттерны</b>\n"]

        if recurring:
            lines.append("<b>Повторяющиеся образы:</b>")
            for image, count in recurring[:5]:
                lines.append(f"  • {image} — встречается {count} раз(а)")
            lines.append("")

        if emotions:
            dominant = emotions[0]
            lines.append(f"<b>Доминирующая эмоция:</b> {dominant[0]} ({dominant[1]} снов)")
            lines.append("")

        if tags:
            lines.append("<b>Частые темы:</b>")
            for tag, count in tags[:5]:
                lines.append(f"  • {tag} — {count}")

        return "\n".join(lines)


analytics_service = AnalyticsService()
