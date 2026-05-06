from __future__ import annotations

from typing import Any

from app.config import load_feature_ranges
from app.utils import clamp01, safe_float


def normalize_features(features: dict[str, Any]) -> dict[str, float]:
    """Normalize known numeric features to 0~1 with config ranges."""
    ranges = load_feature_ranges()
    normalized: dict[str, float] = {}

    for key, spec in ranges.items():
        raw_value = safe_float(features.get(key))
        if raw_value is None:
            continue

        min_value = float(spec["min"])
        max_value = float(spec["max"])
        if max_value == min_value:
            normalized[key] = 0.0
            continue

        normalized[key] = clamp01((raw_value - min_value) / (max_value - min_value))

    return normalized


def feature_risk_values(features: dict[str, Any], normalized: dict[str, float]) -> dict[str, float]:
    """Convert normalized features into risk-oriented 0~1 values."""
    ranges = load_feature_ranges()
    risks: dict[str, float] = {}

    for key, norm_value in normalized.items():
        spec = ranges.get(key, {})
        direction = spec.get("risk_direction", "high")

        if direction == "high":
            risks[key] = clamp01(norm_value)
        elif direction == "low":
            risks[key] = clamp01(1.0 - norm_value)
        elif direction == "mid":
            raw_value = safe_float(features.get(key))
            if raw_value is None:
                continue
            ideal_min = float(spec.get("ideal_min", spec["min"]))
            ideal_max = float(spec.get("ideal_max", spec["max"]))
            min_value = float(spec["min"])
            max_value = float(spec["max"])

            if ideal_min <= raw_value <= ideal_max:
                risks[key] = 0.0
            elif raw_value < ideal_min:
                denom = max(ideal_min - min_value, 1e-9)
                risks[key] = clamp01((ideal_min - raw_value) / denom)
            else:
                denom = max(max_value - ideal_max, 1e-9)
                risks[key] = clamp01((raw_value - ideal_max) / denom)
        else:
            risks[key] = clamp01(norm_value)

    return risks


def average_group_risk(group: str, feature_risks: dict[str, float]) -> float:
    ranges = load_feature_ranges()
    values = [
        feature_risks[key]
        for key, spec in ranges.items()
        if spec.get("group") == group and key in feature_risks
    ]
    if not values:
        return 0.0
    return clamp01(sum(values) / len(values))
