"""Test GPT-5 with a simple balance change extraction."""

import os
import json
import httpx
from dotenv import load_dotenv
from rich.console import Console

console = Console()
load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    console.print("[red]Error: OPENROUTER_API_KEY not found[/red]")
    exit(1)

# Simple test content
test_content = """
# StarCraft II Patch 3.8.0

## Balance Changes

### Terran
- Siege Tank: Health increased from 160 to 175
- Viking: Assault mode now deals +8 bonus damage to mechanical

### Zerg
- Hydralisk: Attack range increased by 2
- Ultralisk: Base armor increased from 1 to 2
"""

console.print("[cyan]Testing GPT-5 with simple patch content...[/cyan]\n")

try:
    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openai/gpt-5",
            "messages": [
                {
                    "role": "user",
                    "content": f"""Extract balance changes from this patch. Return JSON:
{test_content}

Format:
{{"changes": [{{"unit": "name", "change": "description"}}]}}"""
                }
            ],
            "max_tokens": 500,
            "temperature": 0.1
        },
        timeout=30
    )

    console.print(f"Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')

        console.print(f"[yellow]Raw response:[/yellow] '{content}'")
        console.print(f"[yellow]Response length:[/yellow] {len(content)} chars")

        if content:
            try:
                parsed = json.loads(content)
                console.print("[green]✓ Successfully parsed JSON response![/green]")
                console.print(json.dumps(parsed, indent=2))
            except json.JSONDecodeError:
                console.print(f"[yellow]Response is not JSON:[/yellow] {content[:200]}")
        else:
            console.print("[red]✗ GPT-5 returned empty response[/red]")
    else:
        console.print(f"[red]Error {response.status_code}: {response.text[:500]}[/red]")

except Exception as e:
    console.print(f"[red]Error: {e}[/red]")