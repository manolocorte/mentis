"""Amazon S3 Vectors adapter implementing VectorStorePort.

S3 Vectors (GA 2026) is a fully serverless, pay-per-use vector store — ~90%
cheaper than OpenSearch Serverless and $0 at idle. Vectors carry metadata
(including the source text) so retrieval returns text without a second lookup.
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

import boto3

from mentis.domain.ports.vector_store import VectorMatch, VectorRecord, VectorStorePort


class S3VectorsStore(VectorStorePort):
    def __init__(self, region: str, bucket: str):
        self._bucket = bucket
        self._client = boto3.client("s3vectors", region_name=region)

    async def upsert(self, index: str, records: list[VectorRecord]) -> None:
        if not records:
            return
        vectors = [
            {
                "key": r.key,
                "data": {"float32": [float(x) for x in r.vector]},
                "metadata": r.metadata,
            }
            for r in records
        ]
        # PutVectors accepts batches; chunk to stay within request limits.
        for batch in _chunked(vectors, 100):
            await asyncio.to_thread(
                self._client.put_vectors,
                vectorBucketName=self._bucket,
                indexName=index,
                vectors=batch,
            )

    async def query(
        self,
        index: str,
        vector: list[float],
        *,
        top_k: int = 8,
        filter: Optional[dict[str, Any]] = None,
    ) -> list[VectorMatch]:
        kwargs: dict[str, Any] = {
            "vectorBucketName": self._bucket,
            "indexName": index,
            "queryVector": {"float32": [float(x) for x in vector]},
            "topK": top_k,
            "returnMetadata": True,
            "returnDistance": True,
        }
        if filter:
            kwargs["filter"] = filter
        resp = await asyncio.to_thread(self._client.query_vectors, **kwargs)
        matches: list[VectorMatch] = []
        for v in resp.get("vectors", []):
            # cosine distance -> similarity
            distance = v.get("distance", 0.0)
            matches.append(
                VectorMatch(
                    key=v["key"],
                    score=max(0.0, 1.0 - float(distance)),
                    metadata=v.get("metadata", {}) or {},
                )
            )
        return matches

    async def delete(self, index: str, keys: list[str]) -> None:
        if not keys:
            return
        for batch in _chunked(keys, 100):
            await asyncio.to_thread(
                self._client.delete_vectors,
                vectorBucketName=self._bucket,
                indexName=index,
                keys=batch,
            )


def _chunked(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]
