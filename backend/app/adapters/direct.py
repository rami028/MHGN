from __future__ import annotations

from typing import Any

from app.adapters.base import ModelAdapter


class DirectFeatureAdapter(ModelAdapter):
    """Pass through already-computed model outputs from the request body."""

    name = "direct"

    def predict(
        self,
        features: dict[str, Any],
        normalized: dict[str, float],
        feature_risks: dict[str, float],
        external_outputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return dict(external_outputs or {})
