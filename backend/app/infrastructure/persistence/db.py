"""SQLite engines — one DB file per provider, each created on first use."""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy import inspect, text
from sqlmodel import SQLModel, create_engine

from ...config import db_path_for
from . import tables  # noqa: F401  (registers tables on SQLModel.metadata)

# Columns added after the first release — applied to existing DBs via ALTER so a
# user's imported library isn't wiped on upgrade (values backfill on next re-sync).
_ADDED_COLUMNS = {
    "track": [("image", "VARCHAR"), ("explicit", "BOOLEAN")],
}


def _migrate(engine) -> None:
    insp = inspect(engine)
    existing = set(insp.get_table_names())
    for table, cols in _ADDED_COLUMNS.items():
        if table not in existing:
            continue
        present = {c["name"] for c in insp.get_columns(table)}
        with engine.begin() as conn:
            for name, sqltype in cols:
                if name not in present:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sqltype}"))


@lru_cache(maxsize=None)
def engine_for(provider: str):
    eng = create_engine(
        f"sqlite:///{db_path_for(provider)}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(eng)
    _migrate(eng)
    return eng


def init_db(provider: str) -> None:
    engine_for(provider)
