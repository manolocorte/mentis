"""Composition root — builds adapters from settings and wires the supervisor.

Lazily constructed and cached so a warm Lambda reuses boto3 clients across
invocations.
"""
from __future__ import annotations

import logging
from functools import cached_property
from typing import Any

from mentis.adapters.outbound.bedrock_embedding import BedrockEmbedding
from mentis.adapters.outbound.bedrock_llm import BedrockLLM
from mentis.adapters.outbound.dynamo_store import DynamoStore
from mentis.adapters.outbound.local_code_exec import LocalCodeExec
from mentis.adapters.outbound.s3_object_store import S3ObjectStore
from mentis.adapters.outbound.s3_vectors import S3VectorsStore
from mentis.adapters.outbound.sources.registry import build_sources, build_unpaywall
from mentis.adapters.outbound.sqs_queue import SQSQueue
from mentis.application.agents.supervisor import Supervisor
from mentis.config import Settings, get_settings

logger = logging.getLogger(__name__)


class NullQueue:
    """Used in local dev when no SQS queue is configured."""

    async def send(self, body: dict[str, Any]) -> None:
        logger.info("[NullQueue] send %s", body.get("task"))

    async def send_batch(self, bodies: list[dict[str, Any]]) -> None:
        logger.info("[NullQueue] send_batch %d messages", len(bodies))


class Container:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    @cached_property
    def llm(self) -> BedrockLLM:
        return BedrockLLM(self.settings.bedrock_region, self.settings.bedrock_chat_model)

    @cached_property
    def embedding(self) -> BedrockEmbedding:
        return BedrockEmbedding(
            self.settings.bedrock_region, self.settings.bedrock_embed_model, self.settings.bedrock_embed_dim
        )

    @cached_property
    def vectors(self) -> S3VectorsStore:
        return S3VectorsStore(self.settings.aws_region_name, self.settings.vector_bucket)

    @cached_property
    def objects(self) -> S3ObjectStore:
        return S3ObjectStore(self.settings.aws_region_name, self.settings.documents_bucket)

    @cached_property
    def store(self) -> DynamoStore:
        return DynamoStore(self.settings.aws_region_name, self.settings.table_name)

    @cached_property
    def queue(self):
        if self.settings.ingest_queue_url:
            return SQSQueue(self.settings.aws_region_name, self.settings.ingest_queue_url)
        return NullQueue()

    @cached_property
    def code_exec(self) -> LocalCodeExec:
        return LocalCodeExec()

    @cached_property
    def sources(self):
        return build_sources(self.settings)

    @cached_property
    def unpaywall(self):
        return build_unpaywall(self.settings)

    def supervisor(self) -> Supervisor:
        return Supervisor(
            settings=self.settings,
            llm=self.llm,
            embedding=self.embedding,
            vectors=self.vectors,
            code_exec=self.code_exec,
            store=self.store,
        )
