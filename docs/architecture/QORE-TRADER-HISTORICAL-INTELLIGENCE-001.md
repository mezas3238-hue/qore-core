# QORE-TRADER-HISTORICAL-INTELLIGENCE-001 — Trader Historical Intelligence Registry

## Status

**IMPLEMENTED — BOUNDED FOUNDATION SLICE**

Opening baseline:

```text
main @ c283c9d793ca04b7477d32f5cd0969de9a304195
tree @ 6d9a3728ddfbc2161171af1315c59ff1f0adf3d6
```

Primary issue `#500` (Trader Historical Intelligence Registry). This is the first bounded,
append-only longitudinal-memory slice; it composes (never replaces) the existing Trader Lab,
CIBO capability profile, CIBO development review, and CIBO Trader Manager.

## Purpose

Provide a provider-neutral, deterministic, append-only **Trader Historical Intelligence
Registry** that preserves the complete technical/scientific biography of each exact Trader
version and derives current capability views from certified historical evidence.

Canonical law:

```text
TRADER HISTORY IS APPEND-ONLY
CURRENT CAPABILITY = PROJECTION OF CERTIFIED HISTORICAL EVIDENCE
HYPOTHESIS != OBSERVATION != CERTIFIED FACT
NEW TRADER VERSION != MUTATION OF OLD HISTORY
INSUFFICIENT SAMPLE != POSITIVE EVIDENCE
FAILED GATE != END OF RESEARCH
```

## Ownership boundary

| Component | Owns | Never owns |
| --- | --- | --- |
| Trader Lab (`trader_lab/`) | governed stage qualification, candidate binding, promotion gating | historical memory, current-view projection |
| **Trader Historical Intelligence** (`trader_history/`) | append-only study ledger, epistemic/sufficiency typing, consumed-holdout registry, deterministic current view | DEMO eligibility, execution, Risk approval |
| CIBO Capability Profile (`cibo_trader_capability_profile.py`) | immutable capability profile value | historical records, projection |
| CIBO Trader Manager (`cibo_trader_manager.py`) | DEMO-team management decisions | historical memory, evidence production |

`trader_history` is consumed by CIBO through `project_cibo_capability_profile`, which maps the
current view into `CiboTraderCapabilityProfile` **without** mutating history and **without**
allowing cross-Trader identity projection: the supplied CIBO identity family must match the
exact `TraderVersionIdentity.trader_code` (for example `vt-08` -> `virtual.trader.vt08`). It also
operates **without**
constructing `CiboDemoEligibilityEvidence`.

## Append-only laws

- The registry is a frozen aggregate; `append_study` returns a **new** registry.
- No delete, overwrite, or relabel of older-version evidence exists.
- An exact idempotent replay of the same immutable record (same study identity, version, and
  logical content) is a no-op `Success` of the same registry.
- A duplicate logical identity with a contradictory payload fails closed
  (`TraderHistoryBlockedError`).
- Records are canonically ordered by `(produced_at_utc, trader_version_fingerprint,
  study_id, study_version)`, so reordered ingestion yields the identical registry.

## Epistemic and sufficiency semantics

`TraderHistoryEpistemicStatus`: `OBSERVED`, `INFERRED`, `HYPOTHESIS`, `FALSIFIED`, `CERTIFIED`,
`INSUFFICIENT_EVIDENCE`, `STALE`, `SUPERSEDED`.

`TraderHistorySufficiency`: `SUFFICIENT`, `INSUFFICIENT`, `UNKNOWN`.

Construction invariants fail closed:

- `CERTIFIED` requires `SUFFICIENT`; `INSUFFICIENT_EVIDENCE` requires `INSUFFICIENT`.
- `HYPOTHESIS` kind -> `HYPOTHESIS` status (a hypothesis can never be constructed as a fact).
- `HYPOTHESIS_FALSIFICATION` -> `FALSIFIED`; `HYPOTHESIS_CONFIRMATION` -> `CERTIFIED`.
- `FAILURE_ANALYSIS` is diagnostic (`INFERRED`); `CHARACTERIZATION` is descriptive/diagnostic.
- A quantitative claim requires non-empty evidence refs and `OBSERVED`/`INFERRED`/`CERTIFIED`
  status; it can never be `HYPOTHESIS`/`FALSIFIED`/`INSUFFICIENT_EVIDENCE`.

## Study and version lineage

- `TraderVersionIdentity` binds exact code (`vt-01`..`vt-31`), version, config fingerprint,
  methodology identity/fingerprint, and software SHA; a change creates a new version.
- `TraderHistoryStudyRecord` binds study identity/version, exact version, market/timeframe
  scope, side/session/regime/condition, consumed partitions, metrics, findings, evidence refs,
  hypothesis lineage, and a recomputed fingerprint.
- A `HYPOTHESIS_CONFIRMATION` must reference an existing `HYPOTHESIS` parent and must bind a
  fresh (unconsumed) `EXTERNAL_VALIDATION` partition — consumed holdouts cannot certify a
  modified Trader, and hindsight cannot launder into confirmation.
- An `EXTERNAL_VALIDATION` partition may be claimed by at most one study.

## Current-view derivation

`project_current_capability(registry, trader_version, derived_at=...)` is a pure, deterministic
function that:

- selects only records whose exact version fingerprint matches the request (version/config
  mismatch is excluded, never laundered);
- projects only `CERTIFIED`+`SUFFICIENT`+evidence-backed quantitative claims;
- preserves market/timeframe/regime/side/condition specificity (no blind pooling);
- retains contradictory values for the same metric scope as `TraderHistoryContradiction`
  (indeterminate) instead of choosing the favorable value;
- surfaces sparse samples as `insufficient_metrics`, stale/superseded records separately, and
  every consumed holdout;
- returns no ranking (`best market`) and no authority.

## Authority prohibitions

`TRADER HISTORY != EXECUTION AUTHORITY`. No contract here constructs an order, quantity,
account, custody, Risk bypass, or Production/live-capital authority. `CiboCertificationState`
has no `DEMO_ELIGIBLE` member, and this package never constructs `CiboDemoEligibilityEvidence`.

## Determinism and validation

- `@dataclass(frozen=True, slots=True)` throughout; explicit timezone-aware timestamps only;
  canonical deterministic ordering; typed `Result`/`Success`/`Failure`; typed errors.
- `tests/infrastructure/trader_history/test_contracts.py`, `test_registry.py`,
  `test_cibo_adapter.py` cover normal, adversarial, property, and benign-control cases
  (append-only, idempotent replay, contradictory duplicate, version/config isolation,
  insufficient-sample, contradiction retention, holdout reuse, hypothesis lifecycle, exact
  runtime types, timezone fail-closed, canonical ordering, no-authority-field assertion, and
  the full `vt-01`..`vt-31` catalog).

## Explicitly not implemented

- Live/Production data, secrets, or terminal run artifacts (deterministic fixtures only);
- provider adapters, order/execution/custody construction;
- promotion/selection execution or any authority transition;
- the full six-market first-cohort economic program (integration path is provided, conclusions
  are not fabricated before the program completes).
