from __future__ import annotations

from fastapi import FastAPI

from app.ml_registry import ModelRegistry
from app.normalization import feature_risk_values, normalize_features
from app.risk_engine import compute_proxy_scores, risk_level
from app.schemas import RiskScoreRequest, RiskScoreResponse

app = FastAPI(
    title="Insurance Risk Proxy Backend",
    version="0.1.0",
    description=(
        "Feature-level backend for accident, mental-health, and physical-health "
        "risk proxy scoring. Current scoring is an MVP placeholder."
    ),
)
registry = ModelRegistry()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/risk-score", response_model=RiskScoreResponse)
def risk_score(request: RiskScoreRequest) -> RiskScoreResponse:
    normalized = normalize_features(request.features)
    feature_risks = feature_risk_values(request.features, normalized)

    ml_outputs = registry.predict_all(
        features=request.features,
        normalized=normalized,
        feature_risks=feature_risks,
        external_outputs=request.ml_outputs,
    )

    proxy_scores, contribution = compute_proxy_scores(
        feature_risks=feature_risks,
        ml_outputs=ml_outputs,
    )
    total = contribution["total_risk_score"]

    notes = [
        "MVP score only: weights and thresholds are not clinically or actuarially validated.",
        "Unknown features are passed to adapters but are not normalized unless added to config/feature_ranges.yaml.",
        "External teammate ML outputs override placeholder adapter values when matching output keys are supplied.",
    ]

    return RiskScoreResponse(
        user_id=request.user_id,
        timestamp=request.timestamp,
        normalized_features=normalized,
        feature_risk_values=feature_risks,
        ml_outputs=ml_outputs,
        proxy_scores=proxy_scores,
        total_risk_score=total,
        risk_level=risk_level(total),
        contribution=contribution,
        notes=notes,
    )
