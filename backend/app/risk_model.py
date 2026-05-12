"""Risk prediction utilities for the MHGN experimental backend."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_DIR = PROJECT_ROOT / "trained_models"

TARGET_MODEL_FILES = {
    "health_risk_score": "health_risk_score_xgboost_model.pkl",
    "mental_risk_score": "mental_risk_score_xgboost_model.pkl",
    "accident_risk_score": "accident_risk_score_xgboost_model.pkl",
}

BASE_FEATURE_DEFAULTS: dict[str, float] = {
    "total_screentime_hours": 0.0,
    "time_spent_socialmedia_hours": 0.0,
    "time_spent_game_hours": 0.0,
    "last_phone_log_time_minutes": 0.0,
    "first_phone_log_time_minutes": 0.0,
    "night_screentime_hours": 0.0,
    "number_calls": 0.0,
    "total_call_duration_minutes": 0.0,
    "number_messages": 0.0,
    "variance_call_duration": 0.0,
    "mobility_time_hours": 0.0,
    "resting_time_hours": 8.0,
    "avg_sleep_time_hours": 7.0,
    "var_sleep_time": 0.0,
    "avg_heartrate_bpm": 75.0,
    "var_heartrate": 0.0,
    "number_steps": 0.0,
    "distance_traveled_km": 0.0,
}

DEFAULT_TEST_USER: dict[str, float] = {
    "total_screentime_hours": 10.0,
    "time_spent_socialmedia_hours": 22 / 7,
    "time_spent_game_hours": 0.0,
    "last_phone_log_time_minutes": 1500.0,
    "first_phone_log_time_minutes": 420.0,
    "night_screentime_hours": 4.0,
    "number_calls": 11.0,
    "total_call_duration_minutes": 50.0,
    "number_messages": 303 / 7,
    "variance_call_duration": 10.0,
    "mobility_time_hours": 8.0,
    "resting_time_hours": 6.0,
    "avg_sleep_time_hours": 6.0,
    "var_sleep_time": 2.0,
    "avg_heartrate_bpm": 89.0,
    "var_heartrate": 17.0,
    "number_steps": 13000.0,
    "distance_traveled_km": 6.72,
}


def _safe_float(value: Any, default: float) -> float:
    """Convert API input to float while keeping safe defaults."""
    if value is None:
        return default
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(numeric_value):
        return default
    return numeric_value


def build_feature_dict(payload: dict[str, Any]) -> tuple[dict[str, float], list[str]]:
    """Create complete model features from Android JSON input."""
    features: dict[str, float] = {}
    defaults_used: list[str] = []

    for key, default in BASE_FEATURE_DEFAULTS.items():
        if key in payload:
            features[key] = _safe_float(payload.get(key), default)
        else:
            features[key] = default
            defaults_used.append(key)

    features["screen_addiction_score"] = (
        features["total_screentime_hours"] * 0.4
        + features["time_spent_socialmedia_hours"] * 0.4
        + features["night_screentime_hours"] * 0.2
    )
    features["activity_ratio"] = features["mobility_time_hours"] / (
        features["resting_time_hours"] + 1e-6
    )
    features["sleep_irregularity_score"] = features["var_sleep_time"] * (
        7 - features["avg_sleep_time_hours"]
    )
    features["social_interaction_score"] = (
        features["number_calls"] * 0.3 + features["number_messages"] * 0.7
    )
    features["heart_instability_score"] = (
        features["var_heartrate"] * features["avg_heartrate_bpm"]
    )

    return features, defaults_used


class RiskPredictor:
    """Load trained pkl models and predict MHGN risk scores."""

    def __init__(self, model_dir: Path | str = DEFAULT_MODEL_DIR) -> None:
        self.model_dir = Path(model_dir)
        self.feature_columns = joblib.load(self.model_dir / "feature_columns.pkl")
        self.models = {
            target: joblib.load(self.model_dir / file_name)
            for target, file_name in TARGET_MODEL_FILES.items()
        }

    def predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Predict scores from a raw Android feature JSON payload."""
        features, defaults_used = build_feature_dict(payload)
        input_df = pd.DataFrame([features])

        for column in self.feature_columns:
            if column not in input_df.columns:
                input_df[column] = 0.0
                defaults_used.append(column)

        input_df = input_df[self.feature_columns]
        scores = {
            target: self._clamp_score(float(model.predict(input_df)[0]))
            for target, model in self.models.items()
        }

        return {
            "risk_scores": scores,
            "features_used": features,
            "missing_defaults_used": sorted(set(defaults_used)),
        }

    @staticmethod
    def _clamp_score(score: float) -> float:
        """Keep UI scores inside the expected 0-100 range."""
        return round(max(0.0, min(100.0, score)), 1)


def load_json_features(path: Path | str) -> dict[str, Any]:
    """Load feature JSON created by the Android demo app."""
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)
