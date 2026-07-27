"""API endpoints for uploading, downloading and managing .obj assets."""

import os

from dotenv import load_dotenv
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

import database
import storage
from models import ObjAsset

load_dotenv()

router = APIRouter()


def _assets():
    """Return the assets collection, resolved per-call so the DB client
    binds to the request's event loop (avoids cross-loop errors)."""
    return database.get_db()["assets"]


@router.post("/auth/login")
async def login(credentials: dict) -> dict:
    """Check a username/password against the root account or Atlas users.

    Root credentials come from the .env file. Anything else is checked by
    trying an actual MongoDB connection with those credentials.
    """
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


@router.post("/assets")
async def add_asset(asset: ObjAsset) -> dict:
    """Register an asset entry directly (without a file upload)."""
    result = await _assets().insert_one(asset.dict())
    return {"id": str(result.inserted_id)}


@router.post("/assets/upload")
async def upload_asset(
    file: UploadFile = File(...),
    source_tool: str = "Maya",
    ready: bool = False,
    uploaded_by: str = "unknown",
) -> dict:
    """Save an uploaded .obj file and record it in the database.

    Re-uploading an asset with the same name replaces the old entry.
    """
    if not file.filename.endswith(".obj"):
        raise HTTPException(status_code=400, detail="only .obj files allowed")

    await storage.save_file(file.filename, await file.read())

    name = file.filename.replace(".obj", "")
    await _assets().delete_one({"name": name})
    await _assets().insert_one(
        {
            "name": name,
            "source_tool": source_tool,
            "tags": [],
            "ready": ready,
            "uploaded_by": uploaded_by,
        }
    )

    return {"message": f"{file.filename} uploaded"}


@router.get("/assets/download/{name}")
async def download_asset(name: str) -> Response:
    """Send the stored .obj file for an asset back to the client."""
    asset = await _assets().find_one({"name": name})
    if not asset:
        raise HTTPException(status_code=404, detail="not found")
    data = await storage.read_file(f"{name}.obj")
    if data is None:
        raise HTTPException(status_code=404, detail="file missing on server")
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{name}.obj"'},
    )


@router.get("/assets")
async def get_assets() -> list[dict]:
    """List every asset in the database."""
    assets = await _assets().find().to_list(100)
    for asset in assets:
        asset["_id"] = str(asset["_id"])
    return assets


@router.get("/assets/ready")
async def get_ready_assets() -> list[dict]:
    """List only the assets that are marked as ready."""
    assets = await _assets().find({"ready": True}).to_list(100)
    for asset in assets:
        asset["_id"] = str(asset["_id"])
    return assets


@router.patch("/assets/{name}/ready")
async def mark_ready(name: str) -> dict:
    """Mark an asset as ready for other artists to import."""
    result = await _assets().update_one(
        {"name": name}, {"$set": {"ready": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="not found")
    return {"message": f"{name} is ready"}


@router.patch("/assets/{name}/unready")
async def unmark_ready(name: str) -> dict:
    """Take an asset back out of the ready pool."""
    result = await _assets().update_one(
        {"name": name}, {"$set": {"ready": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="not found")
    return {"message": f"{name} is unready"}


@router.post("/assets/{name}/thumbnail/{view}")
async def upload_thumbnail(name: str, view: str, file: UploadFile = File(...)) -> dict:
    """Store a front or top viewport screenshot for an asset."""
    if view not in ("front", "top"):
        raise HTTPException(status_code=400, detail="view must be front or top")
    await storage.save_file(f"{name}_{view}.jpg", await file.read())
    return {"message": f"{view} thumbnail saved for {name}"}


@router.get("/assets/{name}/thumbnail/{view}")
async def get_thumbnail(name: str, view: str) -> Response:
    """Send a stored thumbnail image back to the client."""
    data = await storage.read_file(f"{name}_{view}.jpg")
    if data is None:
        raise HTTPException(status_code=404, detail="not found")
    return Response(content=data, media_type="image/jpeg")


@router.delete("/assets/{name}")
async def delete_asset(name: str) -> dict:
    """Remove an asset's file, thumbnails and database entry."""
    asset = await _assets().find_one({"name": name})
    if not asset:
        raise HTTPException(status_code=404, detail="not found")
    await storage.delete_file(f"{name}.obj")
    for view in ("front", "top"):
        await storage.delete_file(f"{name}_{view}.jpg")
    await _assets().delete_one({"name": name})
    return {"message": f"{name} deleted"}
