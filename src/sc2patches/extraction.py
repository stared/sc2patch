"""HTML extraction utilities.

Single source of truth for:
- URL to filename conversion
- JSON-LD metadata extraction
- HTML body extraction
"""

from urllib.parse import urlparse


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
