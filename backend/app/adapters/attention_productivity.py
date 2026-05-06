from __future__ import annotations

from typing import Any

from app.adapters.base import ModelAdapter
from app.normalization import average_group_risk
from app.utils import clamp01, safe_float, weighted_mean


class AttentionProductivityAdapter(ModelAdapter):
    """Attention / productivity model slot.

    Intended category outputs:
    - attention_productivity_risk: 0~1, higher means lower attention/productivity
    - attention_low_probability: 0~1, higher means low-attention state is more likely
    - task_disturbance_probability: 0~1, higher means phone/task disturbance is more likely
    - stress_probability: 0~1, higher means stress state is more likely

    Candidate implementation sources: K-EmoPhone or StudentLife-style models.
    """

    name = "attention_productivity"

    def predict(
        self,
        features: dict[str, Any],
        normalized: dict[str, float],
        feature_risks: dict[str, float],
        external_outputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        external_outputs = external_outputs or {}

        attention_productivity_override = safe_float(
            external_outputs.get("attention_productivity_risk")
        )
        attention_low_override = safe_float(external_outputs.get("attention_low_probability"))
        disturbance_override = safe_float(
            external_outputs.get("task_disturbance_probability")
        )
        stress_override = safe_float(
            external_outputs.get("stress_probability")
            or external_outputs.get("kemophone_stress_probability")
        )

        if (
            attention_productivity_override is not None
            and attention_low_override is not None
            and disturbance_override is not None
            and stress_override is not None
        ):
            return {
                "attention_productivity_risk": clamp01(attention_productivity_override),
                "attention_low_probability": clamp01(attention_low_override),
                "task_disturbance_probability": clamp01(disturbance_override),
                "stress_probability": clamp01(stress_override),
                "attention_productivity_source": "external_ml_output",
            }

        attention_productivity_risk = weighted_mean(
            {
                "app_switch": feature_risks.get("app_switch_count", 0.0),
                "notifications": feature_risks.get("notification_count", 0.0),
                "screen_time": feature_risks.get("screen_time_h", 0.0),
                "sleep_fatigue": average_group_risk("sleep_fatigue", feature_risks),
            },
            {
                "app_switch": 0.30,
                "notifications": 0.25,
                "screen_time": 0.20,
                "sleep_fatigue": 0.25,
            },
        )

        attention_low = weighted_mean(
            {
                "app_switch": feature_risks.get("app_switch_count", 0.0),
                "notification": feature_risks.get("notification_count", 0.0),
                "screen_time": feature_risks.get("screen_time_h", 0.0),
                "sleep_fatigue": average_group_risk("sleep_fatigue", feature_risks),
            },
            {
                "app_switch": 0.30,
                "notification": 0.25,
                "screen_time": 0.20,
                "sleep_fatigue": 0.25,
            },
        )

        task_disturbance = weighted_mean(
            {
                "notification": feature_risks.get("notification_count", 0.0),
                "unlock": feature_risks.get("phone_unlock_count", 0.0),
                "app_switch": feature_risks.get("app_switch_count", 0.0),
            },
            {"notification": 0.45, "unlock": 0.30, "app_switch": 0.25},
        )

        stress_probability = weighted_mean(
            {
                "stress_self": feature_risks.get("stress_self_report", 0.0),
                "sleep_fatigue": average_group_risk("sleep_fatigue", feature_risks),
                "digital": average_group_risk("digital_overuse", feature_risks),
            },
            {"stress_self": 0.50, "sleep_fatigue": 0.30, "digital": 0.20},
        )

        return {
            "attention_productivity_risk": attention_productivity_risk,
            "attention_low_probability": attention_low,
            "task_disturbance_probability": task_disturbance,
            "stress_probability": stress_probability,
            "attention_productivity_source": "heuristic_placeholder",
        }
