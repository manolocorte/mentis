"""Agent team (Strands "agents-as-tools"):

  Orchestrator (Nova)  → plans, delegates, returns the result
    ├─ research(topic)        → Researcher (Nova): focused queries + relevant gathering
    ├─ analyze(task)          → Analyst (Claude → Nova fallback): computes/plots via run_python
    └─ draft_section(...)      → Writer (Claude Sonnet → Nova fallback): grounded prose

The Validator runs deterministically after the draft (app/citations.py), so it always
runs rather than at the orchestrator's discretion.
"""
from __future__ import annotations

import logging

from strands import Agent, tool

from . import models, prompts, sandbox, sources, tools

logger = logging.getLogger(__name__)

# Registry of source providers (key -> tool). Add new providers here.
SOURCE_TOOLS = {
    "openalex": tools.search_literature,
    "scopus": tools.scopus_search,
    "arxiv": tools.search_arxiv,
}

# Metadata for the UI (key, label, whether it needs a configured key).
AVAILABLE_SOURCES = [
    {"key": "openalex", "label": "OpenAlex", "free": True},
    {"key": "arxiv", "label": "arXiv (preprints)", "free": True},
    {"key": "scopus", "label": "Scopus — Univ. Salamanca", "free": False, "requires": "scopus_api_key"},
]


@tool
def research(topic: str) -> str:
    """Gather and curate the most relevant peer-reviewed sources for a topic. Returns a
    numbered list of sources (with [n] citation indices) plus relevance notes. Call this
    before writing anything that needs grounding.
    """
    active = sources.active_sources()
    tool_list = [SOURCE_TOOLS[k] for k in active if k in SOURCE_TOOLS] or [tools.search_literature]
    researcher = Agent(
        model=models.worker_model(),
        system_prompt=prompts.RESEARCHER_PROMPT + f"\n\nEnabled sources this run: {', '.join(active)}.",
        callback_handler=None,
        tools=tool_list,
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


@tool
def analyze(task: str) -> str:
    """Compute numbers, process an uploaded data file (Excel/CSV/image), or generate a figure via
    the Analyst, who writes and runs Python (numpy/pandas/scipy/sympy/matplotlib/CoolProp) in a
    sandbox. Use for any quantity that should be COMPUTED rather than estimated. Returns the results
    and the names of any files saved to the project workspace.
    """
    ws = sandbox.current_workspace()
    files = sorted(p.name for p in ws.iterdir() if p.is_file()) if ws.exists() else []
    file_note = (
        "Files already in your working directory (read them by these exact names): "
        + ", ".join(files)
        if files
        else "No files have been uploaded to the working directory yet."
    )
    full_task = f"{file_note}\n\n{task}"

    last_err: Exception | None = None
    for make_model in (models.draft_model, models.supervisor_model):  # Claude → Nova fallback
        try:
            analyst = Agent(
                model=make_model(),
                system_prompt=prompts.ANALYST_PROMPT,
                callback_handler=None,
                tools=[tools.run_python],
            )
            return str(analyst(full_task))
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.warning("analyst model failed, trying fallback: %s", e)
    return f"analysis failed: {last_err}"


def build_supervisor() -> Agent:
    """The Orchestrator: delegates to research(), analyze() and draft_section(), can read PDFs."""
    return Agent(
        model=models.supervisor_model(),
        system_prompt=prompts.SUPERVISOR_PROMPT,
        callback_handler=None,
        tools=[research, analyze, draft_section, tools.fetch_pdf_text, tools.verify_doi],
    )
