"""FastAPI app entrypoint for the Tidal Manager sidecar.

Run in dev:   uv run uvicorn app.main:app --port 8765
Packaged:     bundled by PyInstaller and launched by the Tauri shell with --port.
"""
from __future__ import annotations

import argparse
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .composition import container
from .config import DEFAULT_PORT
from .infrastructure.persistence.db import init_db
from .interface.http.routers import auth, catalog, discovery, lib, providers, settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    c = container()  # builds the active provider's container (creates its DB)
    init_db(c.provider)
    if c.restore_session():
        log.info("Restored %s session for %s", c.provider, c.get_status().user_name)
    else:
        log.info("No stored %s session; awaiting login.", c.provider)
    yield


app = FastAPI(title="Music Manager", version="0.1.0", lifespan=lifespan)

# Local-only sidecar bound to 127.0.0.1; permissive CORS for the Tauri/Vite origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth)
app.include_router(lib)
app.include_router(catalog)
app.include_router(discovery)
app.include_router(providers)
app.include_router(settings)


@app.get("/health")
def health():
    return {"ok": True}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
