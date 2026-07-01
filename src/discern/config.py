"""Central config loader — reads configs/documents.yaml and env settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings

REPO_ROOT = Path(__file__).parents[2]
CONFIGS_DIR = REPO_ROOT / "configs"


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

    model_config = {"env_prefix": "DISCERN_", "env_file": ".env", "extra": "ignore"}

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
