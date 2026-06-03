"""Shared agent primitives: a single completion and a tool-use loop over the
Bedrock Converse contract.
"""
from __future__ import annotations

import logging
from typing import Optional

from mentis.application.tools import ToolDispatcher
from mentis.domain.ports.llm import LLMPort, ToolSpec

logger = logging.getLogger(__name__)


def user_msg(text: str) -> dict:
    return {"role": "user", "content": [{"text": text}]}


async def complete(
    llm: LLMPort,
    *,
    system: str,
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 1200,
    cache_system: bool = False,
) -> str:
    resp = await llm.chat(
        [user_msg(prompt)],
        system=system,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        cache_system=cache_system,
    )
    return resp.text


async def run_tool_loop(
    llm: LLMPort,
    *,
    system: str,
    prompt: str,
    tools: list[ToolSpec],
    dispatcher: ToolDispatcher,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 1500,
    max_steps: int = 5,
) -> str:
    """Drive a Converse tool-use conversation until the model stops requesting
    tools (or `max_steps` is hit). Returns the final assistant text.
    """
    messages: list[dict] = [user_msg(prompt)]
    final_text = ""
    for _ in range(max_steps):
        resp = await llm.chat(
            messages,
            system=system,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            cache_system=True,
        )
        final_text = resp.text or final_text
        if resp.stop_reason != "tool_use" or not resp.tool_uses:
            return resp.text or final_text

        # Re-append the assistant turn (text + toolUse blocks).
        assistant_content: list[dict] = []
        if resp.text:
            assistant_content.append({"text": resp.text})
        for tu in resp.tool_uses:
            assistant_content.append(
                {"toolUse": {"toolUseId": tu.tool_use_id, "name": tu.name, "input": tu.input}}
            )
        messages.append({"role": "assistant", "content": assistant_content})

        # Run each requested tool and feed results back.
        tool_results: list[dict] = []
        for tu in resp.tool_uses:
            output = await dispatcher.dispatch(tu)
            tool_results.append(
                {
                    "toolResult": {
                        "toolUseId": tu.tool_use_id,
                        "content": [{"text": output}],
                    }
                }
            )
        messages.append({"role": "user", "content": tool_results})

    return final_text
