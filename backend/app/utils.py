from __future__ import annotations

from typing import Any


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def safe_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    if isinstance(value, bool):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def weighted_mean(values: dict[str, float], weights: dict[str, float]) -> float:
    numerator = 0.0
    denominator = 0.0
    for key, weight in weights.items():
        if key not in values:
            continue
        numerator += values[key] * weight
        denominator += weight
    if denominator <= 0:
        return 0.0
    return clamp01(numerator / denominator)


def pick_first_number(source: dict[str, Any], keys: list[str], default: float = 0.0) -> float:
    for key in keys:
        value = safe_float(source.get(key))
        if value is not None:
            return value
    return default
