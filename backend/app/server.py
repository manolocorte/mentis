"""FastAPI app — SSE streaming chat over the Strands supervisor.

Run locally:  uvicorn app.server:app --reload --port 8080   (from the backend/ dir)
Lift to AgentCore later: swap FastAPI for BedrockAgentCoreApp + @app.entrypoint (~10 lines).
"""
from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .agents import build_supervisor
from .config import get_settings
from .export import build_pdf
from .store import get_store
from .streaming import run_agent_sse

settings = get_settings()
store = get_store()

app = FastAPI(title="Mentis-lean", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",")],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ExportRequest(BaseModel):
    markdown: str
    title: str | None = None


def _check_auth(x_api_key: str | None) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="invalid api key")


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "region": settings.aws_region,
        "supervisor_model": settings.model_supervisor,
        "draft_model": settings.model_draft,
        "scopus": bool(settings.scopus_api_key),
    }


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    conversation_id = req.conversation_id or store.new_conversation()
    store.append(conversation_id, "user", req.message)
    agent = build_supervisor()

    async def gen():
        # Tell the client its conversation id up front.
        yield f'event: conversation\ndata: {{"conversation_id": "{conversation_id}"}}\n\n'
        sink: dict = {}
        async for frame in run_agent_sse(agent, req.message, sink):
            yield frame
        if sink.get("text"):
            store.append(conversation_id, "assistant", sink["text"])

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/export/pdf")
async def export_pdf(req: ExportRequest, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    pdf = build_pdf(req.markdown, req.title)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="mentis-whitepaper.pdf"'},
    )
