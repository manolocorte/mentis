"""Paper source port — pluggable bibliographic providers (OpenAlex, Crossref,
arXiv, and later a university-licensed source via API key).
"""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from mentis.domain.models import Paper


@runtime_checkable
class PaperSourcePort(Protocol):
    name: str

    async def search(self, query: str, *, max_results: int = 25) -> list[Paper]: ...

    async def resolve_oa_pdf(self, paper: Paper) -> Optional[str]:
        """Return a legal open-access PDF URL for the paper, if one exists."""
        ...
