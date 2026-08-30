from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import AuditAction, AuditEntityType


class LogResponse(BaseModel):
    """Read-only audit history returned to an authorized Admin."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_id: UUID | None
    action: AuditAction
    entity_type: AuditEntityType
    entity_id: UUID
    created_at: datetime
