"""API endpoints for uploading, downloading and versioning USD assets.

Each asset keeps a full history of versions. Uploading the same asset again
adds a new version rather than overwriting; a specific version is then
"approved" for other artists to consume (latest, or a pinned version).
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

import database
import storage

load_dotenv()

router = APIRouter()

# USD file formats we accept (crate, ascii, generic, zipped)
USD_EXTS = (".usd", ".usda", ".usdc", ".usdz")


def _assets():
    """Return the assets collection, resolved per-call so the DB client
    binds to the request's event loop (avoids cross-loop errors)."""
    return database.get_db()["assets"]


def _split_ext(filename: str) -> tuple[str, str]:
    """Split a USD filename into (name, extension), or raise if not USD."""
    lower = filename.lower()
    for ext in USD_EXTS:
        if lower.endswith(ext):
            return filename[: -len(ext)], filename[-len(ext):]
    raise HTTPException(status_code=400, detail="only USD files allowed")


@router.post("/auth/login")
async def login(credentials: dict) -> dict:
    """Check a username/password against the root account or Atlas users."""
    username = credentials.get("username")
    password = credentials.get("password")

    if username == os.getenv("ROOT_USER") and password == os.getenv("ROOT_PASS"):
        return {"success": True}

    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        host = os.getenv("MONGO_URI").split("@", 1)[1]
        client = AsyncIOMotorClient(
            f"mongodb+srv://{username}:{password}@{host}",
            serverSelectionTimeoutMS=4000,
        )
        await client[os.getenv("DB_NAME")].list_collection_names()
        client.close()
        return {"success": True}
    except Exception:
        raise HTTPException(status_code=401, detail="invalid credentials")


@router.post("/assets/upload")
async def upload_asset(
    file: UploadFile = File(...),
    source_tool: str = "Maya",
    uploaded_by: str = "unknown",
) -> dict:
    """Upload a USD file as a new version of an asset.

    The first upload of a name creates version 1; each later upload of the
    same name adds the next version. Nothing is overwritten.
    """
    name, ext = _split_ext(file.filename)

    asset = await _assets().find_one({"name": name})
    version = (asset["latest_version"] + 1) if asset else 1

    await storage.save_file(f"{name}/v{version}{ext}", await file.read())

    entry = {
        "version": version,
        "ext": ext,
        "uploaded_by": uploaded_by,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    if asset:
        await _assets().update_one(
            {"name": name},
            {
                "$push": {"versions": entry},
                "$set": {"latest_version": version, "source_tool": source_tool},
            },
        )
    else:
        await _assets().insert_one(
            {
                "name": name,
                "source_tool": source_tool,
                "latest_version": version,
                "approved_version": None,
                "versions": [entry],
            }
        )

    return {"message": f"{file.filename} uploaded as v{version}", "version": version}


@router.get("/assets")
async def get_assets() -> list[dict]:
    """List every asset with its version history."""
    assets = await _assets().find().to_list(100)
    for asset in assets:
        asset["_id"] = str(asset["_id"])
    return assets


@router.get("/assets/ready")
async def get_ready_assets() -> list[dict]:
    """List assets that have an approved version ready to consume."""
    assets = await _assets().find({"approved_version": {"$ne": None}}).to_list(100)
    for asset in assets:
        asset["_id"] = str(asset["_id"])
    return assets


@router.get("/assets/{name}/versions")
async def get_versions(name: str) -> dict:
    """Return the full version history of one asset."""
    asset = await _assets().find_one({"name": name})
    if not asset:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "name": name,
        "latest_version": asset["latest_version"],
        "approved_version": asset.get("approved_version"),
        "versions": asset["versions"],
    }


@router.get("/assets/download/{name}")
async def download_asset(name: str, version: int | None = None) -> Response:
    """Download a USD asset: the approved version by default, or a pinned one."""
    asset = await _assets().find_one({"name": name})
    if not asset:
        raise HTTPException(status_code=404, detail="not found")

    wanted = version if version is not None else asset.get("approved_version")
    if wanted is None:
        raise HTTPException(status_code=404, detail="no approved version")

    entry = next((e for e in asset["versions"] if e["version"] == wanted), None)
    if entry is None:
        raise HTTPException(status_code=404, detail="version not found")

    data = await storage.read_file(f"{name}/v{wanted}{entry['ext']}")
    if data is None:
        raise HTTPException(status_code=404, detail="file missing on server")
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{name}{entry["ext"]}"'},
    )


@router.patch("/assets/{name}/approve")
async def approve_asset(name: str, version: int | None = None) -> dict:
    """Approve a version for others to consume (defaults to the latest)."""
    asset = await _assets().find_one({"name": name})
    if not asset:
        raise HTTPException(status_code=404, detail="not found")

    wanted = version if version is not None else asset["latest_version"]
    if not any(e["version"] == wanted for e in asset["versions"]):
        raise HTTPException(status_code=404, detail="version not found")

    await _assets().update_one(
        {"name": name}, {"$set": {"approved_version": wanted}}
    )
    return {"message": f"{name} v{wanted} approved"}


@router.patch("/assets/{name}/unapprove")
async def unapprove_asset(name: str) -> dict:
    """Take an asset out of the approved pool."""
    result = await _assets().update_one(
        {"name": name}, {"$set": {"approved_version": None}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="not found")
    return {"message": f"{name} unapproved"}


@router.post("/assets/{name}/thumbnail/{view}")
async def upload_thumbnail(
    name: str, view: str, version: int, file: UploadFile = File(...)
) -> dict:
    """Store a front or top screenshot for a specific version of an asset."""
    if view not in ("front", "top"):
        raise HTTPException(status_code=400, detail="view must be front or top")
    await storage.save_file(f"{name}/v{version}_{view}.jpg", await file.read())
    return {"message": f"{view} thumbnail saved for {name} v{version}"}


@router.get("/assets/{name}/thumbnail/{view}")
async def get_thumbnail(name: str, view: str, version: int | None = None) -> Response:
    """Send a thumbnail: for the approved version by default, or a pinned one."""
    asset = await _assets().find_one({"name": name})
    if not asset:
        raise HTTPException(status_code=404, detail="not found")
    wanted = version
    if wanted is None:
        wanted = asset.get("approved_version") or asset["latest_version"]
    data = await storage.read_file(f"{name}/v{wanted}_{view}.jpg")
    if data is None:
        raise HTTPException(status_code=404, detail="not found")
    return Response(content=data, media_type="image/jpeg")


@router.delete("/assets/{name}")
async def delete_asset(name: str) -> dict:
    """Remove an asset entirely: every version, its thumbnails and the record."""
    asset = await _assets().find_one({"name": name})
    if not asset:
        raise HTTPException(status_code=404, detail="not found")
    for entry in asset["versions"]:
        version = entry["version"]
        await storage.delete_file(f"{name}/v{version}{entry['ext']}")
        for view in ("front", "top"):
            await storage.delete_file(f"{name}/v{version}_{view}.jpg")
    await _assets().delete_one({"name": name})
    return {"message": f"{name} deleted"}
