from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Base de données
    database_url: str = "postgresql://agent_user:agent_password@localhost:5432/agent_db"

    # Sécurité
    app_api_key: str = "dev-api-key-changeme"

    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    backend_cors_origins: str = "http://localhost:3000"

    # LLM — Ollama local (Sprint 5)
    llm_base_url: str = "http://localhost:11434"
    llm_model_default: str = "gemma3n:e2b"
    llm_model_hq: str = "qwen2.5:7b-instruct"
    llm_timeout_seconds: int = 120

    # Stockage fichiers
    file_storage_path: str = "/data/files"

    # France Travail API (Sprint 2)
    ft_client_id: str = ""
    ft_client_secret: str = ""
    ft_search_keywords: str = "développeur,data,logiciel,informatique"
    ft_max_results: int = 50

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",")]

    @property
    def ft_configured(self) -> bool:
        return bool(self.ft_client_id and self.ft_client_secret)


settings = Settings()
