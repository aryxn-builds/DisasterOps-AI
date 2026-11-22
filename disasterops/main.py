import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from .config import Settings
from .models import Account
from .routers import auth, citizen, location, rescue, sms

ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger("uvicorn.error")


def create_app(
    settings: Settings | None = None, engine: Engine | None = None
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        from .models import Base
        from sqlalchemy.orm import Session
        from .services.auth import password_hasher

        config = settings or Settings()
        db_url = config.postgres_url()
        is_sqlite = db_url.startswith("sqlite")
        connect_args = {"check_same_thread": False} if is_sqlite else {}

        db_engine = engine or create_engine(
            db_url,
            hide_parameters=True,
            pool_pre_ping=not is_sqlite,
            connect_args=connect_args,
        )
        try:
            Base.metadata.create_all(db_engine)
            with Session(db_engine) as session:
                if not session.scalar(select(Account.id).limit(1)):
                    session.add_all([
                        Account(username="rescue123", role="dispatcher", password_hash=password_hasher.hash("RSC123"), phone="+919811223344"),
                        Account(username="keshav45", role="citizen", password_hash=password_hasher.hash("password123"), phone="+919876543210"),
                        Account(username="keshav99", role="citizen", password_hash=password_hasher.hash("password123"), phone="+919876543210"),
                    ])
                    session.commit()

            with db_engine.connect() as conn:
                conn.execute(select(Account.id).limit(1))
            app.state.engine = db_engine
            app.state.settings = config
            yield
        finally:
            if engine is None:
                db_engine.dispose()

    app = FastAPI(
        title="DisasterOps AI research prototype", version="0.1.0", lifespan=lifespan
    )

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, exc: RequestValidationError):
        # FastAPI's default validation response may echo passwords, coordinates or SMS content.
        return JSONResponse({"detail": "Invalid request data"}, status_code=422)

    @app.exception_handler(SQLAlchemyError)
    async def storage_error(request: Request, exc: SQLAlchemyError):
        logger.error(
            json.dumps(
                {
                    "event": "database_error",
                    "request_id": request.state.request_id,
                    "error_type": type(exc).__name__,
                }
            )
        )
        return JSONResponse(
            {"detail": "Storage temporarily unavailable"}, status_code=503
        )

    @app.middleware("http")
    async def secure_request(request: Request, call_next):
        request.state.request_id = str(uuid4())
        api = request.url.path.startswith("/api/")
        origin = request.headers.get("origin")
        if (
            api
            and request.method not in {"GET", "HEAD", "OPTIONS"}
            and (
                (
                    origin is not None
                    and origin != request.app.state.settings.server_public_url
                )
                or request.headers.get("sec-fetch-site") in {"cross-site", "same-site"}
            )
        ):
            response = JSONResponse(
                {"detail": "Cross-origin request denied"}, status_code=403
            )
        else:
            response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if api or request.url.path == "/share-location":
            response.headers["Cache-Control"] = "no-store"
        if api:
            route = request.scope.get("route")
            logger.info(
                json.dumps(
                    {
                        "event": "api_request",
                        "request_id": request.state.request_id,
                        "method": request.method,
                        "route": getattr(route, "path", None),
                        "status": response.status_code,
                    }
                )
            )
        return response

    for router in (auth, citizen, rescue, sms, location):
        app.include_router(router.router, prefix="/api/v1")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(
            ROOT / "index.html",
            headers={
                "Referrer-Policy": "strict-origin",
                "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' https://unpkg.com/leaflet@1.9.4/dist/leaflet.js; "
                "style-src 'self' 'unsafe-inline' https://unpkg.com/leaflet@1.9.4/dist/leaflet.css; "
                "img-src 'self' data: https://tile.openstreetmap.org; "
                "object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
            },
        )

    @app.get("/registration", include_in_schema=False)
    @app.get("/registration.html", include_in_schema=False)
    def registration():
        return RedirectResponse("/#register")

    @app.get("/share-location", include_in_schema=False)
    def share_location():
        return FileResponse(
            ROOT / "share_location.html",
            headers={
                "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; "
                "style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'"
            },
        )

    @app.get("/sw.js", include_in_schema=False)
    def service_worker():
        return FileResponse(
            ROOT / "sw.js",
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache"},
        )

    @app.get("/app.js", include_in_schema=False)
    def frontend_script():
        return FileResponse(ROOT / "app.js", media_type="application/javascript")

    @app.get("/styles.css", include_in_schema=False)
    def styles():
        return FileResponse(ROOT / "styles.css", media_type="text/css")

    @app.get("/api/v1/config")
    def config(request: Request):
        return {
            "gateway_number": request.app.state.settings.emergency_sms_gateway_number
        }

    return app
