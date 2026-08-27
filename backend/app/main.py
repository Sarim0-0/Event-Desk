from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database.session import dispose_database_engine

# Import every model module before the application handles database queries.
# This replaces a separate model-registry file for runtime mapper configuration.
import app.models.booking
import app.models.event
import app.models.log
import app.models.notification
import app.models.rbac
import app.models.refresh_token
import app.models.review
import app.models.user
from app.routers.auth import router as auth_router
from app.routers.booking import router as booking_router
from app.routers.event import router as event_router
from app.routers.reply import router as reply_router
from app.routers.review import router as review_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_database_engine()


app = FastAPI(title="EventDesk API", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(booking_router)
app.include_router(event_router)
app.include_router(review_router)
app.include_router(reply_router)
