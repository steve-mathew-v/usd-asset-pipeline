"""API endpoints for uploading, downloading and managing .obj assets."""

import os

import aiofiles
from dotenv import load_dotenv
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from database import db
from models import ObjAsset

load_dotenv()

router = APIRouter()
assets_collection = db["assets"]

UPLOAD_DIR = "uploads"
THUMB_DIR = "thumbnails"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)


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
    result = await assets_collection.insert_one(asset.dict())
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

    save_path = os.path.join(UPLOAD_DIR, file.filename)
    async with aiofiles.open(save_path, "wb") as out_file:
        await out_file.write(await file.read())

    name = file.filename.replace(".obj", "")
    await assets_collection.delete_one({"name": name})
    await assets_collection.insert_one(
        {
            "name": name,
            "file_path": save_path,
            "source_tool": source_tool,
            "tags": [],
            "ready": ready,
            "uploaded_by": uploaded_by,
        }
    )

    return {"message": f"{file.filename} uploaded", "path": save_path}


@router.get("/assets/download/{name}")
async def download_asset(name: str) -> FileResponse:
    """Send the stored .obj file for an asset back to the client."""
    asset = await assets_collection.find_one({"name": name})
    if not asset:
        raise HTTPException(status_code=404, detail="not found")
    path = asset["file_path"]
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="file missing on server")
    return FileResponse(path, filename=f"{name}.obj")


@router.get("/assets")
async def get_assets() -> list[dict]:
    """List every asset in the database."""
    assets = await assets_collection.find().to_list(100)
    for asset in assets:
        asset["_id"] = str(asset["_id"])
    return assets


@router.get("/assets/ready")
async def get_ready_assets() -> list[dict]:
    """List only the assets that are marked as ready."""
    assets = await assets_collection.find({"ready": True}).to_list(100)
    for asset in assets:
        asset["_id"] = str(asset["_id"])
    return assets


@router.patch("/assets/{name}/ready")
async def mark_ready(name: str) -> dict:
    """Mark an asset as ready for other artists to import."""
    result = await assets_collection.update_one(
        {"name": name}, {"$set": {"ready": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="not found")
    return {"message": f"{name} is ready"}


@router.patch("/assets/{name}/unready")
async def unmark_ready(name: str) -> dict:
    """Take an asset back out of the ready pool."""
    result = await assets_collection.update_one(
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
    save_path = os.path.join(THUMB_DIR, f"{name}_{view}.jpg")
    async with aiofiles.open(save_path, "wb") as out_file:
        await out_file.write(await file.read())
    await assets_collection.update_one(
        {"name": name}, {"$set": {f"thumb_{view}": save_path}}
    )
    return {"message": f"{view} thumbnail saved for {name}"}


@router.get("/assets/{name}/thumbnail/{view}")
async def get_thumbnail(name: str, view: str) -> FileResponse:
    """Send a stored thumbnail image back to the client."""
    path = os.path.join(THUMB_DIR, f"{name}_{view}.jpg")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path)


@router.delete("/assets/{name}")
async def delete_asset(name: str) -> dict:
    """Remove an asset's file, thumbnails and database entry."""
    asset = await assets_collection.find_one({"name": name})
    if not asset:
        raise HTTPException(status_code=404, detail="not found")
    if os.path.exists(asset.get("file_path", "")):
        os.remove(asset["file_path"])
    for view in ("front", "top"):
        thumb_path = os.path.join(THUMB_DIR, f"{name}_{view}.jpg")
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
    await assets_collection.delete_one({"name": name})
    return {"message": f"{name} deleted"}
