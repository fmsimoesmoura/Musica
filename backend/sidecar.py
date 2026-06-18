"""PyInstaller entrypoint for the bundled sidecar binary.

PyInstaller bundles a script, not a package module, so this thin wrapper imports
and runs the FastAPI app's `main()` (which parses --port/--host and starts uvicorn).
"""
from app.main import main

if __name__ == "__main__":
    main()
