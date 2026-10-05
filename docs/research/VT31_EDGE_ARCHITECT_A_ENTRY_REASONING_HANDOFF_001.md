# QORE CORE — VT31 NAS100 EDGE-ONLY OPTIMIZATION

Owner: Sergio Meza

Source of truth: GitHub repository `mezas3238-hue/qore-core`.

Common base checkpoint: `7d88c99e6cf36cccda9e1eba8a4b3a0082490edc`.

## Non-negotiable owner directive

VT31 must be optimized and certified on **real trading edge only**.

Certification must NOT derive any improvement from:
- position sizing;
- adaptive sizing;
- leverage;
- compounding;
- CIBO capital allocation;
- portfolio netting;
- route-dependent capital weighting;
- monthly risk budgets;
- global risk scalars;
- volume escalation.

All certification economics must be computed on an equal normalized trade basis (1R-equivalent per terminal trade). Capital management may exist elsewhere in QORE, but it is not part of VT31's edge examination.

Silver Bullet source identity remains frozen unless the Owner explicitly orders otherwise.

No outcome-aware tuning, no leakage, no fresh-holdout retuning, no LIVE, no real capital, no production authorization, no merge without Owner order.

## Certification target

Preserve the strongest VT31-specific gates already established and extend the report to the full Owner certification scorecard:
- causal untouched OOS / era validation;
- PF per era >= 1.50;
- combined OOS PF >= 1.70, preferred >= 2.00;
- expectancy > 0, target >= +0.15R/trade;
- observed DD <= 10R, with VT31 target <= 6–8R and existing <=6R contract treated as preferred hard target;
- reject architecture if DD >15R;
- Sharpe >=1.50, preferred >=2.00;
- Sortino >=2.00;
- payoff >=1.20, preferred >=1.50;
- Monte Carlo positive-terminal >=90%, preferred >=95%;
- MC p95 DD <=15R, preferred <=10–12R;
- winner preservation >=80% count / >=90% winner-R, preferred 90% / 95%;
- post-cost PF >1.00 under severe stress, with stronger stress tiers preserved;
- annual/era positivity;
- legitimate operational density only: no manufactured trades to hit a quota.

The prior R5 certification contract is not valid as the new final edge-only contract because it uses route-dependent risk and a global risk scalar. A new edge-only candidate identity must be frozen before any future fresh certification holdout is opened.

## Architect A — ENTRY EDGE · REASONING SOVEREIGNTY · LEGITIMATE REARM

Branch: `agent/vt31-edge-entry-reasoning-a-001`

### Sole ownership

Architect A owns all changes that decide **whether a trade should exist**:
- causal situation model;
- market/context interpretation before entry;
- reasoning engine EXECUTE / WAIT / ABSTAIN;
- entry-family quality and conflict resolution;
- execution translation/zone selection before fill;
- same-source fallback removal;
- legitimate new-event discovery;
- structural rearm admission after a terminal exit;
- density recovery only through new valid market events;
- entry-side loss-sequence root-cause repair.

Primary owned runtime files include:
- `src/qore/infrastructure/traders/vt31_nas100_reasoning_engine.py`
- `src/qore/infrastructure/traders/vt31_nas100_situation_model.py`
- `src/qore/infrastructure/traders/vt31_nas100_market_context_runtime.py`
- `src/qore/infrastructure/traders/vt31_nas100_cibo_causal_structure.py`
- `src/qore/infrastructure/traders/vt31_nas100_trader_experience_memory.py`
- related entry/reasoning/rearm research scripts.

### Forbidden scope

Architect A must not tune:
- stop/trailing behavior after entry;
- DOL locks;
- target extension policy;
- banking/runners;
- certification capital weighting;
- sizing/leverage/compound.

### Research priorities

1. Rebuild the entry economics in equal-risk R units.
2. Keep reasoning sovereign across CORE/SECONDARY/REARM: no execution after ABSTAIN unless there is a genuinely new raid + confirmation + decision and the new reasoning state says EXECUTE.
3. Repair over-restrictive reasoning without returning to same-source fallback.
4. Separate stable cross-fold negative conjunctions from unstable single-feature bans.
5. Recover legitimate density via structural event discovery, not weakened gates.
6. Falsify order-block and late-confirmation weaknesses without promoting a rule unless it generalizes across consumed folds.
7. Deliver an immutable entry ledger to Architect B containing pre-entry state, route/family, normalized 1R trade identity, timestamps and causal fingerprints — no future labels.

### Completion criterion

Architect A is complete only when it produces a frozen entry/rearm candidate that:
- is causal and replay-deterministic;
- has no sizing/capital allocation;
- passes cross-fold entry-quality gates;
- preserves sufficient legitimate opportunity density;
- exposes a stable immutable seam for Architect B to manage positions without changing trade admission.
