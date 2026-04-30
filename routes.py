from fastapi import APIRouter, HTTPException
from database import db
from models import ObjAsset

router = APIRouter()
collection = db["assets"]

@router.post("/assets")
async def create_asset(asset: ObjAsset):
    result = await collection.insert_one(asset.dict())
    return {"id": str(result.inserted_id), "message": "Asset registered"}

@router.get("/assets/ready")
async def get_ready_assets():
    assets = await collection.find({"ready": True}).to_list(100)
    for a in assets:
        a["_id"] = str(a["_id"])
    return assets

@router.get("/assets")
async def get_all_assets():
    assets = await collection.find().to_list(100)
    for a in assets:
        a["_id"] = str(a["_id"])
    return assets

@router.patch("/assets/{name}/ready")
async def mark_ready(name: str):
    result = await collection.update_one(
        {"name": name},
        {"$set": {"ready": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": f"{name} marked as ready"}