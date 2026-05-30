import os
from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, BeforeValidator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Annotated


def parse_cors_origins(v: Any) -> Union[List[str], str]:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, (list, str)):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    # --- Core Settings ---
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "ChronoShield AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # --- Server Settings ---
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_LOG_LEVEL: str = "info"

    # --- Security & JWT ---
    SECRET_KEY: str = "default_placeholder_secret_key_please_change"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_ALGORITHM: str = "HS256"
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS Origins configuration
    BACKEND_CORS_ORIGINS: Annotated[
        Union[List[str], str], BeforeValidator(parse_cors_origins)
    ] = ["http://localhost:5173", "http://localhost:3000", "http://localhost"]

    # --- Database Settings ---
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "secure_postgres_pass_998"
    POSTGRES_DB: str = "chronoshield_db"
    DATABASE_URL: Optional[str] = None

    # Production Database Pool Tuning
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], values: Any) -> Any:
        if isinstance(v, str) and v:
            return v
        data = values.data
        server = data.get("POSTGRES_SERVER", "localhost")
        port = data.get("POSTGRES_PORT", 5432)
        user = data.get("POSTGRES_USER", "postgres")
        password = data.get("POSTGRES_PASSWORD", "")
        db = data.get("POSTGRES_DB", "chronoshield_db")
        return f"postgresql+asyncpg://{user}:{password}@{server}:{port}/{db}"

    # --- Redis Settings ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = "secure_redis_pass_112"
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_connection(cls, v: Optional[str], values: Any) -> Any:
        if isinstance(v, str) and v:
            return v
        data = values.data
        host = data.get("REDIS_HOST", "localhost")
        port = data.get("REDIS_PORT", 6379)
        password = data.get("REDIS_PASSWORD", "")
        db = data.get("REDIS_DB", 0)

        if password:
            return f"redis://:{password}@{host}:{port}/{db}"
        return f"redis://{host}:{port}/{db}"

    # --- Logging Settings ---
    LOGS_DIR: str = "./logs"

    # --- Validations ---
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, values: Any) -> str:
        env = values.data.get("ENVIRONMENT", "development")
        if (
            env.lower() == "production"
            and v == "default_placeholder_secret_key_please_change"
        ):
            raise ValueError(
                "SECRET_KEY must be changed from the default placeholder in production environments"
            )
        return v


settings = Settings()
