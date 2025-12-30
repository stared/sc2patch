"""Unified data models for SC2 patches.

These Pydantic models define the schema for all patch data.
The TypeScript side mirrors these with Zod schemas.
"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Type aliases
Race = Literal["terran", "protoss", "zerg", "neutral"]
ChangeType = Literal["buff", "nerf", "mixed"]
UnitType = Literal["unit", "building", "upgrade", "ability", "mechanic"]
PatchType = Literal["balance", "release"]


class Unit(BaseModel):
    """A game entity (unit, building, upgrade, etc.)."""

    id: str = Field(description="Unique ID: race-name (e.g., 'terran-marine')")
    name: str = Field(description="Display name (e.g., 'Marine')")
    race: Race
    type: UnitType = "unit"
    liquipedia_url: str = Field(description="Wiki URL (Liquipedia or Fandom)")


class Change(BaseModel):
    """A single balance change."""

    raw_text: str = Field(description="Description of the change")
    change_type: ChangeType = Field(description="buff, nerf, or mixed")


class EntityChanges(BaseModel):
    """All changes for a single entity in a patch."""

    entity_id: str = Field(description="Entity ID: race-name")
    changes: list[Change]


class Patch(BaseModel):
    """A single patch with all its changes."""

    version: str = Field(description="Patch version (e.g., '5.0.12')")
    date: str = Field(description="ISO date YYYY-MM-DD")
    url: str = Field(description="URL to patch notes - must be valid HTTP(S) URL")
    patch_type: PatchType = Field(default="balance", description="'balance' for patches, 'release' for expansions")
    entities: list[EntityChanges]

    @field_validator("url")
    @classmethod
    def url_must_be_valid(cls, v: str) -> str:
        """Ensure URL is not empty and starts with http."""
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")
        if not v.startswith("http://") and not v.startswith("https://"):
            raise ValueError(f"URL must start with http:// or https://, got: {v}")
        return v


class PatchesData(BaseModel):
    """Complete dataset: all patches and units."""

    patches: list[Patch]
    units: list[Unit]
    generated_at: str = Field(description="ISO timestamp when data was generated")

    @classmethod
    def create(cls, patches: list[Patch], units: list[Unit]) -> "PatchesData":
        """Create PatchesData with current timestamp."""
        return cls(
            patches=patches,
            units=units,
            generated_at=datetime.now(tz=timezone.utc).isoformat(),
        )
