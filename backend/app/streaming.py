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
import logging
import re
from pathlib import Path
from typing import Any, AsyncIterator
from urllib.parse import quote

from strands import Agent

from .citations import finalize_with_references
from .config import get_settings
from .sandbox import produced_artifacts, reset_artifacts
from .sources import reset_run

logger = logging.getLogger(__name__)

# Shown to the user when a run can't finish (timeout, step-cap abort, or error).
# The real cause is logged server-side; the user gets a calm, actionable message.
TOO_COMPLEX = (
    "I wasn't able to complete this request — it may be too complex or broad for me to handle "
    "in one go. Please try reformulating it, or breaking it into smaller, more specific questions."
)

_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}


def _artifact_markdown(base: str) -> str:
    """Render produced files as markdown: figures inline, other files as links."""
    lines: list[str] = []
    for name in produced_artifacts():
        url = f"{base}/{quote(name)}"
        if Path(name).suffix.lower() in _IMAGE_EXT:
            lines.append(f"\n\n![{name}]({url})")
        else:
            lines.append(f"\n\n[{name}]({url})")
    return "".join(lines)

_THINK_BLOCK = re.compile(r"<thinking>.*?</thinking>", re.DOTALL | re.IGNORECASE)
_OPEN = "<thinking>"
# Some models wrap their answer in stray <response>...</response> tags; strip the
# tags (keep the content) so they don't render in the transcript.
_STRAY = re.compile(r"</?response\s*>", re.IGNORECASE)


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _clean_stream(raw: str) -> str:
    """Strip complete <thinking> blocks; hold back text from an unclosed block or a
    partially-formed opening tag (so we never emit half a tag we'd want to retract)."""
    s = _THINK_BLOCK.sub("", raw)
    s = _STRAY.sub("", s)
    i = s.lower().find(_OPEN)
    if i != -1:
        return s[:i]
    for k in range(len(_OPEN) - 1, 0, -1):
        if s.lower().endswith(_OPEN[:k]):
            return s[:-k]
    return s


def _finalize(raw: str) -> str:
    s = _THINK_BLOCK.sub("", raw)
    s = _STRAY.sub("", s)
    i = s.lower().find(_OPEN)
    if i != -1:
        s = s[:i]
    return s.strip()


async def run_agent_sse(
    agent: Agent,
    prompt: str,
    sink: dict[str, Any] | None = None,
    artifact_base: str | None = None,
) -> AsyncIterator[str]:
    yield _sse("run_started", {})
    reset_run()
    reset_artifacts()
    seen_tools: set[str] = set()
    raw = ""
    emitted = 0
    timed_out = False
    try:
        # Hard wall-clock ceiling: a stalled Bedrock stream (or a wedged sub-agent
        # thread) becomes a clean, bounded error instead of freezing the app. The
        # orchestrator loop stays free (Strands runs sync tools via to_thread), so
        # this timeout actually fires even when a worker thread is stuck.
        try:
            async with asyncio.timeout(get_settings().run_timeout):
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
        except (TimeoutError, asyncio.TimeoutError):
            timed_out = True
        yield _sse("status", {"label": "Checking sources & claims"})
        final_text = _finalize(raw)
        citations: list[dict] = []
        if timed_out or not final_text.strip():
            # Hit the wall-clock ceiling or produced nothing usable → bail gracefully.
            final_text = TOO_COMPLEX
        else:
            final_text, citations = await asyncio.to_thread(finalize_with_references, final_text)
            if artifact_base:
                final_text += _artifact_markdown(artifact_base)
        if citations:
            yield _sse("citations", {"items": citations})
        if sink is not None:
            sink["text"] = final_text
            sink["citations"] = citations
        yield _sse("run_finished", {"text": final_text})
    except Exception:  # noqa: BLE001
        # Step-cap abort, model error after the single retry, etc. Log the real cause,
        # show the user a calm message rather than a raw stack/error event.
        logger.exception("agent run failed")
        if sink is not None:
            sink["text"] = TOO_COMPLEX
            sink["citations"] = []
        yield _sse("run_finished", {"text": TOO_COMPLEX})
