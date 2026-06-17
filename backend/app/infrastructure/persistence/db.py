"""SQLite engine + schema creation."""
from __future__ import annotations

from sqlmodel import SQLModel, create_engine

from ...config import DB_PATH
from . import tables  # noqa: F401  (registers tables on SQLModel.metadata)

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
