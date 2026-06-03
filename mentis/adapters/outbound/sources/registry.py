"""Builds the active set of paper sources from settings.

OA sources are always on. The university (Scopus) source is added only when an
API key is configured — drop the key into SSM/.env later and it joins the mix
with no code change.
"""
from __future__ import annotations

from mentis.adapters.outbound.sources.arxiv import ArxivSource
from mentis.adapters.outbound.sources.crossref import CrossrefSource
from mentis.adapters.outbound.sources.openalex import OpenAlexSource
from mentis.adapters.outbound.sources.university import UniversitySource
from mentis.adapters.outbound.sources.unpaywall import Unpaywall
from mentis.config import Settings
from mentis.domain.ports.paper_source import PaperSourcePort


def build_sources(settings: Settings) -> list[PaperSourcePort]:
    sources: list[PaperSourcePort] = [
        OpenAlexSource(mailto=settings.unpaywall_email),
        CrossrefSource(mailto=settings.unpaywall_email),
        ArxivSource(),
    ]
    if settings.university_api_key:
        sources.append(
            UniversitySource(
                api_key=settings.university_api_key,
                base_url=settings.university_base_url,
            )
        )
    return sources


def build_unpaywall(settings: Settings) -> Unpaywall:
    return Unpaywall(email=settings.unpaywall_email)
