#!/usr/bin/env python3
"""Compare consecutive patches to identify dependencies.

Uses Gemini Flash to analyze if consecutive patches are independent
or if one supersedes/modifies the other.

Usage:
    uv run python scripts/compare_consecutive_patches.py
"""

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# Load .env file
load_dotenv()

console = Console()

# OpenRouter API
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "google/gemini-3-flash-preview"


def load_patches() -> list[dict]:
    """Load all patches sorted by date."""
    patches_file = Path("visualization/public/data/patches.json")
    if not patches_file.exists():
        console.print("[red]Error: patches.json not found. Run export first.[/red]")
        sys.exit(1)

    with open(patches_file) as f:
        data = json.load(f)

    return sorted(data["patches"], key=lambda p: p["date"])


def format_patch_summary(patch: dict) -> str:
    """Create compact summary for LLM comparison."""
    entities = [e["entity_id"] for e in patch["entities"]]
    changes = []
    for e in patch["entities"]:
        for c in e["changes"]:
            changes.append(f"  - {e['entity_id']}: {c['raw_text']}")

    summary = f"""Version: {patch['version']}
Date: {patch['date']}
Entities ({len(entities)}): {', '.join(entities[:15])}{'...' if len(entities) > 15 else ''}
Changes:
{chr(10).join(changes[:25])}{'...' if len(changes) > 25 else ''}"""
    return summary


def compare_patches(patch_a: dict, patch_b: dict) -> dict:
    """Use Gemini Flash to compare two consecutive patches."""
    if not OPENROUTER_API_KEY:
        console.print("[red]Error: OPENROUTER_API_KEY not set[/red]")
        sys.exit(1)

    prompt = f"""Compare these two consecutive StarCraft II balance patches.

PATCH A (earlier):
{format_patch_summary(patch_a)}

PATCH B (later):
{format_patch_summary(patch_b)}

Analyze the relationship:
1. Are these INDEPENDENT patches (completely different balance changes)?
2. Or is B a REVISION/CONTINUATION of A (modifies same units, supersedes changes)?

Consider:
- Do they affect the SAME units/entities?
- Are the changes related or completely different?
- Is B reverting or adjusting changes from A?

Respond in JSON format:
{{
  "relationship": "INDEPENDENT" or "DEPENDENT",
  "confidence": "HIGH" or "MEDIUM" or "LOW",
  "reason": "Brief 1-2 sentence explanation",
  "shared_entities": ["list", "of", "shared", "entity_ids"]
}}"""

    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        return {"relationship": "ERROR", "reason": str(e), "shared_entities": []}


def main() -> None:
    """Compare all consecutive patches."""
    console.print("\n[bold]Comparing Consecutive Patches[/bold]\n")

    patches = load_patches()
    console.print(f"Loaded {len(patches)} patches (sorted by date)\n")

    results = []
    dependent_pairs = []

    for i in range(len(patches) - 1):
        patch_a = patches[i]
        patch_b = patches[i + 1]

        console.print(
            f"[dim]Comparing {patch_a['version']} ({patch_a['date']}) → "
            f"{patch_b['version']} ({patch_b['date']})...[/dim]"
        )

        result = compare_patches(patch_a, patch_b)
        result["patch_a"] = patch_a["version"]
        result["patch_b"] = patch_b["version"]
        result["date_a"] = patch_a["date"]
        result["date_b"] = patch_b["date"]
        results.append(result)

        if result.get("relationship") == "DEPENDENT":
            dependent_pairs.append(result)
            console.print(
                f"  [yellow]DEPENDENT[/yellow]: {result.get('reason', 'No reason')}  "
                f"[dim]({result.get('confidence', '?')} confidence)[/dim]"
            )
        elif result.get("relationship") == "ERROR":
            console.print(f"  [red]ERROR[/red]: {result.get('reason', 'Unknown')}")
        else:
            console.print(f"  [green]INDEPENDENT[/green]")

    # Summary
    console.print("\n" + "=" * 60)
    console.print("[bold]Summary[/bold]\n")

    if dependent_pairs:
        table = Table(title="Potentially Dependent Patch Pairs")
        table.add_column("Patch A", style="cyan")
        table.add_column("Patch B", style="cyan")
        table.add_column("Confidence", style="yellow")
        table.add_column("Reason")

        for pair in dependent_pairs:
            table.add_row(
                f"{pair['patch_a']} ({pair['date_a']})",
                f"{pair['patch_b']} ({pair['date_b']})",
                pair.get("confidence", "?"),
                pair.get("reason", "")[:50] + "..."
                if len(pair.get("reason", "")) > 50
                else pair.get("reason", ""),
            )

        console.print(table)
        console.print(
            f"\n[yellow]Found {len(dependent_pairs)} potentially dependent pairs[/yellow]"
        )
    else:
        console.print("[green]All consecutive patches appear to be independent[/green]")

    # Save results
    output_file = Path("data/logs/patch_comparison_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    console.print(f"\n[dim]Full results saved to: {output_file}[/dim]")


if __name__ == "__main__":
    main()
