"""Process all patches and generate individual JSON files per patch."""

import json
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .parse import parse_patch_html

console = Console()


class ProcessError(Exception):
    """Raised when processing fails."""


def process_single_patch(
    html_path: Path, md_path: Path, output_dir: Path
) -> Path:
    """Process a single patch and save to JSON.

    Args:
        html_path: Path to HTML file
        md_path: Path to Markdown file
        output_dir: Directory to save JSON output

    Returns:
        Path to generated JSON file

    Raises:
        ProcessError: If processing fails
    """
    try:
        metadata, changes = parse_patch_html(html_path, md_path)
    except Exception as e:
        raise ProcessError(f"Failed to parse {html_path.name}: {e}") from e

    # Convert to JSON-serializable format
    output = {
        "metadata": {
            "version": metadata.version,
            "date": metadata.date,
            "title": metadata.title,
            "url": metadata.url,
        },
        "changes": [
            {
                "id": f"{metadata.version}-{idx}",
                "patch_version": metadata.version,
                "entity_id": change.entity_id,
                "raw_text": change.raw_text,
                "source_section": change.section.value,
            }
            for idx, change in enumerate(changes)
        ],
    }

    # Save to file named by version
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{metadata.version}.json"

    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    return output_path


def process_all_patches(
    html_dir: Path, md_dir: Path, output_dir: Path
) -> dict[str, Path]:
    """Process all patches and generate individual JSON files.

    Args:
        html_dir: Directory containing HTML files
        md_dir: Directory containing Markdown files
        output_dir: Directory to save JSON files

    Returns:
        Dictionary mapping version to output file path

    Raises:
        ProcessError: If processing fails
    """
    if not html_dir.exists():
        raise ProcessError(f"HTML directory not found: {html_dir}")

    if not md_dir.exists():
        raise ProcessError(f"Markdown directory not found: {md_dir}")

    # Get all markdown files (these have the version numbers)
    md_files = sorted(md_dir.glob("*.md"))

    if not md_files:
        raise ProcessError(f"No Markdown files found in {md_dir}")

    console.print(f"[bold]Processing {len(md_files)} patches...[/bold]\n")

    results = {}
    errors = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing patches...", total=len(md_files))

        for md_path in md_files:
            # Find corresponding HTML file
            # Markdown files are named like "5.0.15.md"
            # HTML files are named like "starcraft-ii-5-0-15.html"
            version = md_path.stem
            progress.update(task, description=f"Processing {version}...")

            # Try to find HTML file (may need mapping logic)
            # For now, skip if we can't find it
            html_candidates = list(html_dir.glob(f"*{version.replace('.', '-')}*.html"))

            if not html_candidates:
                console.print(f"[yellow]⚠[/yellow] No HTML found for {version}")
                errors.append(version)
                progress.advance(task)
                continue

            html_path = html_candidates[0]

            try:
                output_path = process_single_patch(html_path, md_path, output_dir)
                results[version] = output_path
                console.print(f"[green]✓[/green] {version} → {output_path.name}")

            except ProcessError as e:
                console.print(f"[red]✗[/red] {version}: {e}")
                errors.append(version)

            progress.advance(task)

    if errors:
        console.print(f"\n[yellow]⚠ {len(errors)} patches had errors[/yellow]")
        for version in errors:
            console.print(f"  - {version}")

    console.print(f"\n[green]✓ Processed {len(results)} patches[/green]")
    return results


def main() -> None:
    """Main entry point for processing patches."""
    html_dir = Path("data/raw_html")
    md_dir = Path("data/raw_patches")
    output_dir = Path("data/processed/patches")

    try:
        process_all_patches(html_dir, md_dir, output_dir)
    except Exception as e:
        console.print(f"[red bold]Error:[/red bold] {e}")
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
