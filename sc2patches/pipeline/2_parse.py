#!/usr/bin/env python3
"""Stage 2: Parse HTML patches with LLM to extract structured balance changes.

Usage:
    uv run python sc2patches/pipeline/2_parse.py                    # Parse all
    uv run python sc2patches/pipeline/2_parse.py --skip-existing    # Skip already parsed
    uv run python sc2patches/pipeline/2_parse.py 5.0.15             # Parse specific version

Supports multi-HTML parsing when patches have additional_urls in patch_urls.json.
The LLM parses main + BU HTML files together for intelligent deduplication.
"""

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from sc2patches.core.extraction import url_to_filename
from sc2patches.core.logger import PipelineLogger
from sc2patches.core.models import PatchConfig
from sc2patches.core.parse import ParseError, parse_patch, parse_patches_combined

# Load environment variables from .env file
load_dotenv()

console = Console()


@dataclass
class ParseContext:
    """Context for parsing operations."""

    html_dir: Path
    output_dir: Path
    skip_existing: bool
    logger: PipelineLogger
    api_key: str


def get_api_key() -> str:
    """Get OpenRouter API key from environment. Fails if not found."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        return api_key
    console.print("[red]ERROR: OPENROUTER_API_KEY not found in environment[/red]")
    console.print("Set it in .env file or export OPENROUTER_API_KEY=...")
    sys.exit(1)


def load_patch_config(urls_path: Path) -> list[PatchConfig]:
    """Load and validate patch configuration from patch_urls.json.

    Returns:
        List of validated PatchConfig objects

    Raises:
        ValidationError: If any patch config is invalid
    """
    if not urls_path.exists():
        console.print(f"[red]ERROR: {urls_path} not found[/red]")
        sys.exit(1)

    with urls_path.open() as f:
        data = json.load(f)

    return [PatchConfig(**item) for item in data]


def find_html_files_for_patch(html_dir: Path, version: str, url: str | None = None) -> list[Path]:
    """Find all HTML files for a patch version (main + additional).

    Looks for:
    - Main file: matches version in filename OR URL-derived filename
    - Additional files: {version}_additional_*.html

    Returns:
        List of HTML paths, main file first
    """
    url_matched_files = []
    version_matched_files = []
    additional_files = []

    # Expected filename from URL
    expected_filename = url_to_filename(url) if url else None

    # Version pattern with word boundaries to avoid "4-0" matching "4-4-0"
    # Match version at end of filename or followed by non-digit
    version_dashed = version.replace(".", "-")
    # Pattern: version at end, or version followed by non-digit (like "-bu" or ".html")
    version_pattern = re.compile(rf"(^|[^0-9]){re.escape(version_dashed)}($|[^0-9])")

    # Find main file - prioritize URL match over version match
    for html_path in html_dir.glob("*.html"):
        stem = html_path.stem
        # Skip additional files
        if "_additional_" in stem:
            continue

        # Check URL match first (exact match)
        if expected_filename and stem == expected_filename:
            url_matched_files.append(html_path)
        # Check version match with word boundaries
        elif version_pattern.search(stem):
            version_matched_files.append(html_path)

    # Find additional files
    for html_path in html_dir.glob(f"{version}_additional_*.html"):
        additional_files.append(html_path)

    # Sort additional files by index
    additional_files.sort()

    # Prioritize URL matches over version matches
    if url_matched_files:
        return url_matched_files[:1] + additional_files
    if version_matched_files:
        return version_matched_files[:1] + additional_files
    return additional_files


def process_single_patch(patch_config: PatchConfig, ctx: ParseContext) -> bool:
    """Process a single patch configuration. Returns True to continue."""
    version = patch_config.version
    url = patch_config.url
    output_path = ctx.output_dir / f"{version}.json"

    if output_path.exists() and ctx.skip_existing:
        ctx.logger.log_skip(version, "already exists")
        console.print(f"[dim]  ⊘ {version}: already exists[/dim]")
        return True

    html_files = find_html_files_for_patch(ctx.html_dir, version, url)
    if not html_files:
        ctx.logger.log_skip(version, "no HTML files found")
        console.print(f"[dim]  ⊘ {version}: no HTML files[/dim]")
        return True

    # Parse HTML -> ParsedPatch
    if len(html_files) > 1:
        console.print(f"[cyan]  ↳ Parsing {len(html_files)} files together...[/cyan]")
        parsed = parse_patches_combined(html_files, version, ctx.api_key, patch_config.parse_hint)
    else:
        parsed = parse_patch(html_files[0], version, ctx.api_key, patch_config.parse_hint)

    # Warn if LLM parsed different version
    if parsed.version != version:
        console.print(f"[yellow]  ⚠ Version mismatch: parsed '{parsed.version}' vs config '{version}'[/yellow]")

    # Override with config values (source of truth: patch_urls.json)
    parsed.version = version
    parsed.url = url

    # Save JSON
    output_dict = parsed.to_json_dict()
    with output_path.open("w") as f:
        json.dump(output_dict, f, indent=2)

    entities = len({c.entity_id for c in parsed.changes})
    suffix = f" (merged {len(html_files)} files)" if len(html_files) > 1 else ""

    ctx.logger.log_success(version, f"{entities} entities, {len(parsed.changes)} changes → {output_path.name}")
    console.print(f"[green]  ✓ {version}:[/green] {entities} entities, {len(parsed.changes)} changes{suffix}")

    return True


def main() -> None:
    """Parse all HTML patches with Gemini 3 Pro."""
    api_key = get_api_key()
    skip_existing = "--skip-existing" in sys.argv
    specific_version = next((a for a in sys.argv[1:] if not a.startswith("--")), None)

    html_dir = Path("data/raw_html")
    output_dir = Path("data/processed/patches")
    urls_path = Path("data/patch_urls.json")
    output_dir.mkdir(parents=True, exist_ok=True)

    patch_configs = load_patch_config(urls_path)
    logger = PipelineLogger("parse")
    ctx = ParseContext(
        html_dir=html_dir,
        output_dir=output_dir,
        skip_existing=skip_existing,
        logger=logger,
        api_key=api_key,
    )

    if specific_version:
        configs_to_parse = [p for p in patch_configs if p.version == specific_version]
        if not configs_to_parse:
            console.print(f"[red]No config found for version: {specific_version}[/red]")
            sys.exit(1)
    else:
        configs_to_parse = patch_configs

    multi_html_count = sum(1 for p in configs_to_parse if p.additional_urls)

    console.print("\n[bold]Stage 2: Parse Patches with Gemini 3 Pro[/bold]")
    console.print(f"Patches to parse: {len(configs_to_parse)}")
    console.print(f"Patches with additional URLs (multi-HTML): {multi_html_count}")
    console.print(f"Skip existing: {skip_existing}\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing...", total=len(configs_to_parse))

        for patch_config in configs_to_parse:
            progress.update(task, description=f"Processing {patch_config.version}")

            try:
                process_single_patch(patch_config, ctx)
                time.sleep(2.0)  # Be polite to API
            except ParseError as e:
                ctx.logger.log_failure(patch_config.version, str(e))
                console.print(f"[red]  ✗ {patch_config.version}:[/red] {str(e)[:100]}")

            progress.advance(task)

    log_path = ctx.logger.write(
        additional_summary={
            "Total patches": len(configs_to_parse),
            "Multi-HTML patches": multi_html_count,
            "Output directory": str(output_dir),
        }
    )

    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  ✅ Successful: {len(ctx.logger.successful)}")
    console.print(f"  ❌ Failed: {len(ctx.logger.failed)}")
    console.print(f"  ⊘ Skipped: {len(ctx.logger.skipped)}")
    console.print(f"\n[dim]Log saved to: {log_path}[/dim]")

    if ctx.logger.failed:
        console.print(f"\n[red]Parse failed for {len(ctx.logger.failed)} patches[/red]")
        sys.exit(1)

    console.print("\n[green]✓ Parse stage complete[/green]")


if __name__ == "__main__":
    main()
