"""SQLite engines — one DB file per provider, each created on first use."""
from __future__ import annotations

from functools import lru_cache

from sqlmodel import SQLModel, create_engine

from ...config import db_path_for
from . import tables  # noqa: F401  (registers tables on SQLModel.metadata)


@lru_cache(maxsize=None)
def engine_for(provider: str):
    eng = create_engine(
        f"sqlite:///{db_path_for(provider)}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(eng)
    return eng


def init_db(provider: str) -> None:
    engine_for(provider)
