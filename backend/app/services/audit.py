from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AuditAction, AuditEntityType
from app.models.log import Log
from app.repositories import audit as audit_repository


def record_action(
    session: AsyncSession,
    *,
    actor_id: UUID | None,
    action: AuditAction,
    entity_type: AuditEntityType,
    entity_id: UUID,
) -> Log:
    """Record an audit action in the original operation's transaction."""

    return audit_repository.add_log(
        session,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
    )
