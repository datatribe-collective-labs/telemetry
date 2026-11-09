"""Entry point for the Telemetry API backend (native dev: `python -m backend.main`).

The Docker image runs uvicorn directly (see packages/backend/Dockerfile).
"""

import os

import uvicorn


def main():
    """Run the FastAPI application with Uvicorn.

    Auto-reload is off unless BACKEND_RELOAD=1: its file-watcher parent can die and
    leave the worker process holding port 8000.
    """
    uvicorn.run(
        "backend.api:app",
        host="0.0.0.0",
        port=8000,
        reload=os.environ.get("BACKEND_RELOAD") == "1",
    )


if __name__ == "__main__":
    main()
