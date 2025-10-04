"""Pydantic models for StarCraft 2 patch data."""

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class Expansion(str, Enum):
    """StarCraft 2 expansion."""

    WINGS_OF_LIBERTY = "wings_of_liberty"
    HEART_OF_THE_SWARM = "heart_of_the_swarm"
    LEGACY_OF_THE_VOID = "legacy_of_the_void"


class Source(str, Enum):
    """Data source."""

    BLIZZARD = "blizzard"
    LIQUIPEDIA = "liquipedia"


class Patch(BaseModel):
    """Patch metadata."""

    version: str = Field(..., min_length=1, description="Patch version (e.g., '5.0.12')")
    date: date = Field(..., description="Release date")
    expansion: Expansion = Field(..., description="Game expansion")
    url: HttpUrl = Field(..., description="Source URL")
    source: Source = Field(..., description="Data source")

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate patch version format."""
        if not v.strip():
            raise ValueError("Patch version cannot be empty")
        return v.strip()

    class Config:
        frozen = True


class Race(str, Enum):
    """StarCraft 2 race."""

    TERRAN = "terran"
    ZERG = "zerg"
    PROTOSS = "protoss"
    NEUTRAL = "neutral"


class EntityType(str, Enum):
    """Entity type."""

    UNIT = "unit"
    BUILDING = "building"
    UPGRADE = "upgrade"
    ABILITY = "ability"


class Entity(BaseModel):
    """Game entity (unit, building, upgrade, ability)."""

    id: str = Field(..., min_length=1, description="Normalized identifier (snake_case)")
    name: str = Field(..., min_length=1, description="Display name")
    race: Race = Field(..., description="Race")
    type: EntityType = Field(..., description="Entity type")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate entity ID is lowercase snake_case."""
        if not v.strip():
            raise ValueError("Entity ID cannot be empty")
        normalized = v.strip().lower().replace(" ", "_").replace("-", "_")
        if not normalized.replace("_", "").isalnum():
            raise ValueError(f"Invalid entity ID: {v}")
        return normalized

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate entity name is not empty."""
        if not v.strip():
            raise ValueError("Entity name cannot be empty")
        return v.strip()

    class Config:
        frozen = True


class SourceSection(str, Enum):
    """Source section in patch notes."""

    VERSUS_BALANCE = "versus/balance"
    COOP = "coop"
    GENERAL = "general"
    BUG_FIXES = "bug_fixes"
    UNKNOWN = "unknown"


class Change(BaseModel):
    """Raw balance change from patch notes."""

    id: str = Field(..., min_length=1, description="Auto-generated unique ID")
    patch_version: str = Field(..., min_length=1, description="Patch version")
    entity_id: str = Field(..., min_length=1, description="Entity identifier")
    raw_text: str = Field(..., min_length=1, description="Exact text from patch notes")
    race: Race = Field(..., description="Race")
    source_section: SourceSection = Field(
        default=SourceSection.UNKNOWN, description="Section of patch notes"
    )

    @field_validator("patch_version", "entity_id", "raw_text")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate string fields are not empty."""
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    class Config:
        frozen = True


class DataRecord(BaseModel):
    """JSONL record wrapper with type discrimination."""

    type: Literal["patch", "entity", "change"]
    data: Patch | Entity | Change
