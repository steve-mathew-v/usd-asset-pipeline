"""MongoDB Atlas connection.

The client is created lazily (on first use) rather than at import time, so it
binds to the event loop that actually serves requests. Creating it at import
time binds it to the wrong loop and causes "attached to a different loop"
errors under uvicorn / Docker.
"""

import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket

load_dotenv()

_client = None


def get_db():
    """Return the database, creating the client on first call."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    return _client[os.getenv("DB_NAME")]


def get_bucket() -> AsyncIOMotorGridFSBucket:
    """Return a GridFS bucket for file storage."""
    return AsyncIOMotorGridFSBucket(get_db())
