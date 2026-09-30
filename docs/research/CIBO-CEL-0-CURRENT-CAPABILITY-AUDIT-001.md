# CIBO CEL-0 — Current Capital-Efficient Leverage Capability Audit 001

## Status

**CEL-0 CURRENT CAPABILITY AUDIT — COMPLETE / RESEARCH GOVERNANCE ONLY**

Primary PR: #651  
Branch: `agent/cibo-capital-efficiency-sizing-lab-001`

This audit applies the Owner law:

```text
DO NOT DUPLICATE EXISTING CIBO INTELLIGENCE.

LOW MARGIN != LOW RISK.

CIBO MUST MAXIMIZE ROBUST GROWTH
PER UNIT OF PLAUSIBLE LOSS,
NOT NOMINAL LEVERAGE.
```

It grants no DEMO-governed execution, LIVE, production, real-capital, Risk,
broker, merge or certification authority.

## 1. Critical finding

CEL does **not** start from an empty architecture.

The current CIBO branch already contains causal/research machinery for:

- provider economic normalization;
- minimum viable seed sizing;
- capital source accounting;
- realized-profit compound accounting;
- protected capital floor;
- Core Compound Portfolio;
- marginal capital utility evidence;
- sequential compounding shadow control;
- Internal Capital Market / reserve competition;
- optionality and finite-horizon capacity planning;
- regime-aware capital tool selection;
- factor topology / concentration research;
- provider stress;
- capital-state Monte Carlo;
- causal OOS binding to terminal settlement and release timing;
- Phase20/21/22 governed qualification and holdout lineage.

CEL must compose and extend those capabilities. It must not create a parallel
capital allocator.

## 2. CEL workstream reconciliation

| CEL | Capability | Current repository state | CEL disposition |
|---|---|---|---|
| CEL-0 | Current capability audit | existing CIBO surface revalidated | **AUDIT_COMPLETE** |
| CEL-1 | Notional / Margin / Loss separation | provider economics had notional, GEN-C4/6 had margin/risk separately; no single explicit exposure-state identity | **ENGINE_IMPLEMENTED; real binding pending** |
| CEL-2 | Stressed-loss model | provider stress + stop/execution evidence existed, but no single per-exposure worst-scenario stressed-loss state | **ENGINE_IMPLEMENTED; real stress calibration pending** |
| CEL-3 | Risk-constrained growth | Phase20 robust allocator + hard risk/margin headroom exist | **REUSE_EXISTING_RESEARCH_ENGINE; value not certified** |
| CEL-4 | Robust / distributionally robust growth | robust allocator + path stress exist; explicit DRO growth objective not established | **GAP / RESEARCH_REQUIRED** |
| CEL-5 | Marginal leverage utility | GEN-C4 marginal utility + GEN-C6 Internal Capital Market already exist | **EXTEND_EXISTING; must consume CEL stressed loss before CEL claim** |
| CEL-6 | Volatility-adaptive capitalization | regime selector / T12 exist | **PARTIAL; incremental value not established** |
| CEL-7 | Profit-funded expansion | T06 + compound accounting + GEN-C5 exist | **PARTIAL/RESEARCH; no leverage-specific qualification** |
| CEL-8 | Protected capital floor integration | GEN-C2 protected floor + portfolio integration exist | **REUSE_EXISTING** |
| CEL-9 | Survival vs Growth capital | protected floor / reserve / compoundable states exist | **PARTIAL; explicit two-plane policy still required** |
| CEL-10 | Capital buckets | compound states and source ledger exist | **PARTIAL; do not introduce arbitrary fixed percentages** |
| CEL-11 | Capital velocity | expected/actual capital minutes + release lineage exist | **EVIDENCE_BOUND; optimization value not proven** |
| CEL-12 | Portfolio factor concentration | Phase19 factor topology + T08 magnitude/return research exist | **REUSE_EXISTING_RESEARCH** |
| CEL-13 | Margin offset vs Risk offset | separate risk/margin headroom exists; explicit offset-law engine absent | **GAP** |
| CEL-14 | Capital-efficient instrument selection | provider normalization exists; cross-instrument economic equivalence selector absent | **GAP** |
| CEL-15 | Convex / limited-downside exposure | T17 contract exists | **CONTRACT_DEFINED ONLY** |
| CEL-16 | Internal Capital Market integration | GEN-C6 exists with reserve as competitor and causal OOS binding | **ENGINE_IMPLEMENTED / qualification incomplete** |
| CEL-17 | Compound portfolio integration | GEN-C1..C5 / Core Compound Portfolio exist | **ENGINE_IMPLEMENTED / certification incomplete** |
| CEL-18 | Shared read-only evidence | Shared capital intelligence facts / eligibility firewall exist | **CONTRACT+BOUNDARY IMPLEMENTED; certified Shared facts pending** |
| CEL-19 | Crisis / correlation-convergence stress | provider stress, factor/concentration research, MC stress exist | **PARTIAL/REUSE_EXISTING** |
| CEL-20 | Monte Carlo / path-dependent stress | capital-state block bootstrap exists | **ENGINE/CONTRACT IMPLEMENTED; empirical qualification pending** |
| CEL-21 | OOS / replication | Phase20D→21→22 chain exists | **ACTIVE / NOT PASSED** |
| CEL-22 | Governed admission | fail-closed certification chain exists | **NOT READY** |

