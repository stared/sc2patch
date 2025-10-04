"""Convert downloaded HTML files to Markdown."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify as md
from pydantic import BaseModel
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class ConvertError(Exception):
    """Raised when HTML conversion fails."""


class PatchMetadata(BaseModel):
    """Metadata extracted from patch page."""

    version: str
    date: str
    title: str


def extract_jsonld(html: str) -> dict:
    """Extract JSON-LD NewsArticle data from HTML.

    Args:
        html: HTML content

    Returns:
        Parsed JSON-LD dict

    Raises:
        ConvertError: If JSON-LD not found or invalid
    """
    soup = BeautifulSoup(html, "html.parser")

    # Find JSON-LD script tag
    script = soup.find("script", type="application/ld+json")

    if not script or not script.string:
        raise ConvertError("No JSON-LD script found")

    # Fix common JSON syntax error in Blizzard's JSON-LD
    # Missing comma between author and publisher arrays
    json_str = script.string
    json_str = re.sub(r'(\])\s*("publisher")', r'\1,\2', json_str)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ConvertError(f"Failed to parse JSON-LD: {e}") from e

    if not isinstance(data, dict) or data.get("@type") != "NewsArticle":
        raise ConvertError("JSON-LD is not a NewsArticle")

    return data


def extract_url(html: str) -> str:
    """Extract source URL from HTML meta tags.

    All Blizzard patch notes have og:url meta tag.

    Args:
        html: HTML content

    Returns:
        Source URL

    Raises:
        ConvertError: If URL cannot be extracted
    """
    soup = BeautifulSoup(html, "html.parser")

    og_url = soup.find("meta", property="og:url")
    if not og_url or not og_url.get("content"):
        raise ConvertError("No og:url meta tag found")

    return og_url["content"]


def extract_metadata(html: str) -> PatchMetadata:
    """Extract all metadata from HTML via JSON-LD.

    Args:
        html: HTML content

    Returns:
        PatchMetadata object

    Raises:
        ConvertError: If required metadata cannot be extracted
    """
    jsonld = extract_jsonld(html)

    # Extract title
    title = jsonld.get("headline")
    if not title:
        raise ConvertError("No headline in JSON-LD")

    # Extract date
    date_published = jsonld.get("datePublished")
    if not date_published:
        raise ConvertError("No datePublished in JSON-LD")

    # Parse ISO datetime to date (handle Z timezone indicator)
    try:
        dt = datetime.fromisoformat(date_published.replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError) as e:
        raise ConvertError(f"Invalid datePublished format: {date_published}") from e

    # Extract version from title
    match = re.search(r"\b(\d+\.\d+\.?\d*)\b", title)
    if not match:
        raise ConvertError(f"No version number found in title: {title}")

    version = match.group(1)

    return PatchMetadata(version=version, date=date_str, title=title)


def extract_article_content(html: str) -> str:
    """Extract main article content from HTML.

    All Blizzard patch notes have a section.blog element containing the content.

    Args:
        html: Full HTML content

    Returns:
        Extracted article HTML (content only, no header)

    Raises:
        ConvertError: If blog section cannot be found
    """
    soup = BeautifulSoup(html, "html.parser")

    # All files have section.blog - verified across all 27 patches
    blog_section = soup.find("section", class_="blog")

    if not blog_section:
        raise ConvertError("No section.blog found in HTML")

    return str(blog_section)


def html_to_markdown(html: str, metadata: PatchMetadata, source_url: str) -> str:
    """Convert HTML to Markdown with frontmatter.

    Args:
        html: HTML content to convert
        metadata: Extracted metadata
        source_url: Original patch URL

    Returns:
        Markdown formatted text with frontmatter
    """
    # Convert HTML to Markdown
    markdown = md(html, heading_style="ATX", bullets="-")

    # Get current date for processing timestamp (UTC)
    processed_date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    # Add frontmatter
    frontmatter = f"""---
version: {metadata.version}
date: {metadata.date}
title: {metadata.title}
url: {source_url}
processed: {processed_date}
---

# {metadata.title}

"""
    return frontmatter + markdown


def convert_html_to_markdown(html_path: Path, output_dir: Path) -> Path:
    """Convert HTML file to Markdown.

    Extracts all metadata (version, date, title, URL) from the HTML.

    Args:
        html_path: Path to HTML file
        output_dir: Directory to save Markdown file

    Returns:
        Path to saved Markdown file

    Raises:
        ConvertError: If conversion fails
        FileNotFoundError: If HTML file doesn't exist
    """
    if not html_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")

    # Read HTML
    html = html_path.read_text(encoding="utf-8")

    # Extract metadata FROM HTML
    metadata = extract_metadata(html)
    source_url = extract_url(html)

    # Extract article content
    article_html = extract_article_content(html)

    # Convert to Markdown
    markdown = html_to_markdown(article_html, metadata, source_url)

    # Validate content
    if not markdown.strip():
        raise ConvertError(f"Generated empty Markdown for {html_path.name}")

    # Save to file named by version
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{metadata.version}.md"
    output_path.write_text(markdown, encoding="utf-8")

    return output_path


def convert_all_patches(html_dir: Path, output_dir: Path) -> dict[str, Path]:
    """Convert all HTML files to Markdown.

    Args:
        html_dir: Directory containing HTML files
        output_dir: Directory to save Markdown files

    Returns:
        Dictionary mapping HTML filename to output file path

    Raises:
        ConvertError: If any conversion fails
        FileNotFoundError: If HTML directory doesn't exist
    """
    if not html_dir.exists():
        raise FileNotFoundError(f"HTML directory not found: {html_dir}")

    html_files = sorted(html_dir.glob("*.html"))

    if not html_files:
        raise ConvertError(f"No HTML files found in {html_dir}")

    results: dict[str, Path] = {}

    console.print(f"[bold]Converting {len(html_files)} HTML files to Markdown...[/bold]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Converting patches...", total=len(html_files))

        for html_path in html_files:
            progress.update(task, description=f"Converting {html_path.stem}...")

            try:
                output_path = convert_html_to_markdown(html_path, output_dir)
                results[html_path.stem] = output_path
                console.print(f"[green]✓[/green] {html_path.name} → {output_path.name}")

            except ConvertError as e:
                console.print(f"[red]✗[/red] {html_path.name}: {e}")
                raise

            progress.advance(task)

    console.print(f"\n[green]✓ Converted {len(results)} patches[/green]")
    return results


def main() -> None:
    """Main entry point for converting patches."""
    html_dir = Path("data/raw_html")
    output_dir = Path("data/raw_patches")

    try:
        convert_all_patches(html_dir, output_dir)
    except Exception as e:
        console.print(f"[red bold]Error:[/red bold] {e}")
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
