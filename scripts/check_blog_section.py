"""Check if all HTML files have section.blog element."""

from pathlib import Path

from bs4 import BeautifulSoup


def check_file(html_path: Path) -> tuple[bool, str]:
    """Check if file has section.blog."""
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    blog_section = soup.find("section", class_="blog")
    if blog_section:
        return (True, "section.blog found")

    article = soup.find("article")
    if article:
        return (False, "article found but no section.blog")

    return (False, "NO article or section.blog")


if __name__ == "__main__":
    html_dir = Path("data/raw_html")
    files = sorted(html_dir.glob("*.html"))

    print(f"Checking {len(files)} HTML files...\n")

    missing = []
    for html_path in files:
        has_blog, msg = check_file(html_path)
        status = "✓" if has_blog else "✗"
        print(f"{status} {html_path.name}: {msg}")

        if not has_blog:
            missing.append(html_path.name)

    print(f"\n{'='*80}")
    if missing:
        print(f"Missing section.blog: {len(missing)} files")
        for name in missing:
            print(f"  - {name}")
    else:
        print("✓ ALL files have section.blog")
