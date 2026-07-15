from functools import lru_cache
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
    ai_provider: str = "mock"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
