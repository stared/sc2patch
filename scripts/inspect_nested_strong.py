"""Inspect nested_strong pattern patches to understand structure."""

from pathlib import Path

from bs4 import BeautifulSoup


def inspect_patch(html_path: Path, version: str) -> None:
    """Inspect a single patch HTML structure."""
    print(f"\n{'=' * 60}")
    print(f"Version: {version}")
    print("=" * 60)

    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    blog = soup.find("section", class_="blog")
    if not blog:
        print("ERROR: No blog section found")
        return

    print("\nStructure:")
    for i, elem in enumerate(blog.children):
        if not elem.name:
            continue
        if i >= 25:
            break

        text = elem.get_text(strip=True)[:80]

        if elem.name in ["h2", "h3"]:
            print(f"\n{elem.name.upper()}: {text}")
        elif elem.name == "ul":
            # Check if this is a top-level list with nested structure
            li_count = len(elem.find_all("li", recursive=False))
            print(f"  UL ({li_count} items)")

            for j, li in enumerate(elem.find_all("li", recursive=False)[:3]):
                # Check for strong tags
                strong = li.find("strong")
                nested_ul = li.find("ul")

                if strong and nested_ul:
                    strong_text = strong.get_text(strip=True)
                    nested_li_count = len(nested_ul.find_all("li", recursive=False))
                    print(f"    LI: [strong] {strong_text}")
                    print(f"      → UL ({nested_li_count} nested changes)")
                    for k, nested_li in enumerate(nested_ul.find_all("li", recursive=False)[:2]):
                        nested_text = nested_li.get_text(strip=True)[:60]
                        print(f"        - {nested_text}")
                elif strong:
                    print(f"    LI: [strong] {strong.get_text(strip=True)[:60]}")
                else:
                    print(f"    LI: {text[:60]}")


def main():
    html_dir = Path("data/raw_html")

    # Sample from nested_strong patches
    versions = ["4.11.0", "4.7.1", "3.13.0"]

    for version in versions:
        html_candidates = list(html_dir.glob(f"*{version.replace('.', '-')}*.html"))

        if not html_candidates:
            print(f"\nWARNING: No HTML found for {version}")
            continue

        inspect_patch(html_candidates[0], version)


if __name__ == "__main__":
    main()
