from mentis.adapters.outbound.sources.arxiv import ArxivSource
from mentis.adapters.outbound.sources.crossref import _strip_jats
from mentis.adapters.outbound.sources.openalex import OpenAlexSource, _invert_abstract


def test_invert_abstract_reconstructs_order():
    inverted = {"CO2": [0], "absorption": [1], "refrigeration": [2]}
    assert _invert_abstract(inverted) == "CO2 absorption refrigeration"
    assert _invert_abstract(None) is None


def test_openalex_parse_extracts_fields():
    work = {
        "title": "Test Paper",
        "doi": "https://doi.org/10.1/abc",
        "publication_year": 2024,
        "cited_by_count": 7,
        "authorships": [{"author": {"display_name": "Jane Doe"}}],
        "primary_location": {"source": {"display_name": "Int. J. Refrig."}},
        "best_oa_location": {"pdf_url": "https://x/paper.pdf"},
        "open_access": {"oa_url": "https://x/paper"},
        "id": "https://openalex.org/W1",
    }
    paper = OpenAlexSource._parse(work)
    assert paper.doi == "10.1/abc"
    assert paper.year == 2024
    assert paper.oa_pdf_url == "https://x/paper.pdf"
    assert paper.authors[0].name == "Jane Doe"
    assert paper.source == "openalex"


def test_strip_jats_removes_tags():
    assert _strip_jats("<jats:p>Hello <b>world</b></jats:p>") == "Hello world"


def test_arxiv_parse_atom():
    xml = """<?xml version='1.0'?>
    <feed xmlns='http://www.w3.org/2005/Atom'>
      <entry>
        <title>Quantum Refrigeration</title>
        <summary>An abstract.</summary>
        <published>2023-05-01T00:00:00Z</published>
        <author><name>Alice</name></author>
        <link rel='alternate' href='http://arxiv.org/abs/1234'/>
        <link title='pdf' href='http://arxiv.org/pdf/1234'/>
      </entry>
    </feed>"""
    papers = ArxivSource._parse(xml)
    assert len(papers) == 1
    assert papers[0].title == "Quantum Refrigeration"
    assert papers[0].year == 2023
    assert papers[0].oa_pdf_url == "http://arxiv.org/pdf/1234"
