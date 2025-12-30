#!/usr/bin/env python3
"""Verify all Liquipedia URLs in units.json are valid (return 200)."""
import json
import httpx
from pathlib import Path
from rich.console import Console
from rich.table import Table
import time

console = Console()

def verify_url(url: str, timeout: float = 10.0) -> tuple[bool, int | str]:
    """Check if URL returns 200. Returns (success, status_code_or_error)."""
    if url is None:
        return True, "null (skipped)"

    try:
        # Use head request first (faster)
        response = httpx.head(url, follow_redirects=True, timeout=timeout)
        if response.status_code == 200:
            return True, 200
        # Some servers don't support HEAD, try GET
        response = httpx.get(url, follow_redirects=True, timeout=timeout)
        return response.status_code == 200, response.status_code
    except httpx.TimeoutException:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def main():
    units_path = Path("data/units.json")

    with open(units_path) as f:
        units = json.load(f)

    console.print(f"\n[bold]Verifying {len(units)} unit URLs...[/bold]\n")

    results = {"ok": [], "failed": [], "skipped": []}

    for i, unit in enumerate(units):
        unit_id = unit["id"]
        url = unit.get("liquipedia_url")

        if url is None:
            results["skipped"].append((unit_id, "no URL"))
            console.print(f"[dim]{i+1:3}. {unit_id}: skipped (no URL)[/dim]")
            continue

        success, status = verify_url(url)

        if success:
            results["ok"].append((unit_id, url))
            console.print(f"[green]{i+1:3}. {unit_id}: ✓[/green]")
        else:
            results["failed"].append((unit_id, url, status))
            console.print(f"[red]{i+1:3}. {unit_id}: ✗ ({status})[/red]")
            console.print(f"     [dim]{url}[/dim]")

        # Rate limiting - be nice to Liquipedia
        time.sleep(0.2)

    # Summary
    console.print("\n" + "="*60)
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  [green]OK: {len(results['ok'])}[/green]")
    console.print(f"  [red]Failed: {len(results['failed'])}[/red]")
    console.print(f"  [dim]Skipped: {len(results['skipped'])}[/dim]")

    if results["failed"]:
        console.print(f"\n[bold red]Failed URLs:[/bold red]")
        table = Table()
        table.add_column("Unit ID")
        table.add_column("URL")
        table.add_column("Error")

        for unit_id, url, status in results["failed"]:
            table.add_row(unit_id, url, str(status))

        console.print(table)

        # Exit with error if any failed
        exit(1)
    else:
        console.print("\n[bold green]All URLs are valid![/bold green]")


if __name__ == "__main__":
    main()
