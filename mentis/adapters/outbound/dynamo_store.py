"""DynamoDB single-table adapter implementing DocStorePort.

Single-table design (table has PK/SK + GSI1 with GSI1PK/GSI1SK):

  Project       PK=PROJECT#{id}      SK=META          GSI1PK=PROJECTNAME   GSI1SK={name}
  Conversation  PK=CONV#{id}         SK=META          GSI1PK=PROJECT#{pid} GSI1SK=CONV#{ts}
  Message       PK=CONV#{id}         SK=MSG#{ts}#{id}
  Paper         PK=PROJECT#{pid}     SK=PAPER#{dedup}
  Document      PK=DOC#{id}          SK=META          GSI1PK=DOCUMENT      GSI1SK={ts}
  Chunk         PK=DOC#{docid}       SK=CHUNK#{id}
  Memory        PK=PROJECT#{pid}     SK=MEM#{agent}#{ts}#{id}
  Memory key    PK=PROJECT#{pid}     SK=MEMKEY#{agent}#{key}
"""
from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any, Optional

import boto3
from boto3.dynamodb.conditions import Key

from mentis.domain.models import (
    Author,
    Chunk,
    Conversation,
    Document,
    Message,
    Paper,
    Project,
    new_id,
    now_iso,
)
from mentis.domain.ports.doc_store import DocStorePort


def _clean(value: Any) -> Any:
    """Recursively convert Decimals to int/float for the domain layer."""
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, list):
        return [_clean(v) for v in value]
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    return value


