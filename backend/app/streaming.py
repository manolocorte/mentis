"""Map Strands `agent.stream_async` events to an SSE event vocabulary the React
Claude Code-style transcript understands, stripping models' <thinking> monologue.

Event types emitted:
  run_started   {}
  token         {"text": "..."}            incremental (cleaned) assistant text
  tool_call     {"name": "...", "input": {...}}   a tool/sub-agent invocation
  run_finished  {"text": "<full answer>"}
  error         {"message": "..."}
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, AsyncIterator

from strands import Agent

from .citations import finalize_with_references
from .sources import reset_run

_THINK_BLOCK = re.compile(r"<thinking>.*?</thinking>", re.DOTALL | re.IGNORECASE)
_OPEN = "<thinking>"


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _clean_stream(raw: str) -> str:
    """Strip complete <thinking> blocks; hold back text from an unclosed block or a
    partially-formed opening tag (so we never emit half a tag we'd want to retract)."""
    s = _THINK_BLOCK.sub("", raw)
    i = s.lower().find(_OPEN)
    if i != -1:
        return s[:i]
    for k in range(len(_OPEN) - 1, 0, -1):
        if s.lower().endswith(_OPEN[:k]):
            return s[:-k]
    return s


def _finalize(raw: str) -> str:
    s = _THINK_BLOCK.sub("", raw)
    i = s.lower().find(_OPEN)
    if i != -1:
        s = s[:i]
    return s.strip()


async def run_agent_sse(
    agent: Agent, prompt: str, sink: dict[str, Any] | None = None
) -> AsyncIterator[str]:
    yield _sse("run_started", {})
    reset_run()
    seen_tools: set[str] = set()
    raw = ""
    emitted = 0
    try:
        async for ev in agent.stream_async(prompt):
            if not isinstance(ev, dict):
                continue
            if ev.get("data"):
                raw += str(ev["data"])
                clean = _clean_stream(raw)
                if len(clean) > emitted:
                    yield _sse("token", {"text": clean[emitted:]})
                    emitted = len(clean)
            tu = ev.get("current_tool_use")
            if tu and tu.get("name"):
                key = f"{tu.get('toolUseId', '')}:{tu['name']}"
                if key not in seen_tools:
                    seen_tools.add(key)
                    yield _sse("tool_call", {"name": tu["name"], "input": tu.get("input", {})})
        yield _sse("status", {"label": "Checking sources & claims"})
        final_text = _finalize(raw)
        final_text, citations = await asyncio.to_thread(finalize_with_references, final_text)
        if citations:
            yield _sse("citations", {"items": citations})
        if sink is not None:
            sink["text"] = final_text
            sink["citations"] = citations
        yield _sse("run_finished", {"text": final_text})
    except Exception as e:  # noqa: BLE001
        yield _sse("error", {"message": str(e)})
