from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.core.ledger import set_ledger_poster
from app.core.responses import register_exception_handlers
from app.modules.accounting.poster import RealLedgerPoster

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
)

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
