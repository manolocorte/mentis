"""Tools exposed to tool-using agents via the Bedrock Converse tool loop.

The dispatcher binds tools to the request's ports/context and records every
retrieved chunk so the supervisor can build citations afterwards.
"""
from __future__ import annotations

import json
import logging

from mentis.application.rag import hybrid_retrieve
from mentis.config import Settings
from mentis.domain.models import RetrievedChunk
from mentis.domain.ports.code_exec import CodeExecPort
from mentis.domain.ports.embedding import EmbeddingPort
from mentis.domain.ports.llm import ToolSpec, ToolUse
from mentis.domain.ports.vector_store import VectorStorePort

logger = logging.getLogger(__name__)

RETRIEVE_TOOL = ToolSpec(
    name="retrieve_corpus",
    description=(
        "Search the ingested research corpus (papers on absorption refrigeration, "
        "CO2 refrigerants, biobased solvents) for passages relevant to a question. "
        "Returns numbered chunks with their source DOI/title. Call this whenever you "
        "need evidence to ground a claim."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Focused search query"},
            "top_k": {"type": "integer", "description": "How many chunks (default 8)"},
        },
        "required": ["query"],
    },
)

CODE_TOOL = ToolSpec(
    name="run_python",
    description=(
        "Execute a short Python 3 snippet for thermodynamic / refrigeration-cycle "
        "calculations and return its stdout. Use print() to emit results. No network."
    ),
    input_schema={
        "type": "object",
        "properties": {"code": {"type": "string", "description": "Python source to run"}},
        "required": ["code"],
    },
)


class ToolDispatcher:
    def __init__(
        self,
        *,
        settings: Settings,
        embedding: EmbeddingPort,
        vectors: VectorStorePort,
        code_exec: CodeExecPort,
    ):
        self._settings = settings
        self._embedding = embedding
        self._vectors = vectors
        self._code_exec = code_exec
        # chunk_id -> RetrievedChunk, accumulated across all retrieve calls.
        self.retrieved: dict[str, RetrievedChunk] = {}

    async def dispatch(self, tool_use: ToolUse) -> str:
        if tool_use.name == "retrieve_corpus":
            return await self._retrieve(tool_use.input)
        if tool_use.name == "run_python":
            return await self._run_python(tool_use.input)
        return f"Unknown tool: {tool_use.name}"

    async def _retrieve(self, args: dict) -> str:
        query = args.get("query", "")
        top_k = int(args.get("top_k") or self._settings.retrieve_top_k)
        chunks = await hybrid_retrieve(
            query=query,
            embedding=self._embedding,
            vectors=self._vectors,
            index=self._settings.vector_index_chunks,
            top_k=top_k,
        )
        for c in chunks:
            self.retrieved[c.chunk_id] = c
        if not chunks:
            return "No relevant passages found in the corpus."
        return json.dumps(
            [
                {
                    "chunk_id": c.chunk_id,
                    "title": c.title,
                    "doi": c.doi,
                    "text": c.text[:1200],
                }
                for c in chunks
            ]
        )

    async def _run_python(self, args: dict) -> str:
        result = await self._code_exec.run_python(args.get("code", ""))
        if result.ok:
            return f"stdout:\n{result.stdout}"
        return f"ERROR:\n{result.stderr}\nstdout:\n{result.stdout}"
