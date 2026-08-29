from __future__ import annotations

from typing import Any, Iterable

import numpy as np

from observability.anomaly import zscore_detector


def approximate_token_lengths(texts: Iterable[str]) -> list[int]:
    # Deliberately simple proxy; no tokenizer/model download needed.
    return [len(str(t).split()) for t in texts]


def detect_text_length_shift(
    current_texts: Iterable[str],
    baseline_batch_means: Iterable[float],
    *,
    threshold: float = 3.0,
) -> dict[str, Any]:
    lengths = approximate_token_lengths(current_texts)
    current_mean = float(np.mean(lengths)) if lengths else 0.0
    result = zscore_detector(current_mean, baseline_batch_means, threshold=threshold)
    result["metric"] = "mean_text_length"
    result["current_mean"] = current_mean
    return result


def detect_embedding_norm_shift(
    current_norms: Iterable[float], baseline_norms: Iterable[float], threshold: float = 3.0
) -> dict[str, Any]:
    """Detect embedding-space drift using L2 norm statistics.

    Embedding norms often indicate the "importance" or "confidence" of representations.
    Sustained shifts in norm distribution suggest semantic drift.
    """
    cur_norms = np.asarray(list(current_norms), dtype=float)
    base_norms = np.asarray(list(baseline_norms), dtype=float)

    if cur_norms.size == 0 or base_norms.size == 0:
        return {"is_anomaly": False, "score": 0.0, "method": "embedding_norm", "reason": "empty_input"}

    # Compare norm distributions using quantiles
    base_mean = float(np.mean(base_norms))
    cur_mean = float(np.mean(cur_norms))

    base_std = float(np.std(base_norms))
    cur_std = float(np.std(cur_norms))

    # Score based on mean shift relative to baseline std
    if base_std == 0:
        score = float("inf") if cur_mean != base_mean else 0.0
    else:
        score = abs(cur_mean - base_mean) / base_std

    return {
        "is_anomaly": bool(score > threshold),
        "score": float(score),
        "method": "embedding_norm",
        "reason": f"base_mean={base_mean:.4f} (std={base_std:.4f}), "
                 f"curr_mean={cur_mean:.4f} (std={cur_std:.4f}), score={score:.2f}",
    }
