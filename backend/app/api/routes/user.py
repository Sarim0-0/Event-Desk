from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import DatabaseSession, require_permission
from app.core.permissions import (
    CHANGE_OWN_PASSWORD,
    CHANGE_USER_ROLE,
    CHANGE_USER_STATUS,
    UPDATE_OWN_PROFILE,
    VIEW_ALL_USERS,
)
from app.models.user import User
from app.schemas.user import (
    PasswordChangeRequest,
    UserProfileUpdate,
    UserResponse,
    UserRoleUpdate,
)
from app.services.user import (
    change_own_password,
    change_user_role,
    deactivate_user,
    list_all_users,
    update_own_profile,
)


router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    response_model=list[UserResponse],
    status_code=status.HTTP_200_OK,
    name="list_all_users",
)
async def list_all_users_endpoint(
    current_user: Annotated[
        User,
        Depends(require_permission(VIEW_ALL_USERS)),
    ],
    session: DatabaseSession,
) -> list[UserResponse]:
    return await list_all_users(session)


@router.patch(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    name="update_own_profile",
)
async def update_own_profile_endpoint(
    request: UserProfileUpdate,
    current_user: Annotated[
        User,
        Depends(require_permission(UPDATE_OWN_PROFILE)),
    ],
    session: DatabaseSession,
) -> UserResponse:
    return await update_own_profile(session, current_user, request)


@router.patch(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    name="change_own_password",
)
async def change_own_password_endpoint(
    request: PasswordChangeRequest,
    current_user: Annotated[
        User,
        Depends(require_permission(CHANGE_OWN_PASSWORD)),
    ],
    session: DatabaseSession,
) -> None:
    await change_own_password(session, current_user, request)


@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    name="change_user_role",
)
async def change_user_role_endpoint(
    user_id: UUID,
    request: UserRoleUpdate,
    current_user: Annotated[
        User,
        Depends(require_permission(CHANGE_USER_ROLE)),
    ],
    session: DatabaseSession,
) -> UserResponse:
    return await change_user_role(
        session,
        current_user,
        user_id,
        request,
    )


@router.post(
    "/{user_id}/deactivate",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    name="deactivate_user",
)
async def deactivate_user_endpoint(
    user_id: UUID,
    current_user: Annotated[
        User,
        Depends(require_permission(CHANGE_USER_STATUS)),
    ],
    session: DatabaseSession,
) -> UserResponse:
    return await deactivate_user(session, current_user, user_id)
