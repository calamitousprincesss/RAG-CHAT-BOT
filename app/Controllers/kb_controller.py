from flask import Blueprint, render_template, jsonify, request
from app.Controllers import get_pipeline
from app.Models.document_model import DocumentModel, ChatSessionModel

bp = Blueprint("kb", __name__, url_prefix="/knowledge")


@bp.get("/")
def page():
    docs = DocumentModel.list_all()
    stats = DocumentModel.stats()
    return render_template("knowledge.html",
                           documents=docs,
                           stats=stats,
                           chat_count=ChatSessionModel.count(),
                           avg_latency=round(ChatSessionModel.avg_latency(), 1))


@bp.get("/api/list")
def list_api():
    return jsonify({"documents": DocumentModel.list_all(),
                    "stats": DocumentModel.stats()})


@bp.get("/api/<doc_id>")
def get_one(doc_id):
    doc = DocumentModel.get(doc_id)
    if not doc:
        return jsonify({"ok": False, "error": "not found"}), 404
    pipe = get_pipeline()
    all_chunks = [c for c in pipe.store.all_texts()
                  if c["metadata"].get("doc_id") == doc_id]
    all_chunks.sort(key=lambda c: c["metadata"].get("chunk_idx", 0))
    return jsonify({"ok": True, "document": doc, "chunks": all_chunks})


@bp.delete("/api/<doc_id>")
def delete_one(doc_id):
    pipe = get_pipeline()
    removed = pipe.delete_document(doc_id)
    DocumentModel.delete(doc_id)
    return jsonify({"ok": True, "vectors_removed": removed})
