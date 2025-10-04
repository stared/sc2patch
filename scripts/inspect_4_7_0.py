"""Inspect 4.7.0 to understand why it failed parsing."""

from pathlib import Path

from bs4 import BeautifulSoup


def main():
    html_path = Path("data/raw_html/starcraft-ii-4-7-0.html")

    if not html_path.exists():
        print("ERROR: File not found")
        return

    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    blog = soup.find("section", class_="blog")
    if not blog:
        print("ERROR: No blog section found")
        return

    print("4.7.0 HTML Structure:\n" + "=" * 60)

    # Check for race-related elements
    h2_headers = blog.find_all("h2")
    h3_headers = blog.find_all("h3")
    print(f"\nH2 headers ({len(h2_headers)}):")
    for h2 in h2_headers[:10]:
        print(f"  - {h2.get_text(strip=True)}")

    print(f"\nH3 headers ({len(h3_headers)}):")
    for h3 in h3_headers[:10]:
        print(f"  - {h3.get_text(strip=True)}")

    # Check for nested structure
    print("\nFirst 20 elements:")
    for i, elem in enumerate(blog.children):
        if not elem.name:
            continue
        if i >= 20:
            break

        text = elem.get_text(strip=True)[:80]

        if elem.name in ["h2", "h3"]:
            print(f"\n{elem.name.upper()}: {text}")
        elif elem.name == "ul":
            li_count = len(elem.find_all("li", recursive=False))
            print(f"  UL ({li_count} items)")

            for j, li in enumerate(elem.find_all("li", recursive=False)[:2]):
                strong = li.find("strong")
                nested_ul = li.find("ul")

                if strong and nested_ul:
                    print(f"    LI: [strong] {strong.get_text(strip=True)[:60]}")
                    print(f"      → nested UL")
                elif strong:
                    print(f"    LI: [strong] {strong.get_text(strip=True)[:60]}")
                else:
                    print(f"    LI: {li.get_text(strip=True)[:60]}")


if __name__ == "__main__":
    main()
