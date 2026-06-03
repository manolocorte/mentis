"""PDF ingestion pipeline: extract -> chunk -> embed -> index.

Triggered from the SQS worker. Chunk vectors (with text + provenance metadata)
go to S3 Vectors; document/chunk records go to DynamoDB.
"""
from __future__ import annotations

import hashlib
import io
import logging

from mentis.application.chunking import split_into_chunks
from mentis.config import Settings
from mentis.domain.models import Chunk, Document
from mentis.domain.ports.doc_store import DocStorePort
from mentis.domain.ports.embedding import EmbeddingPort
from mentis.domain.ports.object_store import ObjectStorePort
from mentis.domain.ports.vector_store import VectorRecord, VectorStorePort

logger = logging.getLogger(__name__)
EMBED_BATCH = 32


def extract_pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:  # corrupt / image-only PDF
        logger.warning("PDF extraction failed: %s", exc)
        return ""


async def ingest_document(
    *,
    s3_key: str,
    title: str,
    doi: str | None,
    settings: Settings,
    store: DocStorePort,
    objects: ObjectStorePort,
    embedding: EmbeddingPort,
    vectors: VectorStorePort,
) -> dict:
    data = await objects.get_bytes(s3_key)
    checksum = hashlib.sha256(data).hexdigest()
    text = extract_pdf_text(data)

    document = Document(
        title=title, source_type="pdf", s3_key=s3_key, doi=doi, checksum=checksum, status="processing"
    )
    if not text.strip():
        document.status = "failed"
        await store.upsert_document(document)
        return {"document_id": document.id, "chunks": 0, "status": "failed"}

    pieces = split_into_chunks(text)
    chunks = [Chunk(document_id=document.id, position=i, text=t) for i, t in enumerate(pieces)]

    # Embed + index in batches.
    for start in range(0, len(chunks), EMBED_BATCH):
        batch = chunks[start : start + EMBED_BATCH]
        vecs = await embedding.embed_texts([c.text for c in batch])
        records = [
            VectorRecord(
                key=c.id,
                vector=v,
                metadata={
                    "text": c.text[:2048],
                    "document_id": c.document_id,
                    "doi": doi or "",
                    "title": title,
                    "position": c.position,
                },
            )
            for c, v in zip(batch, vecs)
        ]
        await vectors.upsert(settings.vector_index_chunks, records)

    await store.add_chunks(chunks)
    document.chunk_count = len(chunks)
    document.status = "processed"
    await store.upsert_document(document)
    return {"document_id": document.id, "chunks": len(chunks), "status": "processed"}
