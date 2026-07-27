"""Pydantic models documenting the shape of a versioned asset.

The routes build these dicts directly against MongoDB; these models describe
the structure for reference and could back a typed API later.
"""

from typing import Optional

from pydantic import BaseModel


class AssetVersion(BaseModel):
    """One stored version of an asset."""

    version: int
    ext: str  # the USD file extension (.usd, .usda, .usdc, .usdz)
    uploaded_by: str
    uploaded_at: str  # ISO timestamp


class Asset(BaseModel):
    """An asset and its full version history.

    Attributes:
        name: Asset name (filename without the USD extension).
        source_tool: DCC the asset came from (Maya, Houdini, ...).
        latest_version: The highest version number uploaded.
        approved_version: The version others should consume, or None.
        versions: Every uploaded version, oldest first.
    """

    name: str
    source_tool: Optional[str] = None
    latest_version: int
    approved_version: Optional[int] = None
    versions: list[AssetVersion] = []
