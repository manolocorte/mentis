import pytest

from mentis.application.harvest import harvest
from mentis.domain.models import Paper
from tests.fakes import FakeQueue, InMemoryStore


class FakeSource:
    name = "fake"

    def __init__(self, papers):
        self._papers = papers

    async def search(self, query, *, max_results=25):
        return self._papers

    async def resolve_oa_pdf(self, paper):
        return paper.oa_pdf_url


class FakeUnpaywall:
    async def enrich(self, paper):
        return paper


@pytest.mark.asyncio
async def test_harvest_dedupes_and_enqueues_oa_pdfs():
    store = InMemoryStore()
    queue = FakeQueue()
    project = await store.get_or_create_project("default")

    p1 = Paper(title="A", doi="10.1/a", oa_pdf_url="http://x/a.pdf", source="openalex")
    p1_dup = Paper(title="A again", doi="10.1/a", source="crossref")  # same DOI
    p2 = Paper(title="B", doi="10.1/b", source="arxiv")  # no OA pdf

    summary = await harvest(
        query="co2",
        project_id=project.id,
        sources=[FakeSource([p1, p1_dup]), FakeSource([p2])],
        unpaywall=FakeUnpaywall(),
        store=store,
        queue=queue,
        max_results=25,
    )

    assert summary["found"] == 3
    assert summary["unique"] == 2
    assert summary["new_papers"] == 2
    assert summary["enqueued"] == 1  # only p1 has an OA pdf
    assert queue.sent[0]["doi"] == "10.1/a"
