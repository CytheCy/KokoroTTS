"""Text chunking that keeps natural sentence and paragraph boundaries."""

from __future__ import annotations

import re

SENTENCE_END = re.compile(r"(?<=[.!?])(?:[\"'”’)]*)\s+")


def _split_oversize(text: str, limit: int) -> list[str]:
    """Split a long sentence at whitespace, never dropping text."""
    words = text.split()
    if not words:
        return []
    parts: list[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + len(word) + 1 <= limit:
            current += " " + word
        else:
            parts.append(current)
            current = word
    parts.append(current)
    return parts


def chunk_text(text: str, limit: int = 900) -> list[str]:
    """Return chunks no longer than *limit*, preferring paragraph/sentence ends."""
    if limit < 50:
        raise ValueError("Chunk size must be at least 50 characters")

    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
    units: list[str] = []
    for paragraph in filter(None, paragraphs):
        for sentence in filter(None, SENTENCE_END.split(paragraph)):
            sentence = sentence.strip()
            units.extend(_split_oversize(sentence, limit))

    chunks: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current} {unit}".strip()
        if current and len(candidate) > limit:
            chunks.append(current)
            current = unit
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def streaming_chunks(
    text: str, first_limit: int = 120, later_limit: int = 300
) -> list[str]:
    """Create one short opening chunk, then larger efficient chunks."""
    if first_limit > later_limit:
        raise ValueError("First chunk limit cannot exceed later chunk limit")

    chunks = chunk_text(text, limit=later_limit)
    if not chunks:
        return []

    opening_parts = chunk_text(chunks[0], limit=first_limit)
    if len(opening_parts) == 1:
        return chunks

    remainder = " ".join(opening_parts[1:])
    return [opening_parts[0], remainder, *chunks[1:]]
