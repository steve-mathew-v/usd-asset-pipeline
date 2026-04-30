from fastapi import FastAPI
from routes import router

app = FastAPI(title="OBJ Pipeline Server")

app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {"status": "OBJ pipeline server running"}