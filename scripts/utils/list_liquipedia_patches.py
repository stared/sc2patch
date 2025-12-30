#!/usr/bin/env python3
"""List all SC2 patches with balance changes from Liquipedia.

Uses LLM to extract patch information from Liquipedia's patches page.

Usage:
    uv run python scripts/list_liquipedia_patches.py
    uv run python scripts/list_liquipedia_patches.py --output patches_list.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from markdownify import markdownify
from rich.console import Console
from rich.table import Table

from sc2patches.llm_config import DEFAULT_MODEL

load_dotenv()

console = Console()

LIQUIPEDIA_URL = "https://liquipedia.net/starcraft2/Patches"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def fetch_liquipedia_page(url: str) -> str:
    """Fetch and return the text content of a Liquipedia page."""
    headers = {"User-Agent": "SC2PatchesBot/1.0 (https://github.com/stared/sc2-balance-timeline)"}
    response = httpx.get(url, headers=headers, follow_redirects=True, timeout=30)
    response.raise_for_status()
    return response.text


def extract_patches_with_llm(html_content: str, model: str = DEFAULT_MODEL) -> list[dict]:
    """Use LLM to extract patches with balance changes."""
    if not OPENROUTER_API_KEY:
        console.print("[red]Error: OPENROUTER_API_KEY not set[/red]")
        sys.exit(1)

    console.print(f"[dim]Using model: {model}[/dim]")

    # Convert HTML to markdown to reduce size while preserving structure
    markdown_content = markdownify(html_content, heading_style="ATX")
    console.print(f"[dim]Converted to {len(markdown_content):,} chars markdown[/dim]")

    prompt = f"""Analyze this Liquipedia StarCraft II patches page.
Extract ALL patches that have balance changes.

For each patch with balance changes, return:
- version: The patch version (e.g., "5.0.15", "4.1.4", "2.1.9 BU")
- date: The release date in YYYY-MM-DD format (use NA date if multiple regions listed)
- has_balance_changes: true if the patch has unit/building/ability balance changes
- liquipedia_url: The Liquipedia URL for this patch (format: https://liquipedia.net/starcraft2/Patch_X.X.X)

IMPORTANT:
- Include BOTH numbered patches AND Balance Updates (BU)
- Balance Updates are often listed separately from main patches
- Only include patches that have actual balance changes (unit stats, costs, abilities)
- Do NOT include patches that only have bug fixes, UI changes, or Co-op changes
- For Balance Updates, use format like "4.1.4 BU" for the version

Return a JSON array of objects. Example:
[
  {{"version": "5.0.15", "date": "2025-09-30", "has_balance_changes": true, "liquipedia_url": "https://liquipedia.net/starcraft2/Patch_5.0.15"}},
  {{"version": "4.1.4 BU", "date": "2018-01-29", "has_balance_changes": true, "liquipedia_url": "https://liquipedia.net/starcraft2/Patch_4.1.4"}}
]

Page content (markdown):
{markdown_content}
"""

    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        },
        timeout=120,
    )
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]

    # Parse the JSON response
    try:
        data = json.loads(content)
        # Handle both direct array and wrapped object
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "patches" in data:
            return data["patches"]
        # Try to find an array in the response
        for value in data.values():
            if isinstance(value, list):
                return value
        return []
    except json.JSONDecodeError as e:
        console.print(f"[red]Failed to parse LLM response: {e}[/red]")
        console.print(content[:500])
        return []


def main() -> None:
    parser = argparse.ArgumentParser(description="List SC2 patches with balance changes from Liquipedia")
    parser.add_argument("--output", "-o", type=Path, help="Output JSON file path")
    args = parser.parse_args()

    console.print("[bold]Fetching Liquipedia patches page...[/bold]")
    console.print(f"URL: {LIQUIPEDIA_URL}")

    html_content = fetch_liquipedia_page(LIQUIPEDIA_URL)
    console.print(f"Fetched {len(html_content):,} bytes")

    console.print("\n[bold]Extracting patches...[/bold]")
    patches = extract_patches_with_llm(html_content)

    # Filter to only patches with balance changes
    balance_patches = [p for p in patches if p.get("has_balance_changes", False)]

    console.print(f"\n[green]Found {len(balance_patches)} patches with balance changes[/green]\n")

    # Display as table
    table = Table(title="Patches with Balance Changes")
    table.add_column("Version", style="cyan")
    table.add_column("Date", style="yellow")
    table.add_column("Liquipedia URL", style="dim")

    for patch in sorted(balance_patches, key=lambda p: p.get("date", ""), reverse=True):
        table.add_row(
            patch.get("version", "?"),
            patch.get("date", "?"),
            patch.get("liquipedia_url", "?"),
        )

    console.print(table)

    # Save to file if requested
    if args.output:
        with args.output.open("w") as f:
            json.dump(balance_patches, f, indent=2)
        console.print(f"\n[dim]Saved to {args.output}[/dim]")

    # Also print as JSON for easy copy
    console.print("\n[bold]JSON output:[/bold]")
    print(json.dumps(balance_patches, indent=2))


if __name__ == "__main__":
    main()
