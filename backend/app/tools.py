"""Agent tools — plain functions decorated with @tool. Strands turns the docstring
+ type hints into the tool schema the model sees.

Research is done LIVE per call (no persistent corpus). OpenAlex is free and needs no
key; Scopus activates only when SCOPUS_API_KEY is set.
"""
from __future__ import annotations

import io

import httpx
from strands import tool

from .config import get_settings


def _ua() -> dict[str, str]:
    s = get_settings()
    return {"User-Agent": f"Mentis/0.1 (mailto:{s.contact_email or 'research@example.org'})"}


def _abstract_from_inverted(idx: dict | None) -> str:
    if not idx:
        return ""
    positions: list[tuple[int, str]] = []
    for word, locs in idx.items():
        for loc in locs:
            positions.append((loc, word))
    positions.sort()
    text = " ".join(w for _, w in positions)
    return text[:600]


@tool
def search_literature(query: str, limit: int = 8) -> str:
    """Search peer-reviewed scientific literature (OpenAlex). Returns a numbered list of
    sources with title, authors, year, venue, DOI and an abstract snippet. Use this to
    gather grounding sources BEFORE writing anything.
    """
    params = {
        "search": query,
        "per-page": min(max(limit, 1), 25),
        "select": "title,publication_year,doi,authorships,primary_location,abstract_inverted_index",
    }
    try:
        r = httpx.get("https://api.openalex.org/works", params=params, headers=_ua(), timeout=25)
        r.raise_for_status()
        results = r.json().get("results", [])
    except Exception as e:  # noqa: BLE001 - surface to the model as text
        return f"literature search failed: {e}"

    if not results:
        return f"No literature found for: {query}"

    lines: list[str] = []
    for i, w in enumerate(results, 1):
        authors = ", ".join(
            a.get("author", {}).get("display_name", "")
            for a in (w.get("authorships") or [])[:4]
        )
        venue = ((w.get("primary_location") or {}).get("source") or {}).get("display_name", "")
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        snippet = _abstract_from_inverted(w.get("abstract_inverted_index"))
        lines.append(
            f"[{i}] {w.get('title', 'Untitled')} — {authors} ({w.get('publication_year', 'n.d.')}). "
            f"{venue}. DOI: {doi or 'n/a'}\n    {snippet}"
        )
    return "\n".join(lines)


@tool
def scopus_search(query: str, limit: int = 8) -> str:
    """Search the university's Scopus subscription for peer-reviewed sources. Only works
    when a Scopus API key is configured; otherwise tells you it is unavailable.
    """
    s = get_settings()
    if not s.scopus_api_key:
        return "Scopus is not configured (no API key). Use search_literature instead."
    headers = {"X-ELS-APIKey": s.scopus_api_key, "Accept": "application/json"}
    params = {"query": query, "count": min(max(limit, 1), 25)}
    try:
        r = httpx.get(
            f"{s.scopus_base_url}/search/scopus", params=params, headers=headers, timeout=25
        )
        r.raise_for_status()
        entries = r.json().get("search-results", {}).get("entry", [])
    except Exception as e:  # noqa: BLE001
        return f"Scopus search failed: {e}"
    if not entries:
        return f"No Scopus results for: {query}"
    lines = []
    for i, e in enumerate(entries, 1):
        lines.append(
            f"[{i}] {e.get('dc:title', 'Untitled')} — {e.get('dc:creator', '')} "
            f"({e.get('prism:coverDate', '')[:4]}). {e.get('prism:publicationName', '')}. "
            f"DOI: {e.get('prism:doi', 'n/a')}"
        )
    return "\n".join(lines)


@tool
def fetch_pdf_text(url: str, max_chars: int = 8000) -> str:
    """Download an open-access PDF by URL and extract its text (truncated). Use to read a
    specific paper when the abstract is not enough.
    """
    try:
        from pypdf import PdfReader

        r = httpx.get(url, headers=_ua(), timeout=40, follow_redirects=True)
        r.raise_for_status()
        reader = PdfReader(io.BytesIO(r.content))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as e:  # noqa: BLE001
        return f"could not fetch/parse PDF: {e}"
    return text[:max_chars] if text.strip() else "PDF had no extractable text."


@tool
def verify_doi(doi: str) -> str:
    """Verify a DOI actually resolves (via OpenAlex). Returns the resolved title/year or a
    NOT-FOUND notice. Use to check citations before relying on them.
    """
    clean = doi.strip().replace("https://doi.org/", "")
    try:
        r = httpx.get(
            f"https://api.openalex.org/works/doi:{clean}", headers=_ua(), timeout=20
        )
        if r.status_code == 404:
            return f"NOT FOUND: {clean} does not resolve — do not cite it."
        r.raise_for_status()
        w = r.json()
    except Exception as e:  # noqa: BLE001
        return f"verification failed for {clean}: {e}"
    return f"OK: {clean} -> {w.get('title', '?')} ({w.get('publication_year', '?')})"
