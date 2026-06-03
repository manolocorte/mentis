"""SQS adapter implementing QueuePort."""
from __future__ import annotations

import asyncio
import json
from typing import Any

import boto3


class SQSQueue:
    def __init__(self, region: str, queue_url: str):
        self._queue_url = queue_url
        self._client = boto3.client("sqs", region_name=region)

    async def send(self, body: dict[str, Any]) -> None:
        await asyncio.to_thread(
            self._client.send_message,
            QueueUrl=self._queue_url,
            MessageBody=json.dumps(body),
        )

    async def send_batch(self, bodies: list[dict[str, Any]]) -> None:
        for group in _chunked(bodies, 10):
            entries = [
                {"Id": str(i), "MessageBody": json.dumps(b)} for i, b in enumerate(group)
            ]
            await asyncio.to_thread(
                self._client.send_message_batch,
                QueueUrl=self._queue_url,
                Entries=entries,
            )


def _chunked(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]
