# VT31 NAS100 — Entry Clustering Attribution Findings 001

**Owner:** Sergio Meza  
**Status:** CONSUMED-EVIDENCE DIAGNOSTIC / ARCHITECT-A ESCALATION  
**Branch:** `agent/vt31-edge-position-cert-b-001`  
**Diagnostic workflow:** `37444530744` — SUCCESS  
**Diagnostic head:** `4efa5eba672b00c7ce6ba1c1d3cc9a3d55a0e056`

## Governance

This finding is observation-only.

It did not change:

- entry;
- initial stop;
- H3 management;
- DOL2 target logic;
- PS2 protection;
- sizing;
- leverage;
- compounding;
- capital weighting;
- volume;
- fold-specific action;
- fresh holdout state.

No rule is promoted from this document.

Any entry change must be reconstructed as a causal pre-entry hypothesis and
replayed by Architect A without outcome access at runtime.

## Position-side state

The leading B-side witness remains `H3_W3_DOL2_PS2`.

Across R5 / R6 / R8 / recent consumed it remains:

- PF non-degrading: 4/4;
- mean-R non-degrading: 4/4;
- DD non-degrading: 4/4;
- winner floors: PASS 4/4;
- research survivor: YES;
- promotion / freeze: NO.

Recent consumed remains:

- PF: `1.203943`;
- mean: `+0.174587R`;
- DD: `12.6714R`;
- Monte Carlo positive terminal: `63.34%`;
- Monte Carlo p95 DD: `28.47R`.

Therefore B-side management adds edge but does not solve certification.

## Sequential-risk anatomy

Longest stressed losing streaks under the same leading B-side witness:

- R8: 11 losses, `-11.55R`;
- R6: 8 losses, `-8.40R`;
- R5: 12 losses, `-11.9073R`;
- recent consumed: 9 losses, `-9.45R`.

The worst rolling five-trade window in every fold is five losses totaling
`-5.25R`.

This is the signature of repeated full-stop failure. It is not credible to
repair this primarily by adding more post-entry exit machinery.

## Strongest causal pre-entry anomaly

`reference_volatility_state = expanded` is the cleanest recurring negative
state found by the attribution layer.

Results under `H3_W3_DOL2_PS2`:

| Fold | Sample | Losses | Mean stressed R | Total stressed R |
|---|---:|---:|---:|---:|
| R8 | 2 | 2 | -1.05R | -2.10R |
| R6 | 4 | 4 | -1.05R | -4.20R |
| R5 | 4 | 4 | -1.05R | -4.20R |
| Recent consumed | 5 | 5 | -1.05R | -5.25R |
| **Total** | **15** | **15** | **-1.05R** | **-15.75R** |

This state is available causally at decision time because it is derived from
the current 09:00 reference width versus the prior admitted reference-width
history.

It is therefore a valid **Architect-A research hypothesis**, not yet a rule:

> investigate whether an expanded 09:00 reference-volatility state should
> cause ABSTAIN or require materially stronger entry evidence.

Because this anomaly was discovered on consumed outcomes, it may not be
promoted directly. It must be predeclared and replayed causally.

## Important falsifications

### Do not globally reject Breaker

Breaker is positive in all four folds:

- R8: `+2.2077R/trade`;
- R6: `+1.2447R/trade`;
- R5: `+1.8498R/trade`;
- recent consumed: `+0.6521R/trade`.

Breaker also appears frequently inside losing streaks because it is the
dominant entry family in the surviving population. Frequency inside a streak
is not causal evidence for a global Breaker veto.

Any Breaker repair must target a narrower causal substate.

### Fair-value-gap is unstable, not globally bad

FVG mean stressed R by fold:

- R8: `-1.05R`;
- R6: `+1.9541R`;
- R5: `-0.0407R`;
- recent consumed: `-0.9490R`.

A global FVG veto is unsupported.

### Order-block is weak but small-sample

Order-block mean stressed R:

- R8: `-1.05R` on 3 trades;
- R6: `+0.0976R` on 6 trades;
- R5: `-0.2192R` on 9 trades;
- recent consumed: `-1.05R` on 5 trades.

This warrants deeper contextual attribution, not deletion.

### H1 direction is not a universal veto

H1 states change sign materially across folds. In particular H1 bearish is
strongly positive in some historical folds and fully negative in others.

Therefore H1 must remain part of multidimensional cognition rather than become
a standalone BUY/SELL veto.

## Architect-A next research order

1. Predeclare `reference_volatility_state = expanded` as an admission
   hypothesis.
2. Replay it causally on all consumed folds with no fold identity.
3. Do not change H3, DOL2 or PS2 while measuring the admission effect.
4. Attribute the 15 expanded-state losses by:
   - side;
   - entry family;
   - H1 / M15;
   - prior-day state;
   - location in prior-day range;
   - confirmation latency;
   - entry-evidence age.
5. Test whether a stronger-evidence requirement transfers better than a blunt
   global veto.
6. Continue searching for the second independent clustering cause after
   expanded-volatility handling; even a perfect removal of this defect alone
   is not expected to make recent consumed certification-ready.
7. Preserve the fresh holdout seal.

## Sovereign interpretation

The evidence now supports a sharper separation of responsibilities:

- B has a useful position-side stack;
- the worst residual clusters are largely full-stop sequences;
- the strongest recurring anomaly is observable before entry;
- therefore the dominant remaining repair belongs to admission intelligence.

No sizing rescue is permitted.

No fresh holdout is opened.

No candidate is frozen or certified by this finding.
