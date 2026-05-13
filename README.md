# Context-Aware Retrieval Engine

**Senior Gen AI Assessment — Semantic RAG & Vector Search**
*Focus: Embeddings, Vector Databases, Retrieval Logic, and Benchmarking*

A local Retrieval-Augmented Generation (RAG) pipeline that ingests raw textual
data, generates embeddings, and performs semantic search. Includes a structured
benchmark comparing two retrieval strategies and a web dashboard for manual
exploration.

---

## 1. Problem Statement

Design and implement a local RAG pipeline that:

1. Ingests raw textual data
2. Generates embeddings
3. Performs semantic search

Then evaluate by comparing **two retrieval strategies**:

| Strategy | Description |
|---|---|
| **A — Raw Vector Search** | Traditional embedding-based similarity search. Query is embedded directly and the top-K nearest chunks are returned. |
| **B — AI-Enhanced Retrieval** | A (mocked) generative model rewrites and expands the user query into a more embedding-friendly form **before** embedding and search. |

---

## 2. Technical Requirements & Implementation

| Requirement | Implementation |
|---|---|
| **Embedding Model** — local library simulating Vertex AI's `textembedding-gecko` | [`sentence-transformers/all-MiniLM-L6-v2`](app/Services/embedding_service.py) — 384-dim, L2-normalized at encode time. A second `VertexLikeEmbedder` wraps the mocked Vertex SDK with identical interface so the swap to production is a one-line change. |
| **Vector Database** — lightweight local store (FAISS / ChromaDB / NumPy) | [`FaissVectorStore`](app/Services/faiss_vector_store.py) — `IndexFlatIP` for exact cosine search on normalized vectors, persisted to disk as `faiss.index` + `meta.json`. |
| **Mocking** — `vertexai.language_models.TextEmbeddingModel` and `GenerativeModel` | [`app/Mocks/mock_vertex.py`](app/Mocks/mock_vertex.py) — both classes mirror the real Vertex AI SDK signatures (`from_pretrained`, `get_embeddings → [TextEmbedding]`, `generate_content → GenerationResponse`). |
| **Orchestration** — Python class managing ingestion of 5-10 paragraphs | [`RAGPipeline`](app/Services/rag_pipeline.py) — accepts injected `IEmbedder`, `IVectorStore`, `ILLM`; methods: `ingest_text`, `ingest_file`, `retrieve(strategy="A"\|"B")`, `ask`. [`seed.py`](seed.py) ingests 8 technical paragraphs on first run. |

---

## 3. Benchmarking Task

Produces a structured comparison (both **JSON** and **Markdown table**) of
Strategy A vs Strategy B across **3 complex queries**:

1. *"How does the system handle peak load?"* (PDF example, verbatim)
2. *"What happens when too many users hit the API at once?"*
3. *"Explain the failover mechanism during outages."*

Run `python benchmark.py` (or click **Run benchmark** in the web UI) to
regenerate. Output is written to:

- [`docs/retrieval_benchmark.md`](docs/retrieval_benchmark.md) — human-readable side-by-side table per query, with similarity scores, expanded queries, and latency breakdowns
- [`docs/retrieval_benchmark.json`](docs/retrieval_benchmark.json) — machine-readable, includes every chunk's text, score, rank, source, and per-stage timings

---

## 4. Submission Deliverables

| Deliverable | Location |
|---|---|
| **Modular source code** — Embedding, Storage, Retrieval | [`app/Services/embedding_service.py`](app/Services/embedding_service.py) · [`app/Services/faiss_vector_store.py`](app/Services/faiss_vector_store.py) · [`app/Services/rag_pipeline.py`](app/Services/rag_pipeline.py) |
| **Pytest suites** verifying retrieval and mocking the GCP SDK | [`tests/test_retrieval.py`](tests/test_retrieval.py) · [`tests/test_mocks.py`](tests/test_mocks.py) · [`tests/test_chunker.py`](tests/test_chunker.py) · [`tests/test_llm_provider.py`](tests/test_llm_provider.py) |
| **`retrieval_benchmark.md`** — Strategy A vs B output | [`docs/retrieval_benchmark.md`](docs/retrieval_benchmark.md) |
| **Documentation** — Cosine vs Euclidean + Vertex AI Matching Engine migration | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |

---

## Project Structure

