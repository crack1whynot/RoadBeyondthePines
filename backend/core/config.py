from functools import lru_cache
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Road Beyond the Pines Studio"
    app_env: str = "development"
    app_debug: bool = True
    database_url: str = "sqlite:///./data/app.db"
    log_level: str = "INFO"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:5173"
    unreal_mcp_enabled: bool = False
    unreal_mcp_transport: str = "mock"
    unreal_mcp_host: str = "127.0.0.1"
    unreal_mcp_port: int = Field(default=8765, ge=1, le=65535)
    unreal_mcp_base_url: str = ""
    unreal_mcp_timeout_seconds: float = Field(default=10.0, gt=0)
    unreal_mcp_auto_connect: bool = False
    unreal_mcp_allow_write: bool = False
    unreal_mcp_auth_token: SecretStr | None = None
    ai_provider: str = "mock"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
