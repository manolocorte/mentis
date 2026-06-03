"""Supervisor — orchestrates the multi-agent RAG pipeline.

Flow (research/review/draft/fact_check intents):
    router -> retrieve -> investigate -> synthesize -> [fact-check -> revise]*

The fact-checker drives a bounded reflexion loop: if it finds unsupported claims
and iterations remain, the synthesizer revises with that feedback. `code_execution`
routes to the coder agent instead.
"""
from __future__ import annotations

import logging
import re

from mentis.application.agents import coder, factchecker, investigator, router, synthesizer
from mentis.application.rag import hybrid_retrieve
from mentis.application.tools import ToolDispatcher
from mentis.config import Settings
from mentis.domain.models import (
    AgentStep,
    AnswerResult,
    Citation,
    Message,
    RetrievedChunk,
)
from mentis.domain.ports.code_exec import CodeExecPort
from mentis.domain.ports.doc_store import DocStorePort
from mentis.domain.ports.embedding import EmbeddingPort
from mentis.domain.ports.llm import LLMPort
from mentis.domain.ports.vector_store import VectorStorePort

logger = logging.getLogger(__name__)
_CITE_RE = re.compile(r"\[(\d{1,2})\]")


class Supervisor:
    def __init__(
        self,
        *,
        settings: Settings,
        llm: LLMPort,
        embedding: EmbeddingPort,
        vectors: VectorStorePort,
        code_exec: CodeExecPort,
        store: DocStorePort,
    ):
        self.s = settings
        self.llm = llm
        self.embedding = embedding
        self.vectors = vectors
        self.code_exec = code_exec
        self.store = store

    async def handle(self, query: str, *, project_name: str = "default", conversation_id: str | None = None) -> AnswerResult:
        project = await self.store.get_or_create_project(project_name)
        conversation = None
        if conversation_id:
            conversation = await self.store.get_conversation(conversation_id)
        if conversation is None:
            conversation = await self.store.create_conversation(project.id)

        await self.store.add_message(conversation.id, Message(role="user", content=query))
        history = await self.store.get_messages(conversation.id, limit=8)
        history_dicts = [{"role": m.role, "content": m.content} for m in history[:-1]]

        intent = await router.classify(self.llm, query, history_dicts)
        trace = [AgentStep(agent="router", summary=f"intent={intent.intent} confidence={intent.confidence:.2f}")]

        dispatcher = ToolDispatcher(
            settings=self.s, embedding=self.embedding, vectors=self.vectors, code_exec=self.code_exec
        )

        if intent.intent == "code_execution":
            answer = await coder.run_code_agent(
                self.llm, query=query, dispatcher=dispatcher, model=self.s.bedrock_chat_model
            )
            trace.append(AgentStep(agent="coder", summary="ran calculation via run_python"))
            citations: list[Citation] = []
        else:
            answer, citations, steps = await self._research(query, project.id, intent.intent, history_dicts, dispatcher)
            trace.extend(steps)

        await self.store.add_message(conversation.id, Message(role="assistant", content=answer))
        return AnswerResult(
            conversation_id=conversation.id,
            answer=answer,
            intent=intent.intent,
            confidence=intent.confidence,
            citations=citations,
            trace=trace,
        )

    async def _research(self, query, project_id, intent, history_dicts, dispatcher):
        steps: list[AgentStep] = []

        chunks = await hybrid_retrieve(
            query=query,
            embedding=self.embedding,
            vectors=self.vectors,
            index=self.s.vector_index_chunks,
            top_k=self.s.retrieve_top_k,
        )
        for c in chunks:
            dispatcher.retrieved[c.chunk_id] = c
        steps.append(AgentStep(agent="retriever", summary=f"retrieved {len(chunks)} grounding passages"))

        inv = await investigator.investigate(self.llm, query=query, chunks=chunks, model=self.s.bedrock_chat_model)
        steps.append(AgentStep(agent="investigator", summary="extracted themes, findings and gaps"))

        paper_draft = intent == "paper_draft"
        model = self.s.bedrock_draft_model if paper_draft else self.s.bedrock_chat_model
        history_text = "\n".join(f"{m['role']}: {m['content'][:200]}" for m in history_dicts)

        answer = await synthesizer.synthesize(
            self.llm,
            query=query,
            chunks=chunks,
            investigation=inv.notes,
            history_text=history_text,
            dispatcher=dispatcher,
            model=model,
            paper_draft=paper_draft,
        )
        steps.append(AgentStep(agent="synthesizer", summary="drafted grounded answer with citations"))

        # Reflexion loop: verify, then revise on failure.
        for i in range(self.s.max_reflexion_iterations):
            verdict = await factchecker.fact_check(
                self.llm, answer=answer, chunks=chunks, model=self.s.bedrock_chat_model
            )
            if verdict.supported:
                steps.append(AgentStep(agent="factchecker", summary="claims supported by evidence"))
                break
            steps.append(
                AgentStep(agent="factchecker", summary=f"flagged {len(verdict.issues)} issue(s); requesting revision")
            )
            answer = await synthesizer.synthesize(
                self.llm,
                query=query,
                chunks=chunks,
                investigation=inv.notes,
                history_text=history_text,
                dispatcher=dispatcher,
                model=model,
                paper_draft=paper_draft,
                feedback=verdict.feedback or "; ".join(verdict.issues),
            )
            steps.append(AgentStep(agent="synthesizer", summary=f"revised draft (iteration {i + 1})"))

        citations = self._build_citations(answer, chunks)
        return answer, citations, steps

    @staticmethod
    def _build_citations(answer: str, chunks: list[RetrievedChunk]) -> list[Citation]:
        cited_nums = {int(n) for n in _CITE_RE.findall(answer)}
        citations: list[Citation] = []
        for n in sorted(cited_nums):
            if 1 <= n <= len(chunks):
                c = chunks[n - 1]
                citations.append(
                    Citation(chunk_id=c.chunk_id, snippet=c.text[:300], doi=c.doi, title=c.title, score=c.score)
                )
        return citations
