"""Consistent JSON errors that do not leak paths or secrets."""

import logging
import re

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


logger = logging.getLogger("gist.api")
_PRIVATE_TEXT = re.compile(r"(/|\\|\.env|api[_ ]?key|token|secret)", re.IGNORECASE)


class APIError(Exception):
    """An error with a public message and an HTTP status."""

    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


def public_message(message):
    """Hide filesystem paths and secrets from a stored error string."""

    if not message:
        return None
    if _PRIVATE_TEXT.search(message):
        return "The document could not be ingested."
    return message[:300]


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(APIError)
    async def api_error(_request: Request, exc: APIError):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.message})

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(status_code=exc.status_code, content={"error": detail})

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, _exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"error": "Request validation failed."},
        )

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, exc: Exception):
        logger.exception("Unhandled API error")
        return JSONResponse(
            status_code=500,
            content={"error": "An unexpected error occurred."},
        )
