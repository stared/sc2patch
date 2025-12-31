#!/usr/bin/env python3
# /// script
# dependencies = ["google-genai", "rich"]
# ///
"""Verify unit patch data against Liquipedia using Gemini 3 Pro.

Usage:
    uv run scripts/verify_unit_patches.py --unit Disruptor
    uv run scripts/verify_unit_patches.py --all
    uv run scripts/verify_unit_patches.py --all --limit 10  # Test with first 10 units
"""

import argparse
import asyncio
import json
from pathlib import Path

from google import genai  # type: ignore[import-not-found]
from google.genai import types  # type: ignore[import-not-found]
from rich.console import Console
from rich.table import Table

console = Console()

# Semaphore for rate limiting (10 concurrent)
semaphore = asyncio.Semaphore(10)

# Gemini client (initialized once)
client = genai.Client()


def load_units() -> list[dict]:
    """Load units from data/units.json, filter to actual units only."""
    with Path("data/units.json").open() as f:
        units = json.load(f)
    # Filter to units only (not upgrades, abilities, mechanics)
    return [u for u in units if u.get("type", "unit") == "unit"]


def load_unit_patches(unit_id: str) -> list[dict]:
    """Load all patches that affect a specific unit."""
    patches_dir = Path("data/processed/patches")
    unit_patches = []

    for patch_file in sorted(patches_dir.glob("*.json")):
        with patch_file.open() as f:
            data = json.load(f)

        changes = [c for c in data["changes"] if c["entity_id"] == unit_id]
        if changes:
            unit_patches.append(
                {"version": data["metadata"]["version"], "date": data["metadata"]["date"], "changes": [c["raw_text"] for c in changes]}
            )

    return unit_patches


def query_gemini_sync(prompt: str) -> str:
    """Query Gemini 3 Pro with search grounding (synchronous)."""
    try:
        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=[prompt],
            config=types.GenerateContentConfig(tools=[{"google_search": {}}], thinking_config=types.ThinkingConfig(thinking_level="high")),
        )

        # Extract text from response
        if response.candidates and response.candidates[0].content.parts:
            return "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, "text") and part.text)
        return "No response"
    except Exception as e:
        return f"Error: {e}"


async def query_gemini(prompt: str) -> str:
    """Query Gemini 3 Pro with search grounding (async wrapper)."""
    async with semaphore:
        # Run sync call in thread pool to allow concurrency
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, query_gemini_sync, prompt)


async def verify_unit(unit: dict, progress: dict) -> dict:
    """Verify a single unit's patch data against Liquipedia."""
    unit_id = unit["id"]
    unit_name = unit["name"]
    liquipedia_url = unit.get("liquipedia_url", "")

    progress["done"] += 1
    console.print(f"[{progress['done']}/{progress['total']}] Checking {unit_name}...", style="dim")

    # Get our patch data
    our_patches = load_unit_patches(unit_id)
    our_versions = [p["version"] for p in our_patches]

    if not our_patches:
        return {"unit": unit_name, "our_patches": 0, "result": "No patches in our data"}

    # Build prompt for Gemini
    prompt = f"""Compare patch history for SC2 unit "{unit_name}".

OUR DATA has these patches with {unit_name} changes:
{json.dumps(our_versions, indent=2)}

Search Liquipedia for {unit_name} patch history: {liquipedia_url}

TASK: Identify ANY patches listed on Liquipedia that are MISSING from our data.
Separate into:
1. MISSING RELEASE patches (version 1.x, 2.x, 3.x, 4.x, 5.x - live game patches)
2. MISSING BETA patches (version 0.x, 2.5.x, or labeled "Beta")

Be BRIEF. Format:
MISSING RELEASE: [list versions or "None"]
MISSING BETA: [list versions or "None"]
NOTES: [one sentence if relevant]"""

    result = await query_gemini(prompt)

    return {"unit": unit_name, "our_patches": len(our_patches), "result": result.strip()}


async def main():
    parser = argparse.ArgumentParser(description="Verify unit patches against Liquipedia")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Check all units")
    group.add_argument("--unit", type=str, help="Check specific unit by name")
    parser.add_argument("--limit", type=int, help="Limit to first N units (for testing)")
    args = parser.parse_args()

    units = load_units()
    console.print(f"Loaded {len(units)} units (excluding upgrades/abilities)")

    # Filter to specific unit if requested
    if args.unit:
        units = [u for u in units if u["name"].lower() == args.unit.lower()]
        if not units:
            console.print(f"[red]Unit '{args.unit}' not found[/red]")
            return

    # Apply limit if specified
    if args.limit:
        units = units[: args.limit]

    console.print(f"\nVerifying {len(units)} unit(s) against Liquipedia...\n")

    progress = {"done": 0, "total": len(units)}
    tasks = [verify_unit(u, progress) for u in units]
    results = await asyncio.gather(*tasks)

    # Display results
    table = Table(title="Patch Verification Results")
    table.add_column("Unit", style="cyan")
    table.add_column("Our Patches", justify="right")
    table.add_column("Verification Result")

    for r in results:
        table.add_row(r["unit"], str(r["our_patches"]), r["result"][:200])

    console.print(table)

    # Print full results for single unit
    if len(results) == 1:
        console.print("\n[bold]Full Result:[/bold]")
        console.print(results[0]["result"])


if __name__ == "__main__":
    asyncio.run(main())
