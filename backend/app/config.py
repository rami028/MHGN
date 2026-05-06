from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"


@lru_cache(maxsize=1)
def load_feature_ranges() -> dict[str, dict[str, Any]]:
    path = CONFIG_DIR / "feature_ranges.yaml"
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def load_risk_weights() -> dict[str, Any]:
    path = CONFIG_DIR / "risk_weights.yaml"
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
