"""Shared polite HTTP client for bibliographic sources."""
from __future__ import annotations

import httpx

USER_AGENT = "Mentis-Research-Assistant/0.2 (mailto:research@example.org)"


def client(timeout: float = 30.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    )
