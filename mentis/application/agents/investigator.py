"""Investigator agent — LLM analysis of retrieved evidence into themes, findings
and gaps. (Replaces the legacy token-frequency heuristic with real reasoning.)
"""
from __future__ import annotations

from dataclasses import dataclass

from mentis.application.agents.base import complete
from mentis.domain.models import RetrievedChunk
from mentis.domain.ports.llm import LLMPort

SYSTEM = (
    "You are a meticulous research investigator. Given a question and numbered evidence "
    "passages, identify: (1) the key themes present, (2) concrete findings that bear on the "
    "question (cite passage numbers like [2]), and (3) gaps or contradictions the evidence does "
    "NOT resolve. Be concise and grounded — never invent facts not in the passages."
)


@dataclass
class Investigation:
    notes: str


async def investigate(
    llm: LLMPort, *, query: str, chunks: list[RetrievedChunk], model: str | None = None
) -> Investigation:
    if not chunks:
        return Investigation(notes="No corpus evidence retrieved for this question.")
    evidence = _format_evidence(chunks)
    prompt = f"Question: {query}\n\nEvidence:\n{evidence}\n\nProduce the themes / findings / gaps analysis."
    notes = await complete(llm, system=SYSTEM, prompt=prompt, model=model, max_tokens=900, cache_system=True)
    return Investigation(notes=notes)


def _format_evidence(chunks: list[RetrievedChunk]) -> str:
    lines = []
    for i, c in enumerate(chunks, start=1):
        src = c.title or c.doi or c.document_id or "source"
        lines.append(f"[{i}] ({src}) {c.text[:900]}")
    return "\n\n".join(lines)
