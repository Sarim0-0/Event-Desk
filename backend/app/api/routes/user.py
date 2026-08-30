from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import DatabaseSession, require_permission
from app.core.permissions import CHANGE_OWN_PASSWORD, UPDATE_OWN_PROFILE
from app.models.user import User
from app.schemas.user import (
    PasswordChangeRequest,
    UserProfileUpdate,
    UserResponse,
)
from app.services.user import change_own_password, update_own_profile


router = APIRouter(prefix="/users", tags=["Users"])


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
