"""Pydantic models for StarCraft 2 patch data."""

from datetime import date as Date
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, field_validator


class Expansion(str, Enum):
    """StarCraft 2 expansion."""

    WINGS_OF_LIBERTY = "wings_of_liberty"
    HEART_OF_THE_SWARM = "heart_of_the_swarm"
    LEGACY_OF_THE_VOID = "legacy_of_the_void"


class Patch(BaseModel):
    """Patch metadata."""

    version: str = Field(..., min_length=1, description="Patch version (e.g., '5.0.12')")
    date: Date = Field(..., description="Release date")
    expansion: Expansion = Field(..., description="Game expansion")
    url: HttpUrl = Field(..., description="Source URL")

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
        """Validate entity ID is {race}-{snake_case_name} format."""
        if not v.strip():
            raise ValueError("Entity ID cannot be empty")

        # Must contain at least one hyphen (race-name format)
        if "-" not in v:
            raise ValueError(f"Entity ID must be in format 'race-name': {v}")

        # Split into race and name parts
        parts = v.split("-", 1)
        race_part = parts[0]

        # Verify race prefix is valid
        valid_races = {"terran", "protoss", "zerg", "neutral"}
        if race_part.lower() not in valid_races:
            raise ValueError(f"Invalid race prefix in entity ID: {v}")

        # Normalize: lowercase, underscores only
        normalized = v.strip().lower().replace(" ", "_")
        if not normalized.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                f"Invalid entity ID (must be alphanumeric with hyphens/underscores): {v}"
            )

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
