"""Improved LLM parser that extracts only balance sections before sending to GPT-5."""

import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any
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


class BalanceChange(BaseModel):
    """Structured representation of a balance change."""
    entity_id: str = Field(description="Entity ID in format: race-unit_name")
    entity_name: str = Field(description="Display name of the entity")
    race: str = Field(description="Race: terran, protoss, zerg, or neutral")
    changes: List[str] = Field(description="List of specific changes")


class PatchChanges(BaseModel):
    """All balance changes for a patch."""
    version: str
    date: str
    url: str
    balance_changes: List[BalanceChange]


def extract_balance_section(markdown_content: str) -> str:
    """Extract only the balance/multiplayer/versus section from full patch notes.

    This reduces token count and focuses GPT-5 on relevant content.
    """
    lines = markdown_content.split('\n')
    balance_lines = []
    in_balance_section = False
    section_depth = 0

    # Markers that indicate balance content
    balance_markers = [
        'balance', 'multiplayer', 'versus', 'revamp',
        'terran', 'protoss', 'zerg'
    ]

    # Markers that indicate end of balance section
    end_markers = [
        'bug fix', 'co-op', 'campaign', 'arcade',
        'collection', 'editor', 'general'
    ]

    for i, line in enumerate(lines):
        line_lower = line.lower()

        # Check if we're entering a balance section
        if any(marker in line_lower for marker in balance_markers):
            # Look for section headers with these keywords
            if line.startswith('#') or line.startswith('-') or line.startswith('*'):
                in_balance_section = True
                section_depth = 0

        # Check if we hit a non-balance section (but only if we're past metadata)
        if in_balance_section and i > 20:  # Skip first 20 lines (metadata/header)
            # If we see race names at lower indentation, we're still in balance
            if any(race in line_lower for race in ['terran', 'protoss', 'zerg']):
                balance_lines.append(line)
                continue

            # If we see bug fixes/co-op at same or higher level, balance section ended
            if line.startswith('#') or (line.startswith('-') and not line.startswith('  -')):
                if any(marker in line_lower for marker in end_markers):
                    break

        if in_balance_section:
            balance_lines.append(line)

    # If we didn't find a clear balance section, look for unit names directly
    if len(balance_lines) < 10:
        console.print("[yellow]No clear balance section found, extracting by unit names[/yellow]")
        balance_lines = []
        unit_names = [
            'marine', 'marauder', 'reaper', 'ghost', 'hellion', 'tank', 'thor',
            'banshee', 'raven', 'viking', 'liberator', 'cyclone', 'battlecruiser',
            'zealot', 'stalker', 'sentry', 'adept', 'templar', 'archon',
            'immortal', 'colossus', 'disruptor', 'phoenix', 'oracle', 'carrier',
            'void ray', 'tempest', 'warp prism', 'observer',
            'drone', 'zergling', 'roach', 'hydralisk', 'baneling', 'mutalisk',
            'corruptor', 'swarm host', 'infestor', 'ultralisk', 'brood lord',
            'viper', 'ravager', 'lurker', 'overlord', 'queen'
        ]

        for line in lines:
            line_lower = line.lower()
            if any(unit in line_lower for unit in unit_names):
                # Include context (5 lines before and after)
                idx = lines.index(line)
                start = max(0, idx - 5)
                end = min(len(lines), idx + 15)
                balance_lines.extend(lines[start:end])

    result = '\n'.join(balance_lines)
    console.print(f"[cyan]Extracted {len(balance_lines)} lines from {len(lines)} total lines[/cyan]")
    return result


