from __future__ import annotations

from typing import Any

from app.config import load_risk_weights
from app.normalization import average_group_risk
from app.schemas import ProxyScores
from app.utils import clamp01, safe_float, weighted_mean


def _first_float(source: dict[str, Any], keys: list[str], default: float = 0.0) -> float:
    """Read the new category key first, then older dataset-named aliases."""
    for key in keys:
        value = safe_float(source.get(key))
        if value is not None:
            return value
    return default


def build_base_signals(
    feature_risks: dict[str, float],
    ml_outputs: dict[str, Any],
) -> dict[str, float]:
    """Build normalized model/feature signals used by the risk equation."""
    sleep_fatigue_risk = average_group_risk("sleep_fatigue", feature_risks)
    digital_feature_risk = average_group_risk("digital_overuse", feature_risks)
    digital_model_risk = _first_float(ml_outputs, ["digital_overuse_model_risk"])
    digital_overuse_risk = weighted_mean(
        {"feature": digital_feature_risk, "model": digital_model_risk},
        {"feature": 0.65, "model": 0.35},
    )
    mobility_low_risk = average_group_risk("mobility", feature_risks)
    speed_context_risk = average_group_risk("accident_context", feature_risks)
    physical_feature_risk = average_group_risk("physical_health", feature_risks)

    attention_risk = weighted_mean(
        {
            "attention_productivity": _first_float(ml_outputs, ["attention_productivity_risk"]),
            "attention_low": _first_float(ml_outputs, ["attention_low_probability"]),
            "task_disturbance": _first_float(ml_outputs, ["task_disturbance_probability"]),
        },
        {
            "attention_productivity": 0.40,
            "attention_low": 0.35,
            "task_disturbance": 0.25,
        },
    )

    stress_risk = weighted_mean(
        {
            "stress_self_report": feature_risks.get("stress_self_report", 0.0),
            "stress_model": _first_float(
                ml_outputs,
                ["stress_probability", "kemophone_stress_probability"],
            ),
        },
        {"stress_self_report": 0.55, "stress_model": 0.45},
    )

    activity_low_risk = weighted_mean(
        {
            "steps": feature_risks.get("steps", 0.0),
            "active_minutes": feature_risks.get("active_minutes", 0.0),
            "activity_model": 1.0 - _first_float(ml_outputs, ["activity_level_score"]),
        },
        {"steps": 0.35, "active_minutes": 0.35, "activity_model": 0.30},
    )

    mental_health_risk = _first_float(
        ml_outputs,
        ["mental_health_risk", "depression_probability", "globem_depression_probability"],
    )
    depression_probability = _first_float(
        ml_outputs,
        ["depression_probability", "mental_health_risk", "globem_depression_probability"],
    )
    physical_health_risk = _first_float(
        ml_outputs,
        ["physical_health_risk", "lifesnaps_physical_health_risk"],
    )
    transport_context_risk = _first_float(
        ml_outputs,
        ["transport_context_risk", "collecty_transport_risk"],
    )

    return {
        "sleep_fatigue_risk": sleep_fatigue_risk,
        "fatigue_risk": sleep_fatigue_risk,
        "digital_overuse_risk": digital_overuse_risk,
        "mobility_low_risk": mobility_low_risk,
        "speed_context_risk": speed_context_risk,
        "physical_feature_risk": physical_feature_risk,
        "attention_risk": attention_risk,
        "stress_risk": stress_risk,
        "activity_low_risk": activity_low_risk,
        "sedentary_risk": feature_risks.get("sedentary_minutes", 0.0),
        "social_isolation_score": _first_float(ml_outputs, ["social_isolation_score"]),
        "mental_health_risk": mental_health_risk,
        "depression_probability": depression_probability,
        "physical_health_risk": physical_health_risk,
        "transport_context_risk": transport_context_risk,
    }


def compute_proxy_scores(
    feature_risks: dict[str, float],
    ml_outputs: dict[str, Any],
) -> tuple[ProxyScores, dict[str, Any]]:
    weights = load_risk_weights()
    proxy_weights = weights.get("proxy_weights", {})
    total_weights = weights.get("total_risk_weights", {})

    base = build_base_signals(feature_risks, ml_outputs)

    accident_proxy = weighted_mean(base, proxy_weights.get("accident_proxy", {}))
    mental_health_proxy = weighted_mean(base, proxy_weights.get("mental_health_proxy", {}))
    physical_health_proxy = weighted_mean(base, proxy_weights.get("physical_health_proxy", {}))

    proxy_scores = ProxyScores(
        accident_proxy=accident_proxy,
        mental_health_proxy=mental_health_proxy,
        physical_health_proxy=physical_health_proxy,
    )

    total_risk_score = weighted_mean(
        proxy_scores.model_dump(),
        total_weights,
    )

    contribution = {
        "base_signals": base,
        "proxy_weights": proxy_weights,
        "total_risk_weights": total_weights,
        "total_risk_score": total_risk_score,
    }
    return proxy_scores, contribution


def risk_level(score: float) -> str:
    score = clamp01(score)
    if score < 0.33:
        return "low"
    if score < 0.66:
        return "medium"
    return "high"
