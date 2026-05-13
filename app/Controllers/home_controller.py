from flask import Blueprint, render_template, redirect, url_for
from app.Models.document_model import DocumentModel, ChatSessionModel
from app.Services import langfuse_client as lf

bp = Blueprint("home", __name__)


@bp.get("/")
def index():
    return redirect(url_for("chat.page"))


@bp.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "langfuse": lf.is_enabled(),
        "documents": DocumentModel.stats(),
        "chats": ChatSessionModel.count(),
    }
