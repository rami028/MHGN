#!/usr/bin/env python3

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor


# =========================================================
# CONFIG
# =========================================================

TARGETS = [
    "health_risk_score",
    "mental_risk_score",
    "accident_risk_score",
]

DROP_COLUMNS = [
    "subject_id",
    "risk_score_explanation",
]


CATEGORICAL_COLUMNS = []

TIME_COLUMNS = [
    "last_phone_log_time",
    "first_phone_log_time",
]


# =========================================================
# HELPERS
# =========================================================

def convert_time_to_minutes(time_str):
    """
    Converts HH:MM -> minutes since midnight
    Example:
    23:05 -> 1385
    """

    if pd.isna(time_str):
        return np.nan

    try:
        h, m = str(time_str).split(":")
        return int(h) * 60 + int(m)
    except:
        return np.nan


# =========================================================
# LOAD DATA
# =========================================================

def load_data(csv_path):

    df = pd.read_csv(csv_path)

    print(f"\nLoaded dataset shape: {df.shape}")

    return df


# =========================================================
# PREPROCESSING
# =========================================================

def preprocess_data(df):

    df = df.copy()

    # -----------------------------------------------------
    # Convert time columns
    # -----------------------------------------------------

    for col in TIME_COLUMNS:
        if col in df.columns:
            df[col + "_minutes"] = df[col].apply(convert_time_to_minutes)

    # Drop original time strings
    df = df.drop(columns=TIME_COLUMNS, errors="ignore")

    # Remove profile_type completely
    df = df.drop(columns=["profile_type"], errors="ignore")

    # -----------------------------------------------------
    # Fill missing numeric values
    # -----------------------------------------------------

    numeric_cols = df.select_dtypes(include=np.number).columns

    for col in numeric_cols:
        df[col] = df[col].fillna(df[col].median())

    return df


# =========================================================
# FEATURE ENGINEERING
# =========================================================

def feature_engineering(df):

    df = df.copy()

    # -----------------------------------------------------
    # Screen addiction proxy
    # -----------------------------------------------------

    df["screen_addiction_score"] = (
        df["total_screentime_hours"] * 0.4
        + df["time_spent_socialmedia_hours"] * 0.4
        + df["night_screentime_hours"] * 0.2
    )

    # -----------------------------------------------------
    # Activity ratio
    # -----------------------------------------------------

    df["activity_ratio"] = (
        df["mobility_time_hours"]
        / (df["resting_time_hours"] + 1e-6)
    )

    # -----------------------------------------------------
    # Sleep irregularity
    # -----------------------------------------------------

    df["sleep_irregularity_score"] = (
        df["var_sleep_time"]
        * (7 - df["avg_sleep_time_hours"])
    )

    # -----------------------------------------------------
    # Social interaction score
    # -----------------------------------------------------

    df["social_interaction_score"] = (
        df["number_calls"] * 0.3
        + df["number_messages"] * 0.7
    )

    # -----------------------------------------------------
    # Heart instability score
    # -----------------------------------------------------

    df["heart_instability_score"] = (
        df["var_heartrate"]
        * df["avg_heartrate_bpm"]
    )

    return df


# =========================================================
# TRAIN MODEL
# =========================================================

def train_model(df, target_name, output_dir):

    print(f"\n==============================")
    print(f"Training target: {target_name}")
    print(f"==============================")

    # -----------------------------------------------------
    # Features / Labels
    # -----------------------------------------------------

    X = df.drop(columns=TARGETS + DROP_COLUMNS, errors="ignore")
    joblib.dump(
        list(X.columns),
        "trained_models/feature_columns.pkl"
    )
    y = df[target_name]

    # -----------------------------------------------------
    # Train/Test Split
    # -----------------------------------------------------

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    # -----------------------------------------------------
    # Model
    # -----------------------------------------------------

    model = XGBRegressor(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42,
    )

    # -----------------------------------------------------
    # Train
    # -----------------------------------------------------

    model.fit(X_train, y_train)

    # -----------------------------------------------------
    # Predict
    # -----------------------------------------------------

    preds = model.predict(X_test)

    # -----------------------------------------------------
    # Metrics
    # -----------------------------------------------------

    mse = mean_squared_error(
        y_test,
        preds
    )

    rmse = np.sqrt(mse)

    r2 = r2_score(
        y_test,
        preds
    )

    print(f"\nRMSE: {rmse:.4f}")
    print(f"R²:   {r2:.4f}")

    # -----------------------------------------------------
    # Feature Importance
    # -----------------------------------------------------

    importance_df = pd.DataFrame({
        "feature": X.columns,
        "importance": model.feature_importances_
    })

    importance_df = importance_df.sort_values(
        by="importance",
        ascending=False
    )

    print("\nTop Features:")
    print(importance_df.head(15))

    # -----------------------------------------------------
    # Save model
    # -----------------------------------------------------

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    model_path = output_dir / f"{target_name}_xgboost_model.pkl"

    joblib.dump(model, model_path)

    print(f"\nSaved model: {model_path}")

    return model


# =========================================================
# MAIN
# =========================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--csv-path",
        default="test_dataset.csv"
    )

    parser.add_argument(
        "--output-dir",
        default="trained_models"
    )

    args = parser.parse_args()

    # -----------------------------------------------------
    # Load
    # -----------------------------------------------------

    df = load_data(args.csv_path)

    # -----------------------------------------------------
    # Preprocess
    # -----------------------------------------------------

    df = preprocess_data(df)

    # -----------------------------------------------------
    # Feature Engineering
    # -----------------------------------------------------

    df = feature_engineering(df)

    print("\nFinal dataset shape:", df.shape)

    # -----------------------------------------------------
    # Train all 3 models
    # -----------------------------------------------------

    for target in TARGETS:
        train_model(
            df=df,
            target_name=target,
            output_dir=args.output_dir
        )


if __name__ == "__main__":
    main()
