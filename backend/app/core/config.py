from functools import lru_cache
from typing import Annotated

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "Vineflow Invoicing API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql+psycopg://vineflow:vineflow@localhost:5433/vineflow"

    JWT_SECRET: str = "change-me-to-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PUBLIC_REGISTRATION_ENABLED: bool = False
    SELF_SERVICE_ORG_CREATION_ENABLED: bool = False

    REFRESH_COOKIE_NAME: str = "vf_refresh"
    REFRESH_COOKIE_PATH: str = "/api/v1/auth"
    REFRESH_COOKIE_SECURE: bool = False
    REFRESH_COOKIE_SAMESITE: str = "lax"
    REFRESH_COOKIE_DOMAIN: str | None = None

    SUPER_ADMIN_REFRESH_COOKIE_NAME: str = "vf_super_admin_refresh"
    SUPER_ADMIN_REFRESH_COOKIE_PATH: str = "/api/v1/super-admin/auth"

    # Keep the customer and separately hosted super-admin frontends explicit.
    BACKEND_CORS_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:3005",
        "http://localhost:3010",
    ]

    GOTENBERG_URL: str = "http://localhost:3009"

    FBR_BASE_URL: str = "https://gw.fbr.gov.pk"
    FBR_ENCRYPTION_KEY: str = ""
    FBR_REFERENCE_TOKEN: str = ""

    STORAGE_BACKEND: str = "local" # local | S3
    MEDIA_LOCAL_DIR: str = "media_storage"
    MEDIA_PUBLIC_URL: str = "http://localhost:8005"
    MAX_UPLOAD_MB: int = 5
    S3_BUCKET: str | None = None
    S3_REGION: str | None = None
    S3_ENDPOINT_URL: str | None = None
    S3_PUBLIC_URL: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    # Object-key prefix, e.g. "local/" so dev uploads are isolated from prod ("").
    MEDIA_KEY_PREFIX: str = ""

    # Reverse proxies we run in front of the app. Only their X-Forwarded-For
    # hops are trusted when identifying a client for rate limiting.
    TRUSTED_PROXY_COUNT: int = 0

    CELERY_TASK_ALWAYS_EAGER: bool = True
    SQS_QUEUE_NAME: str = "vineflow-jobs"
    SQS_QUEUE_URL: str | None = None
    SQS_REGION: str | None = None
    CELERY_VISIBILITY_TIMEOUT: int = 3600

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def _enforce_prod_security(self) -> "Settings":
        if self.ENVIRONMENT != "production":
            return self
        if self.JWT_SECRET == "change-me-to-a-long-random-string" or len(self.JWT_SECRET) < 32:
            raise ValueError("JWT_SECRET must be a strong (>= 32 char) secret in production")
        if not self.REFRESH_COOKIE_SECURE:
            raise ValueError("REFRESH_COOKIE_SECURE must be true in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
