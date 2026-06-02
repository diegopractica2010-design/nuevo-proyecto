from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-32-chars-for-ci-only")

from backend.auth import pwd_context  # noqa: E402
from backend.db import Base, SessionLocal, get_db  # noqa: E402
from backend.infrastructure.db.models import UserRecord  # noqa: E402
from backend.main import app  # noqa: E402


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    test_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    with test_engine.begin() as connection:
        alembic_cfg.attributes["connection"] = connection
        command.upgrade(alembic_cfg, "head")

    yield test_engine

    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture()
def db_session(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, autoflush=False, autocommit=False)
    nested = connection.begin_nested()
    previous_bind = SessionLocal.kw.get("bind")
    SessionLocal.configure(bind=connection)

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session_: Session, transaction_) -> None:
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        event.remove(session, "after_transaction_end", restart_savepoint)
        session.close()
        transaction.rollback()
        connection.close()
        SessionLocal.configure(bind=previous_bind)


@pytest.fixture()
async def client(db_session: Session) -> AsyncIterator[AsyncClient]:
    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


_TEST_PASSWORD = "Test@Secure1234!"  # meets new policy: 12+ chars, uppercase, digit, special


@pytest.fixture()
def test_user(db_session: Session) -> UserRecord:
    user = UserRecord(
        username="testuser",
        email="testuser@example.com",
        hashed_password=pwd_context.hash(_TEST_PASSWORD),
        role="user",
        is_verified=True,  # required so authenticate_user doesn't reject the user
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    await client.post(
        "/auth/register",
        json={
            "username": "authuser",
            "email": "authuser@example.com",
            "password": _TEST_PASSWORD,
        },
    )
    response = await client.post(
        "/auth/login",
        json={"username": "authuser", "password": _TEST_PASSWORD},
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
