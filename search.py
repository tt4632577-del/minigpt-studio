"""Live web search so the assistant can answer current or factual questions.

Uses Tavily if TAVILY_API_KEY is set (better quality, free tier), otherwise DuckDuckGo
through the `ddgs` package (no key needed). The whole search is capped at SEARCH_TIMEOUT
seconds so a slow service can never freeze the app.
"""
import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

import requests

SEARCH_TIMEOUT = float(os.getenv("SEARCH_TIMEOUT", "12"))
_pool = ThreadPoolExecutor(max_workers=2)

# Words that usually mean the answer must come from current, real-world information.
SEARCH_HINTS = re.compile(
    r"\b(who is|who are|who was|current|currently|latest|recent|today|tonight|now|news|"
    r"price|cost|fee|fees|salary|weather|score|result|results|schedule|deadline|"
    r"dean|principal|chancellor|vice chancellor|registrar|director|head of|hod|"
    r"ceo|founder|president|minister|"
    r"address|phone|contact|email|website|location|where is|when is|when does|"
    r"admission|admissions|eligibility|campus|university|college|school of|department|"
    r"released|launched|update|2025|2026|2027|search|look up|find out)\b",
    re.IGNORECASE,
)


def should_search(text: str) -> bool:
    """Cheap rule to decide if a message needs live information."""
    t = text.strip()
    if len(t) < 8:
        return False
    return bool(SEARCH_HINTS.search(t))


def _tavily(query: str, n: int) -> list[dict]:
    resp = requests.post(
        "https://api.tavily.com/search",
        headers={"Authorization": f"Bearer {os.environ['TAVILY_API_KEY']}"},
        json={"query": query, "max_results": n, "search_depth": "basic"},
        timeout=8,
    )
    resp.raise_for_status()
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
        for r in resp.json().get("results", [])
    ]


def _duckduckgo(query: str, n: int) -> list[dict]:
    from ddgs import DDGS

    rows = DDGS(timeout=8).text(query, max_results=n)
    return [
        {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
        for r in rows
    ]


def _search(query: str, n: int) -> list[dict]:
    if os.getenv("TAVILY_API_KEY"):
        try:
            return _tavily(query, n)[:n]
        except Exception:
            pass  # fall back to DuckDuckGo
    return _duckduckgo(query, n)[:n]


def web_search(query: str, n: int = 5) -> list[dict]:
    """Return up to n results as dicts with title, url and snippet. Raises TimeoutError if too slow."""
    query = query.strip()
    if not query:
        return []
    future = _pool.submit(_search, query, n)
    try:
        return future.result(timeout=SEARCH_TIMEOUT)
    except FutureTimeout:
        raise TimeoutError(f"web search took longer than {SEARCH_TIMEOUT:.0f}s")