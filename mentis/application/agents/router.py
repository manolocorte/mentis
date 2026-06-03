"""Router agent — cheap intent classification on the Haiku tier."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from mentis.application.agents.base import complete
from mentis.domain.ports.llm import LLMPort

INTENTS = {
    "research_query",
    "literature_review",
    "paper_draft",
    "fact_check",
    "code_execution",
    "general_chat",
}

SYSTEM = (
    "You classify a user's request to a research assistant for absorption-refrigeration / "
    "CO2-refrigerant literature. Respond with ONLY a JSON object: "
    '{"intent": <one of research_query|literature_review|paper_draft|fact_check|code_execution|general_chat>, '
    '"confidence": <0..1>}. '
    "code_execution = thermodynamic/numeric calculation. fact_check = verify a specific claim. "
    "literature_review = summarize/compare the body of work. paper_draft = write a section/paper. "
    "research_query = a grounded question. general_chat = anything else."
)


@dataclass
class Intent:
    intent: str
    confidence: float


async def classify(llm: LLMPort, query: str, history: list[dict] | None = None) -> Intent:
    context = ""
    if history:
        context = "Recent turns:\n" + "\n".join(f"{m['role']}: {m['content'][:160]}" for m in history[-4:]) + "\n\n"
    raw = await complete(
        llm, system=SYSTEM, prompt=f"{context}Request: {query}", temperature=0.0, max_tokens=120
    )
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            intent = data.get("intent", "research_query")
            if intent in INTENTS:
                return Intent(intent=intent, confidence=float(data.get("confidence", 0.6)))
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    return Intent(intent="research_query", confidence=0.4)
