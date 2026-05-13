from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), extra="ignore")

    flask_env: str = "development"
    flask_debug: int = 1
    app_host: str = "127.0.0.1"
    app_port: int = 5000
    secret_key: str = "dev-secret"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    vector_store_path: str = "writable/vectors"

    chunk_size: int = 500
    chunk_overlap: int = 50

    top_k: int = 3
    similarity_metric: str = "cosine"

    llm_provider: str = "mock"
    llm_model: str = ""

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    anthropic_api_key: str = ""

    google_api_key: str = ""

    ollama_base_url: str = "http://localhost:11434"

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    sqlite_path: str = "writable/ragchatbot.db"

    @property
    def root(self) -> Path:
        return ROOT

    @property
    def vector_store_full_path(self) -> str:
        return str(ROOT / self.vector_store_path)

    @property
    def sqlite_full_path(self) -> str:
        return str(ROOT / self.sqlite_path)


settings = Settings()
