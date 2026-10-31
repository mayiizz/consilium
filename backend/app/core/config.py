from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve backend/.env regardless of process cwd (repo root vs backend/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Consilium API"
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    mongodb_uri: str = "mongodb://localhost:27017/consilium"
    mongodb_db_name: str = "consilium"

    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-in-production"
    jwt_refresh_secret: str = "change-me-refresh-secret"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    groq_api_key: str = ""
    # qwen/qwen3-32b shut down 2026-07-17; use openai/gpt-oss-120b
    groq_model: str = "openai/gpt-oss-120b"
    groq_summary_model: str = "openai/gpt-oss-120b"
    groq_fallback_model: str = "openai/gpt-oss-120b"

    tinyfish_api_key: str = ""
    tinyfish_agent_base: str = "https://agent.tinyfish.ai"
    tinyfish_search_url: str = "https://api.search.tinyfish.ai"
    tinyfish_run_timeout_seconds: int = 180
    tinyfish_http_timeout_seconds: int = 60
    tinyfish_max_sites: int = 5

    github_app_id: str = ""
    github_app_private_key: str = ""
    github_webhook_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = ""
    frontend_url: str = "http://localhost:5173"
    github_task_key_prefix: str = "MM"
    github_pat: str = ""
    github_require_pr_merge_for_done: bool = True
    github_require_ci_success_for_done: bool = False
    github_ci_workflow_name_allowlist: str = ""

    task_automation_provider: str = "groq"
    # Prefer a currently available Groq chat model (llama-3.3-70b-versatile is often 404).
    task_automation_model: str = "openai/gpt-oss-120b"
    task_automation_match_threshold: float = 0.78
    task_automation_low_confidence_threshold: float = 0.60
    task_automation_extract_max_tokens: int = 3072
    task_automation_board_sync_max_tokens: int = 2048

    kanban_rag_enabled: bool = True
    kanban_embedding_model: str = "all-MiniLM-L6-v2"
    kanban_rag_chunk_words: int = 250
    kanban_rag_chunk_overlap_words: int = 40
    kanban_rag_top_k: int = 5
    kanban_rag_max_context_chars: int = 12000
    kanban_rag_min_similarity: float = 0.22
    kanban_rag_latest_meeting_score_boost: float = 1.12
    kanban_rag_queries: str = ""
    kanban_rag_fallback_tail_chars: int = 8000
    kanban_rag_board_sync_enabled: bool = True
    kanban_rag_board_max_transcript_chars: int = 10000
    transcript_rag_cache_dir: str = ""
    transcript_rag_qa_top_k: int = 8
    transcript_rag_qa_max_context_chars: int = 8000
    kanban_document_rag_enabled: bool = True
    kanban_document_rag_max_chars: int = 6000

    stale_task_auto_blockers_enabled: bool = True
    stale_task_inactivity_days: int = 3
    stale_task_background_interval_hours: int = 0

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # In-app due-date reminders (Celery beat)
    due_reminder_days: int = 2

    # Topic research agent (TinyFish Search + Agent browser + Groq)
    research_max_results: int = 8
    research_max_pages: int = 5
    research_max_chars_per_page: int = 8000
    research_max_total_chars: int = 24000

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
