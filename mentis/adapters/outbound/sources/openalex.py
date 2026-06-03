"""OpenAlex source — free, no API key, includes open-access PDF URLs."""
from __future__ import annotations

import logging
from typing import Optional

from mentis.adapters.outbound.sources._http import client
from mentis.domain.models import Author, Paper
from mentis.domain.ports.paper_source import PaperSourcePort

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.openalex.org/works"


class OpenAlexSource(PaperSourcePort):
    name = "openalex"

    def __init__(self, mailto: Optional[str] = None):
        self._mailto = mailto

    async def search(self, query: str, *, max_results: int = 25) -> list[Paper]:
        params = {
            "search": query,
            "per_page": min(max_results, 50),
            "sort": "relevance_score:desc",
        }
        if self._mailto:
            params["mailto"] = self._mailto
        async with client() as http:
            resp = await http.get(SEARCH_URL, params=params)
            if resp.status_code != 200:
                logger.warning("OpenAlex %s", resp.status_code)
                return []
            data = resp.json()
        return [self._parse(w) for w in data.get("results", [])]

    async def resolve_oa_pdf(self, paper: Paper) -> Optional[str]:
        return paper.oa_pdf_url

    @staticmethod
    def _parse(w: dict) -> Paper:
        oa = w.get("open_access", {}) or {}
        best = w.get("best_oa_location") or {}
        doi = (w.get("doi") or "").replace("https://doi.org/", "") or None
        loc = w.get("primary_location") or {}
        source = loc.get("source") or {}
        authors = [
            Author(name=a.get("author", {}).get("display_name", ""))
            for a in w.get("authorships", [])
            if a.get("author", {}).get("display_name")
        ]
        return Paper(
            title=w.get("title") or "(untitled)",
            doi=doi,
            authors=authors,
            year=w.get("publication_year"),
            venue=source.get("display_name"),
            abstract=_invert_abstract(w.get("abstract_inverted_index")),
            url=w.get("id"),
            oa_pdf_url=best.get("pdf_url") or oa.get("oa_url"),
            citation_count=w.get("cited_by_count"),
            source="openalex",
            external_ids={"openalex": w.get("id", "")},
        )


def _invert_abstract(inverted: Optional[dict]) -> Optional[str]:
    if not inverted:
        return None
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions)[:4000]
