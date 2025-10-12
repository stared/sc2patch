"""Inspect patches with unknown patterns to understand their structure."""

from pathlib import Path

from bs4 import BeautifulSoup


def inspect_patch(html_path: Path, version: str) -> None:
    """Inspect a single patch HTML structure."""
    print(f"\n{'=' * 60}")
    print(f"Version: {version}")
    print(f"File: {html_path.name}")
    print("=" * 60)

    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    blog = soup.find("section", class_="blog")
    if not blog:
        print("ERROR: No blog section found")
        return

    print("\nStructure (first 20 elements):")
    for i, elem in enumerate(blog.children):
        if not elem.name:
            continue
        if i >= 20:
            break

        text = elem.get_text(strip=True)[:80]

        # Show more details for key elements
        if elem.name in ["h2", "h3", "h4"]:
            print(f"\n{elem.name.upper()}: {text}")
        elif elem.name == "ul":
            li_count = len(elem.find_all("li", recursive=False))
            print(f"  ul ({li_count} items)")
            # Show first few items
            for j, li in enumerate(elem.find_all("li", recursive=False)[:3]):
                li_text = li.get_text(strip=True)[:60]
                strong = li.find("strong")
                if strong:
                    print(f"    - [strong] {li_text}")
                else:
                    print(f"    - {li_text}")
            if li_count > 3:
                print(f"    ... ({li_count - 3} more)")
        elif elem.name == "p":
            if text:
                print(f"  p: {text}")


def main():
    html_dir = Path("data/raw_html")

    # Unknown patterns from categorize_patches.py
    unknown_versions = ["3.14.0", "4.2.2", "4.3.2", "4.5.0"]

    for version in unknown_versions:
        html_candidates = list(html_dir.glob(f"*{version.replace('.', '-')}*.html"))

        if not html_candidates:
            print(f"\nWARNING: No HTML found for {version}")
            continue

        inspect_patch(html_candidates[0], version)


if __name__ == "__main__":
    main()
