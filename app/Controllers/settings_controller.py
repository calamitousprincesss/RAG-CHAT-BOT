from flask import Blueprint, render_template, jsonify
from app.Services.llm_provider import LLMFactory
from app.Services import langfuse_client as lf
from app.Config.settings import settings

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.get("/")
def page():
    return render_template("settings.html",
                           active=LLMFactory.active(),
                           available=LLMFactory.available(),
                           cfg=settings)


@bp.get("/api/llm")
def llm_status():
    return jsonify({"active": LLMFactory.active(),
                    "available": LLMFactory.available(),
                    "langfuse": lf.is_enabled()})
