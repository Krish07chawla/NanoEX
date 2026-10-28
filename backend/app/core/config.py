"""Application settings loaded from environment variables (.env).

`get_settings()` is cached, so the whole app shares one Settings instance
(Singleton via DI). Never hardcode secrets: everything sensitive comes from env.
"""

from decimal import Decimal
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-insecure-secret-change-me"


class Settings(BaseSettings):
    """All tunable configuration for NanoEX Web."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "NanoEX Web"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default=["http://localhost:5173", "http://localhost:3000"])

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./nanoex.db"
    auto_create_tables: bool = True  # dev convenience; production uses Alembic

    # --- Security ---
    jwt_secret_key: str = DEV_JWT_SECRET  # dev only; production must set JWT_SECRET_KEY
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    refresh_cookie_name: str = "nanoex_refresh"
    cookie_secure: bool = False
    rate_limit_auth: str = "5/minute"
    bcrypt_rounds: int = 12

    # --- Seed admin (optional) ---
    admin_email: str | None = None
    admin_password: str | None = None

    # --- Wallet ---
    initial_wallet_balance: Decimal = Decimal("500000.00")
    max_topup_amount: Decimal = Decimal("1000000.00")
    max_daily_topups: int = 5

    # --- Market simulator ---
    market_provider: str = "synthetic"  # synthetic | yfinance
    tick_interval_ms: int = 500
    sim_seed: int | None = 42
    history_buffer_size: int = 600
    book_depth_levels: int = 10

    # --- Arbitrage simulation ---
    arb_min_latency_ms: int = 20
    arb_max_latency_ms: int = 150
    arb_leg_failure_prob: float = 0.05
    arb_opportunity_ttl_seconds: int = 5
    arb_auto_interval_ms: int = 1000

    @model_validator(mode="after")
    def _check_production_secrets(self) -> "Settings":
        weak = self.jwt_secret_key == DEV_JWT_SECRET or len(self.jwt_secret_key) < 32
        if self.environment == "production" and weak:
            raise ValueError("Set a strong JWT_SECRET_KEY (32+ chars) in production")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide Settings singleton."""
    return Settings()
