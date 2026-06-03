"""Harvest pipeline: query paper sources, dedupe, resolve OA full text, persist
metadata, and enqueue OA PDFs for ingestion.

Scalable by design: sources are pluggable (`PaperSourcePort`); adding the
university/Scopus source later requires only an API key, no code change here.
"""
from __future__ import annotations

import logging

from mentis.adapters.outbound.sources.unpaywall import Unpaywall
from mentis.domain.models import Paper
from mentis.domain.ports.doc_store import DocStorePort
from mentis.domain.ports.paper_source import PaperSourcePort
from mentis.domain.ports.queue import QueuePort

logger = logging.getLogger(__name__)


async def harvest(
    *,
    query: str,
    project_id: str,
    sources: list[PaperSourcePort],
    unpaywall: Unpaywall,
    store: DocStorePort,
    queue: QueuePort,
    max_results: int = 25,
) -> dict:
    # 1. Gather from every source.
    gathered: list[Paper] = []
    for source in sources:
        try:
            gathered.extend(await source.search(query, max_results=max_results))
        except Exception as exc:
            logger.warning("source %s failed: %s", getattr(source, "name", "?"), exc)

    # 2. Dedupe within this batch.
    seen: dict[str, Paper] = {}
    for paper in gathered:
        key = paper.dedup_key()
        if key not in seen:
            seen[key] = paper

    # 3. Persist new papers + enqueue OA PDFs for ingestion.
    new_papers = 0
    enqueued = 0
    ingest_messages: list[dict] = []
    for paper in seen.values():
        inserted = await store.upsert_paper(project_id, paper)
        if not inserted:
            continue
        new_papers += 1
        # Resolve a legal OA PDF (Unpaywall fills gaps from metadata-only sources).
        await unpaywall.enrich(paper)
        if paper.oa_pdf_url:
            ingest_messages.append(
                {
                    "task": "fetch_and_ingest",
                    "url": paper.oa_pdf_url,
                    "title": paper.title,
                    "doi": paper.doi,
                    "project_id": project_id,
                }
            )

    if ingest_messages:
        await queue.send_batch(ingest_messages)
        enqueued = len(ingest_messages)

    return {
        "found": len(gathered),
        "unique": len(seen),
        "new_papers": new_papers,
        "enqueued": enqueued,
    }
