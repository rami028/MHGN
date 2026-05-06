# Insurance Risk Proxy Backend

Feature-level prototype backend for a student insurance-innovation project.

This backend assumes the app has already transformed raw Android / wearable records into feature values. Later, the `raw_pipeline.py` module can be expanded to do raw → feature processing.

## What this does now

1. Receives precomputed features from the frontend or data pipeline.
2. Runs placeholder ML adapters organized by **risk category**, not dataset name:
   - `social_isolation`: social / isolation proxy
   - `attention_productivity`: attention, productivity, task-disturbance proxy
   - `digital_overuse`: screen-time / phone-overuse proxy
   - `mental_health`: depression / mental-health proxy
   - `activity_physical_health`: activity and physical-health proxy
   - `transport_mode`: transport-mode and accident-context proxy
3. Normalizes numeric features to `0~1` by configured min-max ranges.
4. Produces three proxy risk scores:
   - `accident_proxy`
   - `mental_health_proxy`
   - `physical_health_proxy`
5. Produces an experimental `total_risk_score`.

## Important caveat

The current scoring is **not actuarially valid** and **not clinically valid**. It is an MVP algorithm so the frontend and product-planning flow can move forward while ML teammates finalize actual model outputs.

## Run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Example request

```bash
curl -X POST http://127.0.0.1:8000/v1/risk-score \
  -H "Content-Type: application/json" \
  -d @examples/request.json
```

## External ML output contract

Prefer category-based keys in `ml_outputs`:

```json
{
  "social_isolation_score": 0.31,
  "attention_productivity_risk": 0.27,
  "attention_low_probability": 0.30,
  "task_disturbance_probability": 0.25,
  "stress_probability": 0.35,
  "digital_overuse_model_risk": 0.44,
  "mental_health_risk": 0.22,
  "depression_probability": 0.22,
  "activity_level_score": 0.74,
  "physical_health_risk": 0.21,
  "transport_mode": "walking",
  "transport_context_risk": 0.12
}
```

Older dataset-named keys such as `globem_depression_probability`, `lifesnaps_physical_health_risk`, `collecty_transport_risk`, and `kemophone_stress_probability` are still accepted as compatibility aliases, but new frontend/backend code should avoid them.

## Model integration plan

The adapter interface is intentionally simple:

```python
adapter.predict(
    features: dict,
    normalized: dict,
    feature_risks: dict,
    external_outputs: dict | None = None,
) -> dict
```

When a teammate prepares a real model, replace the placeholder logic inside the matching category adapter file.

Dataset choices are implementation details inside each adapter:

- `mental_health.py` can wrap GLOBEM-style depression detection
- `social_isolation.py` can use StudentLife-style sociability features
- `attention_productivity.py` can use K-EmoPhone or StudentLife-style labels
- `activity_physical_health.py` can use LifeSnaps-style wearable features
- `transport_mode.py` can use Collecty-style transport classification

## Main files

```text
app/main.py                         FastAPI endpoints
app/schemas.py                      Request/response schemas
app/normalization.py                0~1 feature normalization
app/risk_engine.py                  Proxy risk-score algorithm
app/adapters/social_isolation.py    Social / isolation adapter slot
app/adapters/attention_productivity.py
app/adapters/digital_overuse.py
app/adapters/mental_health.py
app/adapters/activity_physical_health.py
app/adapters/transport_mode.py
config/feature_ranges.yaml          Feature ranges and risk direction
config/risk_weights.yaml            Category/model weights
examples/request.json               Sample payload
```
