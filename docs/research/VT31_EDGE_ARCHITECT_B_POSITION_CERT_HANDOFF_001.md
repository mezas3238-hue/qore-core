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


## Universal volume invariance

Owner clarification: universal does **not** mean a fixed or target volume of 0.01. VT31 must be volume-agnostic.

The same trader cognition, admission, stop, target and certification edge must remain valid whether execution volume is 0.01, 0.10, 1.00 or any other provider-accepted amount. The trader may not contain a hard-coded minimum/maximum lot, preferred lot, volume bucket, or volume-dependent edge rule.

Provider-specific minimums, maximums, steps and rounding belong only to the execution/provider adapter. Partial exits may be used only as an optional execution capability when representable; the certified edge must not require a particular absolute volume or a split that becomes impossible at another valid provider volume.

Certification remains in normalized R and must be invariant to absolute trade volume.

## Architect B — POSITION EDGE · NAS100 JOURNEY · TARGETS · CERTIFICATION

Branch: `agent/vt31-edge-position-cert-b-001`

### Sole ownership

Architect B owns all changes **after a trade has been admitted** plus the certification harness:
- NAS100 M1 journey characterization;
- position intelligence;
- structural protection;
- giveback reduction after favorable excursion;
- DOL1 and deeper-extension decisions using causal closed-M1 state only;
- runner/bank/extend policy;
- winner preservation;
- execution-cost robustness after the trade exists;
- edge-only certification metrics and final frozen certification contract.

Primary owned runtime/research files include:
- `src/qore/infrastructure/traders/vt31_nas100_position_intelligence.py`
- `scripts/vt31_nas100_position_intelligence_forensics_v1.py`
- `scripts/vt31_nas100_ny_delivery_journey_forensics_v1.py`
- `scripts/vt31_nas100_ny_journey_bifurcation_forensics_v1.py`
- `scripts/vt31_nas100_dol1_extension_forensics_v1.py`
- high-density management / structural-protection research scripts;
- new edge-only certification contract/suite.

### Forbidden scope

Architect B must not:
- alter Silver Bullet entry identity;
- change trade admission;
- loosen/tighten reasoning EXECUTE/WAIT/ABSTAIN;
- create same-source fallback;
- use sizing, leverage, compound, CIBO capital allocation or route-weighted risk to improve metrics.

If an entry defect is discovered, report it to Architect A with an immutable forensic case; do not patch admission locally.

### Research priorities

1. Replace the uncalibrated position-management state with NAS100-native causal management.
2. Separate FAILED_BEFORE_1R, GIVEBACK_AFTER_1R, RUNNER_3R_PLUS and EXTENDED_RUNNER_5R_PLUS.
3. Preserve large winners while reducing full-stop givebacks.
4. Use only features observable by the close of the decision M1; future DOL/giveback labels are research labels only.
5. Determine when DOL1 should remain the destination and when a runner has causal evidence to continue deeper.
6. Rebuild certification metrics on equal normalized 1R trades, not `capital_weighted_net_r`.
7. Add Sharpe, Sortino, payoff, winner-preservation and full cost-stress reporting to the final certificate.
8. Freeze a new edge-only candidate and keep any future untouched holdout sealed until both A and B development gates are final.

### Completion criterion

Architect B is complete only when:
- position logic is causal, deterministic and NAS100-native;
- winner preservation meets certification floors;
- post-entry changes improve PF/DD/expectancy without capital weighting;
- full certification suite enforces the Owner scorecard;
- no new fresh holdout has been opened before integration with Architect A.
