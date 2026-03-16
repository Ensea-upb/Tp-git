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

    # LLM (Sprint 3+)
    llm_api_key: str = ""
    llm_model: str = "claude-sonnet-4-20250514"

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
