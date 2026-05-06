#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

import pandas as pd
from autogluon.tabular import TabularPredictor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


TARGET_COL = "stress_score"
USER_COL = "user_id"


def to_snake_case(name: str) -> str:
    name = str(name).strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name


def load_data(daily_path: str, stai_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    daily_df = pd.read_csv(daily_path)
    stai_df = pd.read_csv(stai_path)
    return daily_df, stai_df


def preprocess_data(daily_df: pd.DataFrame, stai_df: pd.DataFrame) -> pd.DataFrame:
    daily_df = daily_df.rename(columns={c: to_snake_case(c) for c in daily_df.columns})
    stai_df = stai_df.rename(columns={c: to_snake_case(c) for c in stai_df.columns})

    if "id" not in daily_df.columns:
        raise ValueError("daily file must contain `id`.")
    if "user_id" in stai_df.columns and "id" not in stai_df.columns:
        stai_df = stai_df.rename(columns={"user_id": "id"})
    if "id" not in stai_df.columns:
        raise ValueError("stai file must contain `id` or `user_id`.")

    # Keep only behavior/physiology fields aligned with your requested schema.
    daily_cols = [
        "id",
        "distance",
        "bpm",
        "lightly_active_minutes",
        "moderately_active_minutes",
        "very_active_minutes",
        "sedentary_minutes",
        "sleep_duration",
        "steps",
        "sleep_efficiency",
        "sleep_deep_ratio",
        "sleep_light_ratio",
        "sleep_rem_ratio",
    ]
    existing_daily_cols = [c for c in daily_cols if c in daily_df.columns]
    daily_df = daily_df[existing_daily_cols].copy()

    if "stai_stress" not in stai_df.columns:
        raise ValueError("stai file must contain `stai_stress`.")
    stai_df["stai_stress"] = pd.to_numeric(stai_df["stai_stress"], errors="coerce")
    stai_df = stai_df[["id", "stai_stress"]].dropna(subset=["id", "stai_stress"])

    # Aggregate per user so final table is user-centric (GLOBEM-like).
    numeric_daily = [c for c in daily_df.columns if c != "id"]
    for c in numeric_daily:
        daily_df[c] = pd.to_numeric(daily_df[c], errors="coerce")
    daily_user = daily_df.groupby("id", as_index=False)[numeric_daily].mean()

    label_user = stai_df.groupby("id", as_index=False)["stai_stress"].mean()

    merged = daily_user.merge(label_user, on="id", how="inner")
    merged = merged.rename(columns={"id": USER_COL, "stai_stress": TARGET_COL})

    # Unit conversion: ms/day -> hours/day
    if "sleep_duration" in merged.columns:
        merged["sleep_duration_hours"] = merged["sleep_duration"] / (1000 * 60 * 60)
        merged = merged.drop(columns=["sleep_duration"])

    # Simple median imputation for numeric features.
    feature_cols = [c for c in merged.columns if c not in [USER_COL, TARGET_COL]]
    for c in feature_cols:
        merged[c] = pd.to_numeric(merged[c], errors="coerce")
        merged[c] = merged[c].fillna(merged[c].median())

    merged[TARGET_COL] = pd.to_numeric(merged[TARGET_COL], errors="coerce")
    merged = merged.dropna(subset=[TARGET_COL]).reset_index(drop=True)
    return merged


def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    lightly = out.get("lightly_active_minutes", 0)
    moderate = out.get("moderately_active_minutes", 0)
    very = out.get("very_active_minutes", 0)
    sedentary = out.get("sedentary_minutes", 0)

    out["total_activity"] = lightly + moderate + very
    out["activity_ratio"] = out["total_activity"] / (out["total_activity"] + sedentary + 1e-6)

    eff = out.get("sleep_efficiency", 0)
    deep = out.get("sleep_deep_ratio", 0)
    rem = out.get("sleep_rem_ratio", 0)
    out["sleep_quality_score"] = 0.5 * eff + 0.25 * deep + 0.25 * rem

    if "bpm" in out.columns:
        bpm_std = out["bpm"].std(ddof=0)
        out["bpm_normalized"] = (out["bpm"] - out["bpm"].mean()) / (bpm_std + 1e-6)
        out = out.rename(columns={"bpm": "avg_bpm"})

    if "distance" in out.columns:
        out = out.rename(columns={"distance": "distance_meter_per_day"})
    if "steps" in out.columns:
        out = out.rename(columns={"steps": "steps_per_day"})

    ordered_front = [
        USER_COL,
        "distance_meter_per_day",
        "avg_bpm",
        "total_activity",
        "activity_ratio",
        "sleep_duration_hours",
        "sleep_quality_score",
        "steps_per_day",
    ]
    ordered_front = [c for c in ordered_front if c in out.columns]
    remaining = [c for c in out.columns if c not in ordered_front + [TARGET_COL]]
    out = out[ordered_front + remaining + [TARGET_COL]]
    return out


def train_model(
    df: pd.DataFrame,
    model_dir: str,
    test_size: float = 0.2,
    random_state: int = 42,
    time_limit: int = 300,
) -> tuple[TabularPredictor, pd.DataFrame, pd.DataFrame]:
    train_df, test_df = train_test_split(df, test_size=test_size, random_state=random_state)

    predictor = TabularPredictor(
        label=TARGET_COL,
        problem_type="regression",
        path=model_dir,
        eval_metric="root_mean_squared_error",
    )
    predictor.fit(train_df, presets="best_quality", time_limit=time_limit)
    return predictor, train_df, test_df


def evaluate_model(
    predictor: TabularPredictor, train_df: pd.DataFrame, test_df: pd.DataFrame
) -> dict:
    y_true = test_df[TARGET_COL]
    y_pred = predictor.predict(test_df)

    rmse = mean_squared_error(y_true, y_pred, squared=False)
    r2 = r2_score(y_true, y_pred)

    print("\n=== Evaluation ===")
    print(f"RMSE: {rmse:.4f}")
    print(f"R^2 : {r2:.4f}")

    print("\n=== Leaderboard ===")
    print(predictor.leaderboard(test_df, silent=True))

    print("\n=== Feature Importance ===")
    fi = predictor.feature_importance(data=test_df, silent=True)
    print(fi.head(20))

    return {"rmse": rmse, "r2": r2}


def main() -> None:
    parser = argparse.ArgumentParser(description="GLOBEM-style tabular pipeline with AutoGluon.")
    parser.add_argument(
        "--daily-path",
        default="rais_anonymized/csv_rais_anonymized/daily_fitbit_sema_df_unprocessed.csv",
    )
    parser.add_argument("--stai-path", default="rais_anonymized/scored_surveys/stai.csv")
    parser.add_argument("--processed-output", default="globem_style_tabular_dataset.csv")
    parser.add_argument("--model-dir", default="autogluon_stress_model")
    parser.add_argument("--time-limit", type=int, default=300)
    args = parser.parse_args()

    daily_df, stai_df = load_data(args.daily_path, args.stai_path)
    merged_df = preprocess_data(daily_df, stai_df)
    final_df = feature_engineering(merged_df)

    final_df.to_csv(args.processed_output, index=False)
    print(f"Saved processed dataset: {args.processed_output}")
    print(f"Final shape: {final_df.shape}")

    predictor, train_df, test_df = train_model(
        final_df, model_dir=args.model_dir, time_limit=args.time_limit
    )
    metrics = evaluate_model(predictor, train_df, test_df)
    print(f"\nModel saved to: {predictor.path}")
    print(f"Metrics: {metrics}")


if __name__ == "__main__":
    main()

