"""Text cleaning and chunking."""

import pytest

from app.utils.text_chunker import chunk_text, clean_text


def test_clean_text_normalizes_whitespace():
    assert clean_text("a\r\n\r\n\r\nb\t\tc\x00d") == "a\n\nb c d"


def test_clean_text_strips_edges():
    assert clean_text("  hello \n") == "hello"


def test_short_text_is_one_chunk():
    assert chunk_text("hello world", chunk_size=100, overlap=10) == ["hello world"]


def test_empty_text_has_no_chunks():
    assert chunk_text("   \n\t", chunk_size=100, overlap=10) == []


def test_chunks_split_on_word_boundaries():
    chunks = chunk_text("alpha beta gamma delta epsilon", chunk_size=12, overlap=0)
    assert chunks == ["alpha beta", "gamma delta", "epsilon"]


def test_overlap_keeps_a_short_tail():
    chunks = chunk_text(
        "alpha beta gamma delta epsilon zeta",
        chunk_size=12,
        overlap=5,
    )
    assert chunks == ["alpha beta", "beta gamma", "gamma delta", "epsilon zeta"]


def test_long_word_is_kept_intact():
    assert chunk_text("supercalifragilistic", chunk_size=5, overlap=0) == [
        "supercalifragilistic"
    ]


def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("hello", chunk_size=10, overlap=10)
