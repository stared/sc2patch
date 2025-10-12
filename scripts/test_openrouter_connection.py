"""Test OpenRouter API connection with a simple request."""

import os
import httpx
from dotenv import load_dotenv
from rich.console import Console

console = Console()

# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MODEL = "openai/gpt-5"

if not OPENROUTER_API_KEY:
    console.print("[red]Error: OPENROUTER_API_KEY not found in .env[/red]")
    exit(1)

console.print(f"[cyan]Testing OpenRouter connection with model: {MODEL}[/cyan]\n")
console.print(f"API Key (first 10 chars): {OPENROUTER_API_KEY[:10]}...")

try:
    # Simple test request
    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/pmigdal/sc2patches",
            "X-Title": "SC2 Patch Parser Test"
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "Say 'Connection successful!' in exactly 3 words."}
            ],
            "temperature": 0.1,
            "max_tokens": 50
        },
        timeout=30
    )

    console.print(f"[yellow]Response status: {response.status_code}[/yellow]")

    if response.status_code == 200:
        result = response.json()
        console.print("[green]✓ API Connection successful![/green]")
        console.print(f"Response: {result['choices'][0]['message']['content']}")
    else:
        console.print(f"[red]✗ API Error: {response.status_code}[/red]")
        console.print(f"Response: {response.text}")

except httpx.TimeoutException:
    console.print("[red]✗ Request timed out (30 seconds)[/red]")
except Exception as e:
    console.print(f"[red]✗ Error: {e}[/red]")
    console.print(f"Type: {type(e).__name__}")