"""
backend/data_loader.py — CSV Data Loading Helper
==================================================
OWNER: Person 6 (Backend + Integration)

PURPOSE:
    Centralized CSV loading so all routes use the same data source.
    Uses pathlib for safe file paths that work on any OS / working directory.

WHY THIS FILE EXISTS:
    - Routes shouldn't each have their own CSV loading code (duplication)
    - File paths must work regardless of where you start the server from
    - When Person 1 changes CSV format or we switch to Supabase,
      we only change THIS file — routes stay untouched

FUNCTIONS:
    load_students()           → DataFrame of all students
    load_questions()          → DataFrame of all questions
    load_attempts()           → DataFrame of all attempts (raw)
    load_clean_attempts()     → DataFrame of preprocessed attempts
                                (auto-builds from raw if missing)
    save_attempt()            → Appends one new attempt to attempts.csv
    refresh_clean_attempts()  → Re-runs Person 1's preprocessing pipeline
                                and saves fresh clean_attempts.csv
"""

import pandas as pd
import sys
import os
from pathlib import Path
from datetime import datetime

# ============================================================
# SAFE FILE PATHS
# ============================================================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

STUDENTS_CSV       = DATA_DIR / "students.csv"
QUESTIONS_CSV      = DATA_DIR / "questions.csv"
ATTEMPTS_CSV       = DATA_DIR / "attempts.csv"
CLEAN_ATTEMPTS_CSV = DATA_DIR / "clean_attempts.csv"


# ============================================================
# LOAD STUDENTS
# ============================================================
def load_students() -> pd.DataFrame:
    if not STUDENTS_CSV.exists():
        print(f"WARNING: {STUDENTS_CSV} not found")
        return pd.DataFrame()
    return pd.read_csv(STUDENTS_CSV)


# ============================================================
# LOAD QUESTIONS
# ============================================================
def load_questions() -> pd.DataFrame:
    if not QUESTIONS_CSV.exists():
        print(f"WARNING: {QUESTIONS_CSV} not found")
        return pd.DataFrame()
    return pd.read_csv(QUESTIONS_CSV)


# ============================================================
# LOAD ATTEMPTS (raw)
# ============================================================
def load_attempts() -> pd.DataFrame:
    if not ATTEMPTS_CSV.exists():
        print(f"WARNING: {ATTEMPTS_CSV} not found")
        return pd.DataFrame()
    return pd.read_csv(ATTEMPTS_CSV)


# ============================================================
# REFRESH CLEAN ATTEMPTS
# ============================================================
# INPUT:  Nothing — reads current attempts.csv, questions.csv, students.csv
# PROCESS:
#   1. Import Person 1's preprocessing functions (clean_attempts, engineer_features)
#   2. Load the 3 raw CSVs
#   3. Run the full preprocessing pipeline
#   4. Save fresh clean_attempts.csv
#   5. Return the fresh DataFrame
#
# WHY:
#   After every quiz submission, a new raw attempt is appended to attempts.csv.
#   Person 2 (mastery) and Person 3 (ML predictor) use clean_attempts.csv which
#   has extra engineered columns: recency_weight, time_taken_bucket,
#   attempt_order_in_topic. Without refreshing, they work on STALE DATA and
#   AFTER mastery = BEFORE mastery (the new attempt doesn't exist yet in their view).
#
# WHY WE REUSE preprocessing.py:
#   Do NOT duplicate the logic. Person 1 already wrote clean_attempts() and
#   engineer_features(). We just call them from here.
#
# IMPORTANT:
#   preprocessing.py uses relative file paths ("students.csv" etc.) — it was
#   written to be run from the data/ directory. We temporarily add data/ to
#   sys.path and change os.chdir so its imports work correctly.

