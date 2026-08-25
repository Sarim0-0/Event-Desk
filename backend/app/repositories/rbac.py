from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Permission, RolePermission


async def role_has_permission(
    session: AsyncSession,
    role_id: UUID,
    permission_key: str,
) -> bool:
    permission_table = Permission.__table__
    role_permission_table = RolePermission.__table__

    statement = select(
        exists().where(
            role_permission_table.c.role_id == role_id,
            role_permission_table.c.permission_id == permission_table.c.id,
            permission_table.c.key == permission_key,
        )
    )
    return bool(await session.scalar(statement))
