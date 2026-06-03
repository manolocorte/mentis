"""Sandboxed Python execution implementing CodeExecPort.

Runs the snippet in a separate Python process with a wall-clock timeout and a
restricted environment. Suitable for the thermodynamic / refrigeration-cycle
calculations the research domain needs. For stronger isolation in production,
swap this adapter for a Bedrock AgentCore Code Interpreter session — the port
contract is identical.
"""
from __future__ import annotations

import asyncio
import sys

from mentis.domain.ports.code_exec import CodeExecPort, CodeResult


class LocalCodeExec(CodeExecPort):
    async def run_python(self, code: str, *, timeout: int = 15) -> CodeResult:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",  # isolated mode: ignore env vars and user site-packages
            "-c",
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return CodeResult(stdout="", stderr=f"Execution timed out after {timeout}s", ok=False)
        return CodeResult(
            stdout=stdout.decode("utf-8", "replace")[:10000],
            stderr=stderr.decode("utf-8", "replace")[:4000],
            ok=proc.returncode == 0,
        )
