#!/usr/bin/env python3
"""Extract Blizzard patch notes URL from a Liquipedia patch page.

Uses LLM to find the official Blizzard link(s) from a Liquipedia patch page.

Usage:
    uv run python scripts/get_blizzard_url_from_liquipedia.py https://liquipedia.net/starcraft2/Patch_5.0.15
    uv run python scripts/get_blizzard_url_from_liquipedia.py "1.5.4"  # Auto-constructs URL
"""

import argparse
import json
import os
import re
import sys

import httpx
from dotenv import load_dotenv
from markdownify import markdownify
from rich.console import Console

from sc2patches.llm_config import DEFAULT_MODEL

load_dotenv()

console = Console()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def construct_liquipedia_url(patch_version: str) -> str:
    """Construct Liquipedia URL from patch version."""
    # Handle BU suffix
    version = patch_version.replace(" BU", "").replace("_BU", "")
    return f"https://liquipedia.net/starcraft2/Patch_{version}"


def fetch_page(url: str) -> str:
    """Fetch and return the text content of a page."""
    headers = {"User-Agent": "SC2PatchesBot/1.0 (https://github.com/stared/sc2-balance-timeline)"}
    response = httpx.get(url, headers=headers, follow_redirects=True, timeout=30)
    response.raise_for_status()
    return response.text


def extract_blizzard_urls(
    html_content: str, patch_version: str, model: str = DEFAULT_MODEL
) -> dict:
    """Use LLM to extract Blizzard URLs from Liquipedia page."""
    if not OPENROUTER_API_KEY:
        console.print("[red]Error: OPENROUTER_API_KEY not set[/red]")
        sys.exit(1)

    console.print(f"[dim]Using model: {model}[/dim]")

    # Convert HTML to markdown to reduce size while preserving structure
    markdown_content = markdownify(html_content, heading_style="ATX")
    console.print(f"[dim]Converted to {len(markdown_content):,} chars markdown[/dim]")

    prompt = f"""Analyze this Liquipedia StarCraft II patch page.
Extract the official Blizzard patch notes URL(s).

Look for:
1. Links to news.blizzard.com or starcraft2.com patch notes
2. Links in the "External Links" section
3. Any references to official Blizzard patch announcements
4. Links to us.battle.net or eu.battle.net SC2 blogs

The patch version is: {patch_version}

Return a JSON object with:
- patch_version: The patch version
- blizzard_urls: Array of Blizzard URLs found (news.blizzard.com, starcraft2.com, battle.net, etc.)
- release_date: The release date if found (YYYY-MM-DD format)
- has_balance_changes: true if this patch has balance/versus changes
- notes: Any relevant notes about the patch

If no Blizzard URL is found, return an empty array for blizzard_urls.

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

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        console.print(f"[red]Failed to parse LLM response: {e}[/red]")
        console.print(content[:500])
        return {"error": str(e)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Blizzard patch notes URL from Liquipedia")
    parser.add_argument(
        "patch",
        help="Liquipedia URL or patch version (e.g., '5.0.15' or 'https://liquipedia.net/starcraft2/Patch_5.0.15')",
    )
    args = parser.parse_args()

    # Determine if input is URL or version
    if args.patch.startswith("http"):
        liquipedia_url = args.patch
        match = re.search(r"Patch_(.+)$", liquipedia_url)
        patch_version = match.group(1) if match else "unknown"
    else:
        patch_version = args.patch
        liquipedia_url = construct_liquipedia_url(patch_version)

    console.print("[bold]Fetching Liquipedia page...[/bold]")
    console.print(f"URL: {liquipedia_url}")

    try:
        html_content = fetch_page(liquipedia_url)
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Failed to fetch page: {e}[/red]")
        sys.exit(1)

    console.print(f"Fetched {len(html_content):,} bytes")

    console.print("\n[bold]Extracting Blizzard URLs...[/bold]")
    result = extract_blizzard_urls(html_content, patch_version)

    console.print("\n[bold]Result:[/bold]")
    print(json.dumps(result, indent=2))

    # Summary
    if result.get("blizzard_urls"):
        console.print(f"\n[green]Found {len(result['blizzard_urls'])} Blizzard URL(s):[/green]")
        for url in result["blizzard_urls"]:
            console.print(f"  - {url}")
    else:
        console.print("\n[yellow]No Blizzard URLs found[/yellow]")


if __name__ == "__main__":
    main()
