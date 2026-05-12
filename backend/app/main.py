"""FastAPI server that receives Android feature JSON and returns risk scores."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from .risk_model import RiskPredictor


app = FastAPI(title="MHGN Experimental Risk API")
predictor = RiskPredictor()

RECEIVED_DIR = Path(__file__).resolve().parents[1] / "received_features"
RECEIVED_DIR.mkdir(parents=True, exist_ok=True)
LATEST_FEATURE_PATH = RECEIVED_DIR / "latest_user_features.json"
LATEST_RESULT_PATH = RECEIVED_DIR / "latest_risk_result.json"


@app.get("/health")
def health() -> dict[str, str]:
    """Simple server health check."""
    return {"status": "ok"}


@app.post("/predict-risk")
def predict_risk(payload: dict[str, Any]) -> dict[str, Any]:
    """Save Android feature JSON, run pkl models, and return risk scores."""
    received_at = datetime.now(timezone.utc).isoformat()
    payload_with_meta = dict(payload)
    payload_with_meta["server_received_at"] = received_at

    with LATEST_FEATURE_PATH.open("w", encoding="utf-8") as file:
        json.dump(payload_with_meta, file, ensure_ascii=False, indent=2)

    result = predictor.predict(payload)
    result["received_at"] = received_at
    result["feature_json_saved_to"] = str(LATEST_FEATURE_PATH)

    with LATEST_RESULT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    return result
