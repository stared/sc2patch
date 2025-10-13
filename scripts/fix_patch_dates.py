"""Robust date extraction and fixing for patches with missing/invalid dates.

This script:
1. Extracts dates from HTML metadata (<meta>, <time> tags)
2. Falls back to URL pattern matching
3. Validates and updates patch JSON files
4. Supports manual date overrides
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()

# Manual date overrides for patches where extraction fails
MANUAL_DATES = {
    "3.11.0 BU": "2017-03-07",  # From URL: march-7-2017
}


def extract_date_from_html(html_path: Path) -> Optional[str]:
    """Extract date from HTML metadata and structure.

    Returns date in YYYY-MM-DD format or None.
    """
    with open(html_path, encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # Try 1: <meta property="article:published_time">
    if meta := soup.find("meta", property="article:published_time"):
        date_str = meta.get("content", "")
        if date_str:
            try:
                # Parse ISO format (e.g., "2017-03-07T12:00:00Z")
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-% d")
            except:
                pass

    # Try 2: <time datetime="...">
    if time_tag := soup.find("time", datetime=True):
        date_str = time_tag.get("datetime", "")
        if date_str:
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d")
            except:
                pass

    # Try 3: <meta name="date">
    if meta := soup.find("meta", attrs={"name": "date"}):
        date_str = meta.get("content", "")
        if date_str:
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d")
            except:
                pass

    return None


def extract_date_from_url(url: str) -> Optional[str]:
    """Extract date from URL patterns.

    Handles formats like:
    - /march-7-2017
    - /2017-03-07
    - /20170307
    """
    # Pattern 1: month-day-year
    month_names = {
        "january": "01", "february": "02", "march": "03",
        "april": "04", "may": "05", "june": "06",
        "july": "07", "august": "08", "september": "09",
        "october": "10", "november": "11", "december": "12",
    }

    pattern = r"(january|february|march|april|may|june|july|august|september|october|november|december)-?(\d{1,2})-?(\d{4})"
    if match := re.search(pattern, url, re.IGNORECASE):
        month_name, day, year = match.groups()
        month = month_names.get(month_name.lower())
        if month:
            return f"{year}-{month}-{day.zfill(2)}"

    # Pattern 2: YYYY-MM-DD
    if match := re.search(r"(\d{4})-(\d{2})-(\d{2})", url):
        return match.group(0)

    # Pattern 3: YYYYMMDD
    if match := re.search(r"(\d{4})(\d{2})(\d{2})", url):
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"

    return None


def fix_patch_date(patch_file: Path, dry_run: bool = False) -> bool:
    """Fix date for a single patch file.

    Returns True if date was fixed or already valid.
    """
    with open(patch_file) as f:
        data = json.load(f)

    metadata = data["metadata"]
    version = metadata["version"]
    current_date = metadata.get("date", "")
    url = metadata.get("url", "")

    # Check if date is already valid
    if current_date and current_date != "unknown" and re.match(r"^\d{4}-\d{2}-\d{2}$", current_date):
        console.print(f"[dim]✓ {version}: Date already valid ({current_date})[/dim]")
        return True

    console.print(f"\n[yellow]Fixing date for {version}...[/yellow]")
    console.print(f"  Current date: [red]{current_date or '(empty)'}[/red]")
    console.print(f"  URL: {url}")

    # Try extraction methods in order
    extracted_date = None
    method = None

    # Method 1: Manual override
    if version in MANUAL_DATES:
        extracted_date = MANUAL_DATES[version]
        method = "manual override"

    # Method 2: HTML metadata
    if not extracted_date:
        # Find HTML file
        html_candidates = [
            Path("data/raw_html") / f"{url.split('/')[-1]}.html",
            Path("data/raw_html") / url.split("/")[-1],
        ]

        for html_path in html_candidates:
            if html_path.exists():
                extracted_date = extract_date_from_html(html_path)
                if extracted_date:
                    method = f"HTML metadata ({html_path.name})"
                    break

    # Method 3: URL pattern
    if not extracted_date and url:
        extracted_date = extract_date_from_url(url)
        if extracted_date:
            method = "URL pattern"

    # Update if we found a date
    if extracted_date:
        console.print(f"  [green]✓ Extracted: {extracted_date}[/green] (via {method})")

        if not dry_run:
            metadata["date"] = extracted_date
            with open(patch_file, "w") as f:
                json.dump(data, f, indent=2)
            console.print(f"  [green]✓ Updated {patch_file.name}[/green]")
        else:
            console.print(f"  [dim](dry run - not saved)[/dim]")

        return True
    else:
        console.print(f"  [red]✗ Could not extract date[/red]")
        return False


def main():
    """Fix dates for all patches with missing/invalid dates."""
    patches_dir = Path("data/processed/patches")

    console.print("\n[bold]Scanning patches for date issues...[/bold]\n")

    patches_to_fix = []
    for patch_file in sorted(patches_dir.glob("*.json")):
        with open(patch_file) as f:
            data = json.load(f)

        date = data["metadata"].get("date", "")
        if not date or date == "unknown" or not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            patches_to_fix.append(patch_file)

    if not patches_to_fix:
        console.print("[green]✓ All patches have valid dates![/green]")
        return

    console.print(f"[yellow]Found {len(patches_to_fix)} patch(es) needing date fixes:[/yellow]")
    for pf in patches_to_fix:
        console.print(f"  • {pf.stem}")

    console.print(f"\n[bold]Fixing dates...[/bold]")

    fixed = 0
    failed = []

    for patch_file in patches_to_fix:
        if fix_patch_date(patch_file, dry_run=False):
            fixed += 1
        else:
            failed.append(patch_file.stem)

    # Summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"[green]✓ Fixed: {fixed}/{len(patches_to_fix)}[/green]")

    if failed:
        console.print(f"\n[red]✗ Failed to fix {len(failed)} patch(es):[/red]")
        for name in failed:
            console.print(f"  • {name}")
        console.print("\n[yellow]These may need manual date entry.[/yellow]")


if __name__ == "__main__":
    main()
