"""Per-run collection of the REAL sources returned by the research tools, so the
References list can be built deterministically from retrieved metadata instead of
whatever the model writes from memory.

Run state is process-global (shared across the threads Strands runs tools in).
Concurrent agent runs are serialized by a lock in server.py, so one run's state
never overlaps another's. (contextvars do NOT work here: Strands executes tools in
worker threads that don't inherit the caller's context.)
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class Source:
    title: str
    authors: str
    year: str
    venue: str
    doi: str  # cleaned (no https://doi.org/ prefix); may be ""
    abstract: str = ""        # used by the Validator to check claim support
    verified: bool = False    # DOI resolves
    supported: bool | None = None  # Validator: does the source back the claim it's cited for


@dataclass
class SourceCollector:
    items: list[Source] = field(default_factory=list)
    _by_key: dict[str, int] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, src: Source) -> int:
        """Add a source (deduped by DOI or title); return its 1-based global index."""
        key = (src.doi or src.title or "").lower().strip()
        with self._lock:
            if key and key in self._by_key:
                return self._by_key[key]
            self.items.append(src)
            idx = len(self.items)
            if key:
                self._by_key[key] = idx
            return idx


_current = SourceCollector()
_active_sources: list[str] = ["openalex", "scopus", "arxiv"]


def reset_run() -> SourceCollector:
    global _current
    _current = SourceCollector()
    return _current


def current() -> SourceCollector:
    return _current


def set_active_sources(keys: list[str]) -> None:
    """Set which source providers the Researcher may use for the current run."""
    global _active_sources
    _active_sources = list(keys) or ["openalex"]


def active_sources() -> list[str]:
    return _active_sources