class DynamoStore(DocStorePort):
    def __init__(self, region: str, table_name: str):
        self._table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    # --- low-level helpers ---
    async def _put(self, item: dict[str, Any]) -> None:
        await asyncio.to_thread(self._table.put_item, Item=item)

    async def _put_unique(self, item: dict[str, Any]) -> bool:
        """Put only if (PK, SK) doesn't already exist. Returns True if inserted."""
        try:
            await asyncio.to_thread(
                self._table.put_item,
                Item=item,
                ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)",
            )
            return True
        except self._table.meta.client.exceptions.ConditionalCheckFailedException:
            return False

    async def _get(self, pk: str, sk: str) -> Optional[dict[str, Any]]:
        resp = await asyncio.to_thread(self._table.get_item, Key={"PK": pk, "SK": sk})
        item = resp.get("Item")
        return _clean(item) if item else None

    async def _query(self, **kwargs) -> list[dict[str, Any]]:
        resp = await asyncio.to_thread(self._table.query, **kwargs)
        return [_clean(i) for i in resp.get("Items", [])]

    # --- projects ---
    async def get_or_create_project(self, name: str) -> Project:
        existing = await self._query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq("PROJECTNAME") & Key("GSI1SK").eq(name),
            Limit=1,
        )
        if existing:
            it = existing[0]
            return Project(id=it["id"], name=it["name"], description=it.get("description"), created_at=it["created_at"])
        project = Project(id=new_id(), name=name)
        await self._put(
            {
                "PK": f"PROJECT#{project.id}",
                "SK": "META",
                "GSI1PK": "PROJECTNAME",
                "GSI1SK": name,
                "type": "project",
                "id": project.id,
                "name": name,
                "created_at": project.created_at,
            }
        )
        return project

    # --- conversations ---
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        it = await self._get(f"CONV#{conversation_id}", "META")
        if not it:
            return None
        return Conversation(id=it["id"], project_id=it["project_id"], created_at=it["created_at"])

    async def create_conversation(self, project_id: str) -> Conversation:
        conv = Conversation(id=new_id(), project_id=project_id)
        await self._put(
            {
                "PK": f"CONV#{conv.id}",
                "SK": "META",
                "GSI1PK": f"PROJECT#{project_id}",
                "GSI1SK": f"CONV#{conv.created_at}",
                "type": "conversation",
                "id": conv.id,
                "project_id": project_id,
                "created_at": conv.created_at,
            }
        )
        return conv

    async def add_message(self, conversation_id: str, message: Message) -> None:
        await self._put(
            {
                "PK": f"CONV#{conversation_id}",
                "SK": f"MSG#{message.created_at}#{message.id}",
                "type": "message",
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
            }
        )

    async def get_messages(self, conversation_id: str, *, limit: int = 20) -> list[Message]:
        items = await self._query(
            KeyConditionExpression=Key("PK").eq(f"CONV#{conversation_id}") & Key("SK").begins_with("MSG#"),
            Limit=limit,
            ScanIndexForward=True,
        )
        return [Message(id=i["id"], role=i["role"], content=i["content"], created_at=i["created_at"]) for i in items]

    # --- papers ---
    async def upsert_paper(self, project_id: str, paper: Paper) -> bool:
        item = {
            "PK": f"PROJECT#{project_id}",
            "SK": f"PAPER#{paper.dedup_key()}",
            "type": "paper",
            "id": paper.id,
            "title": paper.title,
            "doi": paper.doi,
            "authors": [a.name for a in paper.authors],
            "year": paper.year,
            "venue": paper.venue,
            "abstract": paper.abstract,
            "url": paper.url,
            "oa_pdf_url": paper.oa_pdf_url,
            "citation_count": paper.citation_count,
            "source": paper.source,
            "dedup_key": paper.dedup_key(),
            "created_at": now_iso(),
        }
        return await self._put_unique(item)

    async def paper_exists(self, project_id: str, dedup_key: str) -> bool:
        return (await self._get(f"PROJECT#{project_id}", f"PAPER#{dedup_key}")) is not None

    async def search_papers(self, project_id: str, query: str, *, limit: int = 25) -> list[Paper]:
        items = await self._query(
            KeyConditionExpression=Key("PK").eq(f"PROJECT#{project_id}") & Key("SK").begins_with("PAPER#"),
            Limit=200,
        )
        terms = [t for t in query.lower().split() if len(t) > 2]
        scored: list[tuple[int, dict]] = []
        for it in items:
            haystack = f"{it.get('title','')} {it.get('abstract','') or ''} {it.get('venue','') or ''}".lower()
            score = sum(haystack.count(t) for t in terms) if terms else 1
            if score > 0:
                scored.append((score, it))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [self._to_paper(it) for _, it in scored[:limit]]

    @staticmethod
    def _to_paper(it: dict[str, Any]) -> Paper:
        return Paper(
            id=it["id"],
            title=it["title"],
            doi=it.get("doi"),
            authors=[Author(name=n) for n in it.get("authors", [])],
            year=it.get("year"),
            venue=it.get("venue"),
            abstract=it.get("abstract"),
            url=it.get("url"),
            oa_pdf_url=it.get("oa_pdf_url"),
            citation_count=it.get("citation_count"),
            source=it.get("source", "unknown"),
        )

    # --- documents & chunks ---
    async def upsert_document(self, document: Document) -> None:
        await self._put(
            {
                "PK": f"DOC#{document.id}",
                "SK": "META",
                "GSI1PK": "DOCUMENT",
                "GSI1SK": document.created_at,
                "type": "document",
                "id": document.id,
                "title": document.title,
                "source_type": document.source_type,
                "s3_key": document.s3_key,
                "doi": document.doi,
                "checksum": document.checksum,
                "status": document.status,
                "chunk_count": document.chunk_count,
                "created_at": document.created_at,
            }
        )

    async def get_document(self, document_id: str) -> Optional[Document]:
        it = await self._get(f"DOC#{document_id}", "META")
        if not it:
            return None
        return self._to_document(it)

    async def list_documents(self, *, limit: int = 100) -> list[Document]:
        items = await self._query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq("DOCUMENT"),
            Limit=limit,
            ScanIndexForward=False,
        )
        return [self._to_document(i) for i in items]

    @staticmethod
    def _to_document(it: dict[str, Any]) -> Document:
        return Document(
            id=it["id"],
            title=it["title"],
            source_type=it.get("source_type", "pdf"),
            s3_key=it.get("s3_key"),
            doi=it.get("doi"),
            checksum=it.get("checksum"),
            status=it.get("status", "pending"),
            chunk_count=it.get("chunk_count", 0),
            created_at=it["created_at"],
        )

    async def add_chunks(self, chunks: list[Chunk]) -> None:
        def _batch_write():
            with self._table.batch_writer() as batch:
                for c in chunks:
                    batch.put_item(
                        Item={
                            "PK": f"DOC#{c.document_id}",
                            "SK": f"CHUNK#{c.id}",
                            "type": "chunk",
                            "id": c.id,
                            "document_id": c.document_id,
                            "position": c.position,
                            "text": c.text,
                            "metadata": c.metadata,
                        }
                    )

        await asyncio.to_thread(_batch_write)

    async def get_chunk(self, document_id: str, chunk_id: str) -> Optional[Chunk]:
        it = await self._get(f"DOC#{document_id}", f"CHUNK#{chunk_id}")
        if not it:
            return None
        return Chunk(
            id=it["id"],
            document_id=it["document_id"],
            position=it["position"],
            text=it["text"],
            metadata=it.get("metadata", {}),
        )

    # --- agent memory ---
    async def add_memory(self, project_id: str, agent: str, key: Optional[str], content: str) -> None:
        ts = now_iso()
        await self._put(
            {
                "PK": f"PROJECT#{project_id}",
                "SK": f"MEM#{agent}#{ts}#{new_id()}",
                "type": "memory",
                "agent": agent,
                "content": content,
                "created_at": ts,
            }
        )
        if key:
            await self._put(
                {
                    "PK": f"PROJECT#{project_id}",
                    "SK": f"MEMKEY#{agent}#{key}",
                    "type": "memory_key",
                    "agent": agent,
                    "key": key,
                    "created_at": ts,
                }
            )

    async def recent_memory(self, project_id: str, agent: str, *, limit: int = 5) -> list[str]:
        items = await self._query(
            KeyConditionExpression=Key("PK").eq(f"PROJECT#{project_id}") & Key("SK").begins_with(f"MEM#{agent}#"),
            Limit=limit,
            ScanIndexForward=False,
        )
        return [i["content"] for i in items]

    async def memory_key_exists(self, project_id: str, agent: str, key: str) -> bool:
        return (await self._get(f"PROJECT#{project_id}", f"MEMKEY#{agent}#{key}")) is not None
