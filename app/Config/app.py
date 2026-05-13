from flask import Flask
from pathlib import Path
from app.Config.settings import settings
from app.Models.document_model import init_db


def create_app() -> Flask:
    root = settings.root
    app = Flask(
        __name__,
        template_folder=str(root / "app" / "Views"),
        static_folder=str(root / "public" / "assets"),
        static_url_path="/assets",
    )
    app.secret_key = settings.secret_key
    app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024

    init_db()

    from app.Controllers.home_controller import bp as home_bp
    from app.Controllers.upload_controller import bp as upload_bp
    from app.Controllers.kb_controller import bp as kb_bp
    from app.Controllers.chat_controller import bp as chat_bp
    from app.Controllers.benchmark_controller import bp as bench_bp
    from app.Controllers.settings_controller import bp as settings_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(kb_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(bench_bp)
    app.register_blueprint(settings_bp)

    @app.context_processor
    def inject_globals():
        from app.Services import langfuse_client as lf
        from app.Services.llm_provider import LLMFactory
        from app.Models.document_model import DocumentModel
        return {
            "APP_NAME": "RAGChatbot",
            "APP_VERSION": "1.0",
            "LANGFUSE_ENABLED": lf.is_enabled(),
            "GLOBAL_STATS": DocumentModel.stats(),
            "LLM_ACTIVE": LLMFactory.active(),
            "LLM_AVAILABLE": LLMFactory.available(),
        }

    return app
