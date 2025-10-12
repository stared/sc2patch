"""Test HTML parser on a single patch."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from parse_html_with_llm import extract_body_from_html, extract_changes_with_llm
from rich.console import Console

console = Console()

# Test with 1.2.0 patch (known to exist)
html_path = Path("data/raw_html/9995561.html")

console.print(f"\n[bold]Testing HTML parser on {html_path.name}...[/bold]\n")

# Extract body
body_text, version = extract_body_from_html(html_path)

console.print(f"[green]✓[/green] Version: {version}")
console.print(f"[green]✓[/green] Body text: {len(body_text)} chars\n")

# Parse with GPT-5
console.print("[cyan]Parsing with GPT-5...[/cyan]\n")
patch_data = extract_changes_with_llm(body_text, version)

console.print(f"[green]✓[/green] Parsed successfully:")
console.print(f"  Version: {patch_data.version}")
console.print(f"  Date: {patch_data.date}")
console.print(f"  Entities: {len(patch_data.changes)}")
console.print(f"  Total changes: {sum(len(e.changes) for e in patch_data.changes)}")

console.print("\n[bold]Entities:[/bold]")
for entity in patch_data.changes:
    console.print(f"  • {entity.entity_name} ({entity.entity_id}): {len(entity.changes)} changes")
