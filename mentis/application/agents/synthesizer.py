"""Synthesizer agent — writes the grounded, cited answer. May call the retrieve
tool to pull more evidence (agentic). Uses the draft (Opus) tier for paper_draft.
"""
from __future__ import annotations

from mentis.application.agents.base import run_tool_loop
from mentis.application.tools import RETRIEVE_TOOL, ToolDispatcher
from mentis.domain.models import RetrievedChunk
from mentis.domain.ports.llm import LLMPort

SYSTEM = (
    "You are a scientific writing assistant for refrigeration / thermodynamics research. "
    "Write a clear, well-structured answer grounded ONLY in the provided evidence and any "
    "additional passages you retrieve. Cite evidence inline with bracketed numbers like [1], [2] "
    "that refer to the numbered passages. If the evidence is insufficient, say so explicitly and "
    "call retrieve_corpus to look for more. Do not fabricate citations or numbers."
)

DRAFT_SYSTEM = SYSTEM + (
    " This is a paper-drafting task: produce publication-quality prose with sections and a precise, "
    "academic tone."
)


async def synthesize(
    llm: LLMPort,
    *,
    query: str,
    chunks: list[RetrievedChunk],
    investigation: str,
    history_text: str,
    dispatcher: ToolDispatcher,
    model: str | None = None,
    paper_draft: bool = False,
    feedback: str | None = None,
) -> str:
    evidence = _format_evidence(chunks)
    parts = [f"Question: {query}", "", f"Evidence passages:\n{evidence}", "", f"Investigator notes:\n{investigation}"]
    if history_text:
        parts += ["", f"Conversation so far:\n{history_text}"]
    if feedback:
        parts += ["", f"A fact-checker flagged issues with your previous draft. Revise to fix them:\n{feedback}"]
    prompt = "\n".join(parts)
    return await run_tool_loop(
        llm,
        system=DRAFT_SYSTEM if paper_draft else SYSTEM,
        prompt=prompt,
        tools=[RETRIEVE_TOOL],
        dispatcher=dispatcher,
        model=model,
        max_tokens=2200 if paper_draft else 1500,
        temperature=0.3,
    )


def _format_evidence(chunks: list[RetrievedChunk]) -> str:
    return "\n\n".join(
        f"[{i}] ({c.title or c.doi or 'source'}) {c.text[:900]}" for i, c in enumerate(chunks, start=1)
    )
