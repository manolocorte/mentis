"""Scheduled harvester Lambda — pulls new papers from sources and enqueues OA
PDFs for ingestion.

Handler: mentis.adapters.inbound.harvester.handler
Triggered nightly by EventBridge Scheduler; also invokable on demand with a
payload like {"query": "...", "project": "default", "max_results": 25}.
"""
from __future__ import annotations

import asyncio
import logging

from mentis.application.container import Container
from mentis.application.harvest import harvest

logger = logging.getLogger(__name__)
_container = Container()

# Seed query for the project's research domain (absorption refrigeration / CO2).
DEFAULT_QUERY = "absorption refrigeration CO2 biobased solvent working fluid"


async def _run(event: dict) -> dict:
    query = event.get("query", DEFAULT_QUERY)
    project_name = event.get("project", "default")
    max_results = int(event.get("max_results", 25))
    project = await _container.store.get_or_create_project(project_name)
    return await harvest(
        query=query,
        project_id=project.id,
        sources=_container.sources,
        unpaywall=_container.unpaywall,
        store=_container.store,
        queue=_container.queue,
        max_results=max_results,
    )


def handler(event, context):
    event = event or {}
    summary = asyncio.run(_run(event))
    logger.info("harvest summary: %s", summary)
    return summary
