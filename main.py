"""FastAPI entry point for the OBJ pipeline server."""

from fastapi import FastAPI

from routes import router

app = FastAPI(title="OBJ Pipeline")
app.include_router(router, prefix="/api")


@app.get("/")
async def root() -> dict:
    """Health check so clients can tell the server is up."""
    return {"status": "running"}
