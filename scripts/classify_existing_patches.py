"""Add change_type classification to existing patch JSON files that don't have it."""

import json
import os
from pathlib import Path
from typing import List, Dict
import httpx
from rich.console import Console
from rich.progress import track
from pydantic import BaseModel, Field
from dotenv import load_dotenv

console = Console()
load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    console.print("[red]Error: OPENROUTER_API_KEY not found[/red]")
    exit(1)

MODEL = "openai/gpt-5"


class ClassifiedChange(BaseModel):
    """A change with its classification."""
    text: str
    change_type: str = Field(description="Type: buff, nerf, or mixed")


def classify_changes(changes: List[str]) -> List[ClassifiedChange]:
    """Use GPT-5 to classify a list of changes."""

    system_prompt = """You are an expert at classifying StarCraft 2 balance changes.

Classify EACH change as:
- "buff": Positive for the player using the unit (increased damage, reduced cost, faster build time, etc.)
- "nerf": Negative for the player using the unit (decreased damage, increased cost, slower build time, etc.)
- "mixed": Has both positive and negative aspects in the same change

Return the classification for each change."""

    changes_text = "\n".join([f"{i+1}. {change}" for i, change in enumerate(changes)])

    user_prompt = f"""Classify these StarCraft 2 balance changes as buff, nerf, or mixed:

{changes_text}

Return a JSON array:
[
    {{"text": "change text", "change_type": "buff|nerf|mixed"}},
    ...
]"""

    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/pmigdal/sc2patches",
                "X-Title": "SC2 Patch Classifier"
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 4000
            },
            timeout=60
        )

        response.raise_for_status()
        result = response.json()

        content = result["choices"][0]["message"]["content"]
        content = content.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(content)
        return [ClassifiedChange(**item) for item in parsed]

    except Exception as e:
        console.print(f"[red]Error classifying changes: {e}[/red]")
        raise


def process_patch_file(json_path: Path) -> bool:
    """Add change_type to a patch JSON file if missing. Returns True if updated."""

    with open(json_path) as f:
        data = json.load(f)

    # Check if already has change_type
    if data.get("changes") and len(data["changes"]) > 0:
        if "change_type" in data["changes"][0]:
            console.print(f"[yellow]Skipping {json_path.name} - already has change_type[/yellow]")
            return False

    changes = data.get("changes", [])
    if not changes:
        console.print(f"[yellow]Skipping {json_path.name} - no changes[/yellow]")
        return False

    console.print(f"Processing {json_path.name}...")

    # Extract raw_text from all changes
    raw_texts = [change["raw_text"] for change in changes]

    # Classify all changes
    classified = classify_changes(raw_texts)

    # Update changes with change_type
    for change, classified_change in zip(changes, classified):
        change["change_type"] = classified_change.change_type

    # Save updated JSON
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)

    console.print(f"[green]✓ Updated {json_path.name} with {len(changes)} classifications[/green]")
    return True


def main():
    """Classify all patches that don't have change_type."""
    patches_dir = Path("data/processed/patches")

    json_files = sorted(patches_dir.glob("*.json"))
    console.print(f"\n[bold]Checking {len(json_files)} patch files...[/bold]\n")

    updated = 0

    for json_path in track(json_files, description="Processing patches..."):
        try:
            if process_patch_file(json_path):
                updated += 1
        except Exception as e:
            console.print(f"[red]✗ Failed to process {json_path.name}: {e}[/red]")

    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"[green]Updated: {updated} patches[/green]")


if __name__ == "__main__":
    main()
