from pathlib import Path
import uuid
from flask import Blueprint, render_template, request, jsonify
from app.Controllers import get_pipeline
from app.Models.document_model import DocumentModel
from app.Services.file_parser import SUPPORTED_EXTS
from app.Config.settings import settings

bp = Blueprint("upload", __name__, url_prefix="/upload")
UPLOAD_DIR = settings.root / "writable" / "uploads"


@bp.get("/")
def page():
    return render_template("upload.html",
                           stats=DocumentModel.stats(),
                           supported=", ".join(SUPPORTED_EXTS))


@bp.post("/text")
def ingest_text():
    text = (request.form.get("text") or "").strip()
    source = (request.form.get("source") or "pasted-text").strip()
    if not text:
        return jsonify({"ok": False, "error": "empty text"}), 400
    pipe = get_pipeline()
    res = pipe.ingest_text(text, source=source)
    if res.chunk_count:
        DocumentModel.insert(res.doc_id, filename=source, source=source,
                             size_bytes=len(text.encode("utf-8")),
                             char_count=res.char_count,
                             chunk_count=res.chunk_count,
                             file_type="text")
    return jsonify({"ok": True, "doc_id": res.doc_id,
                    "chunks": res.chunk_count, "chars": res.char_count})


@bp.post("/file")
def ingest_file():
    f = request.files.get("file")
    if not f:
        return jsonify({"ok": False, "error": "no file"}), 400
    ext = Path(f.filename).suffix.lower()
    if ext not in SUPPORTED_EXTS:
        return jsonify({"ok": False, "error": f"unsupported type {ext}"}), 400

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex[:8]}_{Path(f.filename).name}"
    path = UPLOAD_DIR / safe_name
    f.save(path)

    pipe = get_pipeline()
    res = pipe.ingest_file(str(path), source=f.filename)
    if res.chunk_count:
        DocumentModel.insert(res.doc_id, filename=f.filename, source=f.filename,
                             size_bytes=path.stat().st_size,
                             char_count=res.char_count,
                             chunk_count=res.chunk_count,
                             file_type=ext.lstrip("."))
    return jsonify({"ok": True, "doc_id": res.doc_id,
                    "chunks": res.chunk_count, "chars": res.char_count,
                    "filename": f.filename})
