"""Download StarCraft 2 patch notes and convert to Markdown."""

import re
import time
from datetime import datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from pydantic import BaseModel
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .discover import load_patch_urls

console = Console()


class DownloadError(Exception):
    """Raised when patch download fails."""


class PatchMetadata(BaseModel):
    """Metadata extracted from patch page."""

    version: str
    date: str
    title: str


def fetch_html(url: str, timeout: int = 30) -> str:
    """Fetch HTML from URL.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        HTML content as string

    Raises:
        DownloadError: If request fails or returns non-200 status
    """
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except httpx.HTTPStatusError as e:
        raise DownloadError(f"HTTP {e.response.status_code} for {url}") from e
    except httpx.RequestError as e:
        raise DownloadError(f"Request failed for {url}: {e}") from e


def extract_patch_version(html: str, url: str) -> str:
    """Extract patch version from HTML.

    Args:
        html: HTML content
        url: URL (used for error messages)

    Returns:
        Patch version string (e.g., "5.0.12")

    Raises:
        DownloadError: If version cannot be extracted
    """
    soup = BeautifulSoup(html, "html.parser")

    # Try to find version in title
    title = soup.find("title")
    if title:
        # Look for patterns like "5.0.12", "4.7.1", etc.
        match = re.search(r"\b(\d+\.\d+\.?\d*)\b", title.text)
        if match:
            return match.group(1)

    # Try h1 heading
    h1 = soup.find("h1")
    if h1:
        match = re.search(r"\b(\d+\.\d+\.?\d*)\b", h1.text)
        if match:
            return match.group(1)

    # Try to extract from URL as last resort
    match = re.search(r"/(\d+-\d+-\d+)", url)
    if match:
        # Convert "5-0-12" to "5.0.12"
        return match.group(1).replace("-", ".")

    raise DownloadError(f"Could not extract patch version from {url}")


def extract_patch_date(html: str) -> str:
    """Extract patch date from HTML.

    Args:
        html: HTML content

    Returns:
        ISO date string (YYYY-MM-DD)

    Raises:
        DownloadError: If date cannot be extracted
    """
    soup = BeautifulSoup(html, "html.parser")

    # Look for time tags with datetime attribute
    time_tag = soup.find("time")
    if time_tag and time_tag.get("datetime"):
        datetime_str = time_tag["datetime"]
        # Parse and convert to YYYY-MM-DD
        try:
            dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            pass

    # Look for common date patterns in text
    date_patterns = [
        r"(\w+ \d{1,2}, \d{4})",  # "October 4, 2025"
        r"(\d{4}-\d{2}-\d{2})",  # "2025-10-04"
    ]

    text = soup.get_text()
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                # Try to parse the matched date
                date_str = match.group(1)
                dt = datetime.strptime(date_str, "%B %d, %Y")
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                # Try other format
                if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
                    return date_str

    raise DownloadError("Could not extract patch date from HTML")


def extract_patch_title(html: str) -> str:
    """Extract patch title from HTML.

    Args:
        html: HTML content

    Returns:
        Title string

    Raises:
        DownloadError: If title cannot be extracted
    """
    soup = BeautifulSoup(html, "html.parser")

    # Try h1 first
    h1 = soup.find("h1")
    if h1 and h1.text.strip():
        return h1.text.strip()

    # Try title tag
    title = soup.find("title")
    if title and title.text.strip():
        # Clean up title (remove " - Blizzard News" etc.)
        return re.sub(r"\s*[-–—]\s*Blizzard.*$", "", title.text.strip())

    raise DownloadError("Could not extract patch title from HTML")


def extract_article_content(html: str) -> str:
    """Extract main article content from HTML.

    Args:
        html: Full HTML content

    Returns:
        Extracted article HTML

    Raises:
        DownloadError: If article content cannot be found
    """
    soup = BeautifulSoup(html, "html.parser")

    # Try common article selectors
    article = (
        soup.find("article")
        or soup.find("div", class_="article-body")
        or soup.find("div", class_="detail-body")
        or soup.find("main")
    )

    if not article:
        raise DownloadError("Could not find article content in HTML")

    return str(article)


def extract_metadata(html: str, url: str) -> PatchMetadata:
    """Extract all metadata from HTML.

    Args:
        html: HTML content
        url: URL (for error messages and fallback)

    Returns:
        PatchMetadata object

    Raises:
        DownloadError: If required metadata cannot be extracted
    """
    version = extract_patch_version(html, url)
    date = extract_patch_date(html)
    title = extract_patch_title(html)

    return PatchMetadata(version=version, date=date, title=title)


def html_to_markdown(html: str, metadata: PatchMetadata, url: str) -> str:
    """Convert HTML to Markdown with frontmatter.

    Args:
        html: HTML content to convert
        metadata: Extracted metadata
        url: Source URL

    Returns:
        Markdown formatted text with frontmatter
    """
    # Convert HTML to Markdown
    markdown = md(html, heading_style="ATX", bullets="-")

    # Add frontmatter
    frontmatter = f"""---
version: {metadata.version}
date: {metadata.date}
title: {metadata.title}
url: {url}
---

# {metadata.title}

"""
    return frontmatter + markdown


def download_url_to_markdown(url: str, output_dir: Path) -> Path:
    """Download URL and convert to Markdown.

    Extracts all metadata (version, date, title) from the HTML.

    Args:
        url: URL to download
        output_dir: Directory to save Markdown file

    Returns:
        Path to saved Markdown file

    Raises:
        DownloadError: If download or extraction fails
    """
    # Fetch HTML
    html = fetch_html(url)

    # Extract metadata FROM the page
    metadata = extract_metadata(html, url)

    # Extract article content
    article_html = extract_article_content(html)

    # Convert to Markdown
    markdown = html_to_markdown(article_html, metadata, url)

    # Validate content
    if not markdown.strip():
        raise DownloadError(f"Generated empty Markdown for {url}")

    # Save to file named by version
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{metadata.version}.md"
    output_path.write_text(markdown, encoding="utf-8")

    return output_path


def download_all_patches(urls_path: Path, output_dir: Path, delay: float = 1.0) -> dict[str, Path]:
    """Download all patches from URL list.

    Args:
        urls_path: Path to patch_urls.json
        output_dir: Directory to save Markdown files
        delay: Delay between requests in seconds

    Returns:
        Dictionary mapping patch URL to output file path

    Raises:
        DownloadError: If any download fails
        FileNotFoundError: If URLs file doesn't exist
    """
    # Load URLs
    urls = load_patch_urls(urls_path)
    results: dict[str, Path] = {}

    console.print(f"[bold]Downloading {len(urls)} patches...[/bold]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading patches...", total=len(urls))

        for url in urls:
            progress.update(task, description=f"Downloading {url.split('/')[-1]}...")

            try:
                output_path = download_url_to_markdown(url, output_dir)
                results[url] = output_path
                console.print(f"[green]✓[/green] {output_path.stem} → {output_path.name}")

            except DownloadError as e:
                console.print(f"[red]✗[/red] {url}: {e}")
                raise

            progress.advance(task)

            # Be polite to the server
            if delay > 0:
                time.sleep(delay)

    console.print(f"\n[green]✓ Downloaded {len(results)} patches[/green]")
    return results


def main() -> None:
    """Main entry point for downloading patches."""
    urls_path = Path("data/patch_urls.json")
    output_dir = Path("raw_patches")

    try:
        download_all_patches(urls_path, output_dir, delay=1.0)
    except Exception as e:
        console.print(f"[red bold]Error:[/red bold] {e}")
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
