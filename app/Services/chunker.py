from __future__ import annotations
import hashlib
import uuid
from app.DTOs import Chunk
from app.Config.settings import settings


def _hash_id(doc_id: str, idx: int, text: str) -> str:
    h = hashlib.sha256(f"{doc_id}:{idx}:{text}".encode()).hexdigest()[:16]
    return f"{doc_id[:8]}-{idx}-{h}"


def chunk_text(text: str, doc_id: str, source: str,
               chunk_size: int | None = None,
               overlap: int | None = None) -> list[Chunk]:
    size = (chunk_size or settings.chunk_size) * 4
    over = (overlap or settings.chunk_overlap) * 4
    if not text or not text.strip():
        return []
    text = text.strip()

    if len(text) <= size:
        return [Chunk(
            id=_hash_id(doc_id, 0, text),
            doc_id=doc_id,
            text=text,
            chunk_idx=0,
            source=source,
            char_start=0,
            char_end=len(text),
        )]

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            last_period = text.rfind(". ", start, end)
            last_newline = text.rfind("\n", start, end)
            cut = max(last_period, last_newline)
            if cut > start + size // 2:
                end = cut + 1
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(Chunk(
                id=_hash_id(doc_id, idx, chunk_text),
                doc_id=doc_id,
                text=chunk_text,
                chunk_idx=idx,
                source=source,
                char_start=start,
                char_end=end,
            ))
            idx += 1
        if end >= len(text):
            break
        start = max(0, end - over)
    return chunks


def make_doc_id() -> str:
    return uuid.uuid4().hex[:12]
