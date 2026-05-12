#!/usr/bin/env python3
"""Predict risk scores from pkl models.

Default mode keeps the old hard-coded demo user.
Use --input-json to predict from Android-collected feature JSON.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.app.risk_model import DEFAULT_TEST_USER, RiskPredictor, load_json_features


def print_report(result: dict) -> None:
    scores = result["risk_scores"]

    print("\n==============================")
    print("DIGITAL PHENOTYPE RISK REPORT")
    print("==============================")
    print(f"\nHealth Risk Score: {scores['health_risk_score']:.1f}/100")
    print(f"Mental Risk Score: {scores['mental_risk_score']:.1f}/100")
    print(f"Accident Risk Score: {scores['accident_risk_score']:.1f}/100")

    if result["missing_defaults_used"]:
        print("\nMissing/defaulted features:")
        for feature in result["missing_defaults_used"]:
            print(f"- {feature}")

    if scores["mental_risk_score"] > 70:
        print("\nMental Risk Analysis:")
        print("- Severe nighttime phone usage")
        print("- Low physical activity")
        print("- Irregular sleep patterns")

    if scores["health_risk_score"] > 70:
        print("\nHealth Risk Analysis:")
        print("- Elevated heart rate variability")
        print("- Sedentary behavior")
        print("- Poor sleep duration")

    if scores["accident_risk_score"] > 70:
        print("\nAccident Risk Analysis:")
        print("- Fatigue-related mobility pattern")
        print("- Reduced attention-related behavior")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-json",
        help="Path to feature JSON created by the Android demo app.",
    )
    parser.add_argument(
        "--output-json",
        help="Optional path to save prediction result JSON.",
    )
    args = parser.parse_args()

    if args.input_json:
        payload = load_json_features(args.input_json)
    else:
        payload = DEFAULT_TEST_USER

    predictor = RiskPredictor()
    result = predictor.predict(payload)
    print_report(result)

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)
        print(f"\nSaved result JSON: {output_path}")


if __name__ == "__main__":
    main()
