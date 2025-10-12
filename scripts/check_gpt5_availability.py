"""Check if GPT-5 is available on OpenRouter."""

import os
import httpx
from dotenv import load_dotenv
from rich.console import Console

console = Console()
load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    console.print("[red]Error: OPENROUTER_API_KEY not found[/red]")
    exit(1)

# Test with GPT-5
console.print("[cyan]Testing GPT-5 availability on OpenRouter...[/cyan]\n")

try:
    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openai/gpt-5",
            "messages": [{"role": "user", "content": "Say hello"}],
            "max_tokens": 50
        },
        timeout=15
    )

    console.print(f"Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        console.print("[green]✓ GPT-5 is available![/green]")
        console.print(f"Response: {result.get('choices', [{}])[0].get('message', {}).get('content', 'No content')}")
    else:
        console.print(f"[yellow]GPT-5 request failed with status {response.status_code}[/yellow]")
        console.print(f"Error: {response.text[:500]}")

        # Try with GPT-4 instead
        console.print("\n[cyan]Testing with GPT-4 Turbo instead...[/cyan]")
        response2 = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-4-turbo",
                "messages": [{"role": "user", "content": "Say hello"}],
                "max_tokens": 50
            },
            timeout=15
        )

        if response2.status_code == 200:
            console.print("[green]✓ GPT-4 Turbo works![/green]")
            console.print("GPT-5 may not be available yet. Consider using GPT-4 Turbo instead.")

except httpx.TimeoutException:
    console.print("[red]✗ Request timed out[/red]")
    console.print("GPT-5 might be taking too long or not available")
except Exception as e:
    console.print(f"[red]✗ Error: {e}[/red]")