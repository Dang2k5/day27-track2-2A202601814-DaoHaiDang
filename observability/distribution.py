from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def detect_distribution_shift(
    current_values: Iterable[float],
    baseline_values: Iterable[float],
    *,
    ratio_threshold: float = 3.0,
    method: str = "quantile",
) -> dict[str, Any]:
    """Detect distribution drift using multiple statistical approaches.

    Methods:
    - mean_ratio: simple mean comparison (baseline starter)
    - quantile: compare quantiles (p10, p50, p90) for robustness
    - ks: Kolmogorov-Smirnov test (requires scipy)
    """
    cur = np.asarray(list(current_values), dtype=float)
    base = np.asarray(list(baseline_values), dtype=float)

    if cur.size == 0 or base.size == 0:
        return {"is_anomaly": False, "score": 0.0, "method": method, "reason": "empty_input"}

    if method == "quantile":
        # Compare distribution shape using quantiles
        base_q10, base_q50, base_q90 = np.percentile(base, [10, 50, 90])
        cur_q10, cur_q50, cur_q90 = np.percentile(cur, [10, 50, 90])

        # Compute drift in each quantile
        drift_scores = []
        for bq, cq in [(base_q10, cur_q10), (base_q50, cur_q50), (base_q90, cur_q90)]:
            if bq == 0:
                drift = float("inf") if cq != 0 else 0.0
            else:
                drift = abs(cq - bq) / abs(bq) if bq != 0 else 0.0
            drift_scores.append(drift)

        score = float(max(drift_scores)) if drift_scores else 0.0
        return {
            "is_anomaly": bool(score > ratio_threshold),
            "score": score,
            "method": "quantile_drift",
            "reason": f"base_quantiles=[{base_q10:.1f},{base_q50:.1f},{base_q90:.1f}] "
                     f"curr=[{cur_q10:.1f},{cur_q50:.1f},{cur_q90:.1f}]",
        }

    elif method == "ks":
        # Kolmogorov-Smirnov test
        try:
            from scipy import stats
            statistic, pvalue = stats.ks_2samp(base, cur)
            return {
                "is_anomaly": bool(pvalue < 0.05),  # Traditional p-value threshold
                "score": float(statistic),
                "method": "ks_test",
                "reason": f"ks_statistic={statistic:.4f}, pvalue={pvalue:.4f}",
            }
        except ImportError:
            return detect_distribution_shift(cur, base, ratio_threshold=ratio_threshold, method="quantile")

    else:  # mean_ratio (default fallback)
        cur_mean = float(np.mean(cur))
        base_mean = float(np.mean(base))
        if base_mean == 0:
            score = float("inf") if cur_mean != 0 else 1.0
        else:
            score = max(abs(cur_mean / base_mean), abs(base_mean / cur_mean)) if cur_mean != 0 else float("inf")
        return {
            "is_anomaly": bool(score >= ratio_threshold),
            "score": float(score),
            "method": "mean_ratio",
            "reason": f"baseline_mean={base_mean:.3f}, current_mean={cur_mean:.3f}",
        }
