from __future__ import annotations

from typing import Any

from app.adapters.base import ModelAdapter
from app.normalization import average_group_risk
from app.utils import clamp01, safe_float, weighted_mean


class DigitalOveruseAdapter(ModelAdapter):
    """Digital-overuse model slot.

    Intended category output:
    - digital_overuse_model_risk: 0~1, higher means stronger overuse pattern

    Candidate implementation sources: screen-time aggregates, K-EmoPhone-style
    phone-use models, or direct app usage data.
    """

    name = "digital_overuse"

    def predict(
        self,
        features: dict[str, Any],
        normalized: dict[str, float],
        feature_risks: dict[str, float],
        external_outputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        external_outputs = external_outputs or {}

        override = safe_float(external_outputs.get("digital_overuse_model_risk"))
        if override is not None:
            return {
                "digital_overuse_model_risk": clamp01(override),
                "digital_overuse_source": "external_ml_output",
            }

        digital_overuse = weighted_mean(
            {
                "group_average": average_group_risk("digital_overuse", feature_risks),
                "screen_time": feature_risks.get("screen_time_h", 0.0),
                "unlock": feature_risks.get("phone_unlock_count", 0.0),
                "notification": feature_risks.get("notification_count", 0.0),
                "app_switch": feature_risks.get("app_switch_count", 0.0),
            },
            {
                "group_average": 0.30,
                "screen_time": 0.25,
                "unlock": 0.15,
                "notification": 0.15,
                "app_switch": 0.15,
            },
        )

        return {
            "digital_overuse_model_risk": digital_overuse,
            "digital_overuse_source": "heuristic_placeholder",
        }
