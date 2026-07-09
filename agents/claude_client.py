"""
Shared Claude API wrapper used by every agent in the pipeline.
Keeps model choice and error handling in one place.
"""
import anthropic
from config import ANTHROPIC_API_KEY

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

MODEL = "claude-sonnet-4-6"


def ask_claude(prompt: str, system: str | None = None, max_tokens: int = 600) -> str:
    """Send a prompt to Claude and return plain text. Falls back to a stub
    message if no API key is configured, so the pipeline still runs."""
    if _client is None:
        return ("[Claude API key not set — set ANTHROPIC_API_KEY to enable live "
                "agent reasoning. Placeholder summary returned instead.]")
    try:
        kwargs = {"model": MODEL, "max_tokens": max_tokens,
                  "messages": [{"role": "user", "content": prompt}]}
        if system:
            kwargs["system"] = system
        response = _client.messages.create(**kwargs)
        return "".join(block.text for block in response.content if block.type == "text")
    except Exception as e:
        return f"[Claude API call failed: {e}]"


def ask_claude_with_web_search(prompt: str, max_tokens: int = 600) -> str:
    """Same as ask_claude but enables the web_search tool for live context."""
    if _client is None:
        return ("[Claude API key not set — set ANTHROPIC_API_KEY to enable live "
                "web-search-enriched reasoning.]")
    try:
        response = _client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")
    except Exception as e:
        return f"[Claude API + web search call failed: {e}]"
