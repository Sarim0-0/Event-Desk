"""Single import point that registers the complete EventDesk ORM schema."""

from app.db.base import Base
from app.modules.audit.models import Log
from app.modules.auth.models import RefreshToken
from app.modules.bookings.models import Booking
from app.modules.events.models import Category, Event, EventTag, Tag
from app.modules.notifications.models import Notification
from app.modules.rbac.models import Permission, Role, RolePermission
from app.modules.reviews.models import Reply, Review
from app.modules.users.models import User

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
