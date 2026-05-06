from __future__ import annotations

from typing import Any

from app.adapters.activity_physical_health import ActivityPhysicalHealthAdapter
from app.adapters.attention_productivity import AttentionProductivityAdapter
from app.adapters.digital_overuse import DigitalOveruseAdapter
from app.adapters.direct import DirectFeatureAdapter
from app.adapters.mental_health import MentalHealthAdapter
from app.adapters.social_isolation import SocialIsolationAdapter
from app.adapters.transport_mode import TransportModeAdapter


class ModelRegistry:
    def __init__(self) -> None:
        self.adapters = [
            DirectFeatureAdapter(),
            SocialIsolationAdapter(),
            AttentionProductivityAdapter(),
            DigitalOveruseAdapter(),
            MentalHealthAdapter(),
            ActivityPhysicalHealthAdapter(),
            TransportModeAdapter(),
        ]

    def predict_all(
        self,
        features: dict[str, Any],
        normalized: dict[str, float],
        feature_risks: dict[str, float],
        external_outputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        outputs: dict[str, Any] = {}
        external_outputs = external_outputs or {}

        for adapter in self.adapters:
            merged_external = {**external_outputs, **outputs}
            outputs.update(adapter.predict(features, normalized, feature_risks, merged_external))

        return outputs
