"""Configuração da aplicação por variáveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _path_from_env(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default))
    return value if value.is_absolute() else BASE_DIR / value


@dataclass(frozen=True)
class Settings:
    model_path: Path = _path_from_env("MODEL_PATH", "artifacts/churn_model.joblib")
    metrics_path: Path = _path_from_env("METRICS_PATH", "artifacts/metrics.json")
    log_path: Path = _path_from_env("LOG_PATH", "logs/predictions.jsonl")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
