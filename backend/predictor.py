"""
predictor.py
Owner: Person 3

REAL-DATA VERSION
------------------
Predicts P(correct) -- the probability that a student answers a given
candidate question correctly -- using a RandomForestClassifier trained
on Person 1's real clean_attempts.csv.

This is the ML piece described in Feature 6 of the project brief. It is
deliberately kept separate from Person 2's mastery/weakness/dependency
logic (see "Separation of responsibilities" in the project context) --
this module only knows about historical performance -> P(correct).

-----------------------------------------------------------------------
WHY THESE FEATURES / AVOIDING LEAKAGE
-----------------------------------------------------------------------
Two columns already in clean_attempts.csv look tempting but are NOT
safe to use as raw inputs for predicting a *specific* attempt's
is_correct:

  * time_taken_seconds / time_taken_bucket
        These describe how long the student took on THIS SAME attempt.
        In a real quiz you only find out the answer time at the same
        moment you find out if they were correct -- using it to predict
        correctness on that same row means partially using the outcome
        to predict itself.

  * recency_weight / days_since_attempt
        These were computed once, relative to whenever Person 1 ran
        preprocessing.py (a single fixed "now" for the whole file), not
        relative to each attempt's position in that student's own
        history. That makes them meaningless as a "how recent was this
        *relative to the prediction moment*" signal for training.

Instead, every feature below is built from what happened BEFORE the
attempt being predicted -- i.e. only the student's own attempt history
up to (but not including) that row, using pandas groupby + shift(1)
so the current row's own outcome/time can never leak into its own
features. This mirrors how the model will actually be used later: at
inference time we only ever know a student's PAST attempts, never the
answer to the question we're about to recommend.

-----------------------------------------------------------------------
FEATURES USED (all knowable before the student answers)
-----------------------------------------------------------------------
  difficulty                  the candidate question's difficulty (1-5)
  prior_attempts_topic        how many times they've attempted this topic before
  prior_accuracy_topic        their accuracy on this topic, before this attempt
  prior_accuracy_overall      their accuracy across ALL topics, before this attempt
  recent_accuracy_topic       accuracy on their last 3 attempts in this topic
  avg_time_topic_prior        their average time-taken on this topic, from PRIOR
                               attempts only (not this one)
  days_since_last_topic       days since their last attempt in this topic
                               (large default if this is their first)

Target: is_correct (0/1)

-----------------------------------------------------------------------
MODULE STRUCTURE
-----------------------------------------------------------------------
  load_data(path)                  -> read + sort clean_attempts.csv
  build_features(df)               -> add leakage-safe feature columns
                                       (avg_time_topic_prior left as NaN
                                       for first-topic-attempts on purpose)
  time_based_split(df, test_size)  -> chronological train/test split
  fit_time_imputer(train_df)       -> fit avg_time_topic_prior fallback,
                                       TRAIN SPLIT ONLY
  apply_time_imputer(df, value)    -> apply that one fitted value to a split
  baseline_predict_proba(df)       -> simple rule-based baseline
  train_model(train_df)            -> fit RandomForestClassifier
  predict_probability(model, row)  -> P(correct) for one feature row
  evaluate(y_true, y_pred, y_proba)-> accuracy/precision/recall/F1/confusion matrix
  get_candidate_features(...)      -> build a feature row for a NOT-YET-ANSWERED
                                       candidate question, for use by adaptive.py
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

RANDOM_STATE = 42
RECENT_WINDOW = 3          # how many of the student's last topic attempts count as "recent"
DEFAULT_ACCURACY = 0.5     # neutral guess when a student has no prior history yet
DEFAULT_DAYS_SINCE = 999.0 # large "never attempted before" sentinel

FEATURE_COLUMNS = [
    "difficulty",
    "prior_attempts_topic",
    "prior_accuracy_topic",
    "prior_accuracy_overall",
    "recent_accuracy_topic",
    "avg_time_topic_prior",
    "days_since_last_topic",
]

TARGET_COLUMN = "is_correct"

REQUIRED_COLUMNS = [
    "student_id",
    "topic",
    "difficulty",
    "is_correct",
    "timestamp",
    "time_taken_seconds",
]


class ValidationError(Exception):
    """Raised when the input DataFrame does not satisfy the data contract."""
    pass


def _validate_columns(df):
    if not isinstance(df, pd.DataFrame):
        raise ValidationError("Input must be a pandas DataFrame.")
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValidationError(f"clean_attempts.csv is missing required column(s): {missing}")


# ---------------------------------------------------------------------------
# 1. Load
# ---------------------------------------------------------------------------

def load_data(csv_path):
    """
    Load Person 1's real clean_attempts.csv and sort chronologically.

    Sorting by timestamp up front is what makes every "prior_*" feature
    in build_features() correct -- shift(1)/expanding() only look
    backwards correctly if the rows are already in time order.
    """
    df = pd.read_csv(csv_path)
    _validate_columns(df)

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df["is_correct"] = pd.to_numeric(df["is_correct"], errors="coerce").fillna(0).clip(0, 1).astype(int)
    df["difficulty"] = pd.to_numeric(df["difficulty"], errors="coerce")

    df = df.sort_values(["student_id", "timestamp"]).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# 2. Feature engineering (leakage-safe: everything is shifted by 1)
# ---------------------------------------------------------------------------

def build_features(df):
    """
    Add leakage-safe historical features to a copy of the attempts data.

    Every "prior_*"/"recent_*"/"avg_*" feature for row i is computed
    ONLY from that same student's rows before row i (via .shift(1) after
    grouping), so the model never sees an attempt's own outcome, time,
    or anything derived from later attempts.

    Returns a new DataFrame with FEATURE_COLUMNS + TARGET_COLUMN added.
    """
    _validate_columns(df)
    df = df.sort_values(["student_id", "timestamp"]).copy()

    # --- overall (cross-topic) prior accuracy, per student ---
    by_student = df.groupby("student_id")["is_correct"]
    df["prior_accuracy_overall"] = (
        by_student.apply(lambda s: s.expanding().mean().shift(1))
        .reset_index(level=0, drop=True)
    )

    # --- per-topic prior stats, per student ---
    by_student_topic = df.groupby(["student_id", "topic"])

    df["prior_attempts_topic"] = by_student_topic.cumcount()  # count of attempts BEFORE this one

    df["prior_accuracy_topic"] = (
        by_student_topic["is_correct"]
        .apply(lambda s: s.expanding().mean().shift(1))
        .reset_index(level=[0, 1], drop=True)
    )

    df["recent_accuracy_topic"] = (
        by_student_topic["is_correct"]
        .apply(lambda s: s.rolling(RECENT_WINDOW, min_periods=1).mean().shift(1))
        .reset_index(level=[0, 1], drop=True)
    )

    df["avg_time_topic_prior"] = (
        by_student_topic["time_taken_seconds"]
        .apply(lambda s: s.expanding().mean().shift(1))
        .reset_index(level=[0, 1], drop=True)
    )

    df["days_since_last_topic"] = (
        by_student_topic["timestamp"]
        .apply(lambda s: s.diff().dt.total_seconds() / 86400)
        .reset_index(level=[0, 1], drop=True)
    )

    # --- fill "no history yet" cases with neutral/sentinel defaults ---
    # These three are FIXED CONSTANTS (not computed from the data), so
    # filling them here is safe regardless of train/test boundaries -- a
    # constant can't leak information about the future.
    df["prior_accuracy_overall"] = df["prior_accuracy_overall"].fillna(DEFAULT_ACCURACY)
    df["prior_accuracy_topic"] = df["prior_accuracy_topic"].fillna(DEFAULT_ACCURACY)
    df["recent_accuracy_topic"] = df["recent_accuracy_topic"].fillna(DEFAULT_ACCURACY)
    df["days_since_last_topic"] = df["days_since_last_topic"].fillna(DEFAULT_DAYS_SINCE)

    # avg_time_topic_prior is intentionally LEFT AS NaN here (a student's
    # first attempt on a topic has no prior average time to report). Unlike
    # the constants above, its natural fallback is a DATA STATISTIC (a
    # median time), and computing that statistic here -- before the
    # train/test split exists -- would let the test period's attempt times
    # influence a value used to fill TRAINING rows. That's a (small but
    # real) leak of future information into training-time preprocessing.
    # It's fixed in two steps instead: fit_time_imputer() computes the
    # median from the TRAIN split only, and apply_time_imputer() applies
    # that one fitted number consistently to both train and test.

    return df


# ---------------------------------------------------------------------------
# 3. Train/test split (chronological, NOT random)
# ---------------------------------------------------------------------------

def time_based_split(df, test_size=0.2):
    """
    Split into train/test by TIME, not randomly.

    A random split would let the model train on an attempt from
    3pm and test on an attempt from 2pm the same day -- effectively
    "seeing the future". Splitting on the timestamp instead means we
    train on earlier attempts and evaluate on later ones, which matches
    how the model will actually be used (predicting what happens next).

    NOTE: the split happens on featured_df (after build_features()), but
    avg_time_topic_prior is still NaN for "first attempt on this topic"
    rows at this point -- see fit_time_imputer()/apply_time_imputer(),
    which must be called on the OUTPUT of this function, not before it.
    """
    df_sorted = df.sort_values("timestamp").reset_index(drop=True)
    cutoff = int(len(df_sorted) * (1 - test_size))
    train_df = df_sorted.iloc[:cutoff].copy()
    test_df = df_sorted.iloc[cutoff:].copy()
    return train_df, test_df


def fit_time_imputer(train_df):
    """
    Compute the fallback value for missing avg_time_topic_prior, using
    ONLY the training split.

    A student's first attempt on a topic has no prior average time, so
    we need *some* neutral number to fill that gap. Using the training
    split's own median (rather than the full dataset's) means this
    number never reflects anything from the held-out test period --
    train-time preprocessing stays blind to the future, the same way it
    would have to be in a real deployment where "the future" simply
    hasn't happened yet.
    """
    value = train_df["avg_time_topic_prior"].median()
    if pd.isna(value):
        # Edge case: if literally every training row is a first-topic-
        # attempt (e.g. a tiny/degenerate training split), fall back to
        # the raw time_taken_seconds median -- still training-data only.
        value = train_df["time_taken_seconds"].median()
    return float(value)


def apply_time_imputer(df, fitted_value):
    """
    Fill missing avg_time_topic_prior with a value that was fit on the
    training split (see fit_time_imputer). Applied identically to both
    train and test so the two splits are preprocessed the same way --
    only the *source* of the fitted number is restricted to train.
    """
    df = df.copy()
    df["avg_time_topic_prior"] = df["avg_time_topic_prior"].fillna(fitted_value)
    return df


# ---------------------------------------------------------------------------
# 4. Baseline (rule-based, no ML) -- required for a fair comparison
# ---------------------------------------------------------------------------

def baseline_predict_proba(df):
    """
    Rule-based baseline: "predicted P(correct) = the student's own recent
    accuracy on this topic" (falls back to overall accuracy, then 0.5).

    This is the simplest reasonable non-ML predictor and is what Random
    Forest has to beat to justify using ML at all.
    """
    proba = df["recent_accuracy_topic"].copy()
    proba = proba.fillna(df["prior_accuracy_overall"])
    proba = proba.fillna(DEFAULT_ACCURACY)
    return proba.clip(0, 1).values


# ---------------------------------------------------------------------------
# 5. Train
# ---------------------------------------------------------------------------

def train_model(train_df, feature_columns=FEATURE_COLUMNS):
    """
    Fit a RandomForestClassifier on the training split.

    Why Random Forest:
      * Works well on a small/medium tabular dataset (~3,300 rows) without
        needing feature scaling.
      * Captures non-linear interactions the brief expects (e.g. "high
        difficulty + low prior accuracy = very low P(correct)") that a
        single logistic model would need manual interaction terms for.
      * feature_importances_ gives an easy, explainable answer to
        "why did the model predict that?" for judges.

    class_weight="balanced" because is_correct is only mildly imbalanced
    here (~57/43), but it costs nothing to be robust to worse splits.
    """
    X_train = train_df[feature_columns]
    y_train = train_df[TARGET_COLUMN]

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    return model


# ---------------------------------------------------------------------------
# 6. Predict
# ---------------------------------------------------------------------------

def predict_probability(model, feature_row, feature_columns=FEATURE_COLUMNS):
    """
    Predict P(correct) for ONE candidate question.

    feature_row: dict with keys matching feature_columns (see
    get_candidate_features() to build one for a real student+topic).

    Returns a float in [0, 1].
    """
    X = pd.DataFrame([{col: feature_row.get(col, DEFAULT_ACCURACY) for col in feature_columns}])
    proba = model.predict_proba(X)[0]
    # predict_proba columns follow model.classes_ order (0, 1) here
    correct_index = list(model.classes_).index(1)
    return float(proba[correct_index])


def predict_probabilities(model, df, feature_columns=FEATURE_COLUMNS):
    """Vectorized version of predict_probability() for a whole DataFrame."""
    X = df[feature_columns]
    proba = model.predict_proba(X)
    correct_index = list(model.classes_).index(1)
    return proba[:, correct_index]


# ---------------------------------------------------------------------------
# 7. Evaluate
# ---------------------------------------------------------------------------

def evaluate(y_true, y_proba, threshold=0.5):
    """
    Standard classification metrics at a 0.5 decision threshold, plus the
    confusion matrix. Returns a plain dict so it's easy to print/compare
    baseline vs Random Forest side by side.
    """
    y_pred = (np.asarray(y_proba) >= threshold).astype(int)

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 3),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 3),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 3),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 3),
        "confusion_matrix": {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        },
    }


# ---------------------------------------------------------------------------
# 8. Inference-time feature builder for a NOT-YET-ANSWERED candidate question
# ---------------------------------------------------------------------------

def get_candidate_features(full_df, student_id, topic, difficulty, time_fallback=None):
    """
    Build a feature row for a CANDIDATE question the student has not
    answered yet -- this is what adaptive.py/FastAPI will call later to
    get P(correct) for "should we show them this question next?".

    full_df should be the FULL clean_attempts dataset (all real history
    up to right now), NOT a train/test split -- at real inference time
    we always want the student's complete history so far. This is not a
    leakage case the same way build_features() was: at the moment of a
    real recommendation there genuinely is no "future" data beyond what's
    in full_df yet, so using all of it here is legitimate.

    time_fallback: the value to use for avg_time_topic_prior when the
    student has NO prior attempts on this topic. Optional -- pass the
    number returned by fit_time_imputer(train_df) if you want inference
    to use the exact same fallback the model was trained with (the more
    consistent choice). If omitted, falls back to the median of
    full_df's time_taken_seconds, which is fine for a live demo but
    won't exactly match the training-time fallback.

    Unlike build_features() (which computes "prior to THIS historical
    row" for training), here there is no existing row for the candidate
    question yet, so we just summarize the student's topic history as it
    stands right now and pair it with the candidate's difficulty.
    """
    student_df = full_df[full_df["student_id"] == student_id]
    topic_df = student_df[student_df["topic"] == topic].sort_values("timestamp")

    if student_df.empty:
        overall_acc = DEFAULT_ACCURACY
    else:
        overall_acc = float(student_df["is_correct"].mean())

    if time_fallback is None:
        time_fallback = float(full_df["time_taken_seconds"].median())

    if topic_df.empty:
        return {
            "difficulty": int(difficulty),
            "prior_attempts_topic": 0,
            "prior_accuracy_topic": DEFAULT_ACCURACY,
            "prior_accuracy_overall": overall_acc,
            "recent_accuracy_topic": DEFAULT_ACCURACY,
            "avg_time_topic_prior": time_fallback,
            "days_since_last_topic": DEFAULT_DAYS_SINCE,
        }

    last_timestamp = topic_df["timestamp"].max()
    now = pd.Timestamp.now()
    days_since = (now - last_timestamp).total_seconds() / 86400

    return {
        "difficulty": int(difficulty),
        "prior_attempts_topic": int(len(topic_df)),
        "prior_accuracy_topic": float(topic_df["is_correct"].mean()),
        "prior_accuracy_overall": overall_acc,
        "recent_accuracy_topic": float(topic_df["is_correct"].tail(RECENT_WINDOW).mean()),
        "avg_time_topic_prior": float(topic_df["time_taken_seconds"].mean()),
        "days_since_last_topic": float(max(days_since, 0.0)),
    }


def predict_for_candidate(model, full_df, student_id, topic, difficulty, time_fallback=None):
    """
    Convenience wrapper: candidate question -> P(correct), in one call.
    This is the function adaptive.py/FastAPI should call.
    """
    feature_row = get_candidate_features(full_df, student_id, topic, difficulty, time_fallback=time_fallback)
    return predict_probability(model, feature_row)


# ---------------------------------------------------------------------------
# 9. Optional persistence, so Person 6's FastAPI doesn't retrain per request
# ---------------------------------------------------------------------------

def save_model(model, path="predictor_model.joblib"):
    import joblib
    joblib.dump(model, path)


def load_model(path="predictor_model.joblib"):
    import joblib
    return joblib.load(path)


def print_metrics(label, metrics):
    print(f"\n--- {label} ---")
    print(f"Accuracy:  {metrics['accuracy']}")
    print(f"Precision: {metrics['precision']}")
    print(f"Recall:    {metrics['recall']}")
    print(f"F1:        {metrics['f1']}")
    cm = metrics["confusion_matrix"]
    print(f"Confusion matrix: TN={cm['true_negative']} FP={cm['false_positive']} "
          f"FN={cm['false_negative']} TP={cm['true_positive']}")


# ---------------------------------------------------------------------------
# REAL-DATA DEMO
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    attempts_path = "person1_package/clean_attempts.csv"

    print("Loading real data...")
    raw_df = load_data(attempts_path)

    print("Building leakage-safe features...")
    featured_df = build_features(raw_df)

    train_df, test_df = time_based_split(featured_df, test_size=0.2)
    print(f"Train rows: {len(train_df)} | Test rows: {len(test_df)} "
          f"(split chronologically, not randomly)")

    # Fit the avg_time_topic_prior fallback on TRAIN ONLY, then apply that
    # same fitted number to both splits -- keeps test-period data out of
    # any statistic used during training-time preprocessing.
    time_fallback = fit_time_imputer(train_df)
    print(f"Time-feature fallback fit from train split only: {round(time_fallback, 2)} seconds")
    train_df = apply_time_imputer(train_df, time_fallback)
    test_df = apply_time_imputer(test_df, time_fallback)

    # --- Baseline ---
    baseline_test_proba = baseline_predict_proba(test_df)
    baseline_metrics = evaluate(test_df[TARGET_COLUMN], baseline_test_proba)
    print_metrics("Rule-based baseline (recent topic accuracy)", baseline_metrics)

    # --- Random Forest ---
    model = train_model(train_df)
    rf_test_proba = predict_probabilities(model, test_df)
    rf_metrics = evaluate(test_df[TARGET_COLUMN], rf_test_proba)
    print_metrics("Random Forest", rf_metrics)

    # --- Feature importance, for judge Q&A ---
    print("\n--- Feature importances ---")
    importances = sorted(
        zip(FEATURE_COLUMNS, model.feature_importances_),
        key=lambda x: x[1],
        reverse=True,
    )
    for name, importance in importances:
        print(f"{name}: {round(float(importance), 3)}")

    # --- Example: predicting for a real candidate (not-yet-asked) question ---
    example_student = str(raw_df.iloc[0]["student_id"])
    example_topic = "LSTM"
    example_difficulty = 3

    proba = predict_for_candidate(
        model, raw_df, example_student, example_topic, example_difficulty,
        time_fallback=time_fallback,
    )
    print(f"\n=== Example candidate prediction ===")
    print(f"Student: {example_student} | Topic: {example_topic} | Difficulty: {example_difficulty}")
    print(f"Predicted P(correct): {round(proba, 3)}")

    if proba < 0.4:
        print("-> Too difficult right now: try an easier question / prerequisite.")
    elif proba < 0.75:
        print("-> Reasonable challenge: candidate can be selected.")
    else:
        print("-> Comfortable: could try a harder question instead.")
