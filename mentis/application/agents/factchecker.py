"""Fact-checker / critic agent — adversarially verifies that the draft's claims
are supported by the evidence. Drives the reflexion loop.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from mentis.application.agents.base import complete
from mentis.domain.models import RetrievedChunk
from mentis.domain.ports.llm import LLMPort

SYSTEM = (
    "You are a skeptical scientific fact-checker. Given an answer and the numbered evidence it was "
    "written from, check every factual/numeric claim. A claim is supported only if the evidence "
    "directly backs it. Respond with ONLY JSON: "
    '{"supported": <true|false>, "issues": [<short strings>], "feedback": "<how to fix, or empty>"}. '
    "Default to supported=false when a claim has no clear backing in the evidence."
)


@dataclass
class Verdict:
    supported: bool
    issues: list[str] = field(default_factory=list)
    feedback: str = ""


async def fact_check(
    llm: LLMPort, *, answer: str, chunks: list[RetrievedChunk], model: str | None = None
) -> Verdict:
    if not chunks:
        return Verdict(supported=True)  # nothing to check against; let it through
    evidence = "\n\n".join(
        f"[{i}] {c.text[:700]}" for i, c in enumerate(chunks, start=1)
    )
    prompt = f"Answer to verify:\n{answer}\n\nEvidence:\n{evidence}"
    raw = await complete(llm, system=SYSTEM, prompt=prompt, model=model, temperature=0.0, max_tokens=600)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return Verdict(supported=True)
    try:
        data = json.loads(match.group(0))
        return Verdict(
            supported=bool(data.get("supported", True)),
            issues=list(data.get("issues", [])),
            feedback=str(data.get("feedback", "")),
        )
    except (json.JSONDecodeError, ValueError, TypeError):
        return Verdict(supported=True)
