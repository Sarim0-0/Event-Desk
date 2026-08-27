from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import ApplicationError


async def application_error_handler(
    _: Request,
    error: ApplicationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"detail": str(error)},
        headers=error.headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        ApplicationError,
        application_error_handler,
    )
