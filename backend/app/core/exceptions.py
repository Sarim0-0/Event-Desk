from collections.abc import Mapping


class ApplicationError(Exception):
    """An expected application error that can be returned safely to clients."""

    status_code = 500
    headers: Mapping[str, str] | None = None


class AuthenticationError(ApplicationError):
    status_code = 401
    headers = {"WWW-Authenticate": "Bearer"}


class ForbiddenError(ApplicationError):
    status_code = 403


class NotFoundError(ApplicationError):
    status_code = 404


class ConflictError(ApplicationError):
    status_code = 409


class ServiceUnavailableError(ApplicationError):
    status_code = 503
