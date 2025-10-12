"""Categorize all patches by their HTML structure pattern.

This helps identify which parser to use for each patch.
"""

import json
from pathlib import Path

from bs4 import BeautifulSoup


def detect_pattern(html_path: Path) -> dict:
    """Detect HTML pattern for a patch.

    Returns:
        Dict with pattern info: {
            'pattern': str,
            'has_h2_race_headers': bool,
            'has_h3_headers': bool,
            'has_race_images': bool,
            'has_strong_tags': bool,
            'sample_structure': str
        }
    """
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    blog = soup.find("section", class_="blog")
    if not blog:
        return {"pattern": "no_blog_section", "error": "No blog section found"}

    # Check for different patterns
    h2_headers = blog.find_all("h2")
    h3_headers = blog.find_all("h3")
    race_images = blog.find_all(
        "img", alt=lambda x: x and any(race in x.lower() for race in ["terran", "protoss", "zerg"])
    )
    strong_tags = blog.find_all("strong")

    # Check if H2 headers contain race names
    h2_race_headers = [
        h2 for h2 in h2_headers if h2.get_text(strip=True) in ["Terran", "Protoss", "Zerg"]
    ]

    # Determine pattern
    pattern = "unknown"
    if h2_race_headers:
        pattern = "direct_h2"
    elif race_images:
        pattern = "image_markers"
    elif h3_headers and any(
        h3.get_text(strip=True) in ["Terran", "Protoss", "Zerg"] for h3 in h3_headers
    ):
        pattern = "h3_race_headers"
    elif strong_tags:
        # Check if strong tags are used for entity names
        pattern = "nested_strong"

    # Get sample structure (first few elements)
    sample_elements = []
    for i, element in enumerate(blog.children):
        if not element.name:
            continue
        if i > 10:
            break
        sample_elements.append(f"{element.name}: {element.get_text(strip=True)[:50]}")

    return {
        "pattern": pattern,
        "has_h2_race_headers": len(h2_race_headers) > 0,
        "has_h3_headers": len(h3_headers) > 0,
        "has_race_images": len(race_images) > 0,
        "has_strong_tags": len(strong_tags) > 0,
        "h2_count": len(h2_headers),
        "h3_count": len(h3_headers),
        "sample_structure": "\n".join(sample_elements[:5]),
    }


def main():
    html_dir = Path("data/raw_html")
    md_dir = Path("data/raw_patches")

    results = {}

    # Get all markdown files to know versions
    md_files = sorted(md_dir.glob("*.md"))

    for md_path in md_files:
        version = md_path.stem

        # Find HTML file
        html_candidates = list(html_dir.glob(f"*{version.replace('.', '-')}*.html"))

        if not html_candidates:
            results[version] = {"pattern": "no_html", "error": "HTML file not found"}
            continue

        html_path = html_candidates[0]
        results[version] = detect_pattern(html_path)

    # Group by pattern
    by_pattern = {}
    for version, info in results.items():
        pattern = info["pattern"]
        if pattern not in by_pattern:
            by_pattern[pattern] = []
        by_pattern[pattern].append(version)

    # Print results
    print("Patches by Pattern:")
    print("=" * 60)
    for pattern, versions in sorted(by_pattern.items()):
        print(f"\n{pattern.upper()} ({len(versions)} patches):")
        for version in sorted(versions):
            print(f"  - {version}")

    print("\n\nDetailed Analysis:")
    print("=" * 60)
    for version in sorted(results.keys()):
        info = results[version]
        print(f"\n{version}:")
        print(f"  Pattern: {info['pattern']}")
        if info["pattern"] not in ["no_html", "no_blog_section"]:
            print(f"  H2 count: {info.get('h2_count', 0)}")
            print(f"  H3 count: {info.get('h3_count', 0)}")
            print(f"  Has H2 race headers: {info.get('has_h2_race_headers', False)}")
            print(f"  Has race images: {info.get('has_race_images', False)}")

    # Save to file
    output_path = Path("scripts/patch_patterns.json")
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n\nFull results saved to {output_path}")


if __name__ == "__main__":
    main()
