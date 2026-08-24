"""Import every model so SQLAlchemy registers the complete schema."""

from app.database.base import Base
from app.models.booking import Booking
from app.models.event import Category, Event, EventTag, Tag
from app.models.log import Log
from app.models.notification import Notification
from app.models.rbac import Permission, Role, RolePermission
from app.models.refresh_token import RefreshToken
from app.models.review import Reply, Review
from app.models.user import User

__all__ = [
    "Base",
    "Booking",
    "Category",
    "Event",
    "EventTag",
    "Log",
    "Notification",
    "Permission",
    "RefreshToken",
    "Reply",
    "Review",
    "Role",
    "RolePermission",
    "Tag",
    "User",
]
