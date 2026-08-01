from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import PayloadTooLargeError, RateLimitError
from app.core.ledger import set_ledger_poster
from app.core.ratelimit import limiter
from app.core.responses import app_error_handler, register_exception_handlers
from app.db.session import engine
from app.modules.accounting.poster import RealLedgerPoster

_docs_enabled = settings.ENVIRONMENT != "production"

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if _docs_enabled else None,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
)

app.state.limiter = limiter


async def _rate_limit_handler(request, exc: RateLimitExceeded):
    return await app_error_handler(
        request, RateLimitError("Too many requests. Please slow down and try again.")
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

_MAX_BODY_BYTES = settings.MAX_UPLOAD_MB * 1024 * 1024 + 1024 * 1024


@app.middleware("http")
async def _limit_request_body(request, call_next):
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > _MAX_BODY_BYTES:
        return await app_error_handler(
            request, PayloadTooLargeError("Request body exceeds the allowed size.")
        )
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

# Bind the real GL poster so finalizing documents / submitting payments post to Books.
set_ledger_poster(RealLedgerPoster())

# Serve locally-stored uploads in dev (S3 serves its own URLs in production).
if settings.STORAGE_BACKEND == "local":
    _media_dir = Path(settings.MEDIA_LOCAL_DIR)
    _media_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media/files", StaticFiles(directory=_media_dir), name="media")

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
def ready() -> dict[str, str]:
    """Report readiness only after the database accepts a query."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready"}
