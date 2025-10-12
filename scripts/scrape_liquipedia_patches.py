"""Scrape balance changes from Liquipedia for patches with dead official URLs."""

import json
from pathlib import Path
from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()


def scrape_liquipedia_balance_changes(url: str) -> Dict[str, List[Dict[str, Any]]]:
    """Scrape balance changes from a Liquipedia patch page.

    Args:
        url: Liquipedia patch URL

    Returns:
        Dict mapping race names to list of unit changes
    """
    response = httpx.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the "Balance Update" section
    balance_heading = soup.find('span', id='Balance_Update')
    if not balance_heading:
        console.print(f"[yellow]No 'Balance Update' section found, trying 'Versus'[/yellow]")
        balance_heading = soup.find('span', id='Versus')

    if not balance_heading:
        raise ValueError("No balance section found on page")

    # Start from the Balance Update heading
    current = balance_heading.parent

    changes_by_race = {}
    current_race = None

    # Walk through siblings until we hit the next major section
    while current:
        current = current.find_next_sibling()

        if not current:
            break

        # Check if we've reached the next major section (h2)
        if current.name == 'h2':
            break

        # Check for race headers (h3)
        if current.name == 'h3':
            race_span = current.find('span', class_='mw-headline')
            if race_span:
                race_name = race_span.get_text().strip().lower()
                # Map race names (handle duplicates like "Zerg_2")
                if 'terran' in race_name:
                    current_race = 'terran'
                elif 'zerg' in race_name:
                    current_race = 'zerg'
                elif 'protoss' in race_name:
                    current_race = 'protoss'
                else:
                    current_race = None

                if current_race and current_race not in changes_by_race:
                    changes_by_race[current_race] = []

        # Check for unit lists (ul directly after h3)
        if current.name == 'ul' and current_race:
            # Each top-level li is a unit
            for unit_li in current.find_all('li', recursive=False):
                # FORMAT 1: Unit name is in <b> tag with nested changes
                unit_bold = unit_li.find('b')
                if unit_bold:
                    unit_link = unit_bold.find('a')
                    unit_name = unit_link.get_text().strip() if unit_link else unit_bold.get_text().strip()

                    # Changes are in nested ul
                    changes_ul = unit_li.find('ul')
                    if changes_ul:
                        changes = []
                        for change_li in changes_ul.find_all('li', recursive=False):
                            change_text = change_li.get_text().strip()
                            if change_text:
                                changes.append(change_text)

                        if changes:
                            changes_by_race[current_race].append({
                                'unit_name': unit_name,
                                'changes': changes
                            })
                else:
                    # FORMAT 2: Unit name in <a> tag with change in same line
                    # e.g., <li><a>Stimpack</a> upgrade research duration reduced...</li>
                    unit_link = unit_li.find('a')
                    if unit_link:
                        unit_name = unit_link.get_text().strip()
                        # Get the full text and remove the unit name
                        full_text = unit_li.get_text().strip()

                        # Unit name + change in same line
                        if unit_name and full_text:
                            changes_by_race[current_race].append({
                                'unit_name': unit_name,
                                'changes': [full_text]
                            })

    return changes_by_race


def convert_to_patch_format(
    version: str,
    date: str,
    url: str,
    liquipedia_url: str,
    changes_by_race: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """Convert Liquipedia changes to our patch JSON format.

    Args:
        version: Patch version (e.g., "5.0.2 BU")
        date: Release date
        url: Liquipedia URL
        liquipedia_url: Source Liquipedia URL
        changes_by_race: Output from scrape_liquipedia_balance_changes

    Returns:
        Patch data in our standard format
    """
    result = {
        "metadata": {
            "version": version,
            "date": date,
            "title": f"StarCraft II Patch {version}",
            "url": url,
            "source": "liquipedia",
            "liquipedia_url": liquipedia_url
        },
        "changes": []
    }

    for race, units in changes_by_race.items():
        for unit_data in units:
            unit_name = unit_data['unit_name']
            # Convert unit name to entity_id format: race-unit_name
            entity_id = f"{race}-{unit_name.lower().replace(' ', '_')}"

            for change_text in unit_data['changes']:
                result["changes"].append({
                    "id": f"{entity_id}_{len(result['changes'])}",
                    "patch_version": version,
                    "entity_id": entity_id,
                    "raw_text": change_text
                })

    return result


def main() -> None:
    """Scrape the 4 Balance Updates with dead official URLs."""

    patches_to_scrape = [
        {
            "version": "5.0.2 BU",
            "date": "2020-08-20",
            "liquipedia_url": "https://liquipedia.net/starcraft2/Patch_5.0.2",
            "official_url": "https://starcraft2.com/news/23495670"
        },
        {
            "version": "4.10.1 BU",
            "date": "2019-08-21",
            "liquipedia_url": "https://liquipedia.net/starcraft2/Patch_4.10.1",
            "official_url": "https://starcraft2.com/news/23093843"
        },
        {
            "version": "3.3.2 BU",
            "date": "2016-07-06",
            "liquipedia_url": "https://liquipedia.net/starcraft2/Patch_3.3.2",
            "official_url": "https://starcraft2.com/en-us/news/20142728"
        },
        {
            "version": "3.3.0 BU",
            "date": "2016-05-23",
            "liquipedia_url": "https://liquipedia.net/starcraft2/Patch_3.3.0",
            "official_url": "http://eu.battle.net/sc2/en/blog/20118421/"
        }
    ]

    output_dir = Path("data/processed/patches")
    output_dir.mkdir(parents=True, exist_ok=True)

    successful = 0
    failed = []

    for patch in patches_to_scrape:
        console.print(f"\n[bold]Scraping {patch['version']}...[/bold]")
        console.print(f"[dim]URL: {patch['liquipedia_url']}[/dim]")

        try:
            # Scrape balance changes
            changes_by_race = scrape_liquipedia_balance_changes(patch['liquipedia_url'])

            if not changes_by_race:
                console.print(f"[yellow]⚠ No balance changes found[/yellow]")
                failed.append((patch['version'], "No balance changes found"))
                continue

            # Convert to our format
            patch_data = convert_to_patch_format(
                version=patch['version'],
                date=patch['date'],
                url=patch['official_url'],
                liquipedia_url=patch['liquipedia_url'],
                changes_by_race=changes_by_race
            )

            # Save to file
            output_path = output_dir / f"{patch['version'].replace(' ', '_')}.json"
            with open(output_path, 'w') as f:
                json.dump(patch_data, f, indent=2)

            total_changes = len(patch_data['changes'])
            console.print(f"[green]✓ Success:[/green] {total_changes} changes from {len(changes_by_race)} races")
            successful += 1

        except Exception as e:
            console.print(f"[red]✗ Error:[/red] {type(e).__name__}: {e}")
            failed.append((patch['version'], str(e)))

    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"[green]Successfully scraped: {successful}/{len(patches_to_scrape)}[/green]")

    if failed:
        console.print(f"\n[red]Failed: {len(failed)}[/red]")
        for version, error in failed:
            console.print(f"  • {version}: {error[:80]}")


if __name__ == "__main__":
    main()
