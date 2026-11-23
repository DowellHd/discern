"""Central config loader — reads configs/documents.yaml and env settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings

REPO_ROOT = Path(__file__).parents[2]
CONFIGS_DIR = REPO_ROOT / "configs"
DEMO_DATA_DIR = REPO_ROOT / "data" / "demo"
DEMO_SAMPLES_DIR = REPO_ROOT / "demo-samples"


class Settings(BaseSettings):
    """Runtime settings sourced from environment variables."""

    app_name: str = "discern"
    log_level: str = "INFO"
    seed: int = 42
    data_dir: Path = REPO_ROOT / "data"
    checkpoints_dir: Path = REPO_ROOT / "checkpoints"
    # Accepts DISCERN_DATABASE_URL (preferred) or bare DATABASE_URL (Render's automatic var).
    database_url: str = Field(
        default="postgresql://discern:discern@localhost:5432/discern",
        validation_alias=AliasChoices("DISCERN_DATABASE_URL", "DATABASE_URL"),
    )
    # Comma-separated list of allowed CORS origins. Set DISCERN_CORS_ORIGINS on Render.
    cors_origins: list[str] = Field(
        default=["https://discern.dowellstandley.com", "http://localhost:3000"],
    )
    # Phase 4: LLM post-processor (feature-flagged, off by default)
    llm_postprocess: bool = False
    # Per-request cost ceiling in US cents; calls that would exceed this are skipped
    llm_postprocess_budget_cents: float = 1.0
    # Phase 5: Auth + privacy
    # Demo mode: all requests use a shared demo user — no login required
    demo_mode: bool = True
    # Secret used to sign JWT tokens (generate with: openssl rand -hex 32)
    jwt_secret: str = ""
    # Fernet key for encrypting sensitive fields at rest
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    field_encryption_key: str = ""

    # Offline demo (DISCERN_OFFLINE_DEMO=true): the whole stack runs locally with no external
    # services. SQLite replaces Postgres, a mock engine replaces the model + OCR + LLM backends,
    # and every request is answered from bundled synthetic data. Unset to use the real services.
    # Distinct from `demo_mode` above, which only controls authentication.
    offline_demo: bool = False
    # With offline_demo on, optionally still run the real local classifier (needs torch).
    # OCR and LLM calls stay mocked either way, so nothing leaves the machine.
    offline_demo_real_model: bool = False

    model_config = {"env_prefix": "DISCERN_", "env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def _isolate_offline_demo(self) -> Settings:
        """Keep offline demo data away from real data and databases.

        Seeding writes to the database and uploads, so even an inherited production
        DATABASE_URL must never be used while the demo is on.
        """
        if self.offline_demo:
            self.data_dir = DEMO_DATA_DIR
            self.database_url = f"sqlite:///{DEMO_DATA_DIR / 'discern-demo.db'}"
        return self

    @field_validator("database_url")
    @classmethod
    def _normalise_scheme(cls, v: str) -> str:
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v


def load_document_schema(path: Path | None = None) -> dict[str, Any]:
    """Load and return the raw document schema from configs/documents.yaml."""
    schema_path = path or (CONFIGS_DIR / "documents.yaml")
    with schema_path.open() as fh:
        return yaml.safe_load(fh)


settings = Settings()
