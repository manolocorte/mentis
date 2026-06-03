from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class CodeResult:
    stdout: str
    stderr: str
    ok: bool


@runtime_checkable
class CodeExecPort(Protocol):
    async def run_python(self, code: str, *, timeout: int = 15) -> CodeResult: ...
