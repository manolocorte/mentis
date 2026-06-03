"""University-licensed source (e.g. Scopus/Elsevier via institutional API key).

Disabled until `university_api_key` is configured. The known target is Elsevier
Scopus (per the project's Universidad de Valladolid access); the search call is
implemented against the Scopus Search API and activated once the key + optional
institutional token are provided. Until then, the registry simply omits it.
"""
from __future__ import annotations

import logging
from typing import Optional

from mentis.adapters.outbound.sources._http import client
from mentis.domain.models import Author, Paper
from mentis.domain.ports.paper_source import PaperSourcePort

logger = logging.getLogger(__name__)

SCOPUS_SEARCH_URL = "https://api.elsevier.com/content/search/scopus"


class UniversitySource(PaperSourcePort):
    """Scopus-backed institutional source. Construct only when a key is present."""

    name = "university"

    def __init__(self, api_key: str, inst_token: Optional[str] = None, base_url: Optional[str] = None):
        self._api_key = api_key
        self._inst_token = inst_token
        self._base_url = base_url or SCOPUS_SEARCH_URL

    def _headers(self) -> dict[str, str]:
        headers = {"X-ELS-APIKey": self._api_key, "Accept": "application/json"}
        if self._inst_token:
            headers["X-ELS-Insttoken"] = self._inst_token
        return headers

    async def search(self, query: str, *, max_results: int = 25) -> list[Paper]:
        wrapped = query if "(" in query else f"TITLE-ABS-KEY({query})"
        params = {
            "query": wrapped,
            "count": min(max_results, 25),
            "sort": "relevancy",
            "field": "dc:title,dc:creator,prism:coverDate,prism:doi,citedby-count,"
            "prism:publicationName,dc:description,eid",
        }
        async with client() as http:
            resp = await http.get(self._base_url, params=params, headers=self._headers())
            if resp.status_code != 200:
                logger.warning("University/Scopus source %s", resp.status_code)
                return []
            entries = resp.json().get("search-results", {}).get("entry", [])
        return [self._parse(e) for e in entries if "error" not in e]

    async def resolve_oa_pdf(self, paper: Paper) -> Optional[str]:
        # Institutional full text is fetched out-of-band; OA resolution stays with Unpaywall.
        return None

    @staticmethod
    def _parse(e: dict) -> Paper:
        cover = e.get("prism:coverDate", "")
        year = int(cover[:4]) if cover[:4].isdigit() else None
        cited = e.get("citedby-count")
        creator = e.get("dc:creator")
        return Paper(
            title=e.get("dc:title", "(untitled)"),
            doi=e.get("prism:doi"),
            authors=[Author(name=creator)] if creator else [],
            year=year,
            venue=e.get("prism:publicationName"),
            abstract=e.get("dc:description"),
            citation_count=int(cited) if cited and str(cited).isdigit() else None,
            source="scopus",
            external_ids={"eid": e.get("eid", "")},
        )
