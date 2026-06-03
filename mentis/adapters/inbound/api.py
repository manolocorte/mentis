"""FastAPI inbound adapter, wrapped by Mangum for Lambda + API Gateway (HTTP API).

Run locally:  uvicorn mentis.adapters.inbound.api:app --reload
Lambda handler: mentis.adapters.inbound.api.handler
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Header, HTTPException
from mangum import Mangum
from pydantic import BaseModel

from mentis.application.container import Container
from mentis.application.harvest import harvest

logger = logging.getLogger(__name__)

app = FastAPI(title="Mentis", version="0.2.0")
_container = Container()


def _check_auth(x_api_key: str | None) -> None:
    expected = _container.settings.api_key
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="invalid api key")


# --- schemas ---
class ChatRequest(BaseModel):
    query: str
    project: str = "default"
    conversation_id: str | None = None


class HarvestRequest(BaseModel):
    query: str
    project: str = "default"
    max_results: int = 25


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(req: ChatRequest, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    result = await _container.supervisor().handle(
        req.query, project_name=req.project, conversation_id=req.conversation_id
    )
    return {
        "conversation_id": result.conversation_id,
        "answer": result.answer,
        "intent": result.intent,
        "confidence": result.confidence,
        "citations": [
            {"chunk_id": c.chunk_id, "doi": c.doi, "title": c.title, "snippet": c.snippet}
            for c in result.citations
        ],
        "trace": [{"agent": s.agent, "summary": s.summary} for s in result.trace],
    }


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    messages = await _container.store.get_messages(conversation_id, limit=100)
    return {
        "id": conversation_id,
        "messages": [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages],
    }


@app.get("/papers")
async def papers(query: str = "", project: str = "default", x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    proj = await _container.store.get_or_create_project(project)
    found = await _container.store.search_papers(proj.id, query)
    return {
        "papers": [
            {
                "id": p.id,
                "title": p.title,
                "authors": [a.name for a in p.authors],
                "year": p.year,
                "venue": p.venue,
                "doi": p.doi,
                "citation_count": p.citation_count,
                "source": p.source,
            }
            for p in found
        ]
    }


@app.get("/documents")
async def documents(x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    docs = await _container.store.list_documents()
    return {
        "documents": [
            {
                "id": d.id,
                "title": d.title,
                "status": d.status,
                "chunk_count": d.chunk_count,
                "created_at": d.created_at,
            }
            for d in docs
        ]
    }


@app.post("/harvest")
async def trigger_harvest(req: HarvestRequest, x_api_key: str | None = Header(default=None)):
    _check_auth(x_api_key)
    proj = await _container.store.get_or_create_project(req.project)
    summary = await harvest(
        query=req.query,
        project_id=proj.id,
        sources=_container.sources,
        unpaywall=_container.unpaywall,
        store=_container.store,
        queue=_container.queue,
        max_results=req.max_results,
    )
    return {
        "enqueued": summary["enqueued"],
        "message": f"Found {summary['found']} results, {summary['new_papers']} new papers, "
        f"{summary['enqueued']} PDFs queued for ingestion.",
    }


handler = Mangum(app, lifespan="off")
