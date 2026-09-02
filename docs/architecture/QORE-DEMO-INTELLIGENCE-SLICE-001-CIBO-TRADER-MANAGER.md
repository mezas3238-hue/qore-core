# QORE DEMO Intelligence Slice — CIBO Trader Manager MVP

Issue #470 · `QORE-DEMO-INTELLIGENCE-SLICE-001` · DEMO/research scope only.

The CIBO Trader Manager is a **pure, deterministic, fail-closed participation manager** over
concrete trader evidence. It selects / reduces / suspends / blocks / recommends bounded
participation. It is **not** execution authority: it never creates an `OrderIntent`, never grants
Risk authorization, never calls a provider/execution gateway, and never bypasses Risk. Its output is
a recommendation, not an order.

## Scope and non-goals

- **In scope:** exact trader version binding, immutable typed performance/risk evidence, an
  immutable manager policy, ordered fail-closed evaluation stages, deterministic ranking and
  tie-break, and full provenance.
- **Out of scope (by design):** Trader Lab / promotion (#473/#474), cTrader execution (#471),
  provider-fill/PnL analytics (#472), any production authority, calibration/OOS promotion.

## Closed enums

| enum | members | meaning |
|---|---|---|
| `CiboManagerMode` | `TRADERS_RISK_ONLY`, `CIBO_MANAGED_TRADERS_RISK` | exact A/B benchmark mode; never relabeled after outcome observation |
| `CiboTraderParticipation` | `ELIGIBLE`, `SELECTED`, `REDUCED`, `SUSPENDED`, `BLOCKED` | closed per-trader participation decision |
| `CiboRiskClassification` | `CLEAR`, `FLAGGED`, `VIOLATION` | closed risk evidence classification |

The two modes are identical except for the retained `mode` label and the derived policy
fingerprint, so a trader's identity/version/configuration remains comparable across modes. No
hindsight relabeling.

## Inputs

### `CiboTraderVersionBinding` (exact, immutable)
- `trader_id` (`CiboTraderId`), `evaluator_family`, `schema_version`, `software_revision`, and a
  `config_fingerprint` (exactly 64 lowercase hex chars).

### `CiboPerformanceEvidence` (immutable, typed, freshness/sample aware)
- `metric_code`, `metric_value` (`Decimal`, finite), `sample_count` (int ≥ 0), `as_of`
  (timezone-aware `datetime`), `evidence_ref` (`UUID`).

### `CiboRiskEvidence` (immutable, typed)
- `classification` (`CiboRiskClassification`), `violation_count` (int ≥ 0), `as_of`
  (timezone-aware `datetime`), `evidence_ref` (`UUID`).

### `CiboManagerPolicy` (exact, immutable, deterministic invariants)
- `mode`, `selection_count` (≥ 1), `ranking_metric_code`, `freshness_bound` (`timedelta` > 0),
  `minimum_samples` (≥ 1), `violation_floor` (≥ 1), `selection_threshold` (finite `Decimal`),
  `reduced_weight` (finite `Decimal` strictly in `(0, 1)`).
- A deterministic SHA-256 `fingerprint` is derived over the canonical policy projection.

## Ordered fail-closed evaluation stages

For each candidate (processed in a deterministic order by
`(family, schema_version, software_revision, trader_id, config_fingerprint)`), the first matching
stage wins:

1. `risk.violation` — `classification == VIOLATION` ⇒ `BLOCKED`, weight 0.
2. `risk.violation-floor` — `violation_count >= policy.violation_floor` ⇒ `BLOCKED`, weight 0.
3. `evidence.contradictory` — `performance.as_of > evaluated_at` or `risk.as_of > evaluated_at`
   (future-dated material evidence) ⇒ `BLOCKED`, weight 0.
4. `performance.stale` — `performance.as_of` older than the freshness bound ⇒ `BLOCKED`, weight 0.
5. `risk.stale` — `risk.as_of` older than the freshness bound ⇒ `BLOCKED`, weight 0.
6. `performance.insufficient-samples` — `sample_count < policy.minimum_samples` ⇒ `BLOCKED`, weight 0.
7. `metric.code-mismatch` — `metric_code != policy.ranking_metric_code` ⇒ `BLOCKED`, weight 0.
8. `risk.flagged` — `classification == FLAGGED` ⇒ `SUSPENDED`, weight 0 (suspended is never selected).
9. `metric.below-threshold` — `metric_value < policy.selection_threshold` ⇒ `REDUCED`,
   weight `policy.reduced_weight`.
10. Otherwise the candidate is `ELIGIBLE` and enters deterministic ranking.

A suspended or blocked trader can never be selected: those outcomes are emitted before ranking.

## Deterministic ranking and tie-break

Eligible candidates are ranked by the canonical stable key:

```
(-metric_value, evaluator_family, schema_version, software_revision, trader_id)
```

The top `selection_count` candidates become `SELECTED` (weight 1); the remainder stay `ELIGIBLE`
(weight `reduced_weight`). Ties are broken exactly by family → schema version → software revision →
trader id, never by input order. Recommendations are returned sorted by `(trader_id, reason)`.

## Provenance

`CiboManagerProvenance` retains the benchmark `mode`, `policy_fingerprint`,
`manager_schema_version` (`v1`), `manager_software_revision` (`qore.cibo.trader-manager.v1`),
`evaluated_at` (supplied explicitly by the caller), `candidate_count`, and `selected_count`.
Recommendation `evidence_refs` reference the exact performance and risk evidence used.

## Determinism and hygiene

- Pure function of `(policy, candidates, evaluated_at)`; no wall clock, RNG, `uuid4`, threads,
  sleeps, schedulers, hidden retries, global mutable state, provider IO, or execution authority.
- `evaluated_at` is caller-supplied and timezone-aware; freshness and "future evidence"
  contradictions are computed against it.
- Secret-like material in public identifiers (`trader id`, `metric code`, reason codes, etc.) is
  rejected at construction.
- Manager output contains no `OrderIntent` / `AuthorizedOrderIntent`; the recommendation is not
  execution authority and cannot bypass Risk.
