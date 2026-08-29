# Incident Report — Data Reliability Game Day

## Severity
**P1 (Critical)** — Direct business impact (fraudulent refunds, revenue miscalculation)

## Summary
System ingested duplicate order records (603 total vs normal 600). Contract validator detected **1 critical failure** on unique constraint. Without this check, duplicates would have propagated downstream to fct_daily_revenue, causing revenue inflation on the CEO dashboard and potentially triggering incorrect refund policies via the Support Agent.

## Detection
- **Signal**: Contract unique constraint violation on `order_id` column (severity: critical)
- **First observed time**: During baseline validation run immediately after fault injection
- **Detection method**: Data contract validation (deterministic check)
- **Detection latency**: <1 second after data arrival

## Root Cause
Data ingestion pipeline inserted duplicate `order_id` rows into the incoming dataset. This appears to be a source-side issue (duplicate kafka messages, re-processing without deduplication, or malformed batch logic).

**Technical root cause**: The order_id is declared as `unique: true, severity: critical` in the contract. The 3 duplicate rows violated this constraint, indicating upstream data quality regression.

## Evidence
1. **Contract validation output**: 1 failed check (unique constraint), severity=critical
2. **Row count anomaly**: 603 rows (vs normal 600) — 3 extra rows detected
3. **Blast radius scope**: Downstream models affected: `fct_daily_revenue`, `ceo_revenue_dashboard`
4. **Business impact**: Duplicates would inflate daily revenue in CEO dashboard by ~0.5% per duplicate
5. **Lineage trace**: stg_orders → fct_daily_revenue → ceo_revenue_dashboard, CEO Refund Policy Agent

```text
orders.csv (duplicate_pk injected)
    ↓
contract validation ← **CAUGHT HERE**
    ↓ (if undetected)
stg_orders ← raw staging
    ↓
fct_daily_revenue ← revenue inflation
    ↓
ceo_revenue_dashboard ← wrong metrics
    ↓
support-agent (old refund policy) ← incorrect decisions
```

## Blast Radius
**Scope**: Revenue metrics and refund decision logic would be corrupted

- **Critical assets affected**:
  - `fct_daily_revenue` — daily revenue aggregates (would be inflated)
  - `ceo_revenue_dashboard` — executive reporting (would show false growth)
  - Support Agent via old refund policy retrieval (would use stale KB)

- **Downstream consumers at risk**:
  - CEO (decision-making based on wrong revenue)
  - Finance team (reconciliation would show discrepancies)
  - Customer Support (refund policy would be inconsistent)

- **Estimated impact**: 
  - 3 duplicate rows out of 600 = 0.5% revenue inflation
  - Affects all downstream aggregations depending on daily_revenue join cardinality

## Mitigation
✅ **Immediate**: Contract validation blocked the data at ingestion boundary
- Prevention worked as designed — contract caught it before transformation

**Short-term actions**:
1. Reject duplicate orders at source (deduplicate in ingestion pipeline)
2. Add duplicate detection in Kafka consumer with idempotent key management
3. Verify no duplicates previously escaped to production

**Verification**:
- Reset lab to healthy baseline
- Re-run contract validation — should pass (0 critical failures)
- Verify dbt tests on stg_orders.order_id (unique constraint)
- Check downstream fct_daily_revenue and dashboard metrics return to normal

## Recovery
```bash
# Step 1: Reset to clean data
make reset

# Step 2: Verify contract passes
python scripts/run_baseline.py
# Expected output: critical contract fails = 0

# Step 3: Verify dbt tests pass
make dbt
# All 14 tests should pass

# Step 4: Verify downstream metrics
pytest tests_public -q
# All 10 tests should pass
```

✅ **Recovery verified**: All systems returned to healthy state

## Verification
- [x] Contract healthy — 0 critical failures (Phase 1)
- [x] dbt tests healthy — 14/14 passing (Phase 2)
- [x] Unique constraint on stg_orders.order_id caught duplicates (Phase 1)
- [x] Anomaly detection returned to baseline (Phase 3)
- [x] SLO healthy — error budget not burned (Phase 5)
- [x] Downstream output verified — blast radius trace via lineage (Phase 4)

## Prevention / Action Items
| Action | Owner | Deadline | Why |
|---|---|---|---|
| Add idempotent key + deduplication to Kafka consumer | Data Eng | T+3d | Prevent duplicate ingestion at source |
| Add sample dbt data test for newer PK duplicates | Analytics | T+1d | Catch future duplicate regressions |
| Enable contract validation in pre-flight checks | DataOps | T+2d | Make contract checks mandatory before loading |
| Document contract severity levels in runbook | SRE | T+5d | Ensure team understands critical vs warning |

---

**Lab Phase Completion:**
- ✅ Phase 0: Healthy baseline established
- ✅ Phase 1: Contract validation with type + freshness checking
- ✅ Phase 2: dbt transformation tests (unique, non-null, business logic)
- ✅ Phase 3: Anomaly detection with seasonality (same_weekday method)
- ✅ Phase 4: Lineage and blast radius calculation
- ✅ Phase 5: SLO/error budget with multi-window burn-rate policy
- ✅ Phase 6: Incident investigation using systematic evidence
- ✅ Phase 7: Incident report and action items
