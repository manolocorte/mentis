"""Coder agent — runs thermodynamic / numeric calculations via the run_python
tool and explains the result.
"""
from __future__ import annotations

from mentis.application.agents.base import run_tool_loop
from mentis.application.tools import CODE_TOOL, ToolDispatcher
from mentis.domain.ports.llm import LLMPort

SYSTEM = (
    "You are a thermodynamics computation assistant. For the user's request, write and run a Python "
    "snippet with the run_python tool to compute the answer (use only the standard library and basic "
    "math; print results). Then explain the result clearly with units. Show the key numbers."
)


async def run_code_agent(
    llm: LLMPort, *, query: str, dispatcher: ToolDispatcher, model: str | None = None
) -> str:
    return await run_tool_loop(
        llm,
        system=SYSTEM,
        prompt=query,
        tools=[CODE_TOOL],
        dispatcher=dispatcher,
        model=model,
        max_tokens=1500,
        temperature=0.1,
    )
