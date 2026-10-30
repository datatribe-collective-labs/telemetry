"""Entry point for the Telemetry API backend."""

import uvicorn


def main():
    """Run the FastAPI application with Uvicorn."""
    uvicorn.run(
        "backend.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()