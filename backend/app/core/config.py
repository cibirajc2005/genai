"""Environment-based application configuration."""

from dataclasses import dataclass
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


def _load_env() -> None:
    """Load the small local .env without adding another runtime dependency."""
    env_file = BACKEND_DIR / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()


@dataclass(frozen=True)
class Settings:
    app_name: str = "Enterprise RAG Knowledge Assistant"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    environment: str = os.getenv("APP_ENV", "development")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "")
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_secret_key: str = os.getenv(
        "SUPABASE_SECRET_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    )
    supabase_database_url: str = os.getenv("SUPABASE_DATABASE_URL", "")
    supabase_storage_bucket: str = os.getenv("SUPABASE_STORAGE_BUCKET", "documents")
    database_path: Path = PROJECT_DIR / "data" / "metadata" / "app.db"
    documents_path: Path = PROJECT_DIR / "data" / "documents"
    agentic_ai_enabled: bool = os.getenv("AGENTIC_AI_ENABLED", "true").lower() in {"1", "true", "yes"}
    agent_max_steps: int = min(max(int(os.getenv("AGENT_MAX_STEPS", "8")), 1), 8)
    agent_max_retrieval_retries: int = min(max(int(os.getenv("AGENT_MAX_RETRIEVAL_RETRIES", "2")), 0), 2)
    agent_max_tool_calls: int = min(max(int(os.getenv("AGENT_MAX_TOOL_CALLS", "10")), 1), 10)

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_secret_key and self.supabase_database_url)
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    )


settings = Settings()
