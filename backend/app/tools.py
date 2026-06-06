"""Agent tools — plain functions decorated with @tool. Strands turns the docstring
+ type hints into the tool schema the model sees.

Research is done LIVE per call (no persistent corpus). OpenAlex is free and needs no
key; Scopus activates only when SCOPUS_API_KEY is set. Each result is recorded in the
per-run source collector (app.sources) so references can be built deterministically
and DOI-verified afterwards — the numbers the model sees are stable global indices.
"""
from __future__ import annotations

import io
import re

import httpx
from strands import tool

from .config import get_settings
from .sources import Source, current


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
    return " ".join(w for _, w in positions)[:600]


@tool
def search_literature(query: str, limit: int = 8) -> str:
    """Search peer-reviewed scientific literature (OpenAlex). Returns a numbered list of
    sources with title, authors, year, venue, DOI and an abstract snippet. The numbers are
    stable citation indices — cite them as [n] and they will resolve to real references.
    Use this to gather grounding sources BEFORE writing anything.
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
    except Exception as e:  # noqa: BLE001
        return f"literature search failed: {e}"

    if not results:
        return f"No literature found for: {query}"

    coll = current()
    lines: list[str] = []
    for w in results:
        authors = ", ".join(
            a.get("author", {}).get("display_name", "")
            for a in (w.get("authorships") or [])[:4]
        )
        venue = ((w.get("primary_location") or {}).get("source") or {}).get("display_name", "")
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        year = str(w.get("publication_year") or "n.d.")
        title = w.get("title", "Untitled")
        snippet = _abstract_from_inverted(w.get("abstract_inverted_index"))
        idx = coll.add(
            Source(title=title, authors=authors, year=year, venue=venue, doi=doi, abstract=snippet)
        )
        lines.append(
            f"[{idx}] {title} — {authors} ({year}). {venue}. DOI: {doi or 'n/a'}\n    {snippet}"
        )
    return "\n".join(lines)


@tool
def scopus_search(query: str, limit: int = 8) -> str:
    """Search the university's Scopus subscription for peer-reviewed sources. Only works
    when a Scopus API key is configured; otherwise tells you it is unavailable. Returns
    numbered sources whose [n] indices resolve to real references.
    """
    s = get_settings()
    if not s.scopus_api_key:
        return "Scopus is not configured (no API key). Use search_literature instead."
    headers = {"X-ELS-APIKey": s.scopus_api_key, "Accept": "application/json"}
    if s.scopus_insttoken:  # institutional token → full access off-campus
        headers["X-ELS-Insttoken"] = s.scopus_insttoken
    # Wrap bare keyword queries in Scopus field syntax for precision (title/abstract/keywords).
    q = query.strip()
    if not re.search(r"\b(TITLE-ABS-KEY|TITLE|ABS|KEY|AUTH|AFFIL|DOI|PUBYEAR|SRCTITLE)\b", q, re.I):
        q = f"TITLE-ABS-KEY({q})"
    params = {"query": q, "count": min(max(limit, 1), 25)}
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

    coll = current()
    lines = []
    for e in entries:
        title = e.get("dc:title", "Untitled")
        authors = e.get("dc:creator", "")
        year = (e.get("prism:coverDate", "") or "")[:4] or "n.d."
        venue = e.get("prism:publicationName", "")
        doi = e.get("prism:doi", "") or ""
        abstract = e.get("dc:description", "") or ""
        idx = coll.add(
            Source(title=title, authors=authors, year=year, venue=venue, doi=doi, abstract=abstract)
        )
        lines.append(f"[{idx}] {title} — {authors} ({year}). {venue}. DOI: {doi or 'n/a'}")
    return "\n".join(lines)


@tool
def search_arxiv(query: str, limit: int = 8) -> str:
    """Search arXiv preprints. Returns numbered sources whose [n] indices resolve to real
    references (abstracts included). Good for recent/preprint work.
    """
    import xml.etree.ElementTree as ET

    params = {"search_query": f"all:{query}", "max_results": min(max(limit, 1), 25), "sortBy": "relevance"}
    try:
        r = httpx.get("https://export.arxiv.org/api/query", params=params, headers=_ua(), timeout=25)
        r.raise_for_status()
        root = ET.fromstring(r.text)
    except Exception as e:  # noqa: BLE001
        return f"arXiv search failed: {e}"
    ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    entries = root.findall("a:entry", ns)
    if not entries:
        return f"No arXiv results for: {query}"

    coll = current()
    lines: list[str] = []
    for e in entries:
        title = (e.findtext("a:title", default="", namespaces=ns) or "Untitled").strip().replace("\n", " ")
        summary = (e.findtext("a:summary", default="", namespaces=ns) or "").strip().replace("\n", " ")[:600]
        authors = ", ".join(
            (a.findtext("a:name", default="", namespaces=ns) or "")
            for a in e.findall("a:author", ns)[:4]
        )
        year = (e.findtext("a:published", default="", namespaces=ns) or "")[:4] or "n.d."
        doi = (e.findtext("arxiv:doi", default="", namespaces=ns) or "").strip()
        url = (e.findtext("a:id", default="", namespaces=ns) or "").strip()
        idx = coll.add(
            Source(title=title, authors=authors, year=year, venue="arXiv", doi=doi, abstract=summary)
        )
        ref = f"DOI: {doi}" if doi else url
        lines.append(f"[{idx}] {title} — {authors} ({year}). arXiv. {ref}\n    {summary}")
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


def _run_python_impl(code: str) -> str:
    from . import sandbox

    ws = sandbox.current_workspace()
    res = sandbox.run_python(code, ws)
    sandbox.record_artifacts(res.files)
    parts: list[str] = []
    if res.timed_out:
        parts.append("TIMEOUT: execution exceeded the time limit.")
    if res.stdout.strip():
        parts.append("STDOUT:\n" + res.stdout[:6000])
    if res.exit_code != 0 and res.stderr.strip():
        parts.append(f"ERROR (exit {res.exit_code}):\n" + res.stderr[-3000:])
    if res.files:
        parts.append("FILES SAVED to the project workspace: " + ", ".join(res.files))
    return "\n\n".join(parts) if parts else "(ran with no output)"


@tool
def run_python(code: str) -> str:
    """Run Python in a sandboxed container to compute results, analyse data, or generate
    figures — use this instead of doing arithmetic or estimating numbers yourself. A full
    scientific stack is available: numpy, pandas, scipy, sympy, matplotlib, openpyxl (read/
    write .xlsx), Pillow, and CoolProp for thermophysical properties.

    Files in the project workspace are readable by their relative path. Write outputs
    (figures as PNG, processed spreadsheets) to the current directory — they are saved to
    the project and reported back. Print results you need to see; there is NO network access.
    """
    return _run_python_impl(code)


@tool
def verify_doi(doi: str) -> str:
    """Verify a DOI actually resolves (via OpenAlex). Returns the resolved title/year or a
    NOT-FOUND notice. Use to check citations before relying on them.
    """
    clean = doi.strip().replace("https://doi.org/", "")
    try:
        r = httpx.get(f"https://api.openalex.org/works/doi:{clean}", headers=_ua(), timeout=20)
        if r.status_code == 404:
            return f"NOT FOUND: {clean} does not resolve — do not cite it."
        r.raise_for_status()
        w = r.json()
    except Exception as e:  # noqa: BLE001
        return f"verification failed for {clean}: {e}"
    return f"OK: {clean} -> {w.get('title', '?')} ({w.get('publication_year', '?')})"
