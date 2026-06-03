"""arXiv source — free preprints with direct PDF links (Atom XML API)."""
from __future__ import annotations

import logging
from typing import Optional
from xml.etree import ElementTree as ET

from mentis.adapters.outbound.sources._http import client
from mentis.domain.models import Author, Paper
from mentis.domain.ports.paper_source import PaperSourcePort

logger = logging.getLogger(__name__)

SEARCH_URL = "http://export.arxiv.org/api/query"
_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivSource(PaperSourcePort):
    name = "arxiv"

    async def search(self, query: str, *, max_results: int = 25) -> list[Paper]:
        params = {
            "search_query": f"all:{query}",
            "max_results": min(max_results, 50),
            "sortBy": "relevance",
        }
        async with client() as http:
            resp = await http.get(SEARCH_URL, params=params)
            if resp.status_code != 200:
                logger.warning("arXiv %s", resp.status_code)
                return []
            text = resp.text
        return self._parse(text)

    async def resolve_oa_pdf(self, paper: Paper) -> Optional[str]:
        return paper.oa_pdf_url

    @staticmethod
    def _parse(xml_text: str) -> list[Paper]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []
        papers: list[Paper] = []
        for entry in root.findall("atom:entry", _NS):
            title = (entry.findtext("atom:title", default="", namespaces=_NS) or "").strip()
            summary = (entry.findtext("atom:summary", default="", namespaces=_NS) or "").strip()
            published = entry.findtext("atom:published", default="", namespaces=_NS) or ""
            year = int(published[:4]) if published[:4].isdigit() else None
            authors = [
                Author(name=(a.findtext("atom:name", default="", namespaces=_NS) or "").strip())
                for a in entry.findall("atom:author", _NS)
            ]
            pdf_url = None
            abs_url = None
            for link in entry.findall("atom:link", _NS):
                if link.get("title") == "pdf":
                    pdf_url = link.get("href")
                if link.get("rel") == "alternate":
                    abs_url = link.get("href")
            papers.append(
                Paper(
                    title=title or "(untitled)",
                    authors=authors,
                    year=year,
                    abstract=summary[:4000] or None,
                    url=abs_url,
                    oa_pdf_url=pdf_url,
                    source="arxiv",
                )
            )
        return papers
