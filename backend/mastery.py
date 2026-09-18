"""
mastery.py
==========
Person 2 - Core Intelligence / Diagnosis Engine.

Computes a 0-100 mastery score per topic for a given student from
Person 1's cleaned attempts data (clean_attempts.csv).

Formula (all four components pre-normalized to 0-100):

    mastery = ACCURACY_WEIGHT   * accuracy_score
            + RECENCY_WEIGHT    * recency_score
            + DIFFICULTY_WEIGHT * difficulty_score
            + TIME_WEIGHT       * time_score

This is an intentionally simple, explainable MVP formula - not a
knowledge-tracing model.
"""

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configurable constants (change these, not the logic, to tune behaviour)
# ---------------------------------------------------------------------------

ACCURACY_WEIGHT = 0.40
RECENCY_WEIGHT = 0.20
DIFFICULTY_WEIGHT = 0.20
TIME_WEIGHT = 0.20

# time_taken_bucket -> 0-100 efficiency score. Buckets are assumed to
# already be difficulty-relative (Person 1's job), so we don't need a
# separate difficulty adjustment here.
TIME_SCORES = {
    "fast": 100,
    "normal": 70,
    "slow": 40,
}
DEFAULT_TIME_SCORE = 70  # fallback when a bucket value is missing/unrecognized

REQUIRED_COLUMNS = [
    "student_id",
    "topic",
    "difficulty",
    "is_correct",
    "recency_weight",
    "time_taken_bucket",
]


class ValidationError(Exception):
    """Raised when an input DataFrame does not satisfy the data contract."""
    pass


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_columns(df, required=REQUIRED_COLUMNS):
    if not isinstance(df, pd.DataFrame):
        raise ValidationError("Input must be a pandas DataFrame.")
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValidationError(f"clean_attempts.csv is missing required column(s): {missing}")


def _clean_is_correct(series):
    """
    Coerce is_correct into a clean 0/1 float signal.

    Anything that isn't a valid 0/1/True/False is treated conservatively
    as incorrect (0), and the count of such values is returned so callers
    can surface a warning instead of silently guessing.
    """
    numeric = pd.to_numeric(series, errors="coerce")
    n_invalid = int(numeric.isna().sum())
    numeric = numeric.fillna(0.0)
    # clip defensively in case of stray values like 2 or -1
    numeric = numeric.clip(0, 1)
    return numeric, n_invalid


# ---------------------------------------------------------------------------
# Component scores (each returns a 0-100 float)
# ---------------------------------------------------------------------------

def _accuracy_score(topic_df):
    """
    Recency-weighted accuracy.

    Plain accuracy (is_correct.mean()) treats an attempt from a month ago
    identically to one from this morning. recency_weight already encodes
    "how much this attempt should count right now" (Person 1's feature),
    so weighting by it reflects *current* ability rather than a flat
    historical average - a student who was weak a month ago but has
    since improved should not be scored as if nothing changed.
    """
    is_correct = topic_df["is_correct"].astype(float)
    weights = pd.to_numeric(topic_df["recency_weight"], errors="coerce").fillna(0.0)

    weight_sum = weights.sum()
    if weight_sum <= 0 or pd.isna(weight_sum):
        # Degenerate weights (e.g. all zero) -> fall back to plain accuracy
        # rather than dividing by zero or returning a meaningless number.
        return float(is_correct.mean() * 100) if len(is_correct) else 0.0

    weighted_accuracy = (is_correct * weights).sum() / weight_sum
    return float(np.clip(weighted_accuracy * 100, 0, 100))


def _recency_score(topic_df, global_min, global_max):
    """
    0-100 recency score built from the existing recency_weight column.

    We don't assume any particular scale for recency_weight (it might be
    0-1, or something else entirely depending on Person 1's exact
    formula). Instead we min-max normalize the topic's average
    recency_weight against the min/max recency_weight seen across the
    *entire* dataset, so 100 always means "as recent as the most recent
    activity anyone has" regardless of the underlying units.
    """
    weights = pd.to_numeric(topic_df["recency_weight"], errors="coerce").dropna()
    if weights.empty:
        return 0.0

    avg = weights.mean()
    if pd.isna(global_min) or pd.isna(global_max) or global_max == global_min:
        # No variation anywhere in the dataset -> can't discriminate,
        # return a neutral score instead of an arbitrary extreme.
        return 50.0

    normalized = (avg - global_min) / (global_max - global_min)
    return float(np.clip(normalized * 100, 0, 100))


