"""Check if all HTML files have og:url meta tag."""

import re
from pathlib import Path

from bs4 import BeautifulSoup


def check_file(html_path: Path) -> tuple[bool, str]:
    """Check if file has og:url."""
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    og_url = soup.find("meta", property="og:url")
    if og_url and og_url.get("content"):
        return (True, og_url["content"])

    return (False, "NOT FOUND")


if __name__ == "__main__":
    html_dir = Path("raw_html")
    files = sorted(html_dir.glob("*.html"))

    print(f"Checking {len(files)} HTML files...\n")

    missing = []
    for html_path in files:
        has_url, url_value = check_file(html_path)
        status = "✓" if has_url else "✗"
        print(f"{status} {html_path.name}: {url_value}")

        if not has_url:
            missing.append(html_path.name)

    print(f"\n{'='*80}")
    if missing:
        print(f"Missing og:url: {len(missing)} files")
    else:
        print("✓ ALL files have og:url meta tag")
