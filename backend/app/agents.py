"""Multi-agent wiring (Strands "agents-as-tools").

A supervisor agent (cheap Nova tier) orchestrates research tools and delegates the
heavy writing to a drafter sub-agent (Claude Sonnet) exposed as the `draft_section` tool.
The drafter falls back to Nova Pro if Claude isn't available (e.g. the Anthropic
use-case form on a fresh account is still pending), so the pipeline degrades gracefully.
"""
from __future__ import annotations

import logging

from strands import Agent, tool

from . import models, prompts, tools

logger = logging.getLogger(__name__)


@tool
def draft_section(request: str, sources: str) -> str:
    """Write a journal-grade whitepaper section in English following Spain/Elsevier
    conventions. `request` describes the section to write; `sources` is the numbered list of
    sources (from search_literature/scopus_search) to ground and cite. Returns the draft.
    """
    message = f"REQUEST:\n{request}\n\nSOURCES:\n{sources}"
    last_err: Exception | None = None
    # Claude Sonnet first (best prose); Nova Pro fallback if Claude is gated/unavailable.
    for make_model in (models.draft_model, models.supervisor_model):
        try:
            drafter = Agent(
                model=make_model(),
                system_prompt=prompts.WHITEPAPER_PROMPT,
                callback_handler=None,
            )
            return str(drafter(message))
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.warning("drafter model failed, trying fallback: %s", e)
    return f"drafting failed: {last_err}"


def build_supervisor() -> Agent:
    """Construct the supervisor agent with research tools + the drafter sub-agent."""
    return Agent(
        model=models.supervisor_model(),
        system_prompt=prompts.SUPERVISOR_PROMPT,
        callback_handler=None,
        tools=[
            tools.search_literature,
            tools.scopus_search,
            tools.fetch_pdf_text,
            tools.verify_doi,
            draft_section,
        ],
    )
