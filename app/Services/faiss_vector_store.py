"""FAISS-backed vector store: exact cosine search via IndexFlatIP."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import numpy as np
import faiss
from app.Services.interfaces import IVectorStore
from app.DTOs import Chunk, RetrievalResult
from app.Config.settings import settings


class FaissVectorStore(IVectorStore):
    def __init__(self, path: str | None = None, dim: int | None = None):
        self._dir = Path(path or settings.vector_store_full_path)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "faiss.index"
        self._meta_path = self._dir / "meta.json"
        self._meta: list[dict[str, Any]] = self._load_meta()
        self._dim = dim or settings.embedding_dim
        self._index = self._load_index()

    def _load_meta(self) -> list[dict[str, Any]]:
        if self._meta_path.exists():
            return json.loads(self._meta_path.read_text(encoding="utf-8"))
        return []

    def _load_index(self) -> faiss.Index:
        if self._index_path.exists():
            return faiss.read_index(str(self._index_path))
        return faiss.IndexFlatIP(self._dim)

    def _persist(self) -> None:
        faiss.write_index(self._index, str(self._index_path))
        self._meta_path.write_text(json.dumps(self._meta), encoding="utf-8")

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if not chunks:
            return
        arr = np.asarray(vectors, dtype=np.float32)
        if arr.shape[1] != self._dim:
            self._dim = arr.shape[1]
            self._index = faiss.IndexFlatIP(self._dim)
            if self._meta:
                self._meta = []
        self._index.add(arr)
        for c in chunks:
            self._meta.append({
                "id": c.id, "doc_id": c.doc_id, "text": c.text,
                "chunk_idx": c.chunk_idx, "source": c.source,
                "char_start": c.char_start, "char_end": c.char_end,
            })
        self._persist()

    def search(self, vector: list[float], top_k: int = 3,
               where: dict | None = None) -> list[RetrievalResult]:
        if self._index.ntotal == 0:
            return []
        q = np.asarray([vector], dtype=np.float32)
        k = min(top_k * 5 if where else top_k, self._index.ntotal)
        scores, ids = self._index.search(q, k)
        results: list[RetrievalResult] = []
        rank = 0
        for score, i in zip(scores[0], ids[0]):
            if i < 0:
                continue
            m = self._meta[int(i)]
            if where and not all(m.get(key) == val for key, val in where.items()):
                continue
            rank += 1
            results.append(RetrievalResult(
                chunk_id=m["id"], doc_id=m["doc_id"], text=m["text"],
                source=m["source"], score=round(float(score), 4),
                rank=rank, strategy="",
            ))
            if rank >= top_k:
                break
        return results

    def delete_by_doc(self, doc_id: str) -> int:
        keep_idx = [i for i, m in enumerate(self._meta) if m["doc_id"] != doc_id]
        removed = len(self._meta) - len(keep_idx)
        if not removed:
            return 0
        if keep_idx:
            kept_vecs = np.vstack([self._index.reconstruct(i) for i in keep_idx])
            self._index = faiss.IndexFlatIP(self._dim)
            self._index.add(kept_vecs)
            self._meta = [self._meta[i] for i in keep_idx]
        else:
            self._index = faiss.IndexFlatIP(self._dim)
            self._meta = []
        self._persist()
        return removed

    def count(self) -> int:
        return int(self._index.ntotal)

    def all_texts(self) -> list[dict[str, Any]]:
        return [{"id": m["id"], "text": m["text"], "metadata": m}
                for m in self._meta]

    def reset(self) -> None:
        self._index = faiss.IndexFlatIP(self._dim)
        self._meta = []
        for p in (self._index_path, self._meta_path):
            p.unlink(missing_ok=True)
