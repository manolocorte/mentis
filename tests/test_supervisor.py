import pytest

from mentis.application.agents.supervisor import Supervisor
from mentis.config import Settings
from mentis.domain.ports.vector_store import VectorRecord
from tests.fakes import (
    FakeCodeExec,
    FakeEmbedding,
    FakeLLM,
    FakeVectorStore,
    InMemoryStore,
    fake_embed,
)


def _settings():
    return Settings(max_reflexion_iterations=1, retrieve_top_k=5, vector_index_chunks="chunks")


async def _seeded_vectors():
    vectors = FakeVectorStore()
    text = "CO2 absorption refrigeration achieves high COP with biobased absorbents"
    await vectors.upsert(
        "chunks",
        [VectorRecord(key="c1", vector=fake_embed(text), metadata={"text": text, "doi": "10.1/x", "title": "Paper A", "document_id": "d1"})],
    )
    return vectors


@pytest.mark.asyncio
async def test_research_pipeline_runs_all_agents_and_cites():
    store = InMemoryStore()
    sup = Supervisor(
        settings=_settings(),
        llm=FakeLLM(),
        embedding=FakeEmbedding(),
        vectors=await _seeded_vectors(),
        code_exec=FakeCodeExec(),
        store=store,
    )

    result = await sup.handle("What COP does CO2 absorption refrigeration achieve?")

    assert result.intent == "research_query"
    assert "[1]" in result.answer
    assert result.citations and result.citations[0].chunk_id == "c1"
    agents = {step.agent for step in result.trace}
    assert {"router", "retriever", "investigator", "synthesizer", "factchecker"} <= agents
    # conversation persisted (user + assistant)
    messages = await store.get_messages(result.conversation_id)
    assert len(messages) == 2


@pytest.mark.asyncio
async def test_conversation_is_reused():
    store = InMemoryStore()
    sup = Supervisor(
        settings=_settings(),
        llm=FakeLLM(),
        embedding=FakeEmbedding(),
        vectors=await _seeded_vectors(),
        code_exec=FakeCodeExec(),
        store=store,
    )
    first = await sup.handle("Question one?")
    second = await sup.handle("Follow up?", conversation_id=first.conversation_id)
    assert first.conversation_id == second.conversation_id
    assert len(await store.get_messages(first.conversation_id)) == 4
