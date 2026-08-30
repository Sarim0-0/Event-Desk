from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import event as event_repository


async def complete_past_events_batch(session: AsyncSession) -> int:
    """Complete all eligible Events in one atomic transaction."""

    async with session.begin():
        completed_count = (
            await event_repository.complete_past_published_events(
                session,
                current_time=datetime.now(timezone.utc),
            )
        )

    return completed_count
