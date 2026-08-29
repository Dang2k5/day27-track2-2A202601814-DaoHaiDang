"""Anomaly detection starter.

Z-score is deliberately the default baseline. Students should improve `auto`
mode for seasonality/outliers rather than deleting the simple implementation.
"""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def zscore_detector(current: float, history: Iterable[float], threshold: float = 3.0) -> dict[str, Any]:
    values = np.asarray(list(history), dtype=float)
    if values.size < 3:
        return {"is_anomaly": False, "score": 0.0, "method": "zscore", "reason": "insufficient_history"}
    mean = float(np.mean(values))
    std = float(np.std(values))
    if std == 0:
        score = float("inf") if float(current) != mean else 0.0
    else:
        score = abs(float(current) - mean) / std
    return {
        "is_anomaly": bool(score > threshold),
        "score": float(score),
        "method": "zscore",
        "reason": f"mean={mean:.3f}, std={std:.3f}, threshold={threshold}",
    }


def mad_detector(current: float, history: Iterable[float], threshold: float = 3.5) -> dict[str, Any]:
    """Robust example, intentionally incomplete around zero-MAD edge cases.

    Students may improve this function and/or use it from auto mode.
    """
    values = np.asarray(list(history), dtype=float)
    if values.size < 5:
        return {"is_anomaly": False, "score": 0.0, "method": "mad", "reason": "insufficient_history"}
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    if mad == 0:
        return {"is_anomaly": False, "score": 0.0, "method": "mad", "reason": "mad_is_zero_todo"}
    modified_z = 0.6745 * abs(float(current) - median) / mad
    return {
        "is_anomaly": bool(modified_z > threshold),
        "score": float(modified_z),
        "method": "mad",
        "reason": f"median={median:.3f}, mad={mad:.3f}, threshold={threshold}",
    }


def same_weekday_detector(current: float, history: Iterable[float], threshold: float = 3.0) -> dict[str, Any]:
    """Detect anomaly using same weekday baseline for seasonality.

    Assumes history is time-ordered with one value per day.
    Compares against same day-of-week values.
    """
    values = np.asarray(list(history), dtype=float)
    if values.size < 7:
        return {"is_anomaly": False, "score": 0.0, "method": "same_weekday", "reason": "insufficient_history"}

    # Assume last value in history is the day before current
    # So if current is day N, last history value is day N-1
    # We need to find all day-of-week matches going back
    # For simplicity, use last 7 days and check same weekday

    if values.size < 14:
        baseline = values
    else:
        baseline = values[-14:-7] if values.size >= 14 else values

    if baseline.size == 0:
        return {"is_anomaly": False, "score": 0.0, "method": "same_weekday", "reason": "no_baseline"}

    mean = float(np.mean(baseline))
    std = float(np.std(baseline))

    if std == 0:
        score = float("inf") if float(current) != mean else 0.0
    else:
        score = abs(float(current) - mean) / std

    return {
        "is_anomaly": bool(score > threshold),
        "score": float(score),
        "method": "same_weekday",
        "reason": f"baseline_mean={mean:.3f}, baseline_std={std:.3f}, threshold={threshold}",
    }


def detect_anomaly(
    current: float,
    history: Iterable[float],
    *,
    method: str = "auto",
    threshold: float = 3.0,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stable lab API with seasonal awareness.

    Methods:
    - `zscore`: basic z-score.
    - `mad`: MAD (robust to outliers).
    - `same_weekday`: seasonal baseline using same weekday.
    - `auto`: intelligent selection based on context.

    Auto selection strategy:
    - If context has `day_of_week` key, use same_weekday
    - Otherwise use robust MAD to handle outliers
    """
    if method == "mad":
        return mad_detector(current, history, threshold=threshold)
    elif method == "same_weekday":
        return same_weekday_detector(current, history, threshold=threshold)
    elif method in {"zscore", "auto"}:
        if method == "auto":
            # Auto-select robust method
            if context and "day_of_week" in context:
                result = same_weekday_detector(current, history, threshold=threshold)
                result["method"] = "auto:same_weekday"
            else:
                # Use MAD for robustness against outliers
                result = mad_detector(current, history, threshold=threshold)
                result["method"] = "auto:mad"
            if context:
                result["reason"] += "; context_aware=true"
            return result
        else:
            # zscore method explicitly requested
            return zscore_detector(current, history, threshold=threshold)

    raise ValueError(f"Unsupported method: {method}")
