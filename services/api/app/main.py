from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from redis import Redis
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from app.api.conversions import router
from app.core.config import Settings
from app.core.errors import Problem
from app.core.http import RequestSafety
from app.models.database import Database
from app.services.jobs import JobRepository
from app.services.storage import Storage


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        database = Database(settings)
        try:
            if settings.auto_create_schema:
                database.initialize()
            else:
                database.check_schema()
            application.state.settings = settings
            application.state.database = database
            application.state.repository = JobRepository(database, settings)
            application.state.storage = Storage(settings)
            yield
        finally:
            database.engine.dispose()

    application = FastAPI(
        title="ConvX API", version="0.2.0", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None
    )
    application.add_middleware(RequestSafety, settings=settings)

    @application.exception_handler(Problem)
    async def problem_handler(request: Request, exc: Problem):
        return JSONResponse(
            {"error": {"code": exc.code, "message": exc.message, "request_id": request.state.request_id}},
            status_code=exc.status,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            {
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Invalid request parameters",
                    "request_id": request.state.request_id,
                }
            },
            status_code=422,
        )

    @application.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        return JSONResponse(
            {
                "error": {
                    "code": "DATABASE_UNAVAILABLE",
                    "message": "Job storage is unavailable",
                    "request_id": request.state.request_id,
                }
            },
            status_code=503,
        )

    @application.get("/api/v1/health")
    def health():
        return {"status": "alive"}

    @application.get("/api/v1/readiness")
    async def readiness(request: Request):
        def probe():
            checks = {"database": False, "storage": False, "broker": False, "admission_worker": False}
            try:
                request.app.state.database.check_schema()
                checks["database"] = True
                checks["admission_worker"] = request.app.state.repository.live_workers()
            except Exception:
                checks["database"] = False
            try:
                # Check write/read/delete permissions without exposing paths.
                import tempfile

                with tempfile.TemporaryFile(dir=request.app.state.storage.root) as scratch:
                    scratch.write(b"probe")
                    scratch.flush()
                checks["storage"] = True
            except OSError:
                pass
            try:
                with Redis.from_url(
                    settings.redis_url.get_secret_value(), socket_connect_timeout=0.5, socket_timeout=0.5
                ) as client:
                    checks["broker"] = bool(client.ping())
            except Exception:
                checks["broker"] = False
            return checks

        checks = await run_in_threadpool(probe)
        # Full conversion readiness remains false until all later pipeline gates are implemented.
        return JSONResponse(
            {
                "ready": False,
                "foundation_ready": all(checks.values()),
                "conversion_ready": False,
                "checks": checks,
                "code": "PIPELINE_NOT_AVAILABLE",
            },
            status_code=503,
        )

    application.include_router(router)
    return application
