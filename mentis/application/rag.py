"""Hybrid retrieval: semantic (S3 Vectors) fused with lexical reranking via
Reciprocal Rank Fusion (RRF). Chunk text + metadata travel inside the vector
record, so a match is self-contained (no second store lookup needed).
"""
from __future__ import annotations

import re

from mentis.domain.models import RetrievedChunk
from mentis.domain.ports.embedding import EmbeddingPort
from mentis.domain.ports.vector_store import VectorStorePort

RRF_K = 60
_TOKEN_RE = re.compile(r"[a-zA-Z]{3,}")


async def hybrid_retrieve(
    *,
    query: str,
    embedding: EmbeddingPort,
    vectors: VectorStorePort,
    index: str,
    top_k: int = 8,
    lex_weight: float = 0.3,
) -> list[RetrievedChunk]:
    query = query.strip()
    if not query:
        return []

    [qvec] = await embedding.embed_texts([query])
    candidates = await vectors.query(index, qvec, top_k=top_k * 3)
    if not candidates:
        return []

    # Vector ranking (already sorted by similarity).
    vec_rank = {m.key: rank for rank, m in enumerate(candidates, start=1)}

    # Lexical ranking over candidate text.
    tokens = set(_TOKEN_RE.findall(query.lower()))
    lex_scored = []
    for m in candidates:
        text = (m.metadata.get("text") or "").lower()
        hits = sum(text.count(t) for t in tokens) if tokens else 0
        if hits:
            lex_scored.append((m.key, hits))
    lex_scored.sort(key=lambda x: x[1], reverse=True)
    lex_rank = {key: rank for rank, (key, _) in enumerate(lex_scored, start=1)}

    by_key = {m.key: m for m in candidates}
    fused = []
    for key, m in by_key.items():
        vr = vec_rank.get(key)
        lr = lex_rank.get(key)
        score = 0.0
        if vr:
            score += (1 - lex_weight) * (1.0 / (RRF_K + vr))
        if lr:
            score += lex_weight * (1.0 / (RRF_K + lr))
        fused.append((score, m))

    fused.sort(key=lambda x: x[0], reverse=True)
    out: list[RetrievedChunk] = []
    for score, m in fused[:top_k]:
        md = m.metadata
        out.append(
            RetrievedChunk(
                chunk_id=m.key,
                text=md.get("text", ""),
                score=score,
                doi=md.get("doi"),
                title=md.get("title"),
                document_id=md.get("document_id"),
            )
        )
    return out
