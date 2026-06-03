"""Unpaywall — resolves a legal open-access PDF URL for a DOI.

This is a *resolver*, not a search source; it fills in `oa_pdf_url` for papers
discovered via metadata-only sources (e.g. Crossref).
"""
from __future__ import annotations

import logging
from typing import Optional

from mentis.adapters.outbound.sources._http import client
from mentis.domain.models import Paper

logger = logging.getLogger(__name__)

BASE_URL = "https://api.unpaywall.org/v2"


class Unpaywall:
    def __init__(self, email: Optional[str]):
        self._email = email

    async def resolve(self, doi: str) -> Optional[str]:
        if not self._email or not doi:
            return None
        async with client() as http:
            resp = await http.get(f"{BASE_URL}/{doi}", params={"email": self._email})
            if resp.status_code != 200:
                return None
            data = resp.json()
        loc = data.get("best_oa_location") or {}
        return loc.get("url_for_pdf") or loc.get("url")

    async def enrich(self, paper: Paper) -> Paper:
        if not paper.oa_pdf_url and paper.doi:
            paper.oa_pdf_url = await self.resolve(paper.doi)
        return paper
