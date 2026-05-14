import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    app_host: str
    app_port: int
    app_debug: bool
    pg_host: str
    pg_port: int
    pg_database: str
    pg_user: str
    pg_password: str
    pg_schema: str
    pg_connect_timeout: int
    pg_sslmode: str
    default_page_size: int
    max_page_size: int
    auto_refresh_seconds: int


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    env_path = Path(__file__).resolve().parents[1] / "config" / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
        print(f"[settings] ENV file loaded: {env_path}")
    else:
        print(f"[settings] ENV file not found: {env_path}, using system/process env variables")

    return Settings(
        app_host=os.getenv("APP_HOST", "0.0.0.0"),
        app_port=int(os.getenv("APP_PORT", "8083")),
        app_debug=_as_bool(os.getenv("APP_DEBUG", "false")),
        pg_host=os.getenv("PGHOST", "127.0.0.1"),
        pg_port=int(os.getenv("PGPORT", "5432")),
        pg_database=os.getenv("PGDATABASE", "wsn_sim"),
        pg_user=os.getenv("PGUSER", "wsn_user"),
        pg_password=os.getenv("PGPASSWORD", ""),
        pg_schema=os.getenv("PGSCHEMA", "wsn"),
        pg_connect_timeout=int(os.getenv("PGCONNECT_TIMEOUT", "5")),
        pg_sslmode=os.getenv("PGSSLMODE", "disable"),
        default_page_size=int(os.getenv("DEFAULT_PAGE_SIZE", "50")),
        max_page_size=int(os.getenv("MAX_PAGE_SIZE", "500")),
        auto_refresh_seconds=int(os.getenv("AUTO_REFRESH_SECONDS", "5")),
    )


settings = load_settings()
