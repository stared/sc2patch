"""Generate parsing status as a markdown checklist."""

import json
from pathlib import Path


def analyze_patch(patch_path: Path) -> dict:
    """Analyze a single processed patch for issues."""
    with patch_path.open() as f:
        data = json.load(f)

    metadata = data["metadata"]
    changes = data["changes"]

    issues = []
    notes = []

    # Count unknowns
    unknown_entities = [c for c in changes if "-unknown" in c["entity_id"]]
    if unknown_entities:
        issues.append(f"{len(unknown_entities)} unknown entities")
        # Show first few examples
        examples = unknown_entities[:3]
        for ex in examples:
            notes.append(f"  - `{ex['entity_id']}`: {ex['raw_text'][:60]}...")

    # Count neutral/non-balance
    neutral_entities = [c for c in changes if c["entity_id"].startswith("neutral-")]
    if neutral_entities:
        issues.append(f"{len(neutral_entities)} non-balance entries (co-op/UI/bugs)")
        # Show entity types
        entity_types = set(c["entity_id"].split("-", 1)[1] for c in neutral_entities[:5])
        for etype in sorted(entity_types)[:3]:
            notes.append(f"  - Type: `neutral-{etype}`")

    # Check for concatenated text
    for c in changes:
        text = c["raw_text"]
        if len(text) > 100 and text.count(" ") / len(text) < 0.1:
            issues.append("Text concatenation detected")
            notes.append(f"  - Example: `{text[:80]}...`")
            break

    # Check for very short changes
    very_short = [c for c in changes if len(c["raw_text"]) < 20]
    if len(very_short) > 2:
        issues.append(f"{len(very_short)} suspiciously short entries")

    status = "✓" if not issues else "⚠️"

    return {
        "version": metadata["version"],
        "date": metadata["date"],
        "url": metadata["url"],
        "change_count": len(changes),
        "issues": issues,
        "notes": notes,
        "status": status,
    }


def main():
    patches_dir = Path("data/processed/patches")
    results = []

    for patch_path in sorted(patches_dir.glob("*.json")):
        result = analyze_patch(patch_path)
        results.append(result)

    # Generate markdown checklist
    md_lines = [
        "# Parsing Status Checklist",
        "",
        f"**Total patches:** {len(results)}",
        "",
    ]

    # Summary
    ok = [r for r in results if r["status"] == "✓"]
    issues = [r for r in results if r["status"] == "⚠️"]

    md_lines.extend([
        "## Summary",
        "",
        f"- ✅ Complete: {len(ok)} patches",
        f"- ⚠️ Needs work: {len(issues)} patches",
        "",
        "---",
        "",
        "## Patches",
        "",
    ])

    # Group by status
    for r in results:
        checkbox = "x" if r["status"] == "✓" else " "

        # Header
        md_lines.append(f"- [{checkbox}] **{r['version']}** ({r['date']}) - {r['change_count']} changes")

        # URL
        md_lines.append(f"  - URL: {r['url']}")

        # Issues
        if r["issues"]:
            md_lines.append(f"  - **Issues:**")
            for issue in r["issues"]:
                md_lines.append(f"    - {issue}")

        # Notes
        if r["notes"]:
            md_lines.append(f"  - **Details:**")
            md_lines.extend(r["notes"])

        md_lines.append("")  # Blank line

    # Save report
    report_path = Path("parsing_status.md")
    report_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"Generated {report_path}")
    print(f"\n✅ {len(ok)} complete")
    print(f"⚠️ {len(issues)} need work")


if __name__ == "__main__":
    main()
