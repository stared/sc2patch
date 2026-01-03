"""HTML extraction utilities.

Single source of truth for:
- URL to filename conversion
- JSON-LD metadata extraction
- HTML body extraction
"""

import json
import re
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup


class ExtractionError(Exception):
    """Raised when extraction fails."""


def url_to_filename(url: str, remove_suffixes: bool = True) -> str:
    """Convert URL to safe filename (without extension).

    Args:
        url: URL to convert
        remove_suffixes: If True, removes common patch note suffixes

    Returns:
        Filename derived from URL path
    """
    parsed = urlparse(url)
    path_parts = parsed.path.strip("/").split("/")
    filename = path_parts[-1] if path_parts else "index"

    if remove_suffixes:
        filename = filename.replace("-patch-notes", "").replace("_patch_notes", "")

    return filename


def extract_jsonld(html: str) -> dict:
    """Extract JSON-LD NewsArticle data from HTML.

    Args:
        html: HTML content

    Returns:
        Parsed JSON-LD dict

    Raises:
        ExtractionError: If JSON-LD not found or invalid
    """
    soup = BeautifulSoup(html, "html.parser")

    script = soup.find("script", type="application/ld+json")
    if not script or not script.string:
        raise ExtractionError("No JSON-LD script found")

    # Fix common JSON syntax error in Blizzard's JSON-LD
    # Missing comma between author and publisher arrays
    json_str = script.string
    json_str = re.sub(r'(\])\s*("publisher")', r"\1,\2", json_str)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ExtractionError(f"Failed to parse JSON-LD: {e}") from e

    if not isinstance(data, dict) or data.get("@type") != "NewsArticle":
        raise ExtractionError("JSON-LD is not a NewsArticle")

    return data


def extract_date_from_jsonld(html: str) -> str | None:
    """Extract publication date from JSON-LD metadata.

    Args:
        html: HTML content

    Returns:
        Date string in YYYY-MM-DD format, or None if not found
    """
    try:
        data = extract_jsonld(html)
    except ExtractionError:
        return None

    date_published = data.get("datePublished")
    if not date_published:
        return None

    try:
        dt = datetime.fromisoformat(date_published.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return None


def extract_body_html(html: str) -> str:
    """Extract article body HTML from patch notes page.

    Supports:
    - Blizzard News: section.blog
    - Liquipedia: div.mw-parser-output (cleaned of navigation elements)

    Args:
        html: Full HTML content

    Returns:
        Article body as HTML string

    Raises:
        ExtractionError: If no supported content container found
    """
    soup = BeautifulSoup(html, "html.parser")

    # Try Blizzard News format first
    blog_section = soup.find("section", class_="blog")
    if blog_section:
        return str(blog_section)

    # Try Liquipedia format
    wiki_content = soup.find("div", class_="mw-parser-output")
    if wiki_content:
        # Clean Liquipedia content - remove non-content elements
        for element in wiki_content.find_all(["script", "style", "nav"]):
            element.decompose()
        for element in wiki_content.find_all(class_=["mw-editsection", "navbox", "toc", "noprint"]):
            element.decompose()
        for element in wiki_content.find_all("table", class_="infobox"):
            element.decompose()
        return str(wiki_content)

    raise ExtractionError("No section.blog or div.mw-parser-output found in HTML")
