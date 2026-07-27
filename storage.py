"""File storage backed by MongoDB GridFS.

The server keeps no files on its own disk, so uploaded assets and thumbnails
live in the database and survive restarts. This is what lets the server run
on an ephemeral cloud host (e.g. Render) without losing files.
"""

from gridfs.errors import NoFile

from database import get_bucket


async def save_file(key: str, data: bytes) -> None:
    """Store bytes under a key, replacing anything already stored there."""
    await delete_file(key)
    await get_bucket().upload_from_stream(key, data)


async def read_file(key: str) -> bytes | None:
    """Return the bytes stored under key, or None if there is nothing there."""
    try:
        stream = await get_bucket().open_download_stream_by_name(key)
    except NoFile:
        return None
    return await stream.read()


async def delete_file(key: str) -> None:
    """Delete whatever is stored under key (normally a single file)."""
    bucket = get_bucket()
    async for grid_file in bucket.find({"filename": key}):
        await bucket.delete(grid_file._id)
