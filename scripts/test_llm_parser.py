"""Test the LLM parser on a single patch (3.8.0)."""

import json
from pathlib import Path
from dotenv import load_dotenv
import os
import sys

# Add parent directory to path to import the parser
sys.path.insert(0, str(Path(__file__).parent))
from parse_with_llm import process_patch, console, MODEL

# Load environment variables
load_dotenv()

def main():
    """Test parsing patch 3.8.0."""

    # Check if API key is available
    if not os.environ.get("OPENROUTER_API_KEY"):
        console.print("[red]Error: OPENROUTER_API_KEY not found in .env file[/red]")
        console.print("Please add your OpenRouter API key to the .env file")
        return

    # Path to patch 3.8.0
    patch_path = Path("data/raw_patches/3.8.0.md")

    if not patch_path.exists():
        console.print(f"[red]Error: {patch_path} not found[/red]")
        return

    console.print(f"[bold cyan]Testing LLM parser on patch 3.8.0 with {MODEL}...[/bold cyan]\n")

    try:
        # Process the patch
        result = process_patch(patch_path)

        # Save to test output
        output_path = Path("data/processed/patches/3.8.0_llm_test.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2))

        # Display results
        console.print(f"[green]✓ Successfully parsed patch 3.8.0[/green]")
        console.print(f"  Version: {result['metadata']['version']}")
        console.print(f"  Date: {result['metadata']['date']}")
        console.print(f"  Total changes: {len(result['changes'])}")

        # Show some sample changes by race
        races = {}
        for change in result['changes']:
            race = change['entity_id'].split('-')[0]
            if race not in races:
                races[race] = []
            races[race].append(change)

        console.print("\n[bold]Sample changes by race:[/bold]")
        for race, changes in races.items():
            console.print(f"\n[cyan]{race.capitalize()}[/cyan] ({len(changes)} changes):")
            for change in changes[:3]:  # Show first 3 changes per race
                entity = change['entity_id'].split('-', 1)[1] if '-' in change['entity_id'] else change['entity_id']
                console.print(f"  • {entity}: {change['raw_text'][:80]}...")

        console.print(f"\n[green]Output saved to: {output_path}[/green]")

    except Exception as e:
        console.print(f"[red]Error processing patch: {e}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()