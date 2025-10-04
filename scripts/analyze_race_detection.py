"""Analyze how to detect race in different HTML patterns."""

from pathlib import Path

from bs4 import BeautifulSoup
from rich.console import Console

console = Console()


def find_race_markers(html_path: Path) -> dict:
    """Find all ways race is indicated in HTML.

    Args:
        html_path: Path to HTML file

    Returns:
        Dict with race detection methods
    """
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    blog_section = soup.find("section", class_="blog")
    if not blog_section:
        return {"error": "No blog section"}

    race_names = {"Zerg", "Protoss", "Terran"}
    results = {
        "h2_races": [],
        "h3_races": [],
        "h4_races": [],
        "strong_races": [],
        "p_races": [],
        "image_markers": [],
    }

    # Check H2 headers
    for h2 in blog_section.find_all("h2"):
        text = h2.get_text(strip=True)
        if text in race_names:
            results["h2_races"].append(text)

    # Check H3 headers
    for h3 in blog_section.find_all("h3"):
        text = h3.get_text(strip=True)
        if any(race in text for race in race_names):
            results["h3_races"].append(text)

    # Check H4 headers
    for h4 in blog_section.find_all("h4"):
        text = h4.get_text(strip=True)
        if any(race in text for race in race_names):
            results["h4_races"].append(text)

    # Check strong tags
    for strong in blog_section.find_all("strong"):
        text = strong.get_text(strip=True)
        if text in race_names:
            results["strong_races"].append(text)

    # Check paragraph tags
    for p in blog_section.find_all("p"):
        text = p.get_text(strip=True)
        if text in race_names:
            results["p_races"].append(text)

    # Check images (race icons)
    for img in blog_section.find_all("img"):
        src = img.get("src", "")
        alt = img.get("alt", "")
        # Look for race names in image paths
        for race in race_names:
            if race.lower() in src.lower() or race.lower() in alt.lower():
                results["image_markers"].append(race)
                break

    # Determine primary method
    if results["h2_races"]:
        primary = "h2_headers"
    elif results["strong_races"]:
        primary = "strong_tags"
    elif results["image_markers"]:
        primary = "image_markers"
    elif results["h3_races"]:
        primary = "h3_headers"
    else:
        primary = "unknown"

    results["primary_method"] = primary
    results["total_race_refs"] = sum(
        len(v) for k, v in results.items() if k != "primary_method" and isinstance(v, list)
    )

    return results


if __name__ == "__main__":
    html_dir = Path("data/raw_html")
    files = sorted(html_dir.glob("*.html"))

    console.print(f"[bold]Analyzing race detection in {len(files)} files...[/bold]\n")

    for html_path in files:
        results = find_race_markers(html_path)

        if "error" in results:
            console.print(f"[red]✗[/red] {html_path.name}: {results['error']}")
            continue

        primary = results["primary_method"]
        total = results["total_race_refs"]

        # Color code by method
        if primary == "h2_headers":
            color = "green"
        elif primary == "strong_tags":
            color = "yellow"
        elif primary == "image_markers":
            color = "blue"
        else:
            color = "red"

        console.print(
            f"[{color}]{primary:15}[/{color}] {html_path.stem:45} "
            f"(H2:{len(results['h2_races'])} "
            f"Strong:{len(results['strong_races'])} "
            f"Img:{len(results['image_markers'])})"
        )

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    console.print("  [green]h2_headers[/green]    - Direct H2 tags with race names")
    console.print("  [yellow]strong_tags[/yellow]   - Nested structure with <strong>Race</strong>")
    console.print("  [blue]image_markers[/blue] - Race icon images as markers")