## 3. CEL-1 / CEL-2 implementation boundary

CEL-1/CEL-2 are implemented in:

`src/qore/infrastructure/cibo_capital_efficient_exposure.py`

They establish a causal exposure state with independent:

```text
NOTIONAL_EXPOSURE_USD
MARGIN_OCCUPANCY_USD
STRUCTURAL_STOP_LOSS_USD
BASE_PLAUSIBLE_LOSS_USD
STRESSED_ECONOMIC_LOSS_USD
```

The stressed-loss engine requires explicit pre-outcome scenario evidence for:

- gap through stop;
- stressed execution cost;
- liquidity shock;
- portfolio/correlation convergence increment;
- forced-liquidation loss.

No default stress multiplier is silently invented.

The current implementation intentionally reports:

```text
ENGINE_IMPLEMENTED = TRUE
REAL_PROVIDER_RUNTIME_BOUND = FALSE
REAL_STRESS_CALIBRATION_BOUND = FALSE
CAUSAL_REPLAY_EXECUTED = FALSE
VALUE_DEMONSTRATED = FALSE
CERTIFIED = FALSE
```

until those later stages actually occur.

## 4. Existing GEN-C6 freeze protection

CEL research must not mutate the frozen GEN-C6 policy merely to make CEL look
better.

Required order:

```text
GEN-C6 CURRENT FROZEN EVIDENCE
        +
CEL EXPOSURE ECONOMICS
        ↓
NEW CEL SHADOW TREATMENT
        ↓
CONTROL / TREATMENT
        ↓
FRESH CAUSAL EVIDENCE
```

Not:

```text
EDIT GEN-C6 AFTER OUTCOMES
→ CALL IT CEL
```

## 5. Immediate next dependency

The next valid CEL bridge is:

```text
CEL-1 / CEL-2
provider-normalized exposure economics
        ↓
REAL PROVIDER / STRESS EVIDENCE BINDING
        ↓
CEL-5
MARGINAL LEVERAGE UTILITY
        ↓
GEN-C6 INTERNAL CAPITAL MARKET
        ↓
ALLOCATE / RESERVE / REDUCE
under stressed-loss-aware marginal utility
```

`EXPAND` and `RELEASE` require separate lifecycle evidence and must not be
manufactured merely to satisfy the target action vocabulary.

## 6. Governance state

```text
CEL PRODUCTIVE AUTHORITY = FALSE
GEN-C6 FROZEN POLICY MUTATED = FALSE
RISK AUTHORITY CHANGED = FALSE
EXECUTION AUTHORITY CHANGED = FALSE
LIVE = FALSE
REAL CAPITAL = FALSE
HOLDOUT OPENED BY CEL = FALSE
```
