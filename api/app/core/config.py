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
    # MCP server the agent connects to. Empty = this app's own server, in-process.
    # Example: http://localhost:8000/mcp or any external MCP server URL
    mcp_client_url: str = ""

    # Thank-you letters
    web_base_url: str = "http://localhost:5173"  # base for the QR / share links
    donate_link: str = "phoenixbikes.org/donate"  # must appear in every note
    letter_max_chars: int = Field(default=520, ge=100)  # fits one Uuna Tek card
    letter_similarity_threshold: float = Field(default=0.75, ge=0, le=1)

    # Agent (Ollama → MCP tools)
    agent_max_steps: int = Field(default=8, ge=1, le=50)
    agent_system_prompt: str = (
        "You are a helpful assistant for the Handwritten project (Phoenix Bikes). "
        "Use the available tools to look up donors and gifts, find gifts eligible for a "
        "thank-you note, write and edit draft notes, and search documents. "
        "You cannot approve or send notes; staff do that. "
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
