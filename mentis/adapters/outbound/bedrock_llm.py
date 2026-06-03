"""Bedrock Converse adapter implementing LLMPort, with tool use and prompt caching.

boto3 is synchronous; calls are dispatched to a thread so the async agent loop
isn't blocked.
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

import boto3

from mentis.domain.ports.llm import LLMPort, LLMResponse, ToolSpec, ToolUse


class BedrockLLM(LLMPort):
    def __init__(self, region: str, default_model: str):
        self._region = region
        self._default_model = default_model
        self._client = boto3.client("bedrock-runtime", region_name=region)

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
        kwargs: dict[str, Any] = {
            "modelId": model or self._default_model,
            "messages": messages,
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": max_tokens,
                "topP": 0.9,
            },
        }
        if system:
            system_blocks: list[dict[str, Any]] = [{"text": system}]
            # Prompt caching: cache the (large, stable) system prompt to cut cost.
            if cache_system:
                system_blocks.append({"cachePoint": {"type": "default"}})
            kwargs["system"] = system_blocks
        if tools:
            kwargs["toolConfig"] = {
                "tools": [
                    {
                        "toolSpec": {
                            "name": t.name,
                            "description": t.description,
                            "inputSchema": {"json": t.input_schema},
                        }
                    }
                    for t in tools
                ]
            }

        response = await asyncio.to_thread(self._client.converse, **kwargs)
        return self._parse(response)

    @staticmethod
    def _parse(response: dict[str, Any]) -> LLMResponse:
        stop_reason = response.get("stopReason", "end_turn")
        message = response.get("output", {}).get("message", {})
        blocks = message.get("content", [])
        text_parts: list[str] = []
        tool_uses: list[ToolUse] = []
        for block in blocks:
            if "text" in block:
                text_parts.append(block["text"])
            elif "toolUse" in block:
                tu = block["toolUse"]
                tool_uses.append(
                    ToolUse(
                        tool_use_id=tu["toolUseId"],
                        name=tu["name"],
                        input=tu.get("input", {}),
                    )
                )
        return LLMResponse(
            text="\n".join(text_parts).strip(),
            tool_uses=tool_uses,
            stop_reason=stop_reason,
        )
