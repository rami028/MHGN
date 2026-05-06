from __future__ import annotations

from typing import Any

from app.adapters.base import ModelAdapter
from app.normalization import average_group_risk
from app.utils import clamp01, safe_float, weighted_mean


class MentalHealthAdapter(ModelAdapter):
    """Mental-health model slot.

    Intended category outputs:
    - mental_health_risk: 0~1, higher means more mental-health risk
    - depression_probability: 0~1, higher means depression state is more likely

    Candidate implementation source: GLOBEM-style depression detection model.
    """

    name = "mental_health"

    def predict(
        self,
        features: dict[str, Any],
        normalized: dict[str, float],
        feature_risks: dict[str, float],
        external_outputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        external_outputs = external_outputs or {}

        mental_override = safe_float(external_outputs.get("mental_health_risk"))
        depression_override = safe_float(
            external_outputs.get("depression_probability")
            or external_outputs.get("globem_depression_probability")
        )
        if mental_override is not None or depression_override is not None:
            mental_value = mental_override if mental_override is not None else depression_override
            depression_value = depression_override if depression_override is not None else mental_override
            return {
                "mental_health_risk": clamp01(mental_value or 0.0),
                "depression_probability": clamp01(depression_value or 0.0),
                "mental_health_source": "external_ml_output",
            }

        sleep_fatigue_risk = average_group_risk("sleep_fatigue", feature_risks)
        stress_risk = feature_risks.get("stress_self_report", 0.0)
        stress_model = safe_float(external_outputs.get("stress_probability"), 0.0) or 0.0
        digital_overuse_risk = average_group_risk("digital_overuse", feature_risks)
        isolation_hint = safe_float(external_outputs.get("social_isolation_score"), 0.0) or 0.0
        mobility_low_risk = average_group_risk("mobility", feature_risks)

        depression_probability = weighted_mean(
            {
                "stress": weighted_mean(
                    {"self_report": stress_risk, "model": stress_model},
                    {"self_report": 0.55, "model": 0.45},
                ),
                "sleep": sleep_fatigue_risk,
                "isolation": isolation_hint,
                "digital": digital_overuse_risk,
                "mobility": mobility_low_risk,
            },
            {
                "stress": 0.30,
                "sleep": 0.25,
                "isolation": 0.20,
                "digital": 0.10,
                "mobility": 0.15,
            },
        )

        return {
            "mental_health_risk": depression_probability,
            "depression_probability": depression_probability,
            "mental_health_source": "heuristic_placeholder",
        }
