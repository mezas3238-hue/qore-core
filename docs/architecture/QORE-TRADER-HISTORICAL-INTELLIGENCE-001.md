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
exact `TraderVersionIdentity.trader_code` (for example `vt-08` -> `virtual.trader.vt08`), and its
schema version must match the exact Trader version. `compute_trader_identity_family` is the
single canonical family convention shared by the Registry, the Trader Lab, and CIBO. Specialty
is derived from the exact Trader methodology, `certification_state`/`freshness` are derived
(`EVIDENCE_COLLECTED`/`CURRENT`) from governed current evidence rather than caller assertion,
scope is joint (never Cartesian), unresolved contradictions fail closed, and a projection with
no current certified quantitative evidence fails closed instead of fabricating a
collected/current certification state. It also operates **without**
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
- The ledger exposes an externally anchorable root (`TraderHistoryLedgerRoot`,
  `compute_trader_history_ledger_root`). A reconstructed (possibly truncated) ledger
  is authenticated only through `verify_reconstructed_history(registry, expected_root)`;
  a self-consistent truncated ledger can never authenticate itself. Rebuilding a ledger
  from an external record set must go through `reconstruct_trader_history(records,
  expected_root)`, which refuses any record set whose root does not match the
  authoritative anchor.

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
- `CERTIFIED` is never caller assertion: it requires a sealed
  `TraderHistoryCertification` envelope (exact authority kind, UUID authority id,
  `issued_at`, and the exact `study_id`/`study_version` it certifies) whose `_issued`
  marker no in-repo constructor can set (only an owning authority or a trusted test double
  can mint it), whose authority kind exactly owns the study kind, whose
  `issued_at >= produced_at`, whose subject binding exactly matches the study identity
  (so an issued envelope can never be replayed onto a different study), and which is hashed
  into the study fingerprint. A non-certified study must carry no certification.
- Out-of-sample stages cannot be laundered from development/calibration data: `OOS`,
  `WALK_FORWARD`, and `INDEPENDENT_VALIDATION` studies must consume an
  `EXTERNAL_VALIDATION` holdout partition.

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
- projects only `CERTIFIED`+`SUFFICIENT`+evidence-backed quantitative claims, honoring each
  record's epistemic moment (`max(produced_at, certification.issued_at)`), so future
  certification/issuance never leaks into an earlier projection;
- preserves market/timeframe/regime/side/condition specificity (no blind pooling), and scope
  is joint (market x timeframe), never Cartesian;
- retains contradictory values for the same metric scope as `TraderHistoryContradiction`
  (indeterminate) instead of choosing the favorable value;
- surfaces sparse samples as `insufficient_metrics`, stale/superseded records separately, and
  every consumed holdout scoped to the exact Trader lineage and the derived_at instant;
- suppresses certified evidence only via a CERTIFIED superseder (never a hypothesis/observed
  record), with supersession cycles, produced-time inversions, and certification-time
  inversions (a superseder certified before its target) rejected;
- returns no ranking (`best market`) and no authority.

`market_evidence(registry, trader_version, derived_at=...)` and
`diff_versions(registry, left, right, derived_at=...)` honor the same epistemic moment:
they report only knowledge whose `max(produced_at, certification.issued_at)` is on or before
`derived_at`, so a future-certified or future-produced record can never leak into a current
market view or version diff.

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
