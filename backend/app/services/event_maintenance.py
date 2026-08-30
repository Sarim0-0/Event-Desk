from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AuditAction, AuditEntityType
from app.repositories import event as event_repository
from app.services import audit as audit_service


async def complete_past_events_batch(session: AsyncSession) -> int:
    """Complete all eligible Events in one atomic transaction."""

    async with session.begin():
        completed_event_ids = (
            await event_repository.complete_past_published_events(
                session,
                current_time=datetime.now(timezone.utc),
            )
        )

        for event_id in completed_event_ids:
            audit_service.record_action(
                session,
                actor_id=None,
                action=AuditAction.EVENT_COMPLETED,
                entity_type=AuditEntityType.EVENT,
                entity_id=event_id,
            )

    return len(completed_event_ids)
