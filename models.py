"""Pydantic models for the asset pipeline."""

from typing import Optional

from pydantic import BaseModel


class ObjAsset(BaseModel):
    """A single .obj asset tracked by the pipeline.

    Attributes:
        name: Asset name (filename without the .obj extension).
        source_tool: Which DCC tool the asset came from (e.g. Maya).
        tags: Optional tags for searching/filtering.
        ready: Whether the asset is approved for other artists to import.
    """

    name: str
    source_tool: Optional[str] = None
    tags: list[str] = []
    ready: bool = False
