"""Normalize extracted text and split it into embedding-sized chunks."""

import re


def clean_text(text: str) -> str:
    """Collapse noisy whitespace while keeping paragraph breaks."""
    cleaned = text.replace("\x00", " ")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into word-aligned chunks.

    Chunks stay within ``chunk_size`` characters when words are short enough.
    A single longer word is kept intact. ``overlap`` keeps a short tail of the
    previous chunk so a sentence split across the boundary is still searchable.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_overlap must be zero or smaller than chunk_size")

    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    current: list[str] = []

    for word in words:
        if current and _length(current) + 1 + len(word) > chunk_size:
            chunks.append(" ".join(current))
            current = _overlap_words(current, overlap)
            # Drop the overlap tail when it cannot fit with this word.
            if current and _length(current) + 1 + len(word) > chunk_size:
                current = []
        current.append(word)

    if current:
        chunks.append(" ".join(current))
    return chunks


def _length(words: list[str]) -> int:
    return len(" ".join(words))


def _overlap_words(words: list[str], overlap: int) -> list[str]:
    if overlap <= 0:
        return []

    kept: list[str] = []
    for word in reversed(words):
        candidate = [word, *kept]
        if _length(candidate) > overlap:
            break
        kept = candidate
    return kept
