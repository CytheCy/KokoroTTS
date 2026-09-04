from kokoro_reader.chunking import chunk_text, streaming_chunks


def test_empty_text_has_no_chunks():
    assert chunk_text("  \n\n  ") == []


def test_prefers_sentence_boundaries_and_preserves_words():
    text = "One short sentence. Another small sentence! A final question?"
    chunks = chunk_text(text, limit=50)
    assert chunks == ["One short sentence. Another small sentence!", "A final question?"]
    assert " ".join(chunks) == text


def test_splits_very_long_sentence_without_exceeding_limit():
    text = " ".join(f"word{i}" for i in range(250))
    chunks = chunk_text(text, limit=100)
    assert len(chunks) > 10
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert " ".join(chunks) == text


def test_normalizes_document_whitespace():
    chunks = chunk_text("First\nline.\n\nSecond   paragraph.", limit=100)
    assert chunks == ["First line. Second paragraph."]


def test_streaming_chunks_make_only_the_opening_batch_short():
    text = " ".join(f"word{i}" for i in range(100))

    chunks = streaming_chunks(text, first_limit=100, later_limit=300)

    assert len(chunks[0]) <= 100
    assert len(chunks[1]) > 100
    assert all(len(chunk) <= 300 for chunk in chunks[1:])
    assert " ".join(chunks) == text
