# SC2Patches Project Guidelines

## Code Quality

- **Python 3.12** required
- **Type hints** mandatory for all functions (checked with `ty`)
- **Formatting** with `ruff` (line length: 100)
- **Strict Pydantic models** - validate all data

## Error Handling Philosophy

- **Fail fast, fail loud** - NEVER pass errors silently
- Raise exceptions immediately on validation failures
- Use custom exceptions (e.g., `ValidationError`, `DownloadError`)
- Provide clear error messages with context
- Exit with code 1 on failures

## NO DEFENSIVE PROGRAMMING

- **CRITICAL RULE**: Do NOT add fallbacks or "if this fails, try that" patterns
- Pick ONE extraction method based on actual data inspection
- If it fails, analyze WHY and fix THAT specific issue
- ONLY add conditionals if you've VERIFIED different files have different formats
- Check actual files, don't guess or assume
- Avoid multiple fallback patterns - they hide real problems

## Module Design

- **Modular functions** - each function does one thing
- **Explicit validation** after each pipeline stage
- **Progress visibility** - use Rich for progress bars and logging
- **Type safety** - use Pydantic models for all data structures

## Data Pipeline Stages

1. **Discover** (`discover.py`) - Build patch URL index
2. **Download** (`download.py`) - Fetch and convert to Markdown
3. **Validate** (`validate.py`) - Check downloads are complete
4. **Extract** (`extract.py`) - Parse to structured data (future)

Each stage must validate its inputs and outputs.

## Testing

Before committing:
```bash
uv run ruff format .
uv run ruff check .
uv run ty check src/
```

## Project Structure

```
sc2patches/
├── src/sc2patches/    # Source code
├── raw_patches/       # Downloaded Markdown files
├── data/              # Structured data and indices
└── pyproject.toml     # Dependencies and config
```

## Conventions

- Use `Path` objects, not strings for file paths
- Use `httpx` for HTTP requests
- Rich console for all user-facing output
- JSONL for structured data output
- Frontmatter in Markdown files for metadata
