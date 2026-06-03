"""S3 object storage implementing ObjectStorePort."""
from __future__ import annotations

import asyncio

import boto3
from botocore.exceptions import ClientError

from mentis.domain.ports.object_store import ObjectStorePort


class S3ObjectStore(ObjectStorePort):
    def __init__(self, region: str, bucket: str):
        self._bucket = bucket
        self._client = boto3.client("s3", region_name=region)

    async def put_bytes(self, key: str, data: bytes, *, content_type: str = "application/octet-stream") -> str:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    async def get_bytes(self, key: str) -> bytes:
        def _get() -> bytes:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
            return resp["Body"].read()

        return await asyncio.to_thread(_get)

    async def exists(self, key: str) -> bool:
        def _head() -> bool:
            try:
                self._client.head_object(Bucket=self._bucket, Key=key)
                return True
            except ClientError:
                return False

        return await asyncio.to_thread(_head)

    def presigned_put_url(self, key: str, *, expires: int = 3600, content_type: str = "application/pdf") -> str:
        return self._client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires,
        )
