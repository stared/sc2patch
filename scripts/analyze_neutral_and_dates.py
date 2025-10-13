"""Comprehensive analysis of neutral entities and date parsing issues.

This script:
1. Finds ALL neutral entities across all patches
2. Checks date validity for all patches
3. Analyzes naming patterns and potential misclassifications
4. Generates actionable recommendations
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def load_all_patches() -> List[Dict]:
    """Load all processed patch files."""
    patches_dir = Path("data/processed/patches")
    patches = []

    for patch_file in sorted(patches_dir.glob("*.json")):
        with open(patch_file) as f:
            data = json.load(f)
            patches.append(data)

    return patches


def analyze_neutral_entities(patches: List[Dict]) -> Dict[str, List[Dict]]:
    """Find all neutral entities and categorize them."""
    neutral_entities = defaultdict(list)

    for patch in patches:
        for change in patch["changes"]:
            entity_id = change["entity_id"]

            if entity_id.startswith("neutral-"):
                entity_name = entity_id.replace("neutral-", "")

                # Check if name contains race keywords (problematic)
                has_race_keyword = any(
                    race in entity_name.lower()
                    for race in ["terran", "protoss", "zerg"]
                )

                neutral_entities[entity_id].append({
                    "patch": patch["metadata"]["version"],
                    "raw_text": change["raw_text"],
                    "change_type": change["change_type"],
                    "has_race_keyword": has_race_keyword,
                })

    return dict(neutral_entities)


def check_dates(patches: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Check all patch dates for validity."""
    valid_dates = []
    invalid_dates = []

    # Date regex pattern (YYYY-MM-DD)
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    for patch in patches:
        metadata = patch["metadata"]
        version = metadata["version"]
        date = metadata.get("date", "")

        if date and date != "unknown" and date_pattern.match(date):
            valid_dates.append({
                "version": version,
                "date": date,
                "url": metadata.get("url", ""),
            })
        else:
            # Check if HTML file exists
            html_candidates = [
                Path("data/raw_html") / f"{version}.html",
                Path("data/raw_html") / f"{version.replace(' ', '_')}.html",
            ]

            html_exists = any(p.exists() for p in html_candidates)

            invalid_dates.append({
                "version": version,
                "date": date,
                "url": metadata.get("url", ""),
                "html_exists": html_exists,
            })

    return valid_dates, invalid_dates


def categorize_neutral_entities(
    neutral_entities: Dict[str, List[Dict]]
) -> Tuple[Dict, Dict, Dict]:
    """Categorize neutral entities into keep/investigate/re-parse."""
    # Legitimate neutral map elements (keep)
    legitimate_keywords = [
        "mineral", "vespene", "gas", "geyser", "rock", "tower",
        "debris", "destructible", "xel", "watch", "watchtower",
    ]

    # Suspicious patterns (investigate)
    suspicious_keywords = ["terran", "protoss", "zerg"]

    keep = {}
    investigate = {}
    reclassify = {}

    for entity_id, occurrences in neutral_entities.items():
        entity_name = entity_id.replace("neutral-", "")
        entity_lower = entity_name.lower()

        # Check for race keywords in name
        has_race = any(race in entity_lower for race in suspicious_keywords)

        # Check if it's a legitimate neutral element
        is_legitimate = any(keyword in entity_lower for keyword in legitimate_keywords)

        if has_race:
            # Definitely suspicious - contains race name
            investigate[entity_id] = {
                "occurrences": occurrences,
                "reason": f"Contains race keyword in name: {entity_name}",
                "entity_name": entity_name,
            }
        elif is_legitimate:
            # Legitimate map element
            keep[entity_id] = {
                "occurrences": occurrences,
                "reason": "Legitimate map element",
                "entity_name": entity_name,
            }
        else:
            # Not obviously legitimate or suspicious - needs review
            investigate[entity_id] = {
                "occurrences": occurrences,
                "reason": f"Unclear classification: {entity_name}",
                "entity_name": entity_name,
            }

    return keep, investigate, reclassify


def print_neutral_analysis(
    keep: Dict, investigate: Dict, reclassify: Dict
) -> None:
    """Print analysis of neutral entities."""
    console.print("\n" + "=" * 80)
    console.print("[bold cyan]NEUTRAL ENTITIES ANALYSIS[/bold cyan]")
    console.print("=" * 80 + "\n")

    # Section 1: Keep (legitimate neutral)
    if keep:
        console.print(Panel("[bold green]✓ KEEP AS NEUTRAL[/bold green] (Legitimate map elements)", expand=False))
        for entity_id, data in sorted(keep.items()):
            console.print(f"\n[green]●[/green] {entity_id}")
            console.print(f"  Reason: {data['reason']}")
            console.print(f"  Appears in {len(data['occurrences'])} patch(es)")

            # Show sample
            if data['occurrences']:
                sample = data['occurrences'][0]
                console.print(f"  Example: [dim]{sample['patch']}: {sample['raw_text'][:80]}...[/dim]")

    # Section 2: Investigate
    if investigate:
        console.print(f"\n\n{Panel('[bold yellow]⚠ INVESTIGATE[/bold yellow] (Needs review)', expand=False)}")
        for entity_id, data in sorted(investigate.items()):
            console.print(f"\n[yellow]●[/yellow] {entity_id}")
            console.print(f"  Reason: {data['reason']}")
            console.print(f"  Appears in {len(data['occurrences'])} patch(es)")

            # Show all occurrences for investigation
            for occ in data['occurrences']:
                console.print(
                    f"    [{occ['patch']}] "
                    f"[{occ['change_type']}] "
                    f"{occ['raw_text'][:60]}..."
                )

    # Section 3: Re-classify (if any)
    if reclassify:
        console.print(f"\n\n{Panel('[bold red]✗ RE-PARSE NEEDED[/bold red] (Wrong classification)', expand=False)}")
        for entity_id, data in sorted(reclassify.items()):
            console.print(f"\n[red]●[/red] {entity_id}")
            console.print(f"  Reason: {data['reason']}")
            console.print(f"  Appears in {len(data['occurrences'])} patch(es)")


