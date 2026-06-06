"""FastAPI app — SSE streaming chat over the Strands supervisor, with projects,
conversations, a per-project source library, and conversation memory.

Run locally:  uvicorn app.server:app --reload --port 8080   (from the backend/ dir)
Lift to AgentCore later: swap FastAPI for BedrockAgentCoreApp + @app.entrypoint.
"""
from __future__ import annotations

import asyncio
import json
import mimetypes
import re
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from .agents import AVAILABLE_SOURCES, build_supervisor
from .compiler import compile_whitepaper
from .config import get_settings
from .export import build_docx, build_pdf
from .sandbox import set_workspace, workspace_for
from .sources import set_active_sources
from .store import get_store
from .streaming import run_agent_sse

settings = get_settings()
store = get_store()

app = FastAPI(title="Mentis-lean", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",")],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- schemas ---
class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ExportRequest(BaseModel):
    markdown: str
    title: str | None = None
    format: str = "pdf"  # "pdf" | "docx"


class CompileRequest(BaseModel):
    format: str = "pdf"  # "pdf" | "docx"


class ProjectCreate(BaseModel):
    name: str


class ProjectUpdate(BaseModel):
    name: str | None = None
    brief: str | None = None
    sources: list[str] | None = None


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationUpdate(BaseModel):
    title: str


def _check_auth(x_api_key: str | None) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="invalid api key")


def _derive_title(message: str) -> str:
    t = " ".join(message.strip().split())
    return (t[:48].rstrip() + "…") if len(t) > 48 else t


def _build_prompt(project: dict | None, history: list[dict], message: str) -> str:
    """Compose the agent prompt with project brief + recent history (continuity)."""
    parts: list[str] = []
    if project and project.get("brief"):
        parts.append("PROJECT BRIEF (the paper you are helping with):\n" + project["brief"])
    if history:
        convo = "\n".join(f"{m['role']}: {m['content'][:600]}" for m in history)
        parts.append("CONVERSATION SO FAR:\n" + convo)
    parts.append("CURRENT REQUEST:\n" + message)
    return "\n\n".join(parts)


@app.get("/sources")
async def list_sources(x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    out = []
    for s in AVAILABLE_SOURCES:
        req = s.get("requires")
        available = True if not req else bool(getattr(settings, req, None))
        out.append(
            {"key": s["key"], "label": s["label"], "free": s.get("free", False), "available": available}
        )
    return {"sources": out}


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "region": settings.aws_region,
        "supervisor_model": settings.model_supervisor,
        "draft_model": settings.model_draft,
        "scopus": bool(settings.scopus_api_key),
    }


