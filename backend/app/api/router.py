from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.booking import router as booking_router
from app.api.routes.event import router as event_router
from app.api.routes.reply import router as reply_router
from app.api.routes.review import router as review_router


api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(booking_router)
api_router.include_router(event_router)
api_router.include_router(review_router)
api_router.include_router(reply_router)
