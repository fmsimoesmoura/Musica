"""Response DTOs for the HTTP API. Decouples the wire format from domain
entities, and from the persistence rows. Domain dataclasses convert cleanly via
dataclasses.asdict at the router boundary, so for M1 these are thin."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any


def to_dict(entity: Any) -> dict:
    return asdict(entity)


def to_list(entities: list) -> list[dict]:
    return [asdict(e) for e in entities]
