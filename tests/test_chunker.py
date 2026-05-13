from app.Services.chunker import chunk_text, make_doc_id


def test_chunk_short_text_single_chunk():
    chunks = chunk_text("hello world", doc_id="d1", source="x.txt")
    assert len(chunks) == 1
    assert chunks[0].text == "hello world"


def test_chunk_long_text_multiple_chunks():
    text = ". ".join([f"sentence number {i}" for i in range(500)])
    chunks = chunk_text(text, doc_id="d2", source="long.txt",
                        chunk_size=128, overlap=10)
    assert len(chunks) > 1
    assert all(c.doc_id == "d2" for c in chunks)
    assert all(c.chunk_idx >= 0 for c in chunks)


def test_chunk_ids_are_unique():
    text = ". ".join([f"unique content piece {i}" for i in range(200)])
    chunks = chunk_text(text, doc_id="d3", source="x", chunk_size=64, overlap=5)
    assert len({c.id for c in chunks}) == len(chunks)


def test_make_doc_id_unique():
    assert make_doc_id() != make_doc_id()
