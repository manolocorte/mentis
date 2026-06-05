"""Project-level whitepaper compilation.

The Editor assembles ONE clean paper from the whole project — brief + drafted material
across all conversations + the project library — citing only the library (grounded),
then the citation pipeline appends a verified, claim-checked References section.
"""
from __future__ import annotations

import logging

from strands import Agent

from . import citations, models, prompts, sources
from .sources import Source

logger = logging.getLogger(__name__)


def _prime_library(library: list[dict]) -> str:
    """Load the project library into a fresh collector so the compiled paper's [n]
    citations resolve to real, verifiable sources. Returns the numbered source list."""
    coll = sources.reset_run()
    lines: list[str] = []
    for s in library:
        idx = coll.add(
            Source(
                title=s.get("title", ""), authors=s.get("authors", ""),
                year=str(s.get("year", "")), venue=s.get("venue", ""),
                doi=s.get("doi", "") or "", abstract="", verified=bool(s.get("verified")),
            )
        )
        lines.append(
            f"[{idx}] {s.get('title', '')} — {s.get('authors', '')} ({s.get('year', '')}). "
            f"{s.get('venue', '')}. DOI: {s.get('doi') or 'n/a'}"
        )
    return "\n".join(lines)


def compile_whitepaper(brief: str, drafts: str, library: list[dict]) -> str:
    """Assemble + validate the full paper markdown for a project."""
    sources_text = _prime_library(library) or "(no sources in the project library yet)"
    message = (
        f"BRIEF:\n{brief or '(none)'}\n\n"
        f"DRAFTED MATERIAL:\n{drafts or '(none yet)'}\n\n"
        f"SOURCES (cite as [n]):\n{sources_text}"
    )
    paper = ""
    last_err: Exception | None = None
    for make_model in (models.editor_model, models.editor_fallback_model):  # Claude → Nova
        try:
            editor = Agent(
                model=make_model(), system_prompt=prompts.EDITOR_PROMPT, callback_handler=None
            )
            paper = str(editor(message))
            break
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.warning("editor model failed, trying fallback: %s", e)
    if not paper:
        raise RuntimeError(f"compile failed: {last_err}")
    final, _records = citations.finalize_with_references(paper)
    return final
