"""Extract all entity names from patches to build vocabulary."""

import json
from collections import defaultdict
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString
from rich.console import Console

console = Console()


def extract_entity_candidates(html_path: Path) -> set[str]:
    """Extract potential entity names from HTML.

    Entities are typically in:
    - <strong> tags within lists
    - <p> tags followed by <ul>
    - <h3> or <h4> headers

    Args:
        html_path: Path to HTML file

    Returns:
        Set of candidate entity names
    """
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    blog_section = soup.find("section", class_="blog")
    if not blog_section:
        return set()

    candidates = set()

    # Strong tags (often unit/building names)
    for strong in blog_section.find_all("strong"):
        text = strong.get_text(strip=True)
        # Filter out section headers like "Terran", "GENERAL"
        if text and len(text) < 50 and not text.isupper():
            candidates.add(text)

    # Paragraphs followed by lists (3.x pattern)
    for p in blog_section.find_all("p"):
        text = p.get_text(strip=True)
        # Check if next sibling is a list
        next_sib = p.find_next_sibling()
        if next_sib and next_sib.name == "ul":
            if text and len(text) < 50 and not text.isupper():
                candidates.add(text)

    # H3/H4 headers (sometimes used for units)
    for header in blog_section.find_all(["h3", "h4"]):
        text = header.get_text(strip=True)
        if text and len(text) < 50 and not text.isupper():
            candidates.add(text)

    # Filter out common non-entities
    filtered = set()
    skip_words = {
        "Terran",
        "Protoss",
        "Zerg",
        "General",
        "Bug Fixes",
        "Co-op",
        "Campaign",
        "Maps",
        "Editor",
        "Versus",
        "Balance",
        "GENERAL",
        "VERSUS",
        "BUG FIXES",
        "CO-OP",
        "CAMPAIGN",
    }

    for candidate in candidates:
        # Skip if it's a known section header
        if candidate in skip_words:
            continue
        # Skip if it starts with numbers or special chars
        if candidate and candidate[0].isalpha():
            filtered.add(candidate)

    return filtered


if __name__ == "__main__":
    html_dir = Path("data/raw_html")
    files = sorted(html_dir.glob("*.html"))

    console.print(f"[bold]Extracting entities from {len(files)} files...[/bold]\n")

    all_entities = defaultdict(int)
    patch_entities = {}

    for html_path in files:
        entities = extract_entity_candidates(html_path)
        patch_entities[html_path.stem] = entities

        for entity in entities:
            all_entities[entity] += 1

        console.print(f"  {html_path.stem:45} - {len(entities)} entities")

    # Sort by frequency
    sorted_entities = sorted(all_entities.items(), key=lambda x: (-x[1], x[0]))

    console.print(f"\n[bold]Found {len(all_entities)} unique entities across all patches[/bold]\n")

    # Show most common entities
    console.print("[bold]Most Common Entities (appears in N patches):[/bold]")
    for entity, count in sorted_entities[:50]:
        console.print(f"  {count:2}x  {entity}")

    # Save to JSON for review
    output = {
        "total_unique": len(all_entities),
        "entities_by_frequency": [
            {"name": name, "patch_count": count} for name, count in sorted_entities
        ],
    }

    output_path = Path("scripts/entity_candidates.json")
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    console.print(f"\n[green]✓[/green] Saved entity candidates to {output_path}")
