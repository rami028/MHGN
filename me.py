import joblib
import pandas as pd


# =========================================================
# LOAD MODELS
# =========================================================

health_model = joblib.load(
    "trained_models/health_risk_score_xgboost_model.pkl"
)

mental_model = joblib.load(
    "trained_models/mental_risk_score_xgboost_model.pkl"
)

accident_model = joblib.load(
    "trained_models/accident_risk_score_xgboost_model.pkl"
)


# =========================================================
# REAL-LIFE TEST USER
# =========================================================

test_user = {
    "total_screentime_hours": 10,
    "time_spent_socialmedia_hours": 22/7,
    "time_spent_game_hours": 0,

    "last_phone_log_time_minutes": 1500,   # 1:00 AM
    "first_phone_log_time_minutes": 420,   # 7:00 AM

    "night_screentime_hours": 4,

    "number_calls": 11,
    "total_call_duration_minutes": 50,

    "number_messages": 303/7,
    "variance_call_duration": 10,

    "mobility_time_hours": 8,
    "resting_time_hours": 6,

    "avg_sleep_time_hours": 6,
    "var_sleep_time": 2,

    "avg_heartrate_bpm": 89,
    "var_heartrate": 17,

    "number_steps": 13000,
    "distance_traveled_km": 6.72,

    # -----------------------------------------------------
    # ENGINEERED FEATURES
    # MUST MATCH TRAINING PIPELINE
    # -----------------------------------------------------

    "screen_addiction_score":
        10 * 0.4 +
        22/7 * 0.4 +
        4 * 0.2,

    "activity_ratio":
        8 / 6,

    "sleep_irregularity_score":
        2 * (7 - 6),

    "social_interaction_score":
        11 * 0.3 +
        303/7 * 0.7,

    "heart_instability_score":
        17 * 89,
}


# =========================================================
# CONVERT TO DATAFRAME
# =========================================================

feature_columns = joblib.load(
    "trained_models/feature_columns.pkl"
)

input_df = pd.DataFrame([test_user])

input_df = input_df[feature_columns]

# =========================================================
# PREDICT
# =========================================================

health_score = health_model.predict(input_df)[0]
mental_score = mental_model.predict(input_df)[0]
accident_score = accident_model.predict(input_df)[0]


# =========================================================
# OUTPUT
# =========================================================

print("\n==============================")
print("DIGITAL PHENOTYPE RISK REPORT")
print("==============================")

print(f"\nHealth Risk Score:   {health_score:.1f}/100")
print(f"Mental Risk Score:   {mental_score:.1f}/100")
print(f"Accident Risk Score: {accident_score:.1f}/100")


# =========================================================
# SIMPLE INTERPRETATION
# =========================================================

if mental_score > 70:
    print("\nMental Risk Analysis:")
    print("- Severe nighttime phone usage")
    print("- Low physical activity")
    print("- Irregular sleep patterns")

if health_score > 70:
    print("\nHealth Risk Analysis:")
    print("- Elevated heart rate variability")
    print("- Sedentary behavior")
    print("- Poor sleep duration")

if accident_score > 70:
    print("\nAccident Risk Analysis:")
    print("- Fatigue-related mobility pattern")
    print("- Reduced attention-related behavior")