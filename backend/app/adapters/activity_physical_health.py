from __future__ import annotations

from typing import Any

from app.adapters.base import ModelAdapter
from app.normalization import average_group_risk
from app.utils import clamp01, safe_float, weighted_mean


class ActivityPhysicalHealthAdapter(ModelAdapter):
    """Activity / physical-health model slot.

    Intended category outputs:
    - activity_level_score: 0~1, higher means more active/healthy
    - physical_health_risk: 0~1, higher means more physical-health risk

    Candidate implementation source: LifeSnaps-style wearable features.
    """

    name = "activity_physical_health"

    def predict(
        self,
        features: dict[str, Any],
        normalized: dict[str, float],
        feature_risks: dict[str, float],
        external_outputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        external_outputs = external_outputs or {}

        activity_override = safe_float(external_outputs.get("activity_level_score"))
        risk_override = safe_float(
            external_outputs.get("physical_health_risk")
            or external_outputs.get("lifesnaps_physical_health_risk")
        )
        if activity_override is not None and risk_override is not None:
            return {
                "activity_level_score": clamp01(activity_override),
                "physical_health_risk": clamp01(risk_override),
                "activity_physical_health_source": "external_ml_output",
            }

        activity_level = weighted_mean(
            {
                "steps": normalized.get("steps", 0.0),
                "active_minutes": normalized.get("active_minutes", 0.0),
                "hrv": normalized.get("hrv_rmssd_ms", 0.0),
                "sleep_efficiency": normalized.get("sleep_efficiency", 0.0),
            },
            {
                "steps": 0.35,
                "active_minutes": 0.35,
                "hrv": 0.15,
                "sleep_efficiency": 0.15,
            },
        )

        physical_health_risk = weighted_mean(
            {
                "activity_low": 1.0 - activity_level,
                "sedentary": feature_risks.get("sedentary_minutes", 0.0),
                "resting_hr": feature_risks.get("resting_heart_rate", 0.0),
                "sleep_fatigue": average_group_risk("sleep_fatigue", feature_risks),
            },
            {
                "activity_low": 0.40,
                "sedentary": 0.25,
                "resting_hr": 0.20,
                "sleep_fatigue": 0.15,
            },
        )

        return {
            "activity_level_score": activity_level,
            "physical_health_risk": physical_health_risk,
            "activity_physical_health_source": "heuristic_placeholder",
        }
