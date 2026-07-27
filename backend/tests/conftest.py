from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.ratelimit import limiter
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.rbac.service import RbacService

# The suite registers an org per test; the /auth/register rate limit would throttle it.
limiter.enabled = False

_BASE_URL = settings.DATABASE_URL.rsplit("/", 1)[0]
TEST_DB_NAME = "vineflow_test"
TEST_DB_URL = f"{_BASE_URL}/{TEST_DB_NAME}"


@pytest.fixture(scope="session", autouse=True)
def _create_test_database() -> Iterator[None]:
    admin = create_engine(f"{_BASE_URL}/postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": TEST_DB_NAME}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin.dispose()
    yield


@pytest.fixture(scope="session")
def engine(_create_test_database):
    eng = create_engine(TEST_DB_URL, pool_pre_ping=True, future=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine) -> Iterator[Session]:
    """A session in a transaction that rolls back after each test.

    `join_transaction_mode="create_savepoint"` turns the service-layer commits
    into savepoints, so the outer rollback fully isolates every test.
    """
    connection = engine.connect()
    trans = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    RbacService(session).seed_permissions()
    session.flush()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()


@pytest.fixture()
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# --- Convenience fixtures (no cross-module imports needed) -----------------

@pytest.fixture()
def register(client: TestClient) -> Callable[..., str]:
    def _register(email: str = "owner@test.io", org: str = "Test Co", password: str = "password123") -> str:
        res = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "User", "org_name": org},
        )
        assert res.status_code == 201, res.text
        return res.json()["data"]["access_token"]

    return _register


@pytest.fixture()
def org_id_of(client: TestClient) -> Callable[[str], int]:
    def _org_id(token: str) -> int:
        res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        return res.json()["data"]["memberships"][0]["org_id"]

    return _org_id


@pytest.fixture()
def h() -> Callable[..., dict[str, str]]:
    def _headers(token: str, org_id: int | None = None) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {token}"}
        if org_id is not None:
            headers["X-Org-Id"] = str(org_id)
        return headers

    return _headers
