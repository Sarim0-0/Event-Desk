from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    ORGANIZER = "organizer"
    ATTENDEE = "attendee"


class BookingStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class ReplyRole(str, Enum):
    ORGANIZER = "organizer"
    ADMIN = "admin"


class EventStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class NotificationType(str, Enum):
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_CANCELLED = "booking_cancelled"
    EVENT_CANCELLED = "event_cancelled"
    EVENT_REVIEWED = "event_reviewed"
    REVIEW_REPLIED = "review_replied"


class NotificationContextFilter(str, Enum):
    ALL = "all"
    BOOKING = "booking"
    REVIEW = "review"
