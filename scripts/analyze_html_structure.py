"""Analyze HTML structure patterns across all patches."""

from pathlib import Path

from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table

console = Console()


def analyze_patch(html_path: Path) -> dict:
    """Analyze HTML structure for a single patch.

    Args:
        html_path: Path to HTML file

    Returns:
        Dict with structure information
    """
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    blog_section = soup.find("section", class_="blog")
    if not blog_section:
        return {"error": "No blog section found"}

    # Count structural elements
    h2_headers = blog_section.find_all("h2")
    h3_headers = blog_section.find_all("h3")
    h4_headers = blog_section.find_all("h4")
    strong_tags = blog_section.find_all("strong")
    images = blog_section.find_all("img")

    # Extract H2 text to identify pattern
    h2_texts = [h2.get_text(strip=True) for h2 in h2_headers]

    # Check for race names directly in H2
    race_names = {"Zerg", "Protoss", "Terran"}
    has_race_h2 = any(race in h2_texts for race in race_names)

    # Check for VERSUS/BALANCE in H2
    has_versus_h2 = any("VERSUS" in text.upper() or "BALANCE" in text.upper() for text in h2_texts)

    # Check for strong tags with race names
    strong_texts = [s.get_text(strip=True) for s in strong_tags]
    has_race_strong = any(race in strong_texts for race in race_names)

    # Determine pattern
    pattern = "unknown"
    if has_race_h2:
        pattern = "direct_h2"  # Pattern A: Direct H2 headers for races
    elif has_versus_h2 and has_race_strong:
        pattern = "nested_strong"  # Pattern B: Nested with strong tags
    elif images and not has_race_h2:
        pattern = "image_markers"  # Pattern C: Images as section markers

    return {
        "h2_count": len(h2_headers),
        "h3_count": len(h3_headers),
        "h4_count": len(h4_headers),
        "strong_count": len(strong_tags),
        "image_count": len(images),
        "h2_samples": h2_texts[:5],  # First 5 H2 headers
        "pattern": pattern,
        "has_race_h2": has_race_h2,
        "has_versus_h2": has_versus_h2,
        "has_race_strong": has_race_strong,
    }


if __name__ == "__main__":
    html_dir = Path("data/raw_html")
    files = sorted(html_dir.glob("*.html"))

    console.print(f"[bold]Analyzing {len(files)} HTML files...[/bold]\n")

    results = {}
    for html_path in files:
        # Extract version from filename
        stem = html_path.stem
        results[stem] = analyze_patch(html_path)

    # Create summary table
    table = Table(title="HTML Structure Patterns")
    table.add_column("File", style="cyan")
    table.add_column("Pattern", style="green")
    table.add_column("H2", justify="right")
    table.add_column("H3", justify="right")
    table.add_column("H4", justify="right")
    table.add_column("Strong", justify="right")
    table.add_column("Images", justify="right")
    table.add_column("H2 Samples", style="dim")

    for filename, data in results.items():
        if "error" in data:
            table.add_row(filename, "[red]ERROR[/red]", "-", "-", "-", "-", "-", data["error"])
            continue

        h2_sample = ", ".join(data["h2_samples"]) if data["h2_samples"] else "-"
        table.add_row(
            filename,
            data["pattern"],
            str(data["h2_count"]),
            str(data["h3_count"]),
            str(data["h4_count"]),
            str(data["strong_count"]),
            str(data["image_count"]),
            h2_sample[:60] + "..." if len(h2_sample) > 60 else h2_sample,
        )

    console.print(table)

    # Pattern distribution
    pattern_counts = {}
    for data in results.values():
        if "pattern" in data:
            pattern = data["pattern"]
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

    console.print("\n[bold]Pattern Distribution:[/bold]")
    for pattern, count in sorted(pattern_counts.items()):
        console.print(f"  {pattern}: {count} patches")
