"""Per-run collection of the REAL sources returned by the research tools, so the
References list can be built deterministically from retrieved metadata instead of
whatever the model writes from memory.

Single-user assumption: one active run at a time. The collector is a process global
reset at the start of each run. (A proper multi-user fix would use Strands tool
context / per-session state.)
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
    verified: bool = False


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


def reset_run() -> SourceCollector:
    global _current
    _current = SourceCollector()
    return _current


def current() -> SourceCollector:
    return _current
