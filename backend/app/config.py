"""Application settings.

Every value is read from an environment variable so no secret or
deployment-specific value lives in source code (README §4, Maintainability).
See `.env.example` at the repo root for the full list with explanations.

`Settings.from_env()` builds a fresh object; tests use it after changing
environment variables, or build `Settings(...)` directly.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_title: str = "Voting System API"

    # --- Database -----------------------------------------------------------
    database_url: str = f"sqlite:///{_BACKEND_DIR / 'data' / 'voting.db'}"

    # --- Auth ---------------------------------------------------------------
    token_ttl_minutes: int = 120
    max_failed_logins: int = 5
    lockout_minutes: int = 15

    # --- Simulated blockchain (see docs/blockchain.md) ----------------------
    chain_data_dir: str = str(_BACKEND_DIR / "data" / "nodes")
    node_count: int = 3
    block_size: int = 5
    block_interval_seconds: int = 30
    pow_difficulty: int = 3
    sealer_enabled: bool = True
    sealer_tick_seconds: float = 1.0
    enable_simulation_tools: bool = False

    # --- Ballot encryption keys (never stored in the database) --------------
    election_keys_dir: str = str(_BACKEND_DIR / "data" / "keys")

    # --- HTTP ---------------------------------------------------------------
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:5500", "http://127.0.0.1:5500"])
    rate_limit_per_minute: int = 20

    @classmethod
    def from_env(cls) -> "Settings":
        d = cls()
        return cls(
            app_title=os.getenv("APP_TITLE", d.app_title),
            database_url=os.getenv("DATABASE_URL", d.database_url),
            token_ttl_minutes=int(os.getenv("TOKEN_TTL_MINUTES", d.token_ttl_minutes)),
            max_failed_logins=int(os.getenv("MAX_FAILED_LOGINS", d.max_failed_logins)),
            lockout_minutes=int(os.getenv("LOCKOUT_MINUTES", d.lockout_minutes)),
            chain_data_dir=os.getenv("CHAIN_DATA_DIR", d.chain_data_dir),
            node_count=int(os.getenv("NODE_COUNT", d.node_count)),
            block_size=int(os.getenv("BLOCK_SIZE", d.block_size)),
            block_interval_seconds=int(os.getenv("BLOCK_INTERVAL_SECONDS", d.block_interval_seconds)),
            pow_difficulty=int(os.getenv("POW_DIFFICULTY", d.pow_difficulty)),
            sealer_enabled=_env_bool("SEALER_ENABLED", d.sealer_enabled),
            sealer_tick_seconds=float(os.getenv("SEALER_TICK_SECONDS", d.sealer_tick_seconds)),
            enable_simulation_tools=_env_bool("ENABLE_SIMULATION_TOOLS", d.enable_simulation_tools),
            election_keys_dir=os.getenv("ELECTION_KEYS_DIR", d.election_keys_dir),
            cors_origins=_env_list("CORS_ORIGINS", d.cors_origins),
            rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", d.rate_limit_per_minute)),
        )


settings = Settings.from_env()
