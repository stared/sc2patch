"""Check if all HTML files have JSON-LD with datePublished."""

import re
from pathlib import Path


def check_file(html_path: Path) -> tuple[bool, str]:
    """Check if file has datePublished in JSON-LD."""
    html = html_path.read_text(encoding="utf-8")

    # Look for datePublished
    match = re.search(r'"datePublished":\s*"([^"]+)"', html)

    if match:
        return (True, match.group(1))
    return (False, "NOT FOUND")


if __name__ == "__main__":
    html_dir = Path("data/raw_html")
    files = sorted(html_dir.glob("*.html"))

    print(f"Checking {len(files)} HTML files...\n")

    missing = []
    for html_path in files:
        has_date, date_value = check_file(html_path)
        status = "✓" if has_date else "✗"
        print(f"{status} {html_path.name}: {date_value}")

        if not has_date:
            missing.append(html_path.name)

    print(f"\n{'=' * 80}")
    if missing:
        print(f"Missing datePublished: {len(missing)} files")
        for name in missing:
            print(f"  - {name}")
    else:
        print("✓ ALL files have datePublished in JSON-LD")
