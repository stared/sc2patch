"""Validation checks for StarCraft 2 patch data pipeline."""

from pathlib import Path

from rich.console import Console
from rich.table import Table

from .discover import load_patch_urls

console = Console()


class ValidationError(Exception):
    """Raised when validation fails."""


def validate_html_downloads(urls_path: Path, html_dir: Path) -> None:
    """Validate that all patches from URL list were fetched as HTML.

    Args:
        urls_path: Path to patch_urls.json
        html_dir: Directory containing downloaded HTML files

    Raises:
        ValidationError: If validation fails
        FileNotFoundError: If URLs file doesn't exist
    """
    console.print("[bold]Validating HTML downloads...[/bold]\n")

    # Load patch URLs
    urls = load_patch_urls(urls_path)
    expected_count = len(urls)

    # Check HTML directory exists
    if not html_dir.exists():
        raise ValidationError(f"HTML directory does not exist: {html_dir}")

    if not html_dir.is_dir():
        raise ValidationError(f"HTML path is not a directory: {html_dir}")

    # Get all downloaded HTML files
    html_files = list(html_dir.glob("*.html"))
    actual_count = len(html_files)

    # Check counts match
    if actual_count != expected_count:
        raise ValidationError(f"Expected {expected_count} HTML files, found {actual_count}")

    # Check each file
    empty = []
    found = []

    for html_file in sorted(html_files):
        if html_file.stat().st_size == 0:
            empty.append(html_file.name)
        else:
            content = html_file.read_text(encoding="utf-8")
            if not content.strip():
                empty.append(html_file.name)
            else:
                found.append(html_file.name)

    # Report results
    table = Table(title="HTML Download Validation")
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")

    table.add_row("[green]✓ Found[/green]", str(len(found)))
    table.add_row("[yellow]⚠ Empty[/yellow]", str(len(empty)))

    console.print(table)

    # Raise error if any issues
    if empty:
        raise ValidationError(f"Found {len(empty)} empty HTML files: {', '.join(empty)}")

    console.print(f"\n[green]✓ All {len(found)} HTML files downloaded[/green]")


def validate_markdown_conversion(html_dir: Path, markdown_dir: Path) -> None:
    """Validate that all HTML files were converted to Markdown.

    Args:
        html_dir: Directory containing HTML files
        markdown_dir: Directory containing Markdown files

    Raises:
        ValidationError: If validation fails
    """
    console.print("[bold]Validating Markdown conversion...[/bold]\n")

    # Check directories exist
    if not html_dir.exists():
        raise ValidationError(f"HTML directory does not exist: {html_dir}")

    if not markdown_dir.exists():
        raise ValidationError(f"Markdown directory does not exist: {markdown_dir}")

    # Get file counts
    html_files = list(html_dir.glob("*.html"))
    md_files = list(markdown_dir.glob("*.md"))

    expected_count = len(html_files)
    actual_count = len(md_files)

    # Check each Markdown file
    empty = []
    invalid = []
    found = []

    for md_file in sorted(md_files):
        content = md_file.read_text(encoding="utf-8")

        if not content.strip():
            empty.append(md_file.name)
            continue

        # Check for frontmatter
        if not content.startswith("---"):
            invalid.append((md_file.name, "Missing frontmatter"))
            continue

        # Check for required frontmatter fields
        required_fields = ["version:", "date:", "title:"]
        missing_fields = []
        for field in required_fields:
            if field not in content[:500]:  # Check first 500 chars
                missing_fields.append(field)

        if missing_fields:
            invalid.append((md_file.name, f"Missing {', '.join(missing_fields)}"))
            continue

        found.append(md_file.name)

    # Report results
    table = Table(title="Markdown Conversion Validation")
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")

    table.add_row("[cyan]HTML files[/cyan]", str(expected_count))
    table.add_row("[green]✓ Converted[/green]", str(len(found)))
    table.add_row("[yellow]⚠ Empty[/yellow]", str(len(empty)))
    table.add_row("[red]✗ Invalid[/red]", str(len(invalid)))

    console.print(table)

    # Show invalid files
    if invalid:
        console.print("\n[red]Invalid files:[/red]")
        for name, reason in invalid:
            console.print(f"  {name}: {reason}")

    # Raise error if any issues
    if empty:
        raise ValidationError(f"Found {len(empty)} empty Markdown files")

    if invalid:
        raise ValidationError(f"Found {len(invalid)} invalid Markdown files")

    if actual_count != expected_count:
        raise ValidationError(f"Expected {expected_count} Markdown files, found {actual_count}")

    console.print(f"\n[green]✓ All {len(found)} Markdown files valid[/green]")


def validate_file_sizes(directory: Path, min_size: int = 100, file_pattern: str = "*") -> None:
    """Validate that files meet minimum size requirements.

    Args:
        directory: Directory containing files
        min_size: Minimum file size in bytes
        file_pattern: Glob pattern for files to check

    Raises:
        ValidationError: If any files are too small
    """
    console.print(f"[bold]Checking file sizes (min: {min_size} bytes)...[/bold]\n")

    if not directory.exists():
        raise ValidationError(f"Directory does not exist: {directory}")

    small_files = []

    for file in sorted(directory.glob(file_pattern)):
        if file.is_file():
            size = file.stat().st_size
            if size < min_size:
                small_files.append((file.name, size))

    if small_files:
        console.print("[yellow]⚠ Files smaller than expected:[/yellow]")
        for name, size in small_files:
            console.print(f"  {name}: {size} bytes")
        raise ValidationError(f"Found {len(small_files)} suspiciously small files")

    console.print("[green]✓ All files meet minimum size requirement[/green]")


def run_all_validations(urls_path: Path, html_dir: Path, markdown_dir: Path) -> None:
    """Run all validation checks.

    Args:
        urls_path: Path to patch_urls.json
        html_dir: Directory containing HTML files
        markdown_dir: Directory containing Markdown files

    Raises:
        ValidationError: If any validation fails
    """
    console.print("\n[bold cyan]═══ Running Validation Checks ═══[/bold cyan]\n")

    try:
        # Validate HTML downloads
        validate_html_downloads(urls_path, html_dir)
        validate_file_sizes(html_dir, min_size=1000, file_pattern="*.html")

        # Validate Markdown conversion
        validate_markdown_conversion(html_dir, markdown_dir)
        validate_file_sizes(markdown_dir, min_size=100, file_pattern="*.md")

        console.print("\n[bold green]═══ All Validations Passed ═══[/bold green]\n")

    except ValidationError as e:
        console.print("\n[bold red]═══ Validation Failed ═══[/bold red]")
        console.print(f"[red]{e}[/red]\n")
        raise


def main() -> None:
    """Main entry point for validation."""
    urls_path = Path("data/patch_urls.json")
    html_dir = Path("data/raw_html")
    markdown_dir = Path("data/raw_patches")

    try:
        run_all_validations(urls_path, html_dir, markdown_dir)
    except ValidationError as e:
        console.print(f"[red bold]Validation Error:[/red bold] {e}")
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
