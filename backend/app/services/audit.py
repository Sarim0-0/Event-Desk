from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AuditAction, AuditEntityType
from app.models.log import Log
from app.repositories import audit as audit_repository
from app.schemas.log import LogResponse


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


async def list_audit_logs(
    session: AsyncSession,
) -> list[LogResponse]:
    """Return all audit records after route-level authorization succeeds."""

    logs = await audit_repository.list_logs(session)
    return [LogResponse.model_validate(log) for log in logs]
