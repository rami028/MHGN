#!/usr/bin/env python3
"""
extract_feature_vector.py
-------------------------
Builds a structured daily feature vector for each user by fusing two datasets:

  1. 1000ppl_dataset.csv
       Synthetic mobile-usage dataset (1 000 users).
       Provides app-usage and screen-time fields:
         Daily_Screen_Time_Hours, Social_Media_Usage_Hours,
         Gaming_App_Usage_Hours, Number_of_Apps_Used.

  2. dartmouth_dataset/
       Real passive-sensing data from the Dartmouth StudentLife study
       (≈60 participants, ~10 weeks longitudinal).
       Sub-folders used:
         call_log/       – timestamped call events with duration
         sms/            – timestamped SMS records
         sensing/gps/    – GPS fixes with latitude, longitude, travelstate
         sensing/dark/   – phone-screen-off intervals (proxy for idle/rest)
         sensing/activity/ – activity-inference labels per timestamp
         EMA/response/Sleep/ – self-reported sleep hours per response session

Because Dartmouth only has 60 participants and 1000ppl has 1 000 rows,
Dartmouth sensing streams are mapped to 1000ppl users via modulo 60
(user_id 1 → u00, user_id 61 → u00, etc.).  This means groups of ~17
1000ppl rows share the same Dartmouth sensing cache; their
app-usage columns (screentime, SNS, game) still come from 1000ppl.

All temporal features are reduced to a per-day average so the vector
represents a single representative day rather than a lifetime total.

Output columns match the feature vector diagram:
  Addiction  – total_screentime, time_spent_SNS, time_spent_game,
               last_phone_log, first_phone_log, night_screentime
  Social     – number_calls, total_call_duration,
               number_messages, variance_call_duration
  Mobility   – mobility_time, resting_time
  Sleep      – avg_sleep_time, var_sleep_time
  Physiology – avg_heartrate*, var_heartrate*, number_steps, distance_traveled

  * heartrate is not available in either dataset; columns are retained as NaN
    so the schema is compatible with the on-device model interface.
"""
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


