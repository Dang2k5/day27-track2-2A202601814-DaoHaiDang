from __future__ import annotations

from typing import Any


def calculate_slo(target: float, bad_events: int, total_events: int) -> dict[str, Any]:
    if not 0 < target < 1:
        raise ValueError("target must be between 0 and 1 (exclusive)")
    if bad_events < 0 or total_events < 0 or bad_events > total_events:
        raise ValueError("invalid event counts")
    allowed_bad_rate = 1.0 - target
    if total_events == 0:
        return {
            "target": target,
            "actual_bad_rate": 0.0,
            "allowed_bad_rate": allowed_bad_rate,
            "burn_rate": 0.0,
            "remaining_error_budget_fraction": 1.0,
            "breached": False,
        }
    actual_bad_rate = bad_events / total_events
    burn_rate = actual_bad_rate / allowed_bad_rate
    consumed_fraction = min(1.0, actual_bad_rate / allowed_bad_rate)
    return {
        "target": target,
        "actual_bad_rate": actual_bad_rate,
        "allowed_bad_rate": allowed_bad_rate,
        "burn_rate": burn_rate,
        "remaining_error_budget_fraction": max(0.0, 1.0 - consumed_fraction),
        "breached": bool(actual_bad_rate > allowed_bad_rate),
    }


def evaluate_multiwindow_burn(
    *,
    short_window_burn: float,
    long_window_burn: float,
    policy: str = "starter",
) -> dict[str, Any]:
    """Multi-window burn-rate policy to distinguish transient spikes from sustained outages.

    Policy thresholds (inspired by Google SRE playbook):
    - Fast burn (6h): burn_rate > 10 on short window triggers page
    - Slow burn (30d): burn_rate > 0.1 on long window triggers page
    - Both sustained: very urgent

    Returns alerting decision and severity.
    """
    page = False
    severity = "info"
    reason = ""

    if policy in {"starter", "google_sre"}:
        # Fast burn threshold: 100% error budget in 6 hours
        # long_window represents 30-day window, short represents 1-hour window
        # If 1-hour burn is > 10x sustainable rate AND 30-day burn is sustained
        fast_burn_threshold = 10.0  # 10x baseline over 1-hour
        slow_burn_threshold = 0.1   # 10% baseline over 30-day

        if short_window_burn > fast_burn_threshold and long_window_burn > slow_burn_threshold:
            # Both short and long windows are elevated: likely real incident
            page = True
            severity = "critical"
            reason = f"sustained_fast_burn: short={short_window_burn:.2f}, long={long_window_burn:.2f}"
        elif short_window_burn > fast_burn_threshold and short_window_burn < 100:
            # Fast short burn but long window normal: transient spike, only warn
            page = False
            severity = "warning"
            reason = f"transient_spike: short={short_window_burn:.2f} (fast but long window ok)"
        elif long_window_burn > slow_burn_threshold:
            # Slow burn sustained over long period: background issues, need investigation
            page = True
            severity = "warning"
            reason = f"slow_sustained_burn: long={long_window_burn:.2f}"
        else:
            severity = "info"
            reason = "all_windows_healthy"

    return {
        "page": page,
        "severity": severity,
        "reason": reason,
        "short_window_burn": short_window_burn,
        "long_window_burn": long_window_burn,
        "thresholds": {"fast_burn": 10.0, "slow_burn": 0.1},
    }
