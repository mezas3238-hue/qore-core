# VT31 NAS100 — Architect A / B Admission Convergence 001

**Owner:** Sergio Meza  
**Status:** CROSS-ARCHITECT CONSUMED-EVIDENCE CONVERGENCE  
**Architect B branch:** `agent/vt31-edge-position-cert-b-001`  
**Architect A observed head:** `08b0f73f9efb37e0a34f6f02f77726665fe0f63d`

## Independent evidence sources

Architect B sequential-risk attribution:

- workflow `37444530744`;
- diagnostic head `4efa5eba672b00c7ce6ba1c1d3cc9a3d55a0e056`;
- post-entry witness: H3 + cognition-selected DOL2 + PS2;
- no entry policy change.

Architect A admitted-state attribution:

- workflow `37444968905`;
- tested head `98b6d8fb11fb78d49894f0e2a0533d7f524a1746`;
- pure entry/admission economics with the common structural-boundary exit;
- no position-management optimization.

The two analyses were built independently on their respective branches.

## Convergence 1 — expanded reference volatility

Both architects isolate `reference_volatility_state = expanded` as a stable
negative pre-entry state.

Architect A entry-only attribution:

| Fold | Sample | Mean R | PF |
|---|---:|---:|---:|
| R8 | 2 | -0.55R | 0 |
| R6 | 4 | -0.80R | 0 |
| R5 | 4 | -0.80R | 0 |
| Recent consumed | 5 | -0.65R | 0 |

Architect B, after the current position-side stack, independently observes the
same 15-trade state as 15/15 full stressed losses totaling `-15.75R`.

This is the strongest current causal admission-repair hypothesis.

It is **not yet a promoted rule** because discovery used consumed outcomes.

## Convergence 2 — Order Block requires admission repair

Architect A classifies `family=order-block` as stable negative 4/4:

- R8: mean `-1.05R`, PF 0, n=3;
- R6: mean `-0.8833R`, PF 0, n=6;
- R5: mean `-0.4421R`, PF `0.5264`, n=9;
- recent consumed: mean `-1.05R`, PF 0, n=5.

The even narrower class
`family_entry_age=order-block|0_2m` is `-1.05R` in all four folds.

Architect B also sees Order Block weak in its final managed population.

Research implication:

- do not blindly delete Order Block;
- test causal ABSTAIN versus materially stronger evidence requirements;
- prefer the narrower fully stable causal conjunction if it transfers.

## Falsification — do not globally reject Breaker

Architect A identifies `family=breaker` as stable positive:

- recent consumed: PF `1.6982`, mean `+0.4795R`;
- R5: PF `4.1860`, mean `+1.6644R`;
- R6: PF `2.8331`, mean `+1.3235R`;
- R8: PF `3.5519`, mean `+1.4673R`.

Architect B independently finds Breaker positive 4/4 under its managed
population.

Therefore older generic "Breaker is bad" interpretations are superseded. Only
specific causal Breaker substates may be rejected.

One such A-side stable negative substate is:

`breaker | mixed H1 | expanded reference volatility`

which is negative 4/4.

## Architect A baseline remains the blocker

Architect A pure-entry baseline recent consumed:

- PF `1.099959`;
- mean `+0.075073R`;
- DD `12.8341R`;
- MC positive terminal `54.79%`;
- MC p95 DD `28.30R`.

Architect B can improve those economics after entry, but the residual
sequential-risk defect cannot be solved credibly through more exit machinery.

## Fixed B-side comparator for the next A frontier

Use:

`VT31_BSIDE_H3_W5_DOL2_PS2_RESEARCH_COMPARATOR_001`

This keeps fixed:

- H3 horizon = 3 closed M1 after first unambiguous +1R;
- soft-DOL1 acceptance window = 5 closed M1;
- full-cognition DOL2 selector;
- PS2 = two confirmed improving M1 protective swings;
- next-M1 actuation;
- no stop widening;
- no sizing.

It is a research comparator, not candidate freeze.

## Required next A frontier

Predeclare and compare, without changing B-side management:

1. current admission control;
2. causal expanded-volatility ABSTAIN;
3. causal Order-Block refinement;
4. combined expanded-volatility + Order-Block refinement.

The Order-Block refinement should test both:

- family-level ABSTAIN;
- narrower `order-block + entry-age 0-2m` / compatible stable conjunctions.

Adjudicate on:

- PF;
- mean R;
- observed DD;
- losing streak;
- Monte Carlo positive terminal;
- MC p95 DD;
- temporal blocks;
- retained trade count;
- winner preservation after integration with fixed B.

Do not select a rule merely because it removes known losers. The runtime rule
must be causal and independent of fold identity or outcome.

## Integration order

After Architect A obtains a consumed-evidence survivor:

1. freeze A's research candidate definition;
2. compose it with the fixed B-side W5 comparator;
3. replay R5 / R6 / R8 / recent consumed;
4. rerun MC and temporal stability;
5. only if combined consumed gates are sufficiently strong, begin formal
   candidate-freeze preparation;
6. fresh holdout stays sealed until then.

No sizing, leverage, compounding or capital rescue may participate in any step.

No merge, LIVE, real capital or production authority is granted here.