FEATURE_COLUMNS = [
    "total_screentime",
    "time_spent_SNS",
    "time_spent_game",
    "last_phone_log",
    "first_phone_log",
    "night_screentime",
    "number_calls",
    "total_call_duration",
    "number_messages",
    "variance_call_duration",
    "mobility_time",
    "resting_time",
    "avg_sleep_time",
    "var_sleep_time",
    "avg_heartrate",
    "var_heartrate",
    "number_steps",
    "distance_traveled",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract feature vectors by combining all datasets."
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Directory containing all datasetss/",
    )
    parser.add_argument(
        "--output",
        default="feature_vectors.csv",
        help="Output CSV path.",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=None,
        help="Optional 1-based user id to export only one row.",
    )
    return parser.parse_args()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance (km) between two WGS-84 coordinates."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def to_float(value: str) -> float:
    """Convert any value to float; return NaN on failure instead of raising."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def safe_mean(values: list[float]) -> float:
    """Mean of a list, ignoring NaN values. Returns NaN when list is empty."""
    clean = [v for v in values if not math.isnan(v)]
    if not clean:
        return float("nan")
    return sum(clean) / len(clean)


def safe_var(values: list[float]) -> float:
    """Population variance ignoring NaN values. Returns NaN when < 2 values."""
    clean = [v for v in values if not math.isnan(v)]
    if len(clean) < 2:
        return float("nan")
    mean_val = sum(clean) / len(clean)
    return sum((v - mean_val) ** 2 for v in clean) / len(clean)


def day_bucket(timestamp_seconds: float) -> int:
    """Map a Unix timestamp (seconds) to an integer day index (days since epoch)."""
    return int(timestamp_seconds // 86400)


def extract_sleep_stats(sleep_file: Path) -> tuple[float, float]:
    """
    Parse the Dartmouth EMA Sleep JSON and return (avg_sleep_hours, var_sleep_hours).

    Each JSON record may contain:
      "hour"      – self-reported hours slept that night
      "resp_time" – Unix timestamp of the EMA response

    Strategy:
      1. Group all valid "hour" responses by calendar day (via resp_time).
      2. Average multiple responses within the same day to get one
         representative value per day.
      3. Return the mean and population variance of those daily values.

    Values outside [0, 24] are discarded as data artifacts.
    """
    if not sleep_file.exists():
        return float("nan"), float("nan")
    with sleep_file.open("r", encoding="utf-8") as f:
        records = json.load(f)
    daily_hours: dict[int, list[float]] = defaultdict(list)
    for row in records:
        if "hour" not in row or "resp_time" not in row:
            continue
        hour_val = to_float(row.get("hour"))
        resp_time = to_float(row.get("resp_time"))
        if math.isnan(hour_val) or math.isnan(resp_time):
            continue
        # Keep only realistic daily sleep duration answers.
        if 0.0 <= hour_val <= 24.0:
            daily_hours[day_bucket(resp_time)].append(hour_val)
    if not daily_hours:
        return float("nan"), float("nan")
    per_day_sleep = [safe_mean(values) for values in daily_hours.values()]
    return safe_mean(per_day_sleep), safe_var(per_day_sleep)


def extract_user_features(base_dir: Path, user_idx: int, ppl_row: dict) -> dict:
    """
    Compute all 18 feature-vector fields for one Dartmouth participant.

    Parameters
    ----------
    base_dir  : project root (contains both datasets)
    user_idx  : Dartmouth participant index 0-59 (mapped from 1000ppl user_id)
    ppl_row   : dict row from 1000ppl_dataset.csv for this user

    Returns a flat dict whose keys match FEATURE_COLUMNS plus 'user_id'.

    Feature computation overview
    ----------------------------
    Addiction domain
      total_screentime  – from 1000ppl Daily_Screen_Time_Hours
                          (clamped up so it is always ≥ SNS + game time)
      time_spent_SNS    – from 1000ppl Social_Media_Usage_Hours
      time_spent_game   – from 1000ppl Gaming_App_Usage_Hours
      first_phone_log   – earliest call/SMS timestamp on the busiest day
      last_phone_log    – latest  call/SMS timestamp on the busiest day
      night_screentime  – total_screentime × fraction of phone events 00:00-06:00

    Social domain
      number_calls          – average daily call count across observed days
      total_call_duration   – average daily total call duration (seconds)
      number_messages       – average daily SMS count
      variance_call_duration – mean of per-day call-duration variances

    Mobility domain
      mobility_time    – average daily hours spent in GPS "moving" state
      resting_time     – average daily hours phone screen was off (dark sensor)

    Sleep domain
      avg_sleep_time   – mean daily self-reported sleep hours (EMA)
      var_sleep_time   – population variance of daily sleep hours

    Physiological domain (partially unavailable in these datasets)
      avg_heartrate    – NaN (no wearable stream present)
      var_heartrate    – NaN
      number_steps     – average daily active-inference event count (proxy)
      distance_traveled – average daily GPS distance (km)
    """
    uid = f"u{user_idx:02d}"
    dartmouth = base_dir / "dartmouth_dataset"

    call_file = dartmouth / "call_log" / f"call_log_{uid}.csv"
    sms_file = dartmouth / "sms" / f"sms_{uid}.csv"
    gps_file = dartmouth / "sensing" / "gps" / f"gps_{uid}.csv"
    dark_file = dartmouth / "sensing" / "dark" / f"dark_{uid}.csv"
    activity_file = dartmouth / "sensing" / "activity" / f"activity_{uid}.csv"

    sleep_avg, sleep_var = extract_sleep_stats(
        dartmouth / "EMA" / "response" / "Sleep" / f"Sleep_{uid}.json"
    )

    # ------------------------------------------------------------------
    # SOCIAL DOMAIN — calls and messages
    # CALLS_date is in milliseconds; convert to seconds for day_bucket.
    # calls_by_day maps each calendar day → list of call durations (seconds).
    # ------------------------------------------------------------------
    event_times: list[int] = []
    event_times_by_day: dict[int, list[int]] = defaultdict(list)
    calls_by_day: dict[int, list[float]] = defaultdict(list)
    if call_file.exists():
        with call_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                call_date = to_float(row.get("CALLS_date"))
                if math.isnan(call_date):
                    continue
                call_duration = to_float(row.get("CALLS_duration"))
                if math.isnan(call_duration):
                    call_duration = 0.0
                ts = int(call_date // 1000)
                day = day_bucket(ts)
                calls_by_day[day].append(call_duration)
                event_times.append(ts)
                event_times_by_day[day].append(ts)

    # messages_by_day maps each calendar day → SMS count.
    messages_by_day: dict[int, int] = defaultdict(int)
    if sms_file.exists():
        with sms_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sms_date = to_float(row.get("MESSAGES_date"))
                if math.isnan(sms_date):
                    continue
                ts = int(sms_date // 1000)
                day = day_bucket(ts)
                messages_by_day[day] += 1
                event_times.append(ts)
                event_times_by_day[day].append(ts)

    # Reduce to daily averages so all social features are on a one-day scale.
    if calls_by_day:
        number_calls = safe_mean([float(len(v)) for v in calls_by_day.values()])
        total_call_duration = safe_mean([sum(v) for v in calls_by_day.values()])
        # Mean of per-day variances captures within-day call duration spread.
        variance_call_duration = safe_mean([safe_var(v) for v in calls_by_day.values()])
    else:
        number_calls = 0.0
        total_call_duration = 0.0
        variance_call_duration = float("nan")
    number_messages = (
        safe_mean([float(v) for v in messages_by_day.values()]) if messages_by_day else 0.0
    )

    # ------------------------------------------------------------------
    # ADDICTION DOMAIN — phone-log timing and night usage ratio
    # Use the busiest single day (most events) as the representative day
    # for first/last phone log, to avoid cross-day timestamp artifacts.
    # ------------------------------------------------------------------
    if event_times:
        representative_day = max(
            event_times_by_day.keys(), key=lambda d: len(event_times_by_day[d])
        )
        day_events = event_times_by_day[representative_day]
        first_phone_log = float(min(day_events))
        last_phone_log = float(max(day_events))
        # Night ratio: fraction of phone events between midnight and 6 AM.
        night_events = 0
        for ts in day_events:
            hour = (int(ts) % 86400) // 3600
            if 0 <= hour < 6:
                night_events += 1
        night_ratio = night_events / len(day_events)
    else:
        first_phone_log = float("nan")
        last_phone_log = float("nan")
        night_ratio = 0.0

    # Screen-time fields come from 1000ppl; enforce the hard constraint
    # that total_screentime ≥ SNS_time + game_time (they are sub-categories).
    sns_time = to_float(ppl_row["Social_Media_Usage_Hours"])
    game_time = to_float(ppl_row["Gaming_App_Usage_Hours"])
    total_screentime = to_float(ppl_row["Daily_Screen_Time_Hours"])
    if not math.isnan(sns_time) and not math.isnan(game_time):
        total_screentime = max(total_screentime, sns_time + game_time)
    # night_screentime = total daily screen time × night-phone-event fraction.
    night_screentime = total_screentime * night_ratio

    # ------------------------------------------------------------------
    # MOBILITY DOMAIN — GPS movement and daily distance
    # GPS fixes arrive roughly every 20 min; consecutive fixes are linked
    # into segments.  A segment is counted as "moving time" only when
    # the travelstate of the later fix is "moving" and the gap is < 1 h
    # (avoids bridging overnight gaps).  Distance is always accumulated
    # regardless of travelstate.  Both are averaged per calendar day.
    # ------------------------------------------------------------------
    mobility_seconds_by_day: dict[int, float] = defaultdict(float)
    distance_by_day: dict[int, float] = defaultdict(float)
    if gps_file.exists():
        points: list[tuple[float, float, float, str]] = []
        with gps_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                t = to_float(row.get("time"))
                lat = to_float(row.get("latitude"))
                lon = to_float(row.get("longitude"))
                if any(math.isnan(v) for v in [t, lat, lon]):
                    continue
                points.append((t, lat, lon, str(row.get("travelstate", "")).lower()))
        points.sort(key=lambda x: x[0])
        for i in range(1, len(points)):
            t0, lat0, lon0, _ = points[i - 1]
            t1, lat1, lon1, state = points[i]
            dt = t1 - t0
            # Ignore segments longer than 1 hour (likely an overnight gap).
            if not (0 < dt < 3600):
                continue
            day = day_bucket(t1)
            if state == "moving":
                mobility_seconds_by_day[day] += dt
            distance_by_day[day] += haversine_km(lat0, lon0, lat1, lon1)
    mobility_time = (
        safe_mean([v / 3600.0 for v in mobility_seconds_by_day.values()])
        if mobility_seconds_by_day
        else 0.0
    )
    distance_traveled = (
        safe_mean(list(distance_by_day.values())) if distance_by_day else 0.0
    )

    # ------------------------------------------------------------------
    # MOBILITY DOMAIN — resting time (phone screen-off intervals)
    # The "dark" sensor records [start, end] Unix timestamps when the
    # phone screen was off.  Segments spanning midnight are split into
    # their respective calendar days before accumulating.
    # ------------------------------------------------------------------
    resting_seconds_by_day: dict[int, float] = defaultdict(float)
    if dark_file.exists():
        with dark_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                s = to_float(row.get("start"))
                e = to_float(row.get("end"))
                if any(math.isnan(v) for v in [s, e]):
                    continue
                if e > s:
                    start_day = day_bucket(s)
                    end_day = day_bucket(e)
                    if start_day == end_day:
                        resting_seconds_by_day[start_day] += (e - s)
                    else:
                        # Split at midnight boundary.
                        day_end = (start_day + 1) * 86400
                        resting_seconds_by_day[start_day] += max(0.0, day_end - s)
                        resting_seconds_by_day[end_day] += max(0.0, e - (end_day * 86400))
    resting_time = (
        safe_mean([v / 3600.0 for v in resting_seconds_by_day.values()])
        if resting_seconds_by_day
        else 0.0
    )

    # ------------------------------------------------------------------
    # PHYSIOLOGICAL DOMAIN — step proxy via activity inference
    # Dartmouth does not have a pedometer stream.  The activity-inference
    # column (0 = stationary, >0 = active) is used as a coarse proxy:
    # we count the number of active samples per day and average them.
    # The column name has a leading space in the raw CSV header.
    # ------------------------------------------------------------------
    number_steps = float("nan")
    if activity_file.exists():
        activity_counts_by_day: dict[int, int] = defaultdict(int)
        with activity_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Column name includes a leading space in this dataset.
                v = to_float(row.get(" activity inference"))
                ts = to_float(row.get("timestamp"))
                if not math.isnan(v) and v > 0 and not math.isnan(ts):
                    activity_counts_by_day[day_bucket(ts)] += 1
        if activity_counts_by_day:
            number_steps = safe_mean([float(v) for v in activity_counts_by_day.values()])

    # avg_heartrate / var_heartrate are included to maintain schema compatibility
    # with the on-device model interface, but remain NaN because neither the
    # 1000ppl dataset nor the Dartmouth GPS/activity streams contain heart-rate
    # data.  These will be populated once a wearable API (Google Fit / Health
    # Connect) is integrated in the Android pipeline.
    return {
        "user_id": int(float(ppl_row["User_ID"])),
        "total_screentime": total_screentime,
        "time_spent_SNS": sns_time,
        "time_spent_game": game_time,
        "last_phone_log": last_phone_log,
        "first_phone_log": first_phone_log,
        "night_screentime": night_screentime,
        "number_calls": number_calls,
        "total_call_duration": total_call_duration,
        "number_messages": number_messages,
        "variance_call_duration": variance_call_duration,
        "mobility_time": mobility_time,
        "resting_time": resting_time,
        "avg_sleep_time": sleep_avg,
        "var_sleep_time": sleep_var,
        "avg_heartrate": float("nan"),
        "var_heartrate": float("nan"),
        "number_steps": number_steps,
        "distance_traveled": float(distance_traveled),
    }


def main() -> None:
    args = parse_args()
    base_dir = Path(args.base_dir).resolve()
    ppl_file = base_dir / "1000ppl_dataset.csv"
    if not ppl_file.exists():
        raise FileNotFoundError(f"Could not find {ppl_file}")

    with ppl_file.open("r", encoding="utf-8") as f:
        ppl_rows = list(csv.DictReader(f))

    # Optional single-user filter for quick inspection / debugging.
    if args.user_id is not None:
        ppl_rows = [r for r in ppl_rows if int(float(r["User_ID"])) == args.user_id]
        if not ppl_rows:
            raise ValueError(f"User_ID {args.user_id} not found in 1000ppl_dataset.csv")

    rows: list[dict] = []
    # Cache Dartmouth sensing results by participant index (0-59) so each
    # file is only read once even though multiple 1000ppl users share it.
    user_cache: dict[int, dict] = {}
    for row in ppl_rows:
        # Map 1000ppl user_id (1-based) → Dartmouth index (0-based, mod 60).
        user_idx = (int(float(row["User_ID"])) - 1) % 60
        if user_idx not in user_cache:
            user_cache[user_idx] = extract_user_features(base_dir, user_idx, row)

        # Clone the cached sensing features and overwrite the fields that
        # must come from this specific 1000ppl row (app-usage and screen time).
        base_features = dict(user_cache[user_idx])
        total_screentime = to_float(row["Daily_Screen_Time_Hours"])
        sns_time = to_float(row["Social_Media_Usage_Hours"])
        game_time = to_float(row["Gaming_App_Usage_Hours"])
        # Re-apply the SNS+game ≥ total_screentime constraint for this row.
        if not math.isnan(sns_time) and not math.isnan(game_time):
            total_screentime = max(total_screentime, sns_time + game_time)
        # Recover the night-usage ratio from the cached Dartmouth sensing data
        # and scale it by this row's total_screentime.
        base_total = base_features["total_screentime"]
        if isinstance(base_total, float) and not math.isnan(base_total) and base_total > 0:
            night_ratio = base_features["night_screentime"] / base_total
        else:
            night_ratio = 0.0
        base_features["user_id"] = int(float(row["User_ID"]))
        base_features["total_screentime"] = total_screentime
        base_features["time_spent_SNS"] = sns_time
        base_features["time_spent_game"] = game_time
        base_features["night_screentime"] = total_screentime * night_ratio
        rows.append(base_features)

    output_path = base_dir / args.output
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["user_id", *FEATURE_COLUMNS])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"Saved {len(rows)} feature vectors to {output_path}")


if __name__ == "__main__":
    main()
