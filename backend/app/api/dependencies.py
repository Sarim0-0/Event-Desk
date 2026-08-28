from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db_session
from app.models.user import User
from app.repositories.rbac import get_role_permission_keys, role_has_permission
from app.services.auth import get_authenticated_user


bearer_scheme = HTTPBearer(auto_error=False)

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


async def get_current_user(
    credentials: BearerCredentials,
    session: DatabaseSession,
) -> User:
    if credentials is None:
        raise _credentials_exception()

    return await get_authenticated_user(session, credentials.credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]


@dataclass(frozen=True)
class PermissionGrant:
    user: User
    permission_keys: frozenset[str]

    def allows(self, permission_key: str) -> bool:
        return permission_key in self.permission_keys


def require_permission(permission_key: str):
    """Build a dependency that allows users with one database permission."""

    async def permission_dependency(
        current_user: CurrentUser,
        session: DatabaseSession,
    ) -> User:
        if not await role_has_permission(
            session,
            current_user.role_id,
            permission_key,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return current_user

    return permission_dependency


def require_any_permission(*permission_keys: str):
    """Allow users whose role has at least one requested permission."""

    requested_permissions = frozenset(permission_keys)
    if not requested_permissions:
        raise ValueError("At least one permission key is required.")

    async def permission_dependency(
        current_user: CurrentUser,
        session: DatabaseSession,
    ) -> PermissionGrant:
        granted_permissions = await get_role_permission_keys(
            session,
            current_user.role_id,
            requested_permissions,
        )
        if not granted_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return PermissionGrant(
            user=current_user,
            permission_keys=granted_permissions,
        )

    return permission_dependency


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