```
ragchatbot/
├── app/
│   ├── Config/           Pydantic settings + Flask factory
│   ├── Controllers/      Flask blueprints (upload, knowledge, chat, benchmark, settings)
│   ├── Models/           SQLite document + chat-session models
│   ├── Services/
│   │   ├── embedding_service.py     ← Embedding logic
│   │   ├── faiss_vector_store.py    ← Storage logic
│   │   ├── rag_pipeline.py          ← Retrieval logic (orchestrator class)
│   │   ├── chunker.py
│   │   ├── file_parser.py
│   │   ├── query_expander.py        ← Strategy B
│   │   ├── llm_provider.py          ← Pluggable LLM (mock/OpenAI/Anthropic/Gemini/Ollama)
│   │   ├── langfuse_client.py
│   │   └── interfaces.py            ← IEmbedder, IVectorStore, ILLM
│   ├── Mocks/mock_vertex.py         ← Vertex AI SDK mocks
│   ├── DTOs/                        ← Chunk, RetrievalResult, ChatTurn
│   └── Views/                       ← Jinja templates + partials
├── public/
│   ├── assets/                      ← CSS (light/dark) + JS
│   └── index.py                     ← Flask entry point
├── tests/                           ← Pytest suites
├── docs/
│   ├── ARCHITECTURE.md              ← Cosine vs Euclidean + Vertex migration
│   ├── retrieval_benchmark.md       ← Strategy A vs B (PDF deliverable)
│   └── retrieval_benchmark.json     ← Same data, machine-readable
├── seed.py                          ← Ingest 8 technical paragraphs
├── benchmark.py                     ← Regenerate the benchmark report
├── pyproject.toml                   ← uv dependency manifest
├── setup.bat / setup.sh             ← One-click setup (Windows / Unix)
└── .env.example                     ← Environment template
```

---

## Setup

This project uses **[uv](https://docs.astral.sh/uv/)** for dependency
management. The setup script installs uv, Python 3.12, all dependencies, and
launches the app — no manual steps.

### Windows
```cmd
setup.bat
```

### macOS / Linux
```bash
./setup.sh
```

The app starts at **http://127.0.0.1:5000**.

### Manual setup

```bash
uv sync                            # creates .venv from pyproject.toml
cp .env.example .env               # then edit .env to add API keys (optional)
uv run python seed.py              # ingest the 8 seed paragraphs
uv run python benchmark.py         # regenerate docs/retrieval_benchmark.md
uv run python public/index.py      # start the web app
```

---

## Configuration

All configuration is via `.env`. Defaults work out of the box (mock LLM
satisfies the PDF requirement). To use a real LLM for query expansion and
chat generation, set:

```bash
LLM_PROVIDER=mock | openai | anthropic | gemini | ollama
LLM_MODEL=<model-name>

# Provider-specific keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
```

The active provider drives both **Strategy B query expansion** and chat
generation. It is shown in the footer and on the Settings page.

---

## Web UI

| Route | Purpose |
|---|---|
| `/chat` | Chat interface with Strategy A / B toggle, top-K slider, source citations |
| `/upload` | Drag-drop file upload (.txt .md .pdf .docx) and paste-text ingestion |
| `/knowledge` | List all ingested documents, preview chunks, delete (cascades to vectors) |
| `/benchmark` | Run Strategy A vs B benchmark, regenerate the report |
| `/settings` | Active LLM, embedding model, vector store, all configuration |
| `/healthz` | Health check (JSON) |

---

## Tests

```bash
uv run pytest -q
```

18 tests across four suites:

- `test_mocks.py` — verifies the Vertex AI SDK mocks (`from_pretrained`, `get_embeddings`, `generate_content`) match the real SDK signatures
- `test_chunker.py` — chunk size, overlap, ID uniqueness
- `test_retrieval.py` — end-to-end ingest → retrieve → delete using the mocked SDK
- `test_llm_provider.py` — provider factory and mock provider

---

## Documentation

- [**`docs/ARCHITECTURE.md`**](docs/ARCHITECTURE.md) — Why cosine over Euclidean for L2-normalized embeddings; step-by-step Vertex AI Matching Engine migration plan (Embedder → Vector Store → Generator → infrastructure).
- [**`docs/retrieval_benchmark.md`**](docs/retrieval_benchmark.md) — Strategy A vs B comparison for 3 queries, with cosine scores, expanded queries, and per-stage latency.

---

## License

MIT
