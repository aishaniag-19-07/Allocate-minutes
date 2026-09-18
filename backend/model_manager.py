"""
backend/model_manager.py — ML Model Loader/Trainer
====================================================
OWNER: Person 6 (Backend + Integration)

PURPOSE:
    Train Person 3's RandomForest model ONCE when the server starts,
    then cache it in memory so every API request can call predict_proba()
    without retraining.

WHY THIS FILE:
    Person 3's predictor.py has all the training logic, but it needs
    to be called once and the result stored. Retraining per API request
    would be very slow. This file handles that lifecycle.

USAGE:
    from backend.model_manager import get_model, get_time_fallback, get_featured_df

    model = get_model()          # trained RandomForest (or None if unavailable)
    fallback = get_time_fallback()  # fitted time imputer value
    featured_df = get_featured_df() # full featured DataFrame for inference
"""

import pandas as pd
from pathlib import Path
from backend.data_loader import load_clean_attempts

# Cached model state (module-level — loaded once per server process)
_model = None
_time_fallback = None
_featured_df = None
_model_metrics = None
_trained = False  # flag so we only train once


def get_model():
    """Return the trained model. None if training failed."""
    return _model


def get_time_fallback():
    """Return the fitted time imputer value."""
    return _time_fallback


def get_featured_df():
    """Return the full featured DataFrame for inference."""
    return _featured_df


def get_model_metrics():
    """Return training metrics dict."""
    return _model_metrics


def initialize_model():
    """
    Train the model from clean_attempts.csv.
    Called once at FastAPI startup.

    INPUT:  clean_attempts.csv from data/
    PROCESS:
        1. Load data
        2. Build leakage-safe features
        3. Time-based train/test split
        4. Fit time imputer on TRAIN only
        5. Train RandomForest
        6. Evaluate on test set
        7. Cache model + metrics
    OUTPUT: Cached model, fallback, featured_df (in module globals)
    """
    global _model, _time_fallback, _featured_df, _model_metrics, _trained

    if _trained:
        return  # Already done

    try:
        from backend.predictor import (
            load_data, build_features, time_based_split,
            fit_time_imputer, apply_time_imputer, train_model,
            predict_probabilities, evaluate, FEATURE_COLUMNS, TARGET_COLUMN
        )

        clean_df = load_clean_attempts()
        if clean_df.empty:
            print("WARNING: model_manager — clean_attempts.csv is empty, model not trained")
            _trained = True
            return

        # Build features
        raw_df = load_data(str(Path(__file__).parent.parent / "data" / "clean_attempts.csv"))
        featured_df = build_features(raw_df)

        # Time-based split (not random — avoids data leakage)
        train_df, test_df = time_based_split(featured_df, test_size=0.2)

        # Fit time imputer on TRAIN only
        time_fallback = fit_time_imputer(train_df)
        train_df = apply_time_imputer(train_df, time_fallback)
        test_df = apply_time_imputer(test_df, time_fallback)

        # Also apply to full featured_df for inference
        featured_df = apply_time_imputer(featured_df, time_fallback)

        # Train the model
        model = train_model(train_df)

        # Evaluate
        y_true = test_df[TARGET_COLUMN]
        y_proba = predict_probabilities(model, test_df)
        metrics = evaluate(y_true, y_proba)
        metrics["model"] = "RandomForestClassifier"
        metrics["training_samples"] = len(train_df)
        metrics["test_samples"] = len(test_df)
        metrics["features"] = FEATURE_COLUMNS

        # Cache everything
        _model = model
        _time_fallback = time_fallback
        _featured_df = featured_df
        _model_metrics = metrics
        _trained = True

        print(f"✅ Model trained — accuracy: {metrics['accuracy']} | "
              f"f1: {metrics['f1']} | train_size: {len(train_df)}")

    except Exception as e:
        print(f"WARNING: model_manager — training failed: {e}")
        _trained = True  # Don't retry every request
