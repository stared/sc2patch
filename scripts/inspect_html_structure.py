"""Inspect HTML structure to understand metadata location."""

import json
from pathlib import Path

from bs4 import BeautifulSoup


def inspect_html(html_path: Path) -> None:
    """Inspect HTML file structure."""
    print(f"\n{'='*80}")
    print(f"Inspecting: {html_path.name}")
    print(f"{'='*80}\n")

    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # Look for JSON-LD script tags
    print("=== JSON-LD Scripts ===")
    scripts = soup.find_all("script", type="application/ld+json")
    for i, script in enumerate(scripts):
        print(f"\nScript {i+1}:")
        try:
            data = json.loads(script.string)
            print(json.dumps(data, indent=2))
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Error parsing: {e}")

    # Look for meta tags
    print("\n=== Meta Tags ===")
    meta_tags = soup.find_all("meta")
    for meta in meta_tags:
        if meta.get("property") or meta.get("name"):
            print(f"{meta.get('property') or meta.get('name')}: {meta.get('content')}")

    # Look for title
    print("\n=== Title ===")
    title = soup.find("title")
    if title:
        print(title.text.strip())

    # Look for h1
    print("\n=== H1 ===")
    h1 = soup.find("h1")
    if h1:
        print(h1.text.strip())

    # Look for time tags
    print("\n=== Time Tags ===")
    time_tags = soup.find_all("time")
    for time_tag in time_tags:
        print(f"Time: {time_tag.get('datetime')} - Text: {time_tag.text.strip()}")


if __name__ == "__main__":
    html_dir = Path("data/raw_html")

    # Inspect a few different patches
    test_files = [
        "starcraft-ii-4-0.html",
        "starcraft-ii-5-0-15.html",
        "20273794.html",  # The problematic one
        "starcraft-ii-2-1-9.html",
    ]

    for filename in test_files:
        html_path = html_dir / filename
        if html_path.exists():
            inspect_html(html_path)
        else:
            print(f"\n{filename} not found")