def _difficulty_score(topic_df):
    """
    Difficulty-weighted correctness: correct answers on harder questions
    count for more, since they're stronger evidence of real mastery than
    correct answers on easy questions.
    """
    difficulty = pd.to_numeric(topic_df["difficulty"], errors="coerce").fillna(0)
    is_correct = topic_df["is_correct"].astype(float)

    diff_sum = difficulty.sum()
    if diff_sum <= 0:
        # No usable difficulty info -> fall back to plain accuracy.
        return float(is_correct.mean() * 100) if len(is_correct) else 0.0

    score = (is_correct * difficulty).sum() / diff_sum
    return float(np.clip(score * 100, 0, 100))


def _time_score(topic_df):
    """
    Average time-efficiency score using Person 1's difficulty-relative
    time_taken_bucket, rather than one fixed global time cutoff (which
    would unfairly penalize slow-but-correct answers on hard questions).
    """
    if "time_taken_bucket" not in topic_df or topic_df.empty:
        return DEFAULT_TIME_SCORE

    scores = topic_df["time_taken_bucket"].map(TIME_SCORES)
    scores = scores.fillna(DEFAULT_TIME_SCORE)
    return float(np.clip(scores.mean(), 0, 100))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_mastery(df, student_id):
    """
    Calculate topic-wise mastery for one student.

    Parameters
    ----------
    df : pd.DataFrame
        The full clean_attempts dataset (all students - needed so recency
        can be normalized against the whole dataset's range).
    student_id : str

    Returns
    -------
    dict with keys:
        student_id : str
        mastery    : {topic: score} (0-100, rounded to 1 decimal)
        details    : {topic: {accuracy, recency, difficulty_score,
                               time_score, attempt_count}}
        warning    : str, only present if something noteworthy happened
                     (e.g. no attempts found, invalid is_correct values)
    """
    _validate_columns(df)

    student_df = df[df["student_id"] == student_id].copy()

    if student_df.empty:
        return {
            "student_id": student_id,
            "mastery": {},
            "details": {},
            "warning": f"No attempts found for student '{student_id}'.",
        }

    student_df["is_correct"], n_invalid = _clean_is_correct(student_df["is_correct"])

    # Global recency range across ALL students, used to normalize recency
    # consistently regardless of Person 1's exact recency_weight formula.
    global_recency = pd.to_numeric(df["recency_weight"], errors="coerce")
    r_min, r_max = global_recency.min(), global_recency.max()

    mastery_scores = {}
    details = {}

    for topic, topic_df in student_df.groupby("topic"):
        accuracy_score = _accuracy_score(topic_df)
        recency_score = _recency_score(topic_df, r_min, r_max)
        difficulty_score = _difficulty_score(topic_df)
        time_score = _time_score(topic_df)

        mastery = (
            ACCURACY_WEIGHT * accuracy_score
            + RECENCY_WEIGHT * recency_score
            + DIFFICULTY_WEIGHT * difficulty_score
            + TIME_WEIGHT * time_score
        )
        mastery = float(np.clip(mastery, 0, 100))

        mastery_scores[topic] = round(mastery, 1)
        details[topic] = {
            "accuracy": round(accuracy_score, 1),
            "recency": round(recency_score, 1),
            "difficulty_score": round(difficulty_score, 1),
            "time_score": round(time_score, 1),
            "attempt_count": int(len(topic_df)),
        }

    result = {
        "student_id": student_id,
        "mastery": mastery_scores,
        "details": details,
    }
    if n_invalid:
        result["warning"] = (
            f"{n_invalid} attempt(s) had invalid is_correct values and "
            "were conservatively treated as incorrect."
        )
    return result
