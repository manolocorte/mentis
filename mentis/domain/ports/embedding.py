from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingPort(Protocol):
    @property
    def dimension(self) -> int: ...

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...
