from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import DatabaseSession, require_permission
from app.core.permissions import VIEW_AUDIT_LOGS
from app.models.user import User
from app.schemas.log import LogResponse
from app.services.audit import list_audit_logs


router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get(
    "",
    response_model=list[LogResponse],
    status_code=status.HTTP_200_OK,
    name="list_audit_logs",
)
async def list_audit_logs_endpoint(
    current_user: Annotated[
        User,
        Depends(require_permission(VIEW_AUDIT_LOGS)),
    ],
    session: DatabaseSession,
) -> list[LogResponse]:
    return await list_audit_logs(session)