def print_date_analysis(valid: List[Dict], invalid: List[Dict]) -> None:
    """Print analysis of patch dates."""
    console.print("\n\n" + "=" * 80)
    console.print("[bold cyan]DATE VALIDATION ANALYSIS[/bold cyan]")
    console.print("=" * 80 + "\n")

    # Valid dates
    console.print(f"[green]✓ Valid dates: {len(valid)}/{ len(valid) + len(invalid)}[/green]\n")

    # Invalid dates
    if invalid:
        console.print(Panel(f"[bold red]✗ INVALID/MISSING DATES: {len(invalid)}[/bold red]", expand=False))

        table = Table(show_header=True, header_style="bold red")
        table.add_column("Patch Version", style="yellow")
        table.add_column("Current Date", style="dim")
        table.add_column("HTML Exists?", justify="center")
        table.add_column("URL", style="cyan")

        for item in invalid:
            html_status = "[green]✓[/green]" if item["html_exists"] else "[red]✗[/red]"
            table.add_row(
                item["version"],
                item["date"] or "[red](empty)[/red]",
                html_status,
                item["url"][:50] + "..." if len(item["url"]) > 50 else item["url"],
            )

        console.print(table)


def suggest_fixes(invalid_dates: List[Dict], investigate: Dict) -> None:
    """Suggest concrete fixes."""
    console.print("\n\n" + "=" * 80)
    console.print("[bold cyan]RECOMMENDED ACTIONS[/bold cyan]")
    console.print("=" * 80 + "\n")

    # Fix dates
    if invalid_dates:
        console.print("[bold]1. Fix Date Extraction[/bold]")
        console.print("\nPatches needing date fixes:")

        for item in invalid_dates:
            console.print(f"\n  • [yellow]{item['version']}[/yellow]")

            if not item["html_exists"]:
                console.print(f"    [red]→ Download HTML from: {item['url']}[/red]")
            else:
                console.print(f"    [yellow]→ Extract date from HTML or URL[/yellow]")

                # Try to extract date from URL
                url = item["url"]
                date_match = re.search(
                    r"(january|february|march|april|may|june|july|august|september|october|november|december)-?(\d{1,2})-?(\d{4})",
                    url,
                    re.IGNORECASE
                )

                if date_match:
                    month_name, day, year = date_match.groups()
                    months = {
                        "january": "01", "february": "02", "march": "03",
                        "april": "04", "may": "05", "june": "06",
                        "july": "07", "august": "08", "september": "09",
                        "october": "10", "november": "11", "december": "12",
                    }
                    month = months.get(month_name.lower())
                    suggested_date = f"{year}-{month}-{day.zfill(2)}"
                    console.print(f"    [green]→ Suggested from URL: {suggested_date}[/green]")

    # Fix neutral entities
    if investigate:
        console.print(f"\n\n[bold]2. Review Neutral Entities ({len(investigate)} entities)[/bold]")
        console.print("\nFor each entity above, decide:")
        console.print("  • Keep as neutral (if it's truly a map element)")
        console.print("  • Re-parse to correct race (if misclassified)")
        console.print("  • Rename to remove race keywords (if confusing)")


def main():
    """Run comprehensive analysis."""
    console.print("\n[bold]Loading all patches...[/bold]")
    patches = load_all_patches()
    console.print(f"[green]✓[/green] Loaded {len(patches)} patches\n")

    # Analyze neutral entities
    console.print("[bold]Analyzing neutral entities...[/bold]")
    neutral_entities = analyze_neutral_entities(patches)
    keep, investigate, reclassify = categorize_neutral_entities(neutral_entities)
    console.print(f"[green]✓[/green] Found {len(neutral_entities)} unique neutral entities\n")

    # Check dates
    console.print("[bold]Validating patch dates...[/bold]")
    valid_dates, invalid_dates = check_dates(patches)
    console.print(f"[green]✓[/green] Validation complete\n")

    # Print results
    print_neutral_analysis(keep, investigate, reclassify)
    print_date_analysis(valid_dates, invalid_dates)
    suggest_fixes(invalid_dates, investigate)

    console.print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
