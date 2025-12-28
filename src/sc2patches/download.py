"""Download and convert StarCraft 2 patch notes."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from pydantic import BaseModel


class DownloadError(Exception):
    """Raised when download or conversion fails."""


class PatchMetadata(BaseModel):
    """Metadata extracted from patch page."""

    version: str
    date: str
    title: str
    url: str


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


def validate_patch_html(html: str, url: str) -> None:
    """Validate that HTML contains patch notes, not homepage.

    Args:
        html: HTML content
        url: Source URL (for error message)

    Raises:
        DownloadError: If HTML is invalid or is homepage instead of patch notes
    """
    if not html.strip():
        raise DownloadError(f"Empty HTML from {url}")

    # Check for homepage indicators
    homepage_indicators = [
        "The ultimate real-time strategy game",
        "REAL-TIME STRATEGY • FREE TO PLAY",
        "The Galaxy is Yours to Conquer",
        "<title>StarCraft II</title>",
    ]

    # Check for patch notes indicators
    patch_indicators = [
        "Patch Notes",
        "Balance Update",
        "patch notes",
        "balance changes",
        "Balance Changes",
    ]

    has_homepage_text = any(ind in html for ind in homepage_indicators)
    has_patch_text = any(ind in html for ind in patch_indicators)

    # If it has homepage text but no patch text, it's a homepage
    if has_homepage_text and not has_patch_text:
        raise DownloadError(
            f"URL returned homepage instead of patch notes: {url}\n"
            "This URL is likely dead or redirected."
        )

    # If it has neither, it's probably an error page
    if not has_patch_text:
        raise DownloadError(
            f"HTML from {url} doesn't appear to contain patch notes\n"
            "Expected to find: 'Patch Notes', 'Balance Update', etc."
        )


def extract_jsonld(html: str) -> dict:
    """Extract JSON-LD NewsArticle data from HTML.

    Args:
        html: HTML content

    Returns:
        Parsed JSON-LD dict

    Raises:
        DownloadError: If JSON-LD not found or invalid
    """
    soup = BeautifulSoup(html, "html.parser")

    # Find JSON-LD script tag
    script = soup.find("script", type="application/ld+json")

    if not script or not script.string:
        raise DownloadError("No JSON-LD script found")

    # Fix common JSON syntax error in Blizzard's JSON-LD
    # Missing comma between author and publisher arrays
    json_str = script.string
    json_str = re.sub(r'(\])\s*("publisher")', r"\1,\2", json_str)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise DownloadError(f"Failed to parse JSON-LD: {e}") from e

    if not isinstance(data, dict) or data.get("@type") != "NewsArticle":
        raise DownloadError("JSON-LD is not a NewsArticle")

    return data


def extract_url(html: str) -> str:
    """Extract source URL from HTML meta tags.

    All Blizzard patch notes have og:url meta tag.

    Args:
        html: HTML content

    Returns:
        Source URL

    Raises:
        DownloadError: If URL cannot be extracted
    """
    soup = BeautifulSoup(html, "html.parser")

    og_url = soup.find("meta", property="og:url")
    if not og_url or not og_url.get("content"):
        raise DownloadError("No og:url meta tag found")

    return og_url["content"]


def extract_metadata(html: str, source_url: str, version_hint: str | None = None) -> PatchMetadata:
    """Extract all metadata from HTML via JSON-LD.

    Args:
        html: HTML content
        source_url: Original source URL (used as fallback)
        version_hint: Optional version to use if not found in title (e.g., for BU patches)

    Returns:
        PatchMetadata object

    Raises:
        DownloadError: If required metadata cannot be extracted
    """
    jsonld = extract_jsonld(html)

    # Extract title
    title = jsonld.get("headline")
    if not title:
        raise DownloadError("No headline in JSON-LD")

    # Extract date
    date_published = jsonld.get("datePublished")
    if not date_published:
        raise DownloadError("No datePublished in JSON-LD")

    # Parse ISO datetime to date (handle Z timezone indicator)
    try:
        dt = datetime.fromisoformat(date_published.replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError) as e:
        raise DownloadError(f"Invalid datePublished format: {date_published}") from e

    # Extract version from title, or use version_hint if provided
    match = re.search(r"\b(\d+\.\d+\.?\d*)\b", title)
    if match:
        version = match.group(1)
    elif version_hint:
        version = version_hint
    else:
        raise DownloadError(f"No version number found in title: {title}")

    # Get canonical URL from meta tags, fallback to source_url
    try:
        url = extract_url(html)
    except DownloadError:
        url = source_url

    return PatchMetadata(version=version, date=date_str, title=title, url=url)


def extract_article_content(html: str) -> str:
    """Extract main article content from HTML.

    All Blizzard patch notes have a section.blog element containing the content.

    Args:
        html: Full HTML content

    Returns:
        Extracted article HTML (content only, no header)

    Raises:
        DownloadError: If blog section cannot be found
    """
    soup = BeautifulSoup(html, "html.parser")

    # All files have section.blog - verified across all patches
    blog_section = soup.find("section", class_="blog")

    if not blog_section:
        raise DownloadError("No section.blog found in HTML")

    return str(blog_section)


def html_to_markdown(html: str, metadata: PatchMetadata) -> str:
    """Convert HTML to Markdown with frontmatter.

    Args:
        html: HTML content to convert
        metadata: Extracted metadata

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
url: {metadata.url}
processed: {processed_date}
---

# {metadata.title}

"""
    return frontmatter + markdown


def url_to_filename(url: str) -> str:
    """Convert URL to safe filename.

    Args:
        url: URL to convert

    Returns:
        Filename (without extension)
    """
    parsed = urlparse(url)
    # Get last part of path
    path_parts = parsed.path.strip("/").split("/")
    filename = path_parts[-1] if path_parts else "index"

    # Remove common suffixes
    return filename.replace("-patch-notes", "").replace("_patch_notes", "")


def download_patch(
    url: str,
    html_dir: Path,
    markdown_dir: Path,
    skip_existing: bool = True,
    version_hint: str | None = None,
) -> tuple[Path, Path, PatchMetadata]:
    """Download and convert a single patch.

    Args:
        url: Patch URL
        html_dir: Directory to save HTML files
        markdown_dir: Directory to save Markdown files
        skip_existing: Skip if HTML file already exists
        version_hint: Optional version to use if not found in title (e.g., for BU patches)

    Returns:
        Tuple of (html_path, markdown_path, metadata)

    Raises:
        DownloadError: If download or conversion fails
    """
    # Generate filename from URL
    filename = url_to_filename(url)
    html_path = html_dir / f"{filename}.html"

    # Check if already downloaded
    if skip_existing and html_path.exists():
        # Read existing HTML to extract metadata
        html = html_path.read_text(encoding="utf-8")
        metadata = extract_metadata(html, url, version_hint)
        markdown_path = markdown_dir / f"{metadata.version}.md"
        return html_path, markdown_path, metadata

    # Fetch HTML
    html = fetch_html(url)

    # Validate content is patch notes, not homepage
    validate_patch_html(html, url)

    # Extract metadata FROM HTML
    metadata = extract_metadata(html, url, version_hint)

    # Save HTML
    html_dir.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")

    # Extract article content and convert to markdown
    article_html = extract_article_content(html)
    markdown = html_to_markdown(article_html, metadata)

    # Validate markdown content
    if not markdown.strip():
        raise DownloadError(f"Generated empty Markdown for {url}")

    # Save markdown
    markdown_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = markdown_dir / f"{metadata.version}.md"
    markdown_path.write_text(markdown, encoding="utf-8")

    return html_path, markdown_path, metadata
