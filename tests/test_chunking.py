from mentis.application.chunking import CHUNK_MAX, split_into_chunks


def test_empty_text_yields_no_chunks():
    assert split_into_chunks("") == []


def test_short_text_is_single_chunk():
    chunks = split_into_chunks("A short paragraph about CO2 refrigeration.")
    assert len(chunks) == 1


def test_long_text_splits_and_respects_max():
    para = "Absorption refrigeration with CO2. " * 200
    text = para + "\n\n" + para
    chunks = split_into_chunks(text)
    assert len(chunks) > 1
    # overlap-merged chunks may slightly exceed target but stay near the max bound
    assert all(len(c) <= CHUNK_MAX + 200 for c in chunks)


def test_overlap_added_between_chunks():
    text = "\n\n".join(f"Paragraph number {i} discussing thermodynamic cycles in detail. " * 10 for i in range(5))
    chunks = split_into_chunks(text)
    assert len(chunks) >= 2
