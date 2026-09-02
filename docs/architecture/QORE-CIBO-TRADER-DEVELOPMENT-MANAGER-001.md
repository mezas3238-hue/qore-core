# QORE-CIBO-TRADER-DEVELOPMENT-MANAGER-001 — CIBO Trader Capability / Development / Manager Foundation

## Status

**IMPLEMENTED — BOUNDED FOUNDATION SLICE**

Opening baseline:

```text
main @ 5a158ef0fb2e21db95f2be0685373780bf1ab197
tree @ 5e2b37b23b01fe23fd373d39b01573e9607a73ad
```

Primary issue `#479 QORE-CIBO-TRADER-DEVELOPMENT-MANAGER-001`; parents #469, #470, #473, #474, #367, #477.
This is the FIRST bounded implementation slice of CIBO as Trader Development Director + Trader Manager.

## Purpose

Introduce three provider-neutral, deterministic, fail-closed CIBO contracts that:

1. represent an exact evidence-backed Trader Capability Profile;
2. let CIBO issue a non-authoritative Trader Development recommendation;
3. let CIBO issue deterministic DEMO-team management decisions only for eligible exact Trader versions.

The slice is generic over the VT-01..VT-31 catalog (and beyond): it hard-codes no trader identity, no methodology family, and no provider.

## Placement and reuse (LSP-verified)

All three contracts live in `src/qore/infrastructure`, beside the existing CIBO supervision
evidence (`cibo_supervised_runtime.py`, `cibo_operational_supervision_evidence.py`). This is
required by layering: `qore.modules` and `qore.governance` have **zero** imports of
`qore.infrastructure`, while the Capability Profile must reuse infrastructure-scoped identity and
evidence types.

Reused exactly:

- `ResearchDecisionEvaluatorIdentity` (`family` + `schema_version` + `software_revision`) — the
  exact Trader identity/version contract; no more-exact Trader identity exists (`ExecutiveTraderId`
  is only an opaque read-model string handle, and `modules/trader/contracts.py` carries no identity).
- `InfrastructureError` — correct error base for pure provider-neutral value/evidence contracts
  (precedent: `research_strategy_freeze.py`, `research_run.py`, all `research_*` evidence modules).
- `Result` / `Success` / `Failure` — deterministic typed outcomes.
- 64-hex SHA-256 fingerprint *pattern* (mirrors `ResearchStrategyConfigurationDigest`,
  `ResearchFrozenOosFingerprint`, and the per-domain fingerprint value objects).

New minimal types (reuse was impossible or semantically inexact):

- `CiboEvidenceRef` — canonical opaque lowercase evidence reference; `ExecutiveEvidenceRef` lives
  in `qore.governance` and cannot be imported by infrastructure without reversing dependency direction.
- `CiboTraderConfigFingerprint` — the trader config fingerprint is a different canonical schema than
  a strategy-parameter manifest, so `ResearchStrategyConfigurationDigest` is not semantically exact.

## Capability Profile

`CiboTraderCapabilityProfile` (`cibo_trader_capability_profile.py`) retains, via exact types:

- exact Trader identity/version (`ResearchDecisionEvaluatorIdentity`);
- methodology/version/config fingerprint (`CiboTraderConfigFingerprint`);
- specialty/role, qualified markets/timeframes, required inputs;
- formal action semantics and lifecycle characteristics as opaque evidence references;
- certified Lab evidence references tagged by stage (REPLAY, FAST_FORWARD, OOS, STRESS,
  MONTE_CARLO, ECONOMIC, RISK);
- favorable/weak/degraded regime evidence references;
- economic/risk metrics (`Decimal`) **only when backed by an explicit certified evidence reference**;
- cost/spread/slippage sensitivity, correlation/dependence, and Risk-envelope references;
- abstain/reduce/suspend/return-to-Lab operating conditions;
- certification state, evidence freshness (`as_of` + state), and explicit limitations.

Invariants enforced at construction:

