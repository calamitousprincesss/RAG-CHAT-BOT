import json
from flask import Blueprint, render_template, request, jsonify
from app.Controllers import get_pipeline
from app.Models.document_model import ChatSessionModel, DocumentModel

bp = Blueprint("chat", __name__, url_prefix="/chat")


@bp.get("/")
def page():
    return render_template("chat.html",
                           recent=ChatSessionModel.recent(limit=10),
                           stats=DocumentModel.stats())


@bp.post("/ask")
def ask():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    strategy = (data.get("strategy") or "B").upper()
    top_k = int(data.get("top_k") or 3)
    if not query:
        return jsonify({"ok": False, "error": "empty query"}), 400

    pipe = get_pipeline()
    qr = pipe.ask(query, strategy=strategy, top_k=top_k)

    sources = [{
        "rank": r.rank, "source": r.source, "score": r.score,
        "text": r.text[:300], "chunk_id": r.chunk_id, "doc_id": r.doc_id
    } for r in qr.results]

    ChatSessionModel.insert(query=query, expanded_query=qr.expanded_query,
                            strategy=strategy, answer=qr.answer,
                            sources_json=json.dumps(sources),
                            latency_ms=qr.latency_ms)

    return jsonify({
        "ok": True,
        "answer": qr.answer,
        "sources": sources,
        "expanded_query": qr.expanded_query,
        "strategy": qr.strategy,
        "latency_ms": qr.latency_ms,
        "timings": {
            "embedding_ms": qr.embedding_latency_ms,
            "retrieval_ms": qr.retrieval_latency_ms,
            "generation_ms": qr.generation_latency_ms,
        }
    })
