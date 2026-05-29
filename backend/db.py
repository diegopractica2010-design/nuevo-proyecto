from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.config import DATA_DIR, DATABASE_URL


class Base(DeclarativeBase):
    pass


def _connect_args() -> dict:
    if DATABASE_URL.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def _engine_kwargs() -> dict:
    if DATABASE_URL in {"sqlite:///:memory:", "sqlite+pysqlite:///:memory:"}:
        return {"poolclass": StaticPool}
    return {}


DATA_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args=_connect_args(), **_engine_kwargs())
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    from backend.infrastructure.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db():
    with SessionLocal() as session:
        yield session


def reset_db() -> None:
    from backend.infrastructure.db import models  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
