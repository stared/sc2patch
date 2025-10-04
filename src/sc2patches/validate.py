"""Validation checks for StarCraft 2 patch data pipeline."""

from pathlib import Path

from rich.console import Console
from rich.table import Table

from .discover import load_patch_urls

console = Console()


class ValidationError(Exception):
    """Raised when validation fails."""


def validate_downloads(urls_path: Path, download_dir: Path) -> None:
    """Validate that all patches from URL list were downloaded.

    Args:
        urls_path: Path to patch_urls.json
        download_dir: Directory containing downloaded Markdown files

    Raises:
        ValidationError: If validation fails
        FileNotFoundError: If URLs file doesn't exist
    """
    console.print("[bold]Validating downloads...[/bold]\n")

    # Load patch URLs
    urls = load_patch_urls(urls_path)
    expected_count = len(urls)

    # Check download directory exists
    if not download_dir.exists():
        raise ValidationError(f"Download directory does not exist: {download_dir}")

    if not download_dir.is_dir():
        raise ValidationError(f"Download path is not a directory: {download_dir}")

    # Get all downloaded files
    downloaded_files = list(download_dir.glob("*.md"))
    actual_count = len(downloaded_files)

    # Check counts match
    if actual_count != expected_count:
        raise ValidationError(
            f"Expected {expected_count} patches, found {actual_count} downloaded files"
        )

    # Check each file
    empty = []
    found = []

    for md_file in sorted(downloaded_files):
        if md_file.stat().st_size == 0:
            empty.append(md_file.name)
        else:
            # File exists and has content
            content = md_file.read_text(encoding="utf-8")
            if not content.strip():
                empty.append(md_file.name)
            else:
                found.append(md_file.name)

    # Report results
    table = Table(title="Download Validation Results")
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Details", overflow="fold")

    table.add_row("[green]✓ Found[/green]", str(len(found)), f"{len(found)} files")
    table.add_row(
        "[yellow]⚠ Empty[/yellow]", str(len(empty)), ", ".join(empty) if empty else "None"
    )

    console.print(table)

    # Raise error if any issues
    if empty:
        raise ValidationError(f"Found {len(empty)} empty patch files: {', '.join(empty)}")

    console.print(f"\n[green]✓ All {len(found)} patches downloaded successfully[/green]")


def validate_file_sizes(download_dir: Path, min_size: int = 100) -> None:
    """Validate that downloaded files meet minimum size requirements.

    Args:
        download_dir: Directory containing downloaded Markdown files
        min_size: Minimum file size in bytes

    Raises:
        ValidationError: If any files are too small
    """
    console.print(f"[bold]Checking file sizes (min: {min_size} bytes)...[/bold]\n")

    if not download_dir.exists():
        raise ValidationError(f"Download directory does not exist: {download_dir}")

    small_files = []

    for md_file in sorted(download_dir.glob("*.md")):
        size = md_file.stat().st_size
        if size < min_size:
            small_files.append((md_file.name, size))

    if small_files:
        console.print("[yellow]⚠ Files smaller than expected:[/yellow]")
        for name, size in small_files:
            console.print(f"  {name}: {size} bytes")
        raise ValidationError(f"Found {len(small_files)} suspiciously small files")

    console.print("[green]✓ All files meet minimum size requirement[/green]")


def validate_markdown_structure(download_dir: Path) -> None:
    """Validate that Markdown files have expected structure.

    Args:
        download_dir: Directory containing downloaded Markdown files

    Raises:
        ValidationError: If files don't have expected structure
    """
    console.print("[bold]Validating Markdown structure...[/bold]\n")

    if not download_dir.exists():
        raise ValidationError(f"Download directory does not exist: {download_dir}")

    invalid = []

    for md_file in sorted(download_dir.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")

        # Check for frontmatter
        if not content.startswith("---"):
            invalid.append((md_file.name, "Missing frontmatter"))
            continue

        # Check for required frontmatter fields
        required_fields = ["version:", "date:", "title:", "url:"]
        for field in required_fields:
            if field not in content[:500]:  # Check first 500 chars
                invalid.append((md_file.name, f"Missing {field} in frontmatter"))
                break

    if invalid:
        console.print("[red]✗ Invalid Markdown files:[/red]")
        for name, reason in invalid:
            console.print(f"  {name}: {reason}")
        raise ValidationError(f"Found {len(invalid)} invalid Markdown files")

    console.print("[green]✓ All Markdown files have valid structure[/green]")


def run_all_validations(urls_path: Path, download_dir: Path) -> None:
    """Run all validation checks.

    Args:
        urls_path: Path to patch_urls.json
        download_dir: Directory containing downloaded Markdown files

    Raises:
        ValidationError: If any validation fails
    """
    console.print("\n[bold cyan]═══ Running Validation Checks ═══[/bold cyan]\n")

    try:
        validate_downloads(urls_path, download_dir)
        validate_file_sizes(download_dir, min_size=100)
        validate_markdown_structure(download_dir)

        console.print("\n[bold green]═══ All Validations Passed ═══[/bold green]\n")

    except ValidationError as e:
        console.print("\n[bold red]═══ Validation Failed ═══[/bold red]")
        console.print(f"[red]{e}[/red]\n")
        raise


def main() -> None:
    """Main entry point for validation."""
    urls_path = Path("data/patch_urls.json")
    download_dir = Path("raw_patches")

    try:
        run_all_validations(urls_path, download_dir)
    except ValidationError as e:
        console.print(f"[red bold]Validation Error:[/red bold] {e}")
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
