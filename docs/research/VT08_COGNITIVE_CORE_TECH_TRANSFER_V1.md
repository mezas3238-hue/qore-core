# VT08 Cognitive — Core Technology Transfer from VT31 NAS100

Status: **RESEARCH TRANSFER CONTRACT / NO LIVE AUTHORITY**

## Verified VT31 reference

The exact certified reference is:

- candidate: `VT31_NAS100_STRUCTURAL_TARGET_V1`
- selected variant: `EQ50_COMPRESSED_ACCEPT_RUN25`
- final certification run: `35519882906`
- artifact: `10607439608`
- HEAD: `75719aef3c625f387d726ff519fdd0f059414f67`
- trades: `806`
- wins / losses: `241 / 565`
- capital-weighted PF: `3.736184576983536383276829235`
- capital-weighted total: `+68.40179211229463578309897772R`
- observed max DD: `3.70898490728154195122908861R`
- MC p95 max DD: `6.33486483102304186370631293R`
- MC positive terminal: `0.9998`

Important semantic boundary: the certified PF is computed from
`capital_weighted_net_r`. It is not an equal-risk one-R-per-signal PF.

## Frozen VT31 Core stack

The certified candidate freezes the following base stack:

- causal capital allocation: `ALLOC_G_CORE_FAMILY_050`
- causal state shield: `SHIELD_060`
- breaker management: `LOCK025_AFTER_CLOSED_1R`
- refined loss-cluster multiplier: `0.35`
- breaker-regime multiplier: `0.35`

Then it adds the structural target architecture:

- 50% bank at the frozen reference equilibrium;
- if DOL1 is reached, default remaining 50% bank at DOL1;
- when reference volatility is compressed and the DOL1-touch M1 closes beyond
  DOL1, bank 25% at DOL1 and leave a 25% runner;
- runner target = DOL2 + 0.25 frozen reference width;
- runner protection = second confirmed M1 protective swing, effective next M1;
- stop may only improve or hold;
- same-bar runner stop/target = STOP FIRST.

## What may transfer to VT08

Only architecture/mechanics may transfer:

1. Causal capital allocation after trade admission.
2. Bounded risk shields for governed negative states.
3. Structural banking without inventing extra entries.
4. Selective runner only when causal capacity is observable.
5. Confirmed structural protection effective after confirmation.
6. Monotonic stop invariant.
7. Chronological fit / OOS validation.
8. Capital-weighted and equal-risk metrics reported separately.
9. Monte Carlo, stress, temporal windows and extreme-trade dependence.

## What may NOT transfer

The following VT31/NAS100 knowledge is prohibited from direct reuse:

- NAS100 entry families (breaker/FVG/order-block tiers);
- `ALLOC_G` multipliers;
- `SHIELD_060` as an automatic VT08 value;
- 09:00-10:00 NAS100 reference equilibrium;
- DOL1/DOL2 definitions specific to VT31;
- PS2 as a universal VT08 rule;
- breaker-regime and loss-cluster thresholds;
- any NAS100 context label learned from VT31 outcomes.

VT08 must learn VT08-specific causal states from its own evidence.

## VT08 transfer sequence

### Stage A — Core Capital Intelligence

Implemented first.

- all admitted VT08 trades remain admitted;
- six source-known causal axes are recorded:
  anchor, side, risk/reference geometry, C2 body state, protected-swing age,
  source-H4 body alignment;
- the first 70% chronological partition fits a frozen state-quality table;
- the final 30% is OOS;
- no OOS trade outcome participates in classification;
- bounded multipliers are applied after admission only;
- equal-risk and capital-weighted PF/DD are both reported.

This stage directly tests the most transferable explanation for VT31's high
capital-weighted PF.

### Stage B — VT08 Structural Destination / Banking

Only after Stage A is understood.

Candidate destinations must come from VT08's own causal H4 journey. No NAS100
09:00 equilibrium or DOL geometry is assumed.

### Stage C — VT08 Selective Runner

A runner is permitted only if VT08-specific causal capacity evidence exists.
No future terminal label may be a runtime input.

### Stage D — VT08 Structural Protection

Use VT08's Position Intelligence contract:

- stop improves or holds;
- never widens;
- confirmation precedes activation;
- ambiguous same-bar precedence fails closed.

## Governance

This transfer cannot mutate the certified VT08 runtime, authorize a new market,
change LIVE/Production state, or grant capital authority. Promotion requires
independent VT08 evidence and explicit Owner authorization.
