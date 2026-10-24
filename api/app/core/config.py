from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "handwritten"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "info"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # PostgreSQL
    postgres_user: str = "handwritten"
    postgres_password: str = "handwritten"
    postgres_db: str = "handwritten"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str = ""

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_vision_model: str = "gemma3:4b"
    ollama_timeout_seconds: float = Field(default=120, gt=0)

    # MCP
    mcp_server_name: str = "handwritten-mcp"
    mcp_mount_path: str = "/mcp"
    # Агент аль MCP серверт холбогдох вэ. Хоосон бол өөрийн серверт in-process холбогдоно.
    # Жишээ: http://localhost:8000/mcp  эсвэл гадны MCP серверийн URL
    mcp_client_url: str = ""

    # Agent (Ollama → MCP tools)
    agent_max_steps: int = Field(default=8, ge=1, le=50)
    agent_system_prompt: str = (
        "You are a helpful assistant for the Handwritten project. "
        "Use the available tools to look up or modify documents when needed. "
        "Answer in the user's language."
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
