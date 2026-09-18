"""
mistakes.py
===========
Person 2 - Core Intelligence / Diagnosis Engine.

Turns mastery scores + raw attempts into a ranked list of weak topics,
each with evidence-based reasons for why it looks weak. Every reason is
a measurable statement (e.g. "low accuracy") - never a psychological
claim about the student.
"""

import numpy as np
import pandas as pd

from backend.mastery import ValidationError  # shared exception type across the pipeline

# ---------------------------------------------------------------------------
# Configurable constants
# ---------------------------------------------------------------------------

HIGH_WEAKNESS_THRESHOLD = 50   # mastery below this -> "high" severity
GOOD_MASTERY_THRESHOLD = 70    # mastery at/above this -> not reported as weak

MASTERY_GAP_WEIGHT = 0.70
RECENT_ERROR_WEIGHT = 0.30

RECENT_WINDOW = 5                 # how many most-recent attempts count as "recent"
REPEATED_ERROR_MIN_COUNT = 2      # a question missed this many times = "repeated"

LOW_ACCURACY_THRESHOLD = 60           # topic accuracy (%) below this -> "low accuracy"
HIGH_RECENT_ERROR_THRESHOLD = 0.5     # recent error rate above this -> "recent mistakes"
HARD_DIFFICULTY_MIN = 4               # difficulty >= this counts as "hard"
HARD_ACCURACY_THRESHOLD = 50          # accuracy (%) on hard questions below this -> flagged
SLOW_RATE_THRESHOLD = 0.4             # share of "slow" attempts above this -> flagged

REQUIRED_COLUMNS = [
    "student_id",
    "topic",
    "question_id",
    "difficulty",
    "is_correct",
    "time_taken_bucket",
    "attempt_order_in_topic",
]


def _validate_columns(df, required=REQUIRED_COLUMNS):
    if not isinstance(df, pd.DataFrame):
        raise ValidationError("Input must be a pandas DataFrame.")
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValidationError(f"clean_attempts.csv is missing required column(s): {missing}")


# ---------------------------------------------------------------------------
# Evidence helpers (each operates on one student's attempts for one topic)
# ---------------------------------------------------------------------------

def _recent_error_rate(topic_df, window=RECENT_WINDOW):
    if topic_df.empty:
        return 0.0
    ordered = topic_df.sort_values("attempt_order_in_topic")
    recent = ordered.tail(window)
    if recent.empty:
        return 0.0
    return float(1 - recent["is_correct"].mean())


def _repeated_question_errors(topic_df, min_count=REPEATED_ERROR_MIN_COUNT):
    incorrect = topic_df[topic_df["is_correct"] == 0]
    if incorrect.empty:
        return {"count": 0, "question_ids": []}
    counts = incorrect.groupby("question_id").size()
    repeated = counts[counts >= min_count]
    return {"count": int(len(repeated)), "question_ids": repeated.index.tolist()}


def _wrong_streak(topic_df):
    if topic_df.empty:
        return 0
    ordered = topic_df.sort_values("attempt_order_in_topic", ascending=False)
    streak = 0
    for correct in ordered["is_correct"]:
        if correct == 0:
            streak += 1
        else:
            break
    return int(streak)


def _hard_question_accuracy(topic_df, min_difficulty=HARD_DIFFICULTY_MIN):
    difficulty = pd.to_numeric(topic_df["difficulty"], errors="coerce")
    hard = topic_df[difficulty >= min_difficulty]
    if hard.empty:
        return None  # no hard-question evidence either way - don't guess
    return float(hard["is_correct"].mean() * 100)


def _slow_response_rate(topic_df):
    if topic_df.empty or "time_taken_bucket" not in topic_df:
        return 0.0
    buckets = topic_df["time_taken_bucket"]
    if len(buckets) == 0:
        return 0.0
    return float((buckets == "slow").mean())


def _build_reasons(accuracy_pct, recent_error_rate, repeated_count, hard_accuracy, slow_rate):
    reasons = []
    if accuracy_pct < LOW_ACCURACY_THRESHOLD:
        reasons.append("low accuracy")
    if recent_error_rate >= HIGH_RECENT_ERROR_THRESHOLD:
        reasons.append("recent mistakes")
    if repeated_count > 0:
        reasons.append("repeated incorrect attempts")
    if hard_accuracy is not None and hard_accuracy < HARD_ACCURACY_THRESHOLD:
        reasons.append("low accuracy on difficulty 4-5 questions")
    if slow_rate >= SLOW_RATE_THRESHOLD:
        reasons.append("slow response times")
    if not reasons:
        # Mastery is below the "good" threshold but no single strong
        # signal explains it in isolation - still an honest, measurable
        # statement, not a guess.
        reasons.append("mastery below target threshold")
    return reasons


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_weaknesses(df, student_id, mastery_result):
    """
    Identify weak topics for a student and explain why each looks weak.

    Parameters
    ----------
    df : pd.DataFrame
        Full clean_attempts dataset.
    student_id : str
    mastery_result : dict
        Output of mastery.calculate_mastery(df, student_id).

    Returns
    -------
    list[dict], sorted by priority (highest first). Each dict has:
        topic, mastery, severity, priority, reasons,
        accuracy, recent_error_rate, repeated_question_errors,
        repeated_question_ids, wrong_streak, attempt_count
    """
    _validate_columns(df)

    mastery_scores = mastery_result.get("mastery", {})
    if not mastery_scores:
        return []

    student_df = df[df["student_id"] == student_id].copy()
    if student_df.empty:
        return []

    student_df["is_correct"] = pd.to_numeric(student_df["is_correct"], errors="coerce").fillna(0).clip(0, 1)

    weak_topics = []
    for topic, mastery in mastery_scores.items():
        if mastery >= GOOD_MASTERY_THRESHOLD:
            continue  # not weak - Person 3 doesn't need it in the plan

        topic_df = student_df[student_df["topic"] == topic]
        severity = "high" if mastery < HIGH_WEAKNESS_THRESHOLD else "moderate"

        accuracy = float(topic_df["is_correct"].mean()) if len(topic_df) else 0.0
        recent_error_rate = _recent_error_rate(topic_df)
        repeated = _repeated_question_errors(topic_df)
        wrong_streak = _wrong_streak(topic_df)
        hard_accuracy = _hard_question_accuracy(topic_df)
        slow_rate = _slow_response_rate(topic_df)

        mastery_gap = 100 - mastery
        priority = (
            MASTERY_GAP_WEIGHT * mastery_gap
            + RECENT_ERROR_WEIGHT * (recent_error_rate * 100)
        )
        priority = float(np.clip(priority, 0, 100))

        reasons = _build_reasons(
            accuracy_pct=accuracy * 100,
            recent_error_rate=recent_error_rate,
            repeated_count=repeated["count"],
            hard_accuracy=hard_accuracy,
            slow_rate=slow_rate,
        )

        weak_topics.append({
            "topic": topic,
            "mastery": round(mastery, 1),
            "severity": severity,
            "priority": round(priority, 1),
            "reasons": reasons,
            "accuracy": round(accuracy, 2),
            "recent_error_rate": round(recent_error_rate, 2),
            "repeated_question_errors": repeated["count"],
            "repeated_question_ids": repeated["question_ids"],
            "wrong_streak": wrong_streak,
            "attempt_count": int(len(topic_df)),
        })

    weak_topics.sort(key=lambda w: w["priority"], reverse=True)
    return weak_topics
