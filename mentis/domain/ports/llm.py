"""LLM port — Bedrock Converse-style chat with optional tool use."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolUse:
    tool_use_id: str
    name: str
    input: dict[str, Any]


@dataclass
class LLMResponse:
    """One turn of model output.

    `text` is the assembled assistant text. `tool_uses` is non-empty when the
    model requested tool invocations (stop_reason == 'tool_use').
    """
    text: str
    tool_uses: list[ToolUse] = field(default_factory=list)
    stop_reason: str = "end_turn"


@runtime_checkable
class LLMPort(Protocol):
    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        tools: Optional[list[ToolSpec]] = None,
        cache_system: bool = False,
    ) -> LLMResponse:
        """Send a Converse turn. `messages` use Bedrock Converse content blocks."""
        ...
