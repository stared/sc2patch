"""Debug script to visualize the normalized tree structure."""

import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sc2patches.normalize import normalize_html_to_tree


def print_tree(items, indent=0):
    """Print tree structure with indentation."""
    for item in items:
        prefix = "  " * indent
        print(f"{prefix}[{item.type}] {item.text[:80]}")
        if item.children:
            print_tree(item.children, indent + 1)


def main():
    """Debug tree structure for a specific patch."""
    if len(sys.argv) < 2:
        print("Usage: python debug_tree.py <version>")
        print("Example: python debug_tree.py 5.0.14")
        sys.exit(1)

    version = sys.argv[1]
    html_dir = Path("data/raw_html")

    # Find HTML file
    html_files = list(html_dir.glob(f"*{version.replace('.', '-')}*.html"))
    if not html_files:
        print(f"No HTML file found for version {version}")
        sys.exit(1)

    html_path = html_files[0]
    print(f"Reading: {html_path}\n")

    # Parse HTML
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # Normalize to tree
    tree = normalize_html_to_tree(soup)

    # Print tree
    print("Normalized Tree Structure:")
    print("=" * 80)
    print_tree(tree)

    # Optionally output JSON
    if "--json" in sys.argv:
        tree_dict = [item.to_dict() for item in tree]
        print("\n\nJSON Output:")
        print(json.dumps(tree_dict, indent=2))


if __name__ == "__main__":
    main()
