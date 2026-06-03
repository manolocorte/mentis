"""Bedrock Titan embeddings implementing EmbeddingPort."""
from __future__ import annotations

import asyncio
import json

import boto3

from mentis.domain.ports.embedding import EmbeddingPort


class BedrockEmbedding(EmbeddingPort):
    def __init__(self, region: str, model_id: str = "amazon.titan-embed-text-v2:0", dim: int = 1024):
        self._client = boto3.client("bedrock-runtime", region_name=region)
        self._model_id = model_id
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        # Titan embeds one input per invocation; fan out across threads.
        return await asyncio.gather(*(self._embed_one(t) for t in texts))

    async def _embed_one(self, text: str) -> list[float]:
        body = json.dumps({"inputText": text or " ", "dimensions": self._dim, "normalize": True})

        def _call() -> list[float]:
            resp = self._client.invoke_model(modelId=self._model_id, body=body)
            payload = json.loads(resp["body"].read())
            return payload["embedding"]

        return await asyncio.to_thread(_call)
