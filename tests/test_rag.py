import pytest

from mentis.application.rag import hybrid_retrieve
from mentis.domain.ports.vector_store import VectorRecord
from tests.fakes import FakeEmbedding, FakeVectorStore, fake_embed


@pytest.mark.asyncio
async def test_hybrid_retrieve_ranks_relevant_chunk_first():
    vectors = FakeVectorStore()
    docs = {
        "c1": "CO2 absorption refrigeration achieves high COP with biobased absorbents",
        "c2": "Total War Warhammer mod list and faction balance",
        "c3": "Two-phase flow and pressure losses in expansion valves",
    }
    await vectors.upsert(
        "chunks",
        [VectorRecord(key=k, vector=fake_embed(v), metadata={"text": v, "title": k}) for k, v in docs.items()],
    )

    results = await hybrid_retrieve(
        query="CO2 absorption refrigeration COP",
        embedding=FakeEmbedding(),
        vectors=vectors,
        index="chunks",
        top_k=2,
    )
    assert results
    assert results[0].chunk_id == "c1"


@pytest.mark.asyncio
async def test_empty_query_returns_nothing():
    results = await hybrid_retrieve(
        query="   ", embedding=FakeEmbedding(), vectors=FakeVectorStore(), index="chunks"
    )
    assert results == []
