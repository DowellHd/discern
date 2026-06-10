"""Central config loader — reads configs/documents.yaml and env settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
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
    database_url: str = "postgresql://discern:discern@localhost:5432/discern"

    model_config = {"env_prefix": "DISCERN_", "env_file": ".env", "extra": "ignore"}


def load_document_schema(path: Path | None = None) -> dict[str, Any]:
    """Load and return the raw document schema from configs/documents.yaml."""
    schema_path = path or (CONFIGS_DIR / "documents.yaml")
    with schema_path.open() as fh:
        return yaml.safe_load(fh)


settings = Settings()
