from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from time import monotonic
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.imports import router as imports_router
from app.api.instruments import router as instruments_router
from app.api.market_data import router as market_data_router
from app.api.portfolios import router as portfolios_router
from app.api.settings import router as settings_router
from app.api.sources import router as sources_router
from app.api.system_status import router as system_status_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging, request_id_var
from app.core.metrics import observe
from app.core.metrics import router as metrics_router

configure_logging()
logger = logging.getLogger(__name__)
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Investment Intelligence API", version="0.1.0", debug=settings.app_debug)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-Request-ID", "X-Filename"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, error: AppError) -> JSONResponse:
        headers = {"Cache-Control": "no-store"}
        if error.retry_after is not None:
            headers["Retry-After"] = str(error.retry_after)
        return JSONResponse(
            status_code=error.status_code,
            content={"error": {"code": error.code, "message": error.message}},
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, _error: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VALIDATION_ERROR", "message": "Invalid request"}},
            headers={"Cache-Control": "no-store"},
        )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if REQUEST_ID_PATTERN.fullmatch(incoming) else str(uuid4())
        token = request_id_var.set(request_id)
        started = monotonic()
        response: Response
        try:
            if request.method in {"POST", "PATCH", "PUT", "DELETE"} and request.url.path.startswith(
                "/api/v1/"
            ):
                origin = request.headers.get("Origin")
                if origin is not None and origin not in {
                    settings.frontend_origin,
                    settings.api_public_origin,
                }:
                    response = JSONResponse(
                        status_code=403,
                        content={
                            "error": {"code": "CSRF_REJECTED", "message": "Invalid request origin"}
                        },
                        headers={"Cache-Control": "no-store"},
                    )
                elif origin is None and request.headers.get("Sec-Fetch-Site") in {
                    "cross-site",
                    "same-site",
                }:
                    response = JSONResponse(
                        status_code=403,
                        content={
                            "error": {"code": "CSRF_REJECTED", "message": "Invalid request origin"}
                        },
                        headers={"Cache-Control": "no-store"},
                    )
                else:
                    response = await call_next(request)
            else:
                response = await call_next(request)
        except Exception:
            logger.exception("unhandled request error")
            response = JSONResponse(
                status_code=500,
                content={"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}},
            )
        finally:
            request_id_var.reset(token)
        route = request.scope.get("route")
        route_path = getattr(route, "path", "unmatched")
        observe(request.method, route_path, response.status_code, monotonic() - started)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.url.path.startswith(("/api/v1/auth/", "/api/v1/settings")):
            response.headers["Cache-Control"] = "no-store"
        return response

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(settings_router)
    app.include_router(instruments_router)
    app.include_router(sources_router)
    app.include_router(imports_router)
    app.include_router(market_data_router)
    app.include_router(portfolios_router)
    app.include_router(system_status_router)
    app.include_router(metrics_router)
    return app


app = create_app()
