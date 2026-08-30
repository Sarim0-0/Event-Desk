from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AuditAction, AuditEntityType
from app.models.log import Log


def add_log(
    session: AsyncSession,
    *,
    actor_id: UUID | None,
    action: AuditAction,
    entity_type: AuditEntityType,
    entity_id: UUID,
) -> Log:
    """Add one append-only audit record to the caller's transaction."""

    log = Log(
        actor_id=actor_id,
        action=action.value,
        entity_type=entity_type.value,
        entity_id=entity_id,
    )
    session.add(log)
    return log
