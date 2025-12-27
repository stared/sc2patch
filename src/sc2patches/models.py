"""Unified data models for SC2 patches.

These Pydantic models define the schema for all patch data.
The TypeScript side mirrors these with Zod schemas.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Type aliases
Race = Literal["terran", "protoss", "zerg", "neutral"]
ChangeType = Literal["buff", "nerf", "mixed"]
UnitType = Literal["unit", "building", "unknown"]


class Unit(BaseModel):
    """A game entity (unit, building, upgrade, etc.)."""

    id: str = Field(description="Unique ID: race-name (e.g., 'terran-marine')")
    name: str = Field(description="Display name (e.g., 'Marine')")
    race: Race
    type: UnitType = "unit"


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
    url: str = Field(description="URL to patch notes")
    entities: list[EntityChanges]


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
            generated_at=datetime.now().isoformat(),
        )
