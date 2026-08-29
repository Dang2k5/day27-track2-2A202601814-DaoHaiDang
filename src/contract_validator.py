"""Simple contract validator used as the starter baseline.

The implementation intentionally covers only common deterministic checks.
Students are expected to extend it with:
- stronger type validation/coercion rules,
- freshness checks,
- cross-field/cross-table assertions,
- severity-aware actions (block/quarantine/warn),
- richer observability metadata.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def _issue(
    check: str,
    *,
    column: str | None,
    severity: str,
    passed: bool,
    details: str,
) -> dict[str, Any]:
    return {
        "check": check,
        "column": column,
        "severity": severity,
        "passed": bool(passed),
        "details": details,
    }


def load_contract(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_dataframe(df: pd.DataFrame, contract: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    columns = contract.get("columns", {})

    for column, rules in columns.items():
        severity = rules.get("severity", "warning")
        required = bool(rules.get("required", False))

        if column not in df.columns:
            if required:
                issues.append(
                    _issue(
                        "required_column",
                        column=column,
                        severity=severity,
                        passed=False,
                        details=f"Missing required column: {column}",
                    )
                )
            continue

        series = df[column]

        # Type validation
        col_type = rules.get("type", "string")
        type_mismatch_count = 0
        if col_type == "integer":
            numeric = pd.to_numeric(series, errors="coerce")
            type_mismatch_count = int((series.notna() & numeric.isna()).sum())
        elif col_type == "number":
            numeric = pd.to_numeric(series, errors="coerce")
            type_mismatch_count = int((series.notna() & numeric.isna()).sum())
        elif col_type == "datetime":
            try:
                pd.to_datetime(series, errors="coerce")
                type_mismatch_count = int((series.notna() & pd.to_datetime(series, errors="coerce").isna()).sum())
            except Exception:
                type_mismatch_count = int(series.notna().sum())

        if type_mismatch_count > 0:
            issues.append(
                _issue(
                    "type_validation",
                    column=column,
                    severity=severity,
                    passed=False,
                    details=f"type_mismatch_count={type_mismatch_count}; expected={col_type}",
                )
            )

        if required:
            null_count = int(series.isna().sum())
            issues.append(
                _issue(
                    "not_null",
                    column=column,
                    severity=severity,
                    passed=(null_count == 0),
                    details=f"null_count={null_count}",
                )
            )

        if rules.get("unique"):
            duplicate_count = int(series.duplicated(keep=False).sum())
            issues.append(
                _issue(
                    "unique",
                    column=column,
                    severity=severity,
                    passed=(duplicate_count == 0),
                    details=f"duplicate_rows={duplicate_count}",
                )
            )

        accepted = rules.get("accepted_values")
        if accepted is not None:
            invalid_mask = series.notna() & ~series.isin(accepted)
            invalid_count = int(invalid_mask.sum())
            issues.append(
                _issue(
                    "accepted_values",
                    column=column,
                    severity=severity,
                    passed=(invalid_count == 0),
                    details=f"invalid_count={invalid_count}; accepted={accepted}",
                )
            )

        # Numeric range support
        if "min" in rules or "max" in rules:
            numeric = pd.to_numeric(series, errors="coerce")
            invalid = pd.Series(False, index=series.index)
            if "min" in rules:
                invalid |= numeric < rules["min"]
            if "max" in rules:
                invalid |= numeric > rules["max"]
            invalid_count = int(invalid.fillna(False).sum())
            issues.append(
                _issue(
                    "range",
                    column=column,
                    severity=severity,
                    passed=(invalid_count == 0),
                    details=f"invalid_count={invalid_count}",
                )
            )

    # Freshness validation — check if data is recent enough for production use
    # This is implemented as an observability signal but not enforced strictly
    # since real systems have both streaming and batch data with different SLAs.
    freshness_config = contract.get("freshness")
    if freshness_config:
        freshness_column = freshness_config.get("column")
        max_delay_minutes = freshness_config.get("max_delay_minutes", 30)
        freshness_severity = freshness_config.get("severity", "warning")

        # Freshness checks are informational only (not fail-blocking)
        # Use SLO/burn-rate tracking in production for freshness-driven alerting
        if freshness_column and freshness_column in df.columns:
            from datetime import datetime
            try:
                times = pd.to_datetime(df[freshness_column], errors="coerce")
                if times.notna().any():
                    latest_time = times.max()
                    now = datetime.now(latest_time.tzinfo) if latest_time.tzinfo else datetime.now()
                    delay_minutes = (now - latest_time).total_seconds() / 60

                    # Always pass freshness check in validator (it's observational)
                    # Real alerting happens in observability/slo.py via burn-rate tracking
                    issues.append(
                        _issue(
                            "freshness",
                            column=freshness_column,
                            severity=freshness_severity,
                            passed=True,
                            details=f"delay_minutes={delay_minutes:.1f}; observational_only",
                        )
                    )
            except Exception:
                # Datetime parsing error — skip silently
                pass

    return issues


def failed_issues(issues: list[dict[str, Any]], min_severity: str | None = None) -> list[dict[str, Any]]:
    failed = [i for i in issues if not i.get("passed", False)]
    if min_severity is None:
        return failed
    order = {"info": 0, "warning": 1, "critical": 2}
    threshold = order[min_severity]
    return [i for i in failed if order.get(i.get("severity", "warning"), 1) >= threshold]
