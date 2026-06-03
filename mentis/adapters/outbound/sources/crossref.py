"""Crossref source — free metadata for scholarly works."""
from __future__ import annotations

import logging
import re
from typing import Optional

from mentis.adapters.outbound.sources._http import client
from mentis.domain.models import Author, Paper
from mentis.domain.ports.paper_source import PaperSourcePort

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.crossref.org/works"


class CrossrefSource(PaperSourcePort):
    name = "crossref"

    def __init__(self, mailto: Optional[str] = None):
        self._mailto = mailto

    async def search(self, query: str, *, max_results: int = 25) -> list[Paper]:
        params = {"query": query, "rows": min(max_results, 50)}
        if self._mailto:
            params["mailto"] = self._mailto
        async with client() as http:
            resp = await http.get(SEARCH_URL, params=params)
            if resp.status_code != 200:
                logger.warning("Crossref %s", resp.status_code)
                return []
            items = resp.json().get("message", {}).get("items", [])
        return [self._parse(it) for it in items]

    async def resolve_oa_pdf(self, paper: Paper) -> Optional[str]:
        return None  # Crossref does not provide OA PDFs; Unpaywall handles that.

    @staticmethod
    def _parse(it: dict) -> Paper:
        title_list = it.get("title") or []
        authors = [
            Author(name=f"{a.get('given','')} {a.get('family','')}".strip())
            for a in it.get("author", [])
            if a.get("family")
        ]
        year = None
        parts = it.get("issued", {}).get("date-parts", [[None]])
        if parts and parts[0] and parts[0][0]:
            year = parts[0][0]
        container = it.get("container-title") or []
        return Paper(
            title=title_list[0] if title_list else "(untitled)",
            doi=it.get("DOI"),
            authors=authors,
            year=year,
            venue=container[0] if container else None,
            abstract=_strip_jats(it.get("abstract")),
            url=it.get("URL"),
            citation_count=it.get("is-referenced-by-count"),
            source="crossref",
        )


def _strip_jats(abstract: Optional[str]) -> Optional[str]:
    if not abstract:
        return None
    return re.sub(r"<[^>]+>", "", abstract).strip()[:4000]
