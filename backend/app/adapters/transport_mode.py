from __future__ import annotations

from typing import Any

from app.adapters.base import ModelAdapter
from app.config import load_risk_weights
from app.utils import clamp01, safe_float, weighted_mean


class TransportModeAdapter(ModelAdapter):
    """Transport-mode / accident-context model slot.

    Intended category outputs:
    - transport_mode: one of car, bus, walking, bicycle, train, tram,
      running, electric_scooter, still, unknown
    - transport_context_risk: 0~1, higher means higher accident context risk

    Candidate implementation source: Collecty-style transport-mode classifier.
    """

    name = "transport_mode"

    def predict(
        self,
        features: dict[str, Any],
        normalized: dict[str, float],
        feature_risks: dict[str, float],
        external_outputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        external_outputs = external_outputs or {}
        weights = load_risk_weights()
        mode_risk_map = weights.get("transport_mode_risk", {})

        explicit_risk = safe_float(
            external_outputs.get("transport_context_risk")
            or external_outputs.get("collecty_transport_risk")
        )
        explicit_mode = external_outputs.get("transport_mode") or features.get("transport_mode")

        if explicit_risk is not None:
            return {
                "transport_mode": str(explicit_mode or "unknown").lower(),
                "transport_context_risk": clamp01(explicit_risk),
                "transport_mode_source": "external_ml_output",
            }

        transport_mode = str(explicit_mode or self._infer_mode_from_speed(features)).lower()
        transport_risk = clamp01(
            float(mode_risk_map.get(transport_mode, mode_risk_map.get("unknown", 0.35)))
        )

        speed_context = weighted_mean(
            {
                "speed_mean": feature_risks.get("speed_mean_kmh", 0.0),
                "speed_max": feature_risks.get("speed_max_kmh", 0.0),
                "night": feature_risks.get("night_mobility_ratio", 0.0),
            },
            {"speed_mean": 0.45, "speed_max": 0.40, "night": 0.15},
        )

        return {
            "transport_mode": transport_mode,
            "transport_context_risk": clamp01(0.70 * transport_risk + 0.30 * speed_context),
            "transport_mode_source": "heuristic_placeholder",
        }

    @staticmethod
    def _infer_mode_from_speed(features: dict[str, Any]) -> str:
        speed = safe_float(features.get("speed_mean_kmh"), 0.0) or 0.0
        if speed < 1:
            return "still"
        if speed < 7:
            return "walking"
        if speed < 14:
            return "running"
        if speed < 28:
            return "bicycle"
        if speed < 70:
            return "bus"
        return "car"
