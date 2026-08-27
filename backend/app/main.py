from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
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
from app.api.exception_handlers import register_exception_handlers
from app.api.router import api_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_database_engine()


app = FastAPI(title="EventDesk API", lifespan=lifespan)
register_exception_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Accept", "Authorization", "Content-Type"],
)
app.include_router(api_router)
