from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class QueuePort(Protocol):
    async def send(self, body: dict[str, Any]) -> None: ...
    async def send_batch(self, bodies: list[dict[str, Any]]) -> None: ...
