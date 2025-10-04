"""Inspect 5.0.13 HTML structure to understand entity detection issue."""

from pathlib import Path

from bs4 import BeautifulSoup


def main():
    html_path = Path("data/raw_html/starcraft-ii-5-0-13.html")
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    blog = soup.find("section", class_="blog")
    if not blog:
        print("ERROR: No blog section")
        return

    print("5.0.13 HTML Structure:\n" + "=" * 60)

    for i, elem in enumerate(blog.children):
        if not elem.name:
            continue

        if i > 50:
            break

        text = elem.get_text(strip=True)

        if elem.name == "h2":
            print(f"\nH2: {text}")
        elif elem.name == "h3":
            print(f"  H3: {text}")
        elif elem.name == "h4":
            print(f"    H4: {text}")
        elif elem.name == "ul":
            li_count = len(elem.find_all("li", recursive=False))
            print(f"    UL ({li_count} items):")
            for j, li in enumerate(elem.find_all("li", recursive=False)[:3]):
                li_text = li.get_text(strip=True)[:80]
                print(f"      - {li_text}")
            if li_count > 3:
                print(f"      ... ({li_count - 3} more)")


if __name__ == "__main__":
    main()
