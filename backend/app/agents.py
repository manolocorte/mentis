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
from strands.event_loop._retry import ModelRetryStrategy
from strands.hooks import BeforeModelCallEvent, HookProvider, HookRegistry

from . import models, prompts, sandbox, sources, tools
from .config import get_settings

logger = logging.getLogger(__name__)


class StepLimiter(HookProvider):
    """Abort a single agent run after `max_steps` model calls.

    Strands' event loop recurses for as long as the model keeps requesting tools —
    there is no native cap. A wedged or looping agent (e.g. retrying a failing tool)
    therefore re-feeds an ever-growing context to the model on every cycle, which
    bills huge INPUT-token counts for almost no output. One BeforeModelCallEvent
    fires per cycle, so counting them and raising past the cap is a hard stop on
    that runaway. Each Agent gets its own fresh limiter (agents are built per call).
    """

    def __init__(self, max_steps: int, label: str) -> None:
        self.max_steps = max_steps
        self.label = label
        self.count = 0

    def register_hooks(self, registry: HookRegistry, **_: object) -> None:
        registry.add_callback(BeforeModelCallEvent, self._on_model_call)

    def _on_model_call(self, _event: BeforeModelCallEvent) -> None:
        self.count += 1
        if self.count > self.max_steps:
            raise RuntimeError(
                f"step limit reached ({self.label}: {self.max_steps} model calls) — "
                "stopping to prevent a runaway loop"
            )


def _limiter(label: str, steps: int | None = None) -> StepLimiter:
    s = get_settings()
    return StepLimiter(steps if steps is not None else s.max_agent_steps, label)


def _retry() -> ModelRetryStrategy:
    # max_attempts = first attempt + N retries; stateful, so build a fresh one per agent.
    return ModelRetryStrategy(max_attempts=get_settings().max_model_retries + 1)

# Claude (model_draft / model_verify) is unavailable until the Anthropic use-case
# form is accepted for the account — every call raises ResourceNotFoundException
# ("use case details have not been submitted"). Once we've seen that once, skip the
# doomed Claude attempt on every later analyze()/draft_section() call: it wastes a
# Bedrock round-trip and the failed stream is correlated with run stalls. Cleared on
# process restart, so accepting the form + restarting re-enables Claude automatically.
_claude_unavailable = False


def _note_model_failure(exc: Exception) -> None:
    """Latch Claude-unavailable when we see the Bedrock 'use case not submitted' signal."""
    global _claude_unavailable
    msg = str(exc).lower()
    if "use case" in msg or "have not been submitted" in msg or "resourcenotfound" in msg:
        _claude_unavailable = True


def _draft_models() -> list:
    """Claude → Nova, skipping Claude once it's proven unavailable this process."""
    return [models.supervisor_model] if _claude_unavailable else [models.draft_model, models.supervisor_model]

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
    {"key": "scopus", "label": "Scopus — Univ. Valladolid", "free": False, "requires": "scopus_api_key"},
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
        hooks=[_limiter("researcher")],
        retry_strategy=_retry(),
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
    for make_model in _draft_models():  # Claude → Nova fallback (Claude skipped if unavailable)
        try:
            writer = Agent(
                model=make_model(),
                system_prompt=prompts.WHITEPAPER_PROMPT,
                callback_handler=None,
                hooks=[_limiter("writer")],
                retry_strategy=_retry(),
            )
            return str(writer(message))
        except Exception as e:  # noqa: BLE001
            last_err = e
            _note_model_failure(e)
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
    for make_model in _draft_models():  # Claude → Nova fallback (Claude skipped if unavailable)
        try:
            analyst = Agent(
                model=make_model(),
                system_prompt=prompts.ANALYST_PROMPT,
                callback_handler=None,
                tools=[tools.run_python],
                hooks=[_limiter("analyst", get_settings().max_analyst_steps)],
                retry_strategy=_retry(),
            )
            return str(analyst(full_task))
        except Exception as e:  # noqa: BLE001
            last_err = e
            _note_model_failure(e)
            logger.warning("analyst model failed, trying fallback: %s", e)
    return f"analysis failed: {last_err}"


def build_supervisor() -> Agent:
    """The Orchestrator: delegates to research(), analyze() and draft_section(), can read PDFs."""
    return Agent(
        model=models.supervisor_model(),
        system_prompt=prompts.SUPERVISOR_PROMPT,
        callback_handler=None,
        tools=[research, analyze, draft_section, tools.fetch_pdf_text, tools.verify_doi],
        hooks=[_limiter("orchestrator")],
        retry_strategy=_retry(),
    )