# --- projects ---
@app.get("/projects")
async def list_projects(x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    return {"projects": store.list_projects()}


@app.post("/projects")
async def create_project(req: ProjectCreate, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    name = req.name.strip() or "Untitled project"
    return store.create_project(name)


@app.get("/projects/{pid}")
async def get_project(pid: str, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    project = store.get_project(pid)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@app.patch("/projects/{pid}")
async def update_project(pid: str, req: ProjectUpdate, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    if not store.get_project(pid):
        raise HTTPException(status_code=404, detail="project not found")
    if req.name is not None:
        store.rename_project(pid, req.name.strip() or "Untitled project")
    if req.brief is not None:
        store.update_brief(pid, req.brief)
    if req.sources is not None:
        store.update_sources(pid, req.sources)
    return store.get_project(pid)


@app.delete("/projects/{pid}")
async def delete_project(pid: str, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    store.delete_project(pid)
    return {"ok": True}


# --- project files (per-project workspace the Analyst reads/writes) ---
_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}


def _project_or_404(pid: str) -> dict:
    project = store.get_project(pid)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    return project


def _safe_file(pid: str, name: str) -> Path:
    """Resolve a workspace file path, rejecting any path traversal."""
    ws = workspace_for(pid).resolve()
    target = (ws / Path(name).name).resolve()
    if target != ws and ws not in target.parents:
        raise HTTPException(status_code=400, detail="invalid filename")
    return target


def _file_info(p: Path) -> dict:
    st = p.stat()
    return {
        "name": p.name,
        "size": st.st_size,
        "modified": st.st_mtime,
        "kind": "image" if p.suffix.lower() in _IMAGE_EXT else "file",
    }


@app.get("/projects/{pid}/files")
async def list_files(pid: str, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    _project_or_404(pid)
    ws = workspace_for(pid)
    files = (
        sorted((_file_info(p) for p in ws.iterdir() if p.is_file()), key=lambda f: f["name"])
        if ws.exists()
        else []
    )
    return {"files": files}


@app.post("/projects/{pid}/files")
async def upload_files(
    pid: str,
    files: list[UploadFile] = File(...),
    x_api_key: str | None = Header(default=None),
):
    _check_auth(x_api_key)
    _project_or_404(pid)
    ws = workspace_for(pid)
    ws.mkdir(parents=True, exist_ok=True)
    saved: list[dict] = []
    for uf in files:
        name = Path(uf.filename or "").name
        if not name:
            continue
        dest = _safe_file(pid, name)
        dest.write_bytes(await uf.read())
        saved.append(_file_info(dest))
    store.touch_project(pid)
    return {"files": saved}


@app.get("/projects/{pid}/files/{name}")
async def get_file(pid: str, name: str, x_api_key: str | None = Header(default=None)):
    # No auth gate: images load via <img src> which can't send headers. Files are
    # scoped to the project workspace and contain only user/agent project data.
    target = _safe_file(pid, name)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    media = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return FileResponse(target, media_type=media)


@app.delete("/projects/{pid}/files/{name}")
async def delete_file(pid: str, name: str, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    target = _safe_file(pid, name)
    if target.is_file():
        target.unlink()
    return {"ok": True}


@app.get("/projects/{pid}/conversations")
async def list_conversations(pid: str, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    return {"conversations": store.list_conversations(pid)}


@app.post("/projects/{pid}/conversations")
async def create_conversation(
    pid: str, req: ConversationCreate, x_api_key: str | None = Header(default=None)
):
    _check_auth(x_api_key)
    if not store.get_project(pid):
        raise HTTPException(status_code=404, detail="project not found")
    return store.create_conversation(pid, (req.title or "New conversation").strip())


@app.get("/projects/{pid}/library")
async def get_library(pid: str, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    return {"sources": store.get_library(pid)}


@app.get("/conversations/{cid}")
async def get_conversation(cid: str, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    conv = store.get_conversation(cid)
    if not conv:
        raise HTTPException(status_code=404, detail="conversation not found")
    return {**conv, "messages": store.get_messages(cid, limit=200)}


@app.patch("/conversations/{cid}")
async def rename_conversation(
    cid: str, req: ConversationUpdate, x_api_key: str | None = Header(default=None)
):
    _check_auth(x_api_key)
    if not store.get_conversation(cid):
        raise HTTPException(status_code=404, detail="conversation not found")
    store.rename_conversation(cid, req.title.strip() or "New conversation")
    return store.get_conversation(cid)


@app.delete("/conversations/{cid}")
async def delete_conversation(cid: str, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    store.delete_conversation(cid)
    return {"ok": True}


# --- chat ---
@app.post("/chat/stream")
async def chat_stream(req: ChatRequest, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    conv = store.get_conversation(req.conversation_id) if req.conversation_id else None
    if conv is None:
        # Bootstrap a default project + conversation if the client didn't pick one.
        project = store.create_project("Default project")
        conv = store.create_conversation(project["id"], "New conversation")
    else:
        project = store.get_project(conv["project_id"])

    set_active_sources(project.get("sources") or ["openalex"])
    set_workspace(workspace_for(project["id"]))  # Analyst reads/writes this project's files
    history = store.get_messages(conv["id"], limit=settings.history_limit)
    # Auto-title the conversation from its first message.
    title = conv.get("title")
    if (title in (None, "", "New conversation")) and not history:
        derived = _derive_title(req.message)
        if derived:
            store.rename_conversation(conv["id"], derived)
            title = derived
    store.add_message(conv["id"], "user", req.message)
    prompt = _build_prompt(project, history, req.message)
    agent = build_supervisor()
    cid, pid = conv["id"], project["id"]

    async def gen():
        yield "event: conversation\ndata: " + json.dumps(
            {"conversation_id": cid, "project_id": pid, "title": title}
        ) + "\n\n"
        sink: dict = {}
        async for frame in run_agent_sse(agent, prompt, sink, artifact_base=f"/projects/{pid}/files"):
            yield frame
        if sink.get("text"):
            store.add_message(cid, "assistant", sink["text"])
        if sink.get("citations"):
            verified = [c for c in sink["citations"] if c.get("verified")]
            if verified:
                store.add_library(pid, verified)
        store.touch_project(pid)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/export")
async def export_doc(req: ExportRequest, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    if req.format == "docx":
        data = build_docx(req.markdown, req.title)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = "mentis-whitepaper.docx"
    else:
        data = build_pdf(req.markdown, req.title)
        media = "application/pdf"
        filename = "mentis-whitepaper.pdf"
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/projects/{pid}/compile")
async def compile_project(pid: str, req: CompileRequest, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    project = store.get_project(pid)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    paper_md = await asyncio.to_thread(
        compile_whitepaper,
        project.get("brief", ""),
        store.get_project_drafts(pid),
        store.get_library(pid),
    )
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", project["name"])[:60] or "whitepaper"
    if req.format == "docx":
        data = build_docx(paper_md, project["name"])
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"{safe}.docx"
    else:
        data = build_pdf(paper_md, project["name"])
        media = "application/pdf"
        filename = f"{safe}.pdf"
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
