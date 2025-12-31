#!/usr/bin/env python3
"""Compare different LLM models on parsing a patch.

Usage:
    uv run python sc2patches/tools/compare_models.py 5-0-13
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from sc2patches.core.llm_config import ALLOWED_MODELS, get_openrouter_api_key
from sc2patches.core.parse import extract_body_from_html, parse_with_llm

load_dotenv()

# Output directory
OUTPUT_DIR = Path("data/model_comparison")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run python sc2patches/tools/compare_models.py <patch-filename>")
        sys.exit(1)

    patch_pattern = sys.argv[1]
    html_dir = Path("data/raw_html")

    # Find matching HTML file
    html_files = list(html_dir.glob(f"*{patch_pattern}*.html"))
    if not html_files:
        print(f"No HTML files found matching: {patch_pattern}")
        sys.exit(1)

    html_path = html_files[0]
    print(f"Parsing: {html_path.name}")

    # Extract body text once
    body_text = extract_body_from_html(html_path)
    version_hint = html_path.stem
    api_key = get_openrouter_api_key()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = {}

    for model in ALLOWED_MODELS:
        print(f"\n{'=' * 60}")
        print(f"Model: {model}")
        print("=" * 60)

        try:
            patch_data = parse_with_llm(body_text, version_hint, api_key, model=model)

            # Save result
            output_file = OUTPUT_DIR / f"{version_hint}_{model.replace('/', '_')}.json"
            result = {
                "model": model,
                "version": patch_data.version,
                "date": patch_data.date,
                "entity_count": len(patch_data.changes),
                "change_count": sum(len(e.changes) for e in patch_data.changes),
                "changes": [
                    {
                        "entity_id": e.entity_id,
                        "entity_name": e.entity_name,
                        "race": e.race,
                        "changes": [{"text": c.text, "change_type": c.change_type} for c in e.changes],
                    }
                    for e in patch_data.changes
                ],
            }
            results[model] = result

            with output_file.open("w") as f:
                json.dump(result, f, indent=2)

            print(f"  Entities: {result['entity_count']}")
            print(f"  Changes: {result['change_count']}")
            print(f"  Saved: {output_file.name}")

        except Exception as e:
            print(f"  ERROR: {e}")
            results[model] = {"model": model, "error": str(e)}

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print("=" * 60)
    for model, result in results.items():
        if "error" in result:
            print(f"{model}: ERROR - {result['error'][:50]}")
        else:
            print(f"{model}: {result['entity_count']} entities, {result['change_count']} changes")

    # Save summary
    summary_file = OUTPUT_DIR / f"{version_hint}_summary.json"
    with summary_file.open("w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSummary saved to: {summary_file}")


if __name__ == "__main__":
    main()
