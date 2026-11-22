"""Compatibility entry point for the modular DisasterOps backend."""

from disasterops.main import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="127.0.0.1", port=8000, access_log=False)
