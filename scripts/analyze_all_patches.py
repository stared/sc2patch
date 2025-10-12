"""Analyze all processed patches and identify issues."""

import json
from pathlib import Path


def analyze_patch(patch_path: Path) -> dict:
    """Analyze a single processed patch for issues."""
    with patch_path.open() as f:
        data = json.load(f)

    metadata = data["metadata"]
    changes = data["changes"]

    issues = []

    # Check for unknown entities
    unknown_count = sum(1 for c in changes if "-unknown" in c["entity_id"])
    if unknown_count > 0:
        issues.append(f"{unknown_count} unknown entities")

    # Check for neutral race (likely wrong)
    neutral_count = sum(1 for c in changes if c["entity_id"].startswith("neutral-"))
    if neutral_count > 0:
        issues.append(f"{neutral_count} neutral entities (likely non-balance)")

    # Check for concatenated text (no spaces in long text)
    for c in changes:
        text = c["raw_text"]
        # Check for patterns like "CycloneMag" or "TerranMarine"
        if len(text) > 100 and text.count(" ") / len(text) < 0.1:
            issues.append("Possible text concatenation")
            break

    # Check for very short changes (likely incomplete)
    very_short = [c for c in changes if len(c["raw_text"]) < 20]
    if len(very_short) > 0:
        issues.append(f"{len(very_short)} very short changes")

    return {
        "version": metadata["version"],
        "date": metadata["date"],
        "url": metadata["url"],
        "change_count": len(changes),
        "unknown_count": unknown_count,
        "neutral_count": neutral_count,
        "issues": issues,
        "status": "⚠️ Issues" if issues else "✓ OK",
    }


def main():
    patches_dir = Path("data/processed/patches")
    results = []

    for patch_path in sorted(patches_dir.glob("*.json")):
        result = analyze_patch(patch_path)
        results.append(result)

    # Generate markdown report
    md_lines = [
        "# Parsing Status Report",
        "",
        f"Total patches: {len(results)}",
        "",
        "## Summary",
        "",
    ]

    ok_count = sum(1 for r in results if r["status"] == "✓ OK")
    issue_count = len(results) - ok_count

    md_lines.extend(
        [
            f"- ✓ OK: {ok_count} patches",
            f"- ⚠️ Issues: {issue_count} patches",
            "",
            "## Detailed Status",
            "",
            "| Version | Changes | Status | Issues |",
            "|---------|---------|--------|--------|",
        ]
    )

    for r in results:
        issues_str = ", ".join(r["issues"]) if r["issues"] else "-"
        md_lines.append(f"| {r['version']} | {r['change_count']} | {r['status']} | {issues_str} |")

    md_lines.extend(
        [
            "",
            "## Patches by Issue Type",
            "",
        ]
    )

    # Group by issue type
    unknown_patches = [r for r in results if r["unknown_count"] > 0]
    if unknown_patches:
        md_lines.extend(
            [
                f"### Unknown Entities ({len(unknown_patches)} patches)",
                "",
            ]
        )
        for r in unknown_patches:
            md_lines.append(f"- **{r['version']}**: {r['unknown_count']} unknown entities")
        md_lines.append("")

    neutral_patches = [r for r in results if r["neutral_count"] > 0]
    if neutral_patches:
        md_lines.extend(
            [
                f"### Neutral/Non-Balance ({len(neutral_patches)} patches)",
                "",
            ]
        )
        for r in neutral_patches:
            md_lines.append(f"- **{r['version']}**: {r['neutral_count']} neutral entities")
        md_lines.append("")

    # Save report
    report_path = Path("parsing_status.md")
    report_path.write_text("\n".join(md_lines), encoding="utf-8")

    print("\n".join(md_lines))
    print(f"\n\nReport saved to {report_path}")


if __name__ == "__main__":
    main()