- immutable tuples with canonical deterministic order; duplicates rejected;
- exact runtime types (`bool` cannot launder as `int`; `float` cannot launder as `Decimal`);
- economic metrics require certified backing (fail closed, no fabricated quantitative claims);
- evidence references are sanitized (no secrets/tokens/credentials in refs or `logical_values()`);
- no hidden clock, `uuid4`, random state, or mutable globals — all timestamps are explicit;
- `CiboCertificationState` has **no** `DEMO_ELIGIBLE` member, so a profile cannot manufacture demo eligibility.

## Development Director review

`review_capability_profile` (`cibo_trader_development_review.py`) consumes a profile and returns an
immutable `CiboDevelopmentReview` with a non-authoritative recommendation:

- continue curriculum / more evidence required;
- retrain / return to Lab;
- recommend promotion for independent gate consideration;
- recommend rejection;
- recommend suspension/degradation review.

The review never mutates the candidate and creates no promotion authority. Fail-closed cases:

- identity/version or config-fingerprint mismatch (optional expected bindings) — blocked;
- contradictory suspend/promotion evidence — blocked;
- unsupported quantitative claims (revalidated defensively after reflective corruption) — blocked;
- stale/incomplete evidence is never treated as current certainty (stale → return-to-Lab,
  insufficient → more-evidence-required);
- promotion is structurally unreachable for REJECTED/SUSPENDED/DEGRADED states (no promotion laundering).

## Trader Manager MVP

`CiboTraderManager` (`cibo_trader_manager.py`) is a stateless policy over
`CiboDemoEligibilityEvidence` (the only DEMO_ELIGIBLE proof) and produces `CiboManagementDecision`
with states `ELIGIBLE`, `SELECTED`, `REDUCED`, `SUSPENDED`, `BLOCKED`:

- only an exact version with valid `DEMO_ELIGIBLE` evidence is selectable;
- suspended/blocked/ineligible (rejected/suspended/degraded/stale) traders cannot be selected;
- selection/reduction/suspension retain exact reasons and evidence references;
- the decision binds exact experiment arm and risk mode (`TRADERS_RISK_ONLY` vs
  `CIBO_MANAGED_TRADERS_RISK`) and rejects version/config mismatch between arms;
- `CIBO_MANAGED_TRADERS_RISK` requires Risk-envelope evidence (no Risk bypass);
- the output has no provider-native order/execution fields;
- concentration conclusions are produced only from explicit certified correlation evidence —
  missing evidence yields no conclusion (`None`), never an invented conclusion.

## Authority boundary

`CIBO MANAGEMENT != EXECUTION AUTHORITY` and `CIBO RECOMMENDATION != PROMOTION AUTHORITY`.

None of these contracts constructs an order, mutates account/capital state, bypasses Risk, or
grants production/execution authority. `TRADER VOICE != FORMAL SIGNAL` and free-form dialogue is
outside this slice (existing `cibo_executive_dialogue.py` already bounds that surface).

## Determinism

- `@dataclass(frozen=True, slots=True)` throughout;
- explicit timezone-aware timestamps only;
- canonical deterministic ordering of all tuples and reasons;
- deterministic `logical_values()`; deterministic equality/replay for identical inputs;
- typed `Result / Success / Failure` and typed errors.

## Validation evidence

- `tests/infrastructure/test_cibo_trader_capability_profile.py`
- `tests/infrastructure/test_cibo_trader_development_review.py`
- `tests/infrastructure/test_cibo_trader_manager.py`

Together they cover: exact valid profile; wrong identity/config binding; immutable/canonical
ordering; exact runtime types (`bool`/`float` laundering rejected); duplicate evidence/market
rejection; stale/missing evidence fail-closed; unbacked metric rejection; recommendation cannot
self-promote; non-DEMO-eligible cannot be selected; suspended/blocked cannot be selected; no
provider-native execution fields; Risk bypass blocked by contract; A/B version mismatch rejected;
no hidden time/randomness; sanitization; deterministic replay/equality.

## Explicitly not implemented

- Lab evidence production, replay, fast-forward, OOS, Monte Carlo, or Risk computation (those
  contracts already exist under `qore.infrastructure/research_*` and are referenced, not owned);
- promotion/selection *execution* or any authority transition — this slice is advisory/policy only;
- provider adapters, order construction, deposits/withdrawals;
- the full Program J roadmap (this is the first bounded CIBO slice).
