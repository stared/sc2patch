"""Parse SC2 patch notes using OpenRouter LLM API to extract structured balance changes."""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
import httpx
from rich.console import Console
from rich.progress import track
from pydantic import BaseModel, Field
from dotenv import load_dotenv

console = Console()

# Load environment variables from .env file
load_dotenv()

# OpenRouter API configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    console.print("[red]Error: OPENROUTER_API_KEY not found[/red]")
    console.print("Please add OPENROUTER_API_KEY to your .env file")
    console.print("Example: OPENROUTER_API_KEY=sk-or-v1-...")
    exit(1)

# Model to use - GPT-5
MODEL = "openai/gpt-5"  # GPT-5 on OpenRouter


class BalanceChange(BaseModel):
    """Structured representation of a balance change."""
    entity_id: str = Field(description="Entity ID in format: race-unit_name (e.g., terran-marine, zerg-hydralisk)")
    entity_name: str = Field(description="Display name of the entity (e.g., Marine, Hydralisk)")
    race: str = Field(description="Race: terran, protoss, zerg, or neutral")
    changes: List[str] = Field(description="List of specific changes for this entity")


class PatchChanges(BaseModel):
    """All balance changes for a patch."""
    version: str
    date: str
    url: str
    balance_changes: List[BalanceChange]


def extract_changes_with_llm(markdown_content: str, metadata: dict) -> PatchChanges:
    """Use LLM to extract structured balance changes from patch notes."""

    # Prepare the prompt
    system_prompt = """You are an expert at extracting StarCraft 2 balance changes from patch notes.
Your task is to extract ONLY gameplay balance changes (unit stats, ability changes, upgrades, etc).
Do NOT include:
- Bug fixes
- UI/visual changes
- Campaign content
- Co-op content
- Map pool updates
- General announcements

Format entity IDs as: race-entity_name (lowercase, spaces replaced with underscores)
Examples: terran-marine, zerg-hydralisk, protoss-high_templar

For each entity that has changes, group ALL its changes together."""

    user_prompt = f"""Extract all balance changes from this patch note:

{markdown_content}

Return a JSON object with this structure:
{{
    "balance_changes": [
        {{
            "entity_id": "race-unit_name",
            "entity_name": "Unit Name",
            "race": "terran|protoss|zerg|neutral",
            "changes": ["change 1", "change 2"]
        }}
    ]
}}

Remember: Only include actual balance/gameplay changes, not bug fixes or visual updates."""

    try:
        # Make API request to OpenRouter
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/pmigdal/sc2patches",
                "X-Title": "SC2 Patch Parser"
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
            timeout=120
        )

        response.raise_for_status()
        result = response.json()

        # Extract the content
        content = result["choices"][0]["message"]["content"]

        # Remove markdown code blocks
        content = content.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(content)

        # Create structured response
        return PatchChanges(
            version=metadata["version"],
            date=metadata["date"],
            url=metadata["url"],
            balance_changes=[BalanceChange(**change) for change in parsed.get("balance_changes", [])]
        )

    except httpx.HTTPError as e:
        console.print(f"[red]HTTP Error: {e}[/red]")
        raise
    except json.JSONDecodeError as e:
        console.print(f"[red]Failed to parse LLM response: {e}[/red]")
        raise
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise


def parse_markdown_metadata(md_path: Path) -> dict:
    """Extract metadata from Markdown frontmatter."""
    content = md_path.read_text(encoding="utf-8")

    if not content.startswith("---"):
        raise ValueError("No frontmatter found in Markdown")

    lines = content.split("\n")
    metadata = {}

    for line in lines[1:]:  # Skip first ---
        if line.strip() == "---":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()

    return metadata


def process_patch(md_path: Path) -> Dict[str, Any]:
    """Process a single patch file."""
    console.print(f"Processing {md_path.name}...")

    # Extract metadata
    metadata = parse_markdown_metadata(md_path)

    # Read full content
    content = md_path.read_text(encoding="utf-8")

    # Extract changes using LLM
    patch_changes = extract_changes_with_llm(content, metadata)

    # Convert to format compatible with existing visualization
    result = {
        "metadata": {
            "version": patch_changes.version,
            "date": patch_changes.date,
            "title": f"StarCraft II Patch {patch_changes.version}",
            "url": patch_changes.url
        },
        "changes": []
    }

    # Convert balance changes to the expected format
    for change in patch_changes.balance_changes:
        for change_text in change.changes:
            result["changes"].append({
                "id": f"{change.entity_id}_{len(result['changes'])}",
                "patch_version": patch_changes.version,
                "entity_id": change.entity_id,
                "raw_text": change_text
            })

    console.print(f"[green]✓[/green] Found {len(patch_changes.balance_changes)} entities with changes")
    return result


def main():
    """Parse all patches using LLM."""
    # Input and output directories
    input_dir = Path("data/raw_patches")
    output_dir = Path("data/processed/patches")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all markdown files
    md_files = sorted(input_dir.glob("*.md"))
    console.print(f"\n[bold]Processing {len(md_files)} patch files with LLM...[/bold]\n")

    # Process each patch
    successful = 0
    failed = []

    for md_path in track(md_files, description="Parsing patches..."):
        try:
            # Process the patch
            result = process_patch(md_path)

            # Save to JSON
            version = result["metadata"]["version"]
            output_path = output_dir / f"{version}.json"
            output_path.write_text(json.dumps(result, indent=2))

            successful += 1

        except Exception as e:
            console.print(f"[red]✗ Failed to process {md_path.name}: {e}[/red]")
            failed.append(md_path.name)

    # Summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"[green]Successfully processed: {successful}/{len(md_files)}[/green]")

    if failed:
        console.print(f"[red]Failed patches: {', '.join(failed)}[/red]")

    # Test one specific patch
    if Path("data/processed/patches/3.8.0.json").exists():
        test_data = json.loads(Path("data/processed/patches/3.8.0.json").read_text())
        console.print(f"\n[cyan]Test - Patch 3.8.0 has {len(test_data['changes'])} changes[/cyan]")
        if test_data['changes']:
            console.print(f"Sample changes:")
            for change in test_data['changes'][:3]:
                console.print(f"  - {change['entity_id']}: {change['raw_text']}")


if __name__ == "__main__":
    main()