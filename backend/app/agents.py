"""Four-agent team (Strands "agents-as-tools"):

  Orchestrator (Nova)  → plans, delegates, returns the result
    ├─ research(topic)        → Researcher (Nova): focused queries + relevant gathering
    └─ draft_section(...)      → Writer (Claude Sonnet → Nova fallback): grounded prose

The Validator runs deterministically after the draft (app/citations.py), so it always
runs rather than at the orchestrator's discretion.
"""
from __future__ import annotations

import logging

from strands import Agent, tool

from . import models, prompts, tools

logger = logging.getLogger(__name__)


@tool
def research(topic: str) -> str:
    """Gather and curate the most relevant peer-reviewed sources for a topic. Returns a
    numbered list of sources (with [n] citation indices) plus relevance notes. Call this
    before writing anything that needs grounding.
    """
    researcher = Agent(
        model=models.worker_model(),
        system_prompt=prompts.RESEARCHER_PROMPT,
        callback_handler=None,
        tools=[tools.search_literature, tools.scopus_search],
    )
    return str(researcher(f"Topic: {topic}"))


@tool
def draft_section(request: str, sources: str) -> str:
    """Write grounded prose (adaptive register: brief answer, a section, or a full paper as
    the request warrants), in English following Spain/Elsevier conventions. `sources` is the
    numbered list from research(). Returns the draft. Do not call before research().
    """
    message = f"REQUEST:\n{request}\n\nSOURCES:\n{sources}"
    last_err: Exception | None = None
    for make_model in (models.draft_model, models.supervisor_model):  # Claude → Nova fallback
        try:
            writer = Agent(
                model=make_model(),
                system_prompt=prompts.WHITEPAPER_PROMPT,
                callback_handler=None,
            )
            return str(writer(message))
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.warning("writer model failed, trying fallback: %s", e)
    return f"drafting failed: {last_err}"


def build_supervisor() -> Agent:
    """The Orchestrator: delegates to research() and draft_section(), can read PDFs."""
    return Agent(
        model=models.supervisor_model(),
        system_prompt=prompts.SUPERVISOR_PROMPT,
        callback_handler=None,
        tools=[research, draft_section, tools.fetch_pdf_text, tools.verify_doi],
    )
