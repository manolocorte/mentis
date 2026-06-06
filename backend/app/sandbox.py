"""Sandboxed Python execution.

Runs model- or user-supplied code inside a locked-down Docker container with a
scientific Python stack baked in (numpy, pandas, scipy, matplotlib, sympy,
openpyxl, Pillow, CoolProp). Stateless by design: each call mounts a *workspace*
directory — the local analog of an S3 prefix — as ``/workspace``, runs the code
with no network and capped resources, and reports stdout/stderr plus any files
produced (PNGs, processed spreadsheets, ...).

This deliberately mirrors the planned cloud shape (Lambda container + S3) so the
engine can later be swapped for a remote invoker without touching callers: same
libraries, same ``/workspace`` contract, same result shape.
"""
from __future__ import annotations

import subprocess
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path

from .config import get_settings


# --- Workspace context -----------------------------------------------------
# Each project gets its own workspace directory (the local stand-in for an S3
# prefix). Uploaded files live there and produced files land there, so work
# persists per project across conversations. The server sets the active
# workspace per request; tools read it via current_workspace().

_current_workspace: ContextVar[Path | None] = ContextVar("mentis_workspace", default=None)


def workspace_root() -> Path:
    return Path(get_settings().store_path).parent / "workspaces"


def workspace_for(project_id: str) -> Path:
    return workspace_root() / project_id


def set_workspace(path: Path | str | None) -> None:
    _current_workspace.set(Path(path) if path is not None else None)


def current_workspace() -> Path:
    ws = _current_workspace.get() or workspace_root() / "_scratch"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


# --- Per-run artifact collector --------------------------------------------
# run_python records the files it produces here so the streaming layer can
# surface them (figures, processed spreadsheets) to the UI and the export.
# Reset at the start of each agent run.

_artifacts: ContextVar[list[str] | None] = ContextVar("mentis_artifacts", default=None)


def reset_artifacts() -> None:
    _artifacts.set([])


def record_artifacts(files: list[str]) -> None:
    cur = _artifacts.get()
    if cur is None:
        cur = []
        _artifacts.set(cur)
    for f in files:
        if f not in cur:
            cur.append(f)


def produced_artifacts() -> list[str]:
    return list(_artifacts.get() or [])


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    files: list[str] = field(default_factory=list)  # workspace-relative paths produced/changed

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


def _snapshot(root: Path) -> dict[str, tuple[int, float]]:
    """Map each file under ``root`` to (size, mtime) so we can diff before/after."""
    snap: dict[str, tuple[int, float]] = {}
    for p in root.rglob("*"):
        if p.is_file():
            st = p.stat()
            snap[str(p.relative_to(root))] = (st.st_size, st.st_mtime)
    return snap


def run_python(
    code: str,
    workspace: Path,
    *,
    timeout: int | None = None,
    memory: str | None = None,
    cpus: str | None = None,
) -> SandboxResult:
    """Execute ``code`` in the sandbox image with ``workspace`` mounted at /workspace.

    The container has no network, a read-only root filesystem (only /workspace and a
    512 MB tmpfs /tmp are writable), capped memory (swap disabled), CPU and PID
    limits, and runs as a non-root user. Relative file paths in the code resolve
    inside /workspace, so anything written there is returned in ``files``.
    """
    s = get_settings()
    timeout = timeout or s.sandbox_timeout
    memory = memory or s.sandbox_memory
    cpus = cpus or s.sandbox_cpus

    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    before = _snapshot(workspace)

    name = f"mentis-run-{uuid.uuid4().hex[:12]}"
    args = [
        "docker", "run", "--rm", "-i",
        "--name", name,
        "--network", "none",
        f"--memory={memory}", f"--memory-swap={memory}",  # equal => swap disabled
        f"--cpus={cpus}", "--pids-limit=256",
        "--read-only",
        "--tmpfs", "/tmp:rw,exec,size=512m",
        "--security-opt", "no-new-privileges",
        "-w", "/workspace",
        "-v", f"{workspace.resolve()}:/workspace",
        s.sandbox_image, "python", "-",
    ]

    timed_out = False
    try:
        proc = subprocess.run(
            args,
            input=code,
            capture_output=True,
            encoding="utf-8",  # force UTF-8 both ways; host locale (e.g. cp1252) would mangle code/output
            errors="replace",
            timeout=timeout,
        )
        stdout, stderr, exit_code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        subprocess.run(["docker", "kill", name], capture_output=True, text=True)
        timed_out = True
        stdout = _as_text(exc.stdout)
        stderr = _as_text(exc.stderr) + f"\n[sandbox] killed after {timeout}s timeout"
        exit_code = 124

    after = _snapshot(workspace)
    produced = sorted(rel for rel, meta in after.items() if before.get(rel) != meta)
    return SandboxResult(stdout, stderr, exit_code, timed_out, produced)


def _as_text(v: object) -> str:
    if v is None:
        return ""
    if isinstance(v, bytes):
        return v.decode(errors="replace")
    return str(v)
