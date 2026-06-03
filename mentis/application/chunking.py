"""Paragraph-aware text chunking with overlap (no infra dependencies)."""
from __future__ import annotations

import re

CHUNK_TARGET = 900
CHUNK_MAX = 1300
OVERLAP = 120


def split_into_chunks(text: str) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()] if text.strip() else []

    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        if len(para) > CHUNK_MAX:
            for sentence in re.split(r"(?<=[.!?])\s+", para):
                if len(buf) + len(sentence) + 1 > CHUNK_TARGET and buf:
                    chunks.append(buf)
                    buf = sentence
                else:
                    buf = f"{buf} {sentence}".strip()
        elif len(buf) + len(para) + 2 > CHUNK_TARGET and buf:
            chunks.append(buf)
            buf = para
        else:
            buf = f"{buf}\n{para}".strip()
    if buf:
        chunks.append(buf)

    # Add a short prefix overlap from the previous chunk for context continuity.
    with_overlap: list[str] = []
    for i, c in enumerate(chunks):
        if i == 0:
            with_overlap.append(c)
            continue
        overlap = chunks[i - 1][-OVERLAP:]
        merged = f"{overlap} {c}".strip()
        with_overlap.append(merged if len(merged) <= CHUNK_MAX else c)
    return with_overlap
