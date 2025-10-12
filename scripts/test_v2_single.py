"""Test v2 parser on a single patch (3.8.0)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from parse_with_llm_v2 import process_patch, console

def main():
    """Test on 3.8.0."""
    patch_path = Path("data/raw_patches/3.8.0.md")

    if not patch_path.exists():
        console.print(f"[red]Error: {patch_path} not found[/red]")
        return

    console.print("[bold cyan]Testing improved parser on patch 3.8.0...[/bold cyan]\n")

    try:
        result = process_patch(patch_path)

        console.print(f"\n[green]✓ Successfully parsed patch 3.8.0[/green]")
        console.print(f"  Total changes: {len(result['changes'])}")

        # Group by race
        races = {}
        for change in result['changes']:
            race = change['entity_id'].split('-')[0]
            if race not in races:
                races[race] = []
            races[race].append(change)

        console.print("\n[bold]Changes by race:[/bold]")
        for race, changes in races.items():
            console.print(f"\n[cyan]{race.capitalize()}[/cyan] ({len(changes)} changes):")
            entities = {}
            for change in changes:
                entity = change['entity_id']
                if entity not in entities:
                    entities[entity] = []
                entities[entity].append(change['raw_text'])

            for entity, texts in list(entities.items())[:3]:  # Show first 3 entities
                console.print(f"  • {entity}:")
                for text in texts[:2]:  # Show first 2 changes per entity
                    console.print(f"    - {text[:80]}...")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()