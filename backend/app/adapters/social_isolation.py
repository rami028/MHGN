from __future__ import annotations

from typing import Any

from app.adapters.base import ModelAdapter
from app.normalization import average_group_risk
from app.utils import clamp01, safe_float, weighted_mean


class SocialIsolationAdapter(ModelAdapter):
    """Social / isolation model slot.

    Intended category output:
    - social_isolation_score: 0~1, higher means more isolated

    Candidate implementation source: StudentLife-style phone sensing features.
    Replace this heuristic with a trained model when ready.
    """

    name = "social_isolation"

    def predict(
        self,
        features: dict[str, Any],
        normalized: dict[str, float],
        feature_risks: dict[str, float],
        external_outputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        external_outputs = external_outputs or {}

        override = safe_float(external_outputs.get("social_isolation_score"))
        if override is not None:
            return {
                "social_isolation_score": clamp01(override),
                "social_isolation_source": "external_ml_output",
            }

        social_isolation = weighted_mean(
            {
                "conversation_low": average_group_risk(
                    "social_isolation",
                    self._only_keys(
                        feature_risks,
                        [
                            "conversation_minutes",
                            "call_count",
                            "sms_count",
                            "bluetooth_unique_devices",
                        ],
                    ),
                ),
                "mobility_low": average_group_risk(
                    "mobility",
                    self._only_keys(
                        feature_risks,
                        ["location_entropy", "distance_traveled_km", "home_stay_ratio"],
                    ),
                ),
            },
            {"conversation_low": 0.75, "mobility_low": 0.25},
        )

        return {
            "social_isolation_score": social_isolation,
            "social_isolation_source": "heuristic_placeholder",
        }

    @staticmethod
    def _only_keys(data: dict[str, float], keys: list[str]) -> dict[str, float]:
        return {key: data[key] for key in keys if key in data}
