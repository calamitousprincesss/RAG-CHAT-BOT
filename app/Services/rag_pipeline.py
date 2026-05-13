"""RAG orchestrator: ingestion, retrieval (Strategy A & B), generation."""
from __future__ import annotations
import time
from dataclasses import dataclass
from app.Services.interfaces import IEmbedder, IVectorStore, ILLM
from app.Services.chunker import chunk_text, make_doc_id
from app.Services.file_parser import parse_file
from app.Services.query_expander import QueryExpander
from app.Services.llm_provider import LLMFactory
from app.DTOs import RetrievalResult
from app.Services import langfuse_client as lf


@dataclass
class IngestionResult:
    doc_id: str
    source: str
    chunk_count: int
    char_count: int


@dataclass
class QueryResult:
    query: str
    expanded_query: str
    strategy: str
    results: list[RetrievalResult]
    answer: str
    latency_ms: float
    embedding_latency_ms: float
    retrieval_latency_ms: float
    generation_latency_ms: float


class RAGPipeline:
    """End-to-end RAG orchestrator. Services are injected via constructor."""

    def __init__(
        self,
        embedder: IEmbedder,
        vector_store: IVectorStore,
        query_expander: QueryExpander | None = None,
        generator: ILLM | None = None,
    ):
        self.embedder = embedder
        self.store = vector_store
        self.generator = generator or LLMFactory.create()
        self.expander = query_expander or QueryExpander(self.generator)

    def ingest_text(self, text: str, source: str) -> IngestionResult:
        doc_id = make_doc_id()
        chunks = chunk_text(text, doc_id=doc_id, source=source)
        if not chunks:
            return IngestionResult(doc_id=doc_id, source=source,
                                   chunk_count=0, char_count=0)
        vectors = self.embedder.embed([c.text for c in chunks])
        self.store.add(chunks, vectors)
        return IngestionResult(doc_id=doc_id, source=source,
                               chunk_count=len(chunks), char_count=len(text))

    def ingest_file(self, path: str, source: str | None = None) -> IngestionResult:
        text = parse_file(path)
        return self.ingest_text(text, source=source or str(path))

    def retrieve(self, query: str, strategy: str = "A",
                 top_k: int = 3) -> tuple[list[RetrievalResult], str, dict[str, float]]:
        timings = {"embed_ms": 0.0, "search_ms": 0.0, "expand_ms": 0.0}
        expanded = ""

        if strategy.upper() == "B":
            t0 = time.perf_counter()
            expanded = self.expander.expand(query)
            timings["expand_ms"] = (time.perf_counter() - t0) * 1000
            embed_input = expanded
        else:
            embed_input = query

        t0 = time.perf_counter()
        qvec = self.embedder.embed_one(embed_input)
        timings["embed_ms"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        results = self.store.search(qvec, top_k=top_k)
        timings["search_ms"] = (time.perf_counter() - t0) * 1000

        for r in results:
            r.strategy = strategy.upper()
        return results, expanded, timings

    def ask(self, query: str, strategy: str = "B", top_k: int = 3) -> QueryResult:
        t_start = time.perf_counter()
        with lf.trace("chat_query", query=query, strategy=strategy) as tr:
            with lf.span(tr, "retrieval"):
                results, expanded, timings = self.retrieve(query, strategy, top_k)

            with lf.span(tr, "generation"):
                t_gen = time.perf_counter()
                context = "\n\n---\n\n".join(
                    f"[Source: {r.source} | sim {r.score}]\n{r.text}" for r in results
                ) or "(no relevant context found)"
                prompt = (
                    "You are a helpful assistant. Answer using only the provided context.\n\n"
                    f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"
                )
                try:
                    answer_text = self.generator.generate(prompt)
                except Exception as e:
                    answer_text = f"[LLM error: {e}] Falling back to context.\n\n{context[:400]}"
                gen_ms = (time.perf_counter() - t_gen) * 1000

        total_ms = (time.perf_counter() - t_start) * 1000
        return QueryResult(
            query=query,
            expanded_query=expanded,
            strategy=strategy.upper(),
            results=results,
            answer=answer_text,
            latency_ms=round(total_ms, 2),
            embedding_latency_ms=round(timings["embed_ms"] + timings["expand_ms"], 2),
            retrieval_latency_ms=round(timings["search_ms"], 2),
            generation_latency_ms=round(gen_ms, 2),
        )

    def delete_document(self, doc_id: str) -> int:
        return self.store.delete_by_doc(doc_id)
