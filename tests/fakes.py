"""In-memory fakes implementing the ports — let the suite run without AWS."""
from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Optional

from mentis.domain.models import (
    Chunk,
    Conversation,
    Document,
    Message,
    Paper,
    Project,
    new_id,
)
from mentis.domain.ports.code_exec import CodeResult
from mentis.domain.ports.llm import LLMResponse, ToolSpec
from mentis.domain.ports.vector_store import VectorMatch, VectorRecord

_TOKEN = re.compile(r"[a-z]{2,}")
_DIM = 64


def fake_embed(text: str) -> list[float]:
    """Deterministic bag-of-tokens embedding: cosine reflects token overlap."""
    vec = [0.0] * _DIM
    for tok in _TOKEN.findall(text.lower()):
        bucket = int(hashlib.md5(tok.encode()).hexdigest(), 16) % _DIM
        vec[bucket] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class FakeEmbedding:
    dimension = _DIM

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [fake_embed(t) for t in texts]


class FakeVectorStore:
    def __init__(self) -> None:
        self.data: dict[str, dict[str, VectorRecord]] = {}

    async def upsert(self, index: str, records: list[VectorRecord]) -> None:
        bucket = self.data.setdefault(index, {})
        for r in records:
            bucket[r.key] = r

    async def query(self, index, vector, *, top_k=8, filter=None) -> list[VectorMatch]:
        bucket = self.data.get(index, {})
        scored = []
        for r in bucket.values():
            sim = sum(a * b for a, b in zip(vector, r.vector))
            scored.append(VectorMatch(key=r.key, score=sim, metadata=r.metadata))
        scored.sort(key=lambda m: m.score, reverse=True)
        return scored[:top_k]

    async def delete(self, index, keys) -> None:
        bucket = self.data.get(index, {})
        for k in keys:
            bucket.pop(k, None)


class FakeLLM:
    """Returns canned responses keyed off distinctive system-prompt substrings."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def chat(self, messages, *, system=None, model=None, temperature=0.2, max_tokens=1024, tools=None, cache_system=False):
        self.calls.append({"system": system, "model": model})
        sys = system or ""
        if "classify" in sys:
            return LLMResponse(text='{"intent": "research_query", "confidence": 0.9}')
        if "fact-checker" in sys:
            return LLMResponse(text='{"supported": true, "issues": [], "feedback": ""}')
        if "investigator" in sys:
            return LLMResponse(text="Themes: CO2 absorption. Findings: high COP [1]. Gaps: none.")
        if "writing assistant" in sys:
            return LLMResponse(text="CO2 with biobased absorbents shows promising COP [1].")
        if "computation assistant" in sys:
            return LLMResponse(text="The COP is 3.5.")
        return LLMResponse(text="ok")


class FakeCodeExec:
    async def run_python(self, code: str, *, timeout: int = 15) -> CodeResult:
        return CodeResult(stdout="3.5\n", stderr="", ok=True)


class FakeQueue:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, body: dict[str, Any]) -> None:
        self.sent.append(body)

    async def send_batch(self, bodies: list[dict[str, Any]]) -> None:
        self.sent.extend(bodies)


class InMemoryStore:
    """Minimal DocStorePort implementation backed by dicts."""

    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}
        self.conversations: dict[str, Conversation] = {}
        self.messages: dict[str, list[Message]] = {}
        self.papers: dict[str, dict[str, Paper]] = {}
        self.documents: dict[str, Document] = {}
        self.chunks: dict[str, Chunk] = {}
        self.memory: list[tuple] = []
        self.memory_keys: set[tuple] = set()

    async def get_or_create_project(self, name: str) -> Project:
        for p in self.projects.values():
            if p.name == name:
                return p
        p = Project(id=new_id(), name=name)
        self.projects[p.id] = p
        return p

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        return self.conversations.get(conversation_id)

    async def create_conversation(self, project_id: str) -> Conversation:
        c = Conversation(id=new_id(), project_id=project_id)
        self.conversations[c.id] = c
        self.messages[c.id] = []
        return c

    async def add_message(self, conversation_id: str, message: Message) -> None:
        self.messages.setdefault(conversation_id, []).append(message)

    async def get_messages(self, conversation_id: str, *, limit: int = 20) -> list[Message]:
        return self.messages.get(conversation_id, [])[-limit:]

    async def upsert_paper(self, project_id: str, paper: Paper) -> bool:
        bucket = self.papers.setdefault(project_id, {})
        if paper.dedup_key() in bucket:
            return False
        bucket[paper.dedup_key()] = paper
        return True

    async def paper_exists(self, project_id: str, dedup_key: str) -> bool:
        return dedup_key in self.papers.get(project_id, {})

    async def search_papers(self, project_id: str, query: str, *, limit: int = 25) -> list[Paper]:
        return list(self.papers.get(project_id, {}).values())[:limit]

    async def upsert_document(self, document: Document) -> None:
        self.documents[document.id] = document

    async def get_document(self, document_id: str) -> Optional[Document]:
        return self.documents.get(document_id)

    async def list_documents(self, *, limit: int = 100) -> list[Document]:
        return list(self.documents.values())[:limit]

    async def add_chunks(self, chunks: list[Chunk]) -> None:
        for c in chunks:
            self.chunks[c.id] = c

    async def get_chunk(self, document_id: str, chunk_id: str) -> Optional[Chunk]:
        return self.chunks.get(chunk_id)

    async def add_memory(self, project_id, agent, key, content) -> None:
        self.memory.append((project_id, agent, content))
        if key:
            self.memory_keys.add((project_id, agent, key))

    async def recent_memory(self, project_id, agent, *, limit=5) -> list[str]:
        return [c for p, a, c in self.memory if p == project_id and a == agent][-limit:]

    async def memory_key_exists(self, project_id, agent, key) -> bool:
        return (project_id, agent, key) in self.memory_keys
