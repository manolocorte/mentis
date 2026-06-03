from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable


@dataclass
class VectorRecord:
    key: str
    vector: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorMatch:
    key: str
    score: float  # similarity in [0, 1] (1 = identical)
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class VectorStorePort(Protocol):
    async def upsert(self, index: str, records: list[VectorRecord]) -> None: ...

    async def query(
        self,
        index: str,
        vector: list[float],
        *,
        top_k: int = 8,
        filter: Optional[dict[str, Any]] = None,
    ) -> list[VectorMatch]: ...

    async def delete(self, index: str, keys: list[str]) -> None: ...
