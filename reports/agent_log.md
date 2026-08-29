# AI Agent Decision Log — Data Reliability Lab

## Decision 1: Type Validation in Contract Validator
- **Hypothesis**: Type drift (string/integer confusion) can hide data quality issues even when not_null checks pass
- **Prompt**: "Add explicit type validation to contract_validator.py to detect type mismatches on integer, number, and datetime columns"
- **Agent proposal**: Added type coercion checks for each declared type using pd.to_numeric() and pd.to_datetime() with error='coerce' to detect invalid types
- **Evidence/test**: Type validation now catches when a column declared as `integer` contains strings or NaN after coercion
- **Accept**: ✅ ACCEPTED
- **Why**: Type validation is a critical data quality check that simple NOT_NULL misses. Example: "123ABC" passes NOT_NULL but fails type validation for integer

## Decision 2: Freshness Validation
- **Hypothesis**: Stale data is a silent failure — pipeline can succeed but downstream gets wrong data
- **Prompt**: "Implement freshness validation using the contract['freshness'] configuration"
- **Agent proposal**: Added datetime-based freshness check comparing max(updated_at) against current time with configurable max_delay_minutes threshold
- **Evidence/test**: Freshness check reports delay_minutes metric, flags warnings when data is older than threshold
- **Accept**: ✅ ACCEPTED
- **Why**: Phase 3 fault scenario (stale_kb) requires freshness detection. This is business-critical for real-time systems

## Decision 3: Anomaly Detection with Seasonality
- **Hypothesis**: Z-score without seasonal adjustment has high false positives. Same weekday baseline reduces false alerts
- **Prompt**: "Upgrade detect_anomaly() 'auto' mode to handle seasonality using same-weekday comparisons instead of naive z-score"
- **Agent proposal**: Implemented same_weekday_detector() that compares current value against previous week's same weekday values. Auto mode now chooses between same_weekday (if context has day_of_week) or MAD (robust to outliers)
- **Evidence/test**: Baseline run now shows "auto:same_weekday" method with score=0.00 for healthy data (no false alert on legitimate Friday variation)
- **Accept**: ✅ ACCEPTED with enhancement
- **Why**: Without seasonality, Friday with 600 orders vs Tuesday with 400 orders would falsely trigger anomaly. Same-weekday comparison is more reliable for business metrics

## Decision 4: Enhanced Distribution Drift Detection
- **Hypothesis**: Mean-only comparison misses distribution shape changes. Quantile-based detection is more robust
- **Prompt**: "Add quantile-based distribution drift detection to detect_distribution_shift()"
- **Agent proposal**: Implemented quantile method comparing p10, p50, p90 across baseline vs current. Falls back to KS test if scipy available, else uses quantile method
- **Evidence/test**: Distribution drift now catches shifts in shape, not just mean. Example: skew from uniform to bimodal distribution
- **Accept**: ✅ ACCEPTED
- **Why**: KB document embedding drift is often a shape issue (many similar documents) not just mean shift. Quantiles detect this

## Decision 5: Multi-Window Burn Rate Policy
- **Hypothesis**: Single-window burn rate triggers false alerts on transient spikes. Google SRE playbook shows multi-window helps distinguish incidents from glitches
- **Prompt**: "Implement evaluate_multiwindow_burn() using short-window (1h) and long-window (30d) thresholds"
- **Agent proposal**: Added two-tier policy: fast_burn threshold=10.0 (burn 100% budget in 6h), slow_burn threshold=0.1 (10% budget burn over 30d). Pages only when both elevated (sustained incident) or slow burn sustained
- **Evidence/test**: Can now distinguish 10x spike in 1h (warn only if also elevated over 30d) from sustained slow leak (page immediately even if short window normal)
- **Accept**: ✅ ACCEPTED
- **Why**: Prevents alert fatigue from transient spikes. Matches Google's multi-window alerting strategy proven in production

## Decision 6: Column-Level Lineage Traversal
- **Hypothesis**: Dataset-level lineage isn't enough for incident blast radius. Column-level traces show which exact metrics are affected
- **Prompt**: "Implement transitive column-level downstream traversal in get_column_downstream()"
- **Agent proposal**: Added BFS traversal with deque, similar to dataset-level graph walk. Now handles transitive dependencies (order_amount → revenue_total → dashboard_metric)
- **Evidence/test**: Can now trace "if order_amount corrupts, which dashboard metrics are affected?" beyond just "datasets affected"
- **Accept**: ✅ ACCEPTED
- **Why**: Incident response needs precision — knowing "fct_daily_revenue affected" is less actionable than "daily_revenue.amount column affected"

## Decision 7: Severity-Based Action Handling
- **Hypothesis**: Not all contract failures warrant the same action. Critical issues should block, warnings should quarantine, info should log
- **Prompt**: "Extend contract validator to support severity-aware actions: block vs quarantine vs warn"
- **Agent proposal**: Already present in contract rules. Validator now returns severity with each issue. Failed_issues() function filters by min_severity allowing downstream to decide action
- **Evidence/test**: Phase 1 scenario catches duplicate_pk with severity=critical, fails with 1 critical contract failure
- **Accept**: ✅ ACCEPTED
- **Why**: Enables sophisticated data governance — critical PK violations block, type warnings quarantine for manual review

## Decision 8: dbt Singular Tests for Business Logic
- **Hypothesis**: Generic data tests catch schema issues, but business logic failures (like multi-version customer inflation) need custom SQL assertions
- **Prompt**: "Add singular tests to catch revenue inflation from multi-version customers and verify data freshness"
- **Agent proposal**: Added assert_unique_active_customers.sql (detects when same customer_id has multiple active versions, which would cause left-join inflation) and assert_recent_order_dates.sql (verifies latest data within 30 days)
- **Evidence/test**: Tests detect the SCD violation pattern that would break fct_daily_revenue join cardinality
- **Accept**: ✅ ACCEPTED
- **Why**: dbt can only test schema; business rules require domain knowledge. Example: multi-version customers are valid in slowly-changing dimension but not when is_active is true for >1 row

## Summary of Improvements
1. **Deterministic validation** (types, freshness) catches silent failures
2. **Seasonal anomaly detection** reduces false positives, improves signal
3. **Robust distribution tests** find subtle pattern changes
4. **Multi-window alerting** distinguishes transient from real incidents
5. **Column-level lineage** enables precise blast-radius calculation
6. **Business logic tests** complement schema validation
7. **Severity-driven actions** enable sophisticated incident response

All decisions were validated through Phase 0-7 lab completion and successful detection of public fault scenarios (duplicate_pk caught by contract validator, volume_drop handled by anomaly detector, etc.).
