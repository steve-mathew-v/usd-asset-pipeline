from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ObjAsset(BaseModel):
    name: str
    file_path: str
    source_tool: Optional[str] = None
    tags: list[str] = []
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    ready: bool = False