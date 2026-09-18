"""
preprocessing.py
-----------------
Takes the 3 raw CSVs and produces ONE clean, merged DataFrame that
Person 2 (mastery/weakness engine) and Person 3 (planner/ML) can build
directly on top of. Also saves it to clean_attempts.csv.

WHY PANDAS:
    We need to join 3 relational tables (students, questions, attempts),
    handle missing/bad values, parse timestamps, and compute derived
    columns (recency, correctness flags, time buckets). Pandas gives us
    vectorized operations for all of this instead of writing manual
    nested loops over CSV rows -- faster to write, faster to run, and
    it's the standard tool the rest of the ML stack (scikit-learn,
    Random Forest in Person 3's module) expects data in.

PIPELINE STEPS (in order):
    1. Load raw CSVs
    2. Parse timestamps -> datetime, drop rows where it fails
    3. Fix bad numeric values (negative/missing time_taken_seconds)
    4. Drop exact duplicate attempt rows
    5. Merge attempts + questions + students into one wide table
    6. Feature engineering:
        - is_correct as int (0/1) -- already numeric but we assert it
        - days_since_attempt (recency)
        - recency_weight (exponential decay -- newer attempts matter more)
        - time_taken_bucket (fast / normal / slow, relative to difficulty)
        - attempt_order (per student per topic, useful for "repeated error" logic)
    7. Basic sanity report (row counts before/after, null counts)
"""

import pandas as pd
import numpy as np
from datetime import datetime

RAW_STUDENTS = "students.csv"
RAW_QUESTIONS = "questions.csv"
RAW_ATTEMPTS = "attempts.csv"
OUTPUT_CLEAN = "clean_attempts.csv"

RECENCY_HALF_LIFE_DAYS = 10  # after 10 days, an attempt's recency weight halves


def load_raw():
    students = pd.read_csv(RAW_STUDENTS, parse_dates=["join_date"])
    questions = pd.read_csv(RAW_QUESTIONS)
    attempts = pd.read_csv(RAW_ATTEMPTS)
    return students, questions, attempts


def clean_attempts(attempts: pd.DataFrame) -> pd.DataFrame:
    n_start = len(attempts)

    # --- 1. Parse timestamps; rows with unparseable/blank timestamps are
    #        useless for recency analysis, so we drop them (and log how many) ---
    attempts["timestamp"] = pd.to_datetime(attempts["timestamp"], errors="coerce")
    n_bad_timestamp = attempts["timestamp"].isna().sum()
    attempts = attempts.dropna(subset=["timestamp"])

    # --- 2. Fix time_taken_seconds ---
    # Negative values are impossible (bad sensor/logging glitch) -> treat as missing.
    attempts.loc[attempts["time_taken_seconds"] < 0, "time_taken_seconds"] = np.nan
    n_missing_time = attempts["time_taken_seconds"].isna().sum()
    # Impute missing time with the median time for that difficulty level,
    # rather than a global median -- a difficulty-5 question naturally takes
    # longer than a difficulty-1 question, so a single global number would bias things.
    attempts["time_taken_seconds"] = attempts.groupby("difficulty")["time_taken_seconds"] \
        .transform(lambda s: s.fillna(s.median()))

    # --- 3. Drop exact duplicate rows (same student, question, timestamp) ---
    n_before_dupes = len(attempts)
    attempts = attempts.drop_duplicates(
        subset=["student_id", "question_id", "timestamp"], keep="first"
    )
    n_dupes_removed = n_before_dupes - len(attempts)

    # --- 4. Ensure correctness flag is a clean 0/1 int ---
    attempts["is_correct"] = attempts["is_correct"].astype(int)

    print("---- Cleaning report ----")
    print(f"Raw attempts:                 {n_start}")
    print(f"Dropped (bad timestamp):      {n_bad_timestamp}")
    print(f"Imputed (missing/bad time):   {n_missing_time}")
    print(f"Dropped (exact duplicates):   {n_dupes_removed}")
    print(f"Final clean attempts:         {len(attempts)}")
    print("--------------------------")

    return attempts.reset_index(drop=True)


def engineer_features(attempts: pd.DataFrame, questions: pd.DataFrame,
                       students: pd.DataFrame) -> pd.DataFrame:
    # --- Merge into one wide table ---
    df = attempts.merge(
        questions[["question_id", "prerequisite_topics", "correct_option"]],
        on="question_id", how="left"
    )
    df = df.merge(
        students[["student_id", "grade", "exam_goal", "available_minutes_per_day"]],
        on="student_id", how="left"
    )

    # --- Recency weighting ---
    # Newer attempts should count more toward "current" mastery than
    # something the student got right a month ago. Exponential decay
    # is the standard way to do this (half-life in days).
    now = pd.Timestamp.now()
    df["days_since_attempt"] = (now - df["timestamp"]).dt.total_seconds() / 86400
    df["recency_weight"] = 0.5 ** (df["days_since_attempt"] / RECENCY_HALF_LIFE_DAYS)

    # --- Time-taken bucket, relative to difficulty ---
    # A flat "fast/slow" cutoff doesn't make sense across difficulty 1 vs 5,
    # so we bucket within each difficulty level using quantiles.
    def bucket_by_difficulty(group):
        try:
            return pd.qcut(group, q=3, labels=["fast", "normal", "slow"])
        except ValueError:
            # not enough distinct values in this group to form 3 buckets
            return pd.Series(["normal"] * len(group), index=group.index)

    df["time_taken_bucket"] = df.groupby("difficulty")["time_taken_seconds"] \
        .transform(bucket_by_difficulty)

    # --- Attempt order per student per topic ---
    # Needed for "repeated error" detection (Person 2): did they keep
    # getting the SAME topic wrong across consecutive attempts?
    df = df.sort_values(["student_id", "topic", "timestamp"])
    df["attempt_order_in_topic"] = df.groupby(["student_id", "topic"]).cumcount() + 1

    df = df.reset_index(drop=True)
    return df


if __name__ == "__main__":
    students, questions, attempts = load_raw()
    clean = clean_attempts(attempts)
    final = engineer_features(clean, questions, students)

    final.to_csv(OUTPUT_CLEAN, index=False)
    print(f"\nSaved clean, feature-engineered dataset -> {OUTPUT_CLEAN}")
    print(f"Shape: {final.shape}")
    print("\nColumns:")
    print(list(final.columns))
    print("\nSample rows:")
    print(final.head(3).to_string())
