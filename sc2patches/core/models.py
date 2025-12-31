"""Pydantic models for SC2 patches. TypeScript mirrors these with Zod schemas."""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Type aliases
Race = Literal["terran", "protoss", "zerg", "neutral"]
ChangeType = Literal["buff", "nerf", "mixed"]
UnitType = Literal["unit", "building", "upgrade", "ability", "mechanic"]
PatchType = Literal["balance", "release"]


def _validate_url(v: str) -> str:
    if not v or not v.startswith(("http://", "https://")):
        raise ValueError(f"Invalid URL: {v}")
    return v


class PatchConfig(BaseModel):
    """Config entry from patch_urls.json."""

    version: str
    url: str
    liquipedia: str | None = None
    additional_urls: list[str] = Field(default_factory=list)
    parse_hint: str | None = None
    note: str | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_url(v)


class Unit(BaseModel):
    """Game entity (unit, building, upgrade, etc.)."""

    id: str
    name: str
    race: Race
    type: UnitType = "unit"
    liquipedia_url: str


# Intermediate format (flat changes, for storage)
class ParsedChange(BaseModel):
    entity_id: str
    raw_text: str
    change_type: ChangeType


class ParsedPatch(BaseModel):
    """Flat changes from LLM. Saved to data/processed/patches/*.json."""

    version: str
    date: str
    url: str
    changes: list[ParsedChange]

    def to_patch(self, patch_type: PatchType = "balance") -> "Patch":
        """Group changes by entity for visualization."""
        by_entity: dict[str, list[Change]] = defaultdict(list)
        for c in self.changes:
            by_entity[c.entity_id].append(Change(raw_text=c.raw_text, change_type=c.change_type))
        return Patch(
            version=self.version,
            date=self.date,
            url=self.url,
            patch_type=patch_type,
            entities=[EntityChanges(entity_id=eid, changes=ch) for eid, ch in sorted(by_entity.items())],
        )

    @classmethod
    def from_json_file(cls, data: dict) -> "ParsedPatch":
        """Load from JSON file format with metadata wrapper."""
        m = data["metadata"]
        return cls(
            version=m["version"],
            date=m["date"],
            url=m.get("url", ""),
            changes=[ParsedChange(entity_id=c["entity_id"], raw_text=c["raw_text"], change_type=c["change_type"]) for c in data["changes"]],
        )

    def to_json_dict(self) -> dict:
        """Convert to JSON file format with metadata wrapper."""
        return {
            "metadata": {"version": self.version, "date": self.date, "url": self.url},
            "changes": [{"entity_id": c.entity_id, "raw_text": c.raw_text, "change_type": c.change_type} for c in self.changes],
        }


# Final format (grouped by entity, for visualization)
class Change(BaseModel):
    raw_text: str
    change_type: ChangeType


class EntityChanges(BaseModel):
    entity_id: str
    changes: list[Change]


class Patch(BaseModel):
    """Grouped changes for visualization."""

    version: str
    date: str
    url: str
    patch_type: PatchType = "balance"
    entities: list[EntityChanges]

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_url(v)


class PatchesData(BaseModel):
    """Complete dataset for visualization."""

    patches: list[Patch]
    units: list[Unit]
    generated_at: str

    @classmethod
    def create(cls, patches: list[Patch], units: list[Unit]) -> "PatchesData":
        return cls(patches=patches, units=units, generated_at=datetime.now(tz=timezone.utc).isoformat())
