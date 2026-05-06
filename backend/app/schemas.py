from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RiskScoreRequest(BaseModel):
    """Feature-level request body.

    `features` is intentionally open-ended because ML teammates may change the
    feature contract. Known numeric columns are normalized with config ranges;
    unknown values are passed through for adapters to use if needed.
    """

    model_config = ConfigDict(extra="allow")

    user_id: str | None = Field(default=None, examples=["demo-user-001"])
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        examples=["2026-05-07T00:00:00Z"],
    )
    features: dict[str, Any] = Field(default_factory=dict)
    ml_outputs: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional external ML outputs supplied by teammate models.",
    )


class ProxyScores(BaseModel):
    accident_proxy: float
    mental_health_proxy: float
    physical_health_proxy: float


class RiskScoreResponse(BaseModel):
    user_id: str | None
    timestamp: datetime
    normalized_features: dict[str, float]
    feature_risk_values: dict[str, float]
    ml_outputs: dict[str, Any]
    proxy_scores: ProxyScores
    total_risk_score: float
    risk_level: str
    contribution: dict[str, Any]
    notes: list[str]