def refresh_clean_attempts() -> pd.DataFrame:
    """
    Re-runs Person 1's full preprocessing pipeline on the current raw CSVs.
    Saves fresh clean_attempts.csv and returns the resulting DataFrame.
    """
    # Temporarily add data/ to sys.path so we can import preprocessing.py
    data_dir_str = str(DATA_DIR)
    if data_dir_str not in sys.path:
        sys.path.insert(0, data_dir_str)

    # preprocessing.py uses relative paths, so we must run it from data/
    original_cwd = os.getcwd()
    os.chdir(DATA_DIR)

    try:
        # Import Person 1's preprocessing functions
        # (reimport each time in case the file changed)
        import importlib
        import preprocessing
        importlib.reload(preprocessing)

        # Step 1: Load raw CSVs
        students  = pd.read_csv("students.csv")
        questions = pd.read_csv("questions.csv")
        attempts  = pd.read_csv("attempts.csv")

        # Step 2: Clean raw attempts (fix timestamps, bad times, duplicates)
        clean = preprocessing.clean_attempts(attempts)

        # Step 3: Engineer features (merge, recency_weight, time_taken_bucket,
        #         attempt_order_in_topic)
        final = preprocessing.engineer_features(clean, questions, students)

        # Step 4: Save to clean_attempts.csv
        final.to_csv("clean_attempts.csv", index=False)
        print(f"[DONE] clean_attempts.csv refreshed - {len(final)} rows")

        # BUG 2 FIX: pd.qcut() leaves time_taken_bucket as pandas 'category' dtype.
        # Returning the in-memory DataFrame directly causes Person 2 to fail with:
        #   'Categorical' dtype does not support reduction 'mean'
        # Reloading from CSV converts category → normal object/string,
        # and parse_dates ensures timestamp is datetime-compatible (Bug 1 fix too).
        return pd.read_csv("clean_attempts.csv", parse_dates=["timestamp"])

    except Exception as e:
        print(f"ERROR in refresh_clean_attempts(): {e}")
        raise

    finally:
        # Always restore working directory
        os.chdir(original_cwd)


# ============================================================
# LOAD CLEAN ATTEMPTS
# ============================================================
# INPUT:  Nothing
# PROCESS:
#   - If clean_attempts.csv exists → read and return it
#   - If it does NOT exist → call refresh_clean_attempts() to build it first
# WHY:
#   Person 2 and Person 3 always need the preprocessed file.
#   This function guarantees they never get an empty DataFrame just
#   because clean_attempts.csv was accidentally deleted.

def load_clean_attempts() -> pd.DataFrame:
    if not CLEAN_ATTEMPTS_CSV.exists():
        print("WARNING: clean_attempts.csv not found — rebuilding from raw data...")
        return refresh_clean_attempts()
    # BUG 1 FIX: parse_dates ensures timestamp is datetime, not string.
    # Without this, Person 3's ML prediction fails with:
    #   unsupported operand type(s) for -: 'Timestamp' and 'str'
    return pd.read_csv(CLEAN_ATTEMPTS_CSV, parse_dates=["timestamp"])


# ============================================================
# SAVE ONE NEW ATTEMPT
# ============================================================
# INPUT:  Dictionary with attempt data
# PROCESS:
#   1. Generate attempt_id (auto-increment from last row)
#   2. Generate timestamp (backend owns this — not trusted from frontend)
#   3. Append one row to attempts.csv
# OUTPUT:  attempt_id (string like "A003372")
# NOTE:
#   This saves to RAW attempts.csv only.
#   Caller must call refresh_clean_attempts() afterwards if they need
#   Person 2 / Person 3 to see the new attempt immediately.

def save_attempt(attempt_data: dict) -> str:
    """
    Appends a new attempt row to attempts.csv.
    Returns the generated attempt_id.
    """
    attempts = load_attempts()

    if len(attempts) > 0 and "attempt_id" in attempts.columns:
        # Historical CSV rows can have blank or malformed IDs.
        last_ids = pd.to_numeric(
            attempts["attempt_id"].astype(str).str.extract(r"^A(\d+)$")[0],
            errors="coerce",
        )
        next_num = int(last_ids.max()) + 1 if last_ids.notna().any() else 1
    else:
        next_num = 1

    attempt_id = f"A{next_num:06d}"
    timestamp  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_row = pd.DataFrame([{
        "attempt_id":        attempt_id,
        "student_id":        attempt_data["student_id"],
        "question_id":       attempt_data["question_id"],
        "topic":             attempt_data["topic"],
        "difficulty":        attempt_data["difficulty"],
        "timestamp":         timestamp,
        "selected_option":   attempt_data["selected_option"],
        "is_correct":        attempt_data["is_correct"],
        "time_taken_seconds": attempt_data["time_taken_seconds"],
    }])

    if not ATTEMPTS_CSV.exists():
        new_row.to_csv(ATTEMPTS_CSV, index=False)
    else:
        new_row.to_csv(ATTEMPTS_CSV, mode="a", header=False, index=False)

    return attempt_id
