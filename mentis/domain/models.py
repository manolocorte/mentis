"""Pure domain models (no infrastructure dependencies)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


def new_id() -> str:
    return uuid.uuid4().hex


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Project:
    id: str
    name: str
    description: Optional[str] = None
    created_at: str = field(default_factory=now_iso)


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str
    id: str = field(default_factory=new_id)
    created_at: str = field(default_factory=now_iso)


@dataclass
class Conversation:
    id: str
    project_id: str
    created_at: str = field(default_factory=now_iso)


@dataclass
class Author:
    name: str
    affiliation: Optional[str] = None


@dataclass
class Paper:
    title: str
    id: str = field(default_factory=new_id)
    doi: Optional[str] = None
    authors: list[Author] = field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    abstract: Optional[str] = None
    url: Optional[str] = None
    oa_pdf_url: Optional[str] = None
    citation_count: Optional[int] = None
    source: str = "unknown"
    external_ids: dict[str, str] = field(default_factory=dict)

    def dedup_key(self) -> str:
        if self.doi:
            return f"doi:{self.doi.lower()}"
        return f"title:{self.title.strip().lower()[:120]}"


@dataclass
class Document:
    title: str
    id: str = field(default_factory=new_id)
    source_type: str = "pdf"
    s3_key: Optional[str] = None
    doi: Optional[str] = None
    checksum: Optional[str] = None
    status: str = "pending"  # pending | processing | processed | failed
    chunk_count: int = 0
    created_at: str = field(default_factory=now_iso)


@dataclass
class Chunk:
    document_id: str
    position: int
    text: str
    id: str = field(default_factory=new_id)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Citation:
    chunk_id: str
    snippet: str
    doi: Optional[str] = None
    title: Optional[str] = None
    score: float = 0.0


@dataclass
class AgentStep:
    """A single step in the multi-agent trace, surfaced to the UI."""
    agent: str
    summary: str


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    score: float
    doi: Optional[str] = None
    title: Optional[str] = None
    document_id: Optional[str] = None


@dataclass
class AnswerResult:
    conversation_id: str
    answer: str
    intent: str
    confidence: float
    citations: list[Citation] = field(default_factory=list)
    trace: list[AgentStep] = field(default_factory=list)
