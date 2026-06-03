"""SQS worker Lambda — fetches OA PDFs and runs the ingestion pipeline.

Handler: mentis.adapters.inbound.worker.handler
Reports partial batch failures so only failed messages are retried/DLQ'd.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging

import httpx

from mentis.application.container import Container
from mentis.application.ingestion import ingest_document

logger = logging.getLogger(__name__)
_container = Container()


async def _process(body: dict) -> None:
    task = body.get("task")
    if task == "fetch_and_ingest":
        await _fetch_and_ingest(body)
    elif task == "ingest_s3":
        await ingest_document(
            s3_key=body["s3_key"],
            title=body.get("title", body["s3_key"]),
            doi=body.get("doi"),
            settings=_container.settings,
            store=_container.store,
            objects=_container.objects,
            embedding=_container.embedding,
            vectors=_container.vectors,
        )
    else:
        logger.warning("unknown task: %s", task)


async def _fetch_and_ingest(body: dict) -> None:
    url = body["url"]
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as http:
        resp = await http.get(url, headers={"User-Agent": "Mentis-Research-Assistant/0.2"})
        resp.raise_for_status()
        data = resp.content
    key = f"documents/{hashlib.sha256(url.encode()).hexdigest()[:24]}.pdf"
    await _container.objects.put_bytes(key, data, content_type="application/pdf")
    await ingest_document(
        s3_key=key,
        title=body.get("title", key),
        doi=body.get("doi"),
        settings=_container.settings,
        store=_container.store,
        objects=_container.objects,
        embedding=_container.embedding,
        vectors=_container.vectors,
    )


async def _process_all(records: list[dict]) -> list[dict]:
    failures: list[dict] = []
    for record in records:
        try:
            await _process(json.loads(record.get("body", "{}")))
        except Exception as exc:
            logger.exception("message %s failed: %s", record.get("messageId"), exc)
            failures.append({"itemIdentifier": record.get("messageId")})
    return failures


def handler(event, context):
    records = event.get("Records", [])
    logger.info("worker received %d records", len(records))
    failures = asyncio.run(_process_all(records))
    return {"batchItemFailures": failures}