def extract_changes_with_llm(markdown_content: str, metadata: dict) -> PatchChanges:
    """Use LLM to extract structured balance changes."""

    # Extract only balance section to reduce token count
    balance_content = extract_balance_section(markdown_content)

    system_prompt = """You are an expert at extracting StarCraft 2 balance changes from patch notes.
Extract ONLY gameplay balance changes (unit stats, ability changes, upgrades, etc).
Do NOT include bug fixes, UI changes, campaign content, or co-op content.

Format entity IDs as: race-entity_name (lowercase, spaces replaced with underscores)
Examples: terran-marine, zerg-hydralisk, protoss-high_templar

Group ALL changes for each entity together."""

    user_prompt = f"""Extract all balance changes from this section:

{balance_content}

Return a JSON object:
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

Only include actual balance/gameplay changes."""

    try:
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
                "max_tokens": 16000
            },
            timeout=120
        )

        response.raise_for_status()
        result = response.json()

        console.print(f"[yellow]API Response status:[/yellow] {response.status_code}")
        console.print(f"[yellow]Response keys:[/yellow] {list(result.keys())}")

        if 'choices' in result and len(result['choices']) > 0:
            content = result["choices"][0]["message"]["content"]
            console.print(f"[yellow]Content length:[/yellow] {len(content) if content else 0}")
            console.print(f"[yellow]Content (first 200 chars):[/yellow] {content[:200] if content else 'EMPTY'}")
        else:
            console.print(f"[red]No choices in response![/red] Full response: {result}")
            raise ValueError("No choices in GPT-5 response")

        # Remove markdown code blocks
        content = content.replace("```json", "").replace("```", "").strip()

        if not content:
            console.print(f"[red]GPT-5 returned empty content! Full response:[/red] {json.dumps(result, indent=2)}")
            raise ValueError("GPT-5 returned empty content")

        parsed = json.loads(content)

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
        console.print(f"[yellow]Raw response (first 500 chars):[/yellow] {content[:500] if 'content' in locals() else 'No content'}")
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

    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()

    return metadata


def process_patch(md_path: Path) -> Dict[str, Any]:
    """Process a single patch file."""
    console.print(f"Processing {md_path.name}...")

    metadata = parse_markdown_metadata(md_path)
    content = md_path.read_text(encoding="utf-8")

    patch_changes = extract_changes_with_llm(content, metadata)

    result = {
        "metadata": {
            "version": patch_changes.version,
            "date": patch_changes.date,
            "title": f"StarCraft II Patch {patch_changes.version}",
            "url": patch_changes.url
        },
        "changes": []
    }

    for change in patch_changes.balance_changes:
        for change_text in change.changes:
            result["changes"].append({
                "id": f"{change.entity_id}_{len(result['changes'])}",
                "patch_version": patch_changes.version,
                "entity_id": change.entity_id,
                "raw_text": change_text
            })

    console.print(f"[green]✓[/green] Found {len(patch_changes.balance_changes)} entities with {len(result['changes'])} total changes")
    return result


def main():
    """Parse all patches using improved LLM approach."""
    input_dir = Path("data/raw_patches")
    output_dir = Path("data/processed/patches")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get patches to re-parse (failed ones)
    failed_patches = [
        "3.8.0.md", "4.0.md", "4.11.0.md", "4.7.1.md",
        "5.0.12.md", "5.0.13.md", "5.0.14.md", "5.0.15.md"
    ]

    md_files = [input_dir / p for p in failed_patches if (input_dir / p).exists()]
    console.print(f"\n[bold]Re-parsing {len(md_files)} failed patches with improved approach...[/bold]\n")

    successful = 0
    failed = []

    for md_path in track(md_files, description="Parsing patches..."):
        try:
            result = process_patch(md_path)

            version = result["metadata"]["version"]
            output_path = output_dir / f"{version}.json"
            output_path.write_text(json.dumps(result, indent=2))

            successful += 1

        except Exception as e:
            console.print(f"[red]✗ Failed to process {md_path.name}: {e}[/red]")
            failed.append(md_path.name)

    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"[green]Successfully processed: {successful}/{len(md_files)}[/green]")

    if failed:
        console.print(f"[red]Failed patches: {', '.join(failed)}[/red]")


if __name__ == "__main__":
    main()