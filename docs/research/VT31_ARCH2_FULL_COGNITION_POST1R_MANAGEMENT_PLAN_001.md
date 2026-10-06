# VT31 NAS100 — Full-Cognition Post-1R Management Plan 001

**Owner:** Sergio Meza  
**Status:** PREDECLARED / CONSUMED EVIDENCE ONLY / NO HOLDOUT  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Sovereign objective

VT31 must learn to operate with the maximum causal intelligence available to
the trader.

This experiment does not reduce VT31 to one signal. It combines:

- full pre-entry reasoning/memory synthesis;
- H4/H1/M15 causal context;
- M1 execution path;
- structure/liquidity/regime/volatility;
- entry-family and destination intelligence;
- management context / protection urgency;
- strategy-native R;
- post-1R causal persistence.

Sizing, leverage, compounding and capital weighting remain forbidden for
certification.

## Scientific separation

The experiment requires:

`FULL_COGNITIVE_ACCOUNTING = TRUE`

for every evaluated trade.

It does **not** claim:

`MAXIMUM_INTELLIGENCE_CERTIFICATION_READY = TRUE`

before journey and contextual management are calibrated. The purpose of the
experiment is to help close those exact blockers.

## Population

Use the exact sovereign VT31 admission population. Do not alter:

- entry admission;
- entry price;
- initial structural invalidation;
- primary structural target;
- lifecycle;
- trade weight / certification exposure.

## Causal observation event

After an admitted trade reaches an unambiguous +1R milestone:

- do not protect immediately merely because +1R occurred;
- wait a frozen observation horizon of 2, 3, or 5 fully closed M1 bars;
- derive only from those already-closed bars one of:

  - `PERSISTENT_1R_FLOOR`
  - `RECOVERED_1R_FLOOR`
  - `POSITIVE_BELOW_1R`
  - `ENTRY_OR_WORSE`

The observation becomes actionable only on the next M1 bar.

Future journey labels are evaluation-only and may never select an action.

## Frozen variants

### V0 — STRUCTURAL_ONLY

No post-1R protection. Original structural invalidation / destination remain.

### V1 — PERSISTENCE_DEFENSIVE

At each frozen horizon independently:

- `PERSISTENT_1R_FLOOR` -> HOLD
- `RECOVERED_1R_FLOOR` -> HOLD
- `POSITIVE_BELOW_1R` -> move stop to entry next bar
- `ENTRY_OR_WORSE` -> move stop to entry next bar if still causally possible

### V2 — FULL_COGNITION_PERSISTENCE

Use both persistence and the full entry cognition:

Preserve runner (HOLD) when:

- persistence is `PERSISTENT_1R_FLOOR`; or
- persistence is `RECOVERED_1R_FLOOR` and entry cognition is SUPPORTIVE /
  destination DEEP.

Protect at entry from next bar when:

- persistence is `ENTRY_OR_WORSE`; or
- persistence is `POSITIVE_BELOW_1R` and cognition is CAUTIOUS / destination
  SHALLOW.

For MIXED / NEUTRAL states not covered above, HOLD. They must not be forced
into a protection rule merely to improve DD.

### V3 — FULL_COGNITION_R4_BACKSTOP

Same as V2, except a trade that remains unresolved by V2 may also arm the
already-defined +4R -> BE rule only when the full entry cognition is not
SUPPORTIVE.

This tests whether R is useful as a *secondary cognitive management tool*, not
as a universal rule.

## Horizons

Evaluate 2M1, 3M1 and 5M1 independently.

No horizon may be selected because it looks best after outcomes. All three
must be reported.

## Required gates

Against V0 in each fold:

- same admitted and terminal population;
- PF;
- expectancy / mean R;
- total R;
- max DD;
- losing streak;
- Monte Carlo positive terminal;
- MC p95 DD;
- winner-count preservation >=80% (preferred >=90%);
- winner-R preservation >=90% (preferred >=95%);
- half-year stability;
- side stability;
- entry-family stability.

A research survivor requires:

- economic non-degradation in at least 3/4 folds;
- no catastrophic fold;
- winner floors in every fold;
- no hidden sizing/capital logic;
- no future label in action selection.

## Maximum-intelligence closure

A successful experiment may calibrate:

- `DEEPER_JOURNEY_CAPACITY_UNCALIBRATED`;
- `CONTEXTUAL_POSITION_MANAGEMENT_UNRESOLVED`;

only if its states generalize cross-fold and are encoded causally.

Until both are closed, candidate freeze remains prohibited.

## Governance

- R strategy logic: allowed;
- R-driven volume changes: forbidden;
- sizing rescue: forbidden;
- fresh holdout: sealed;
- merge: not authorized;
- LIVE / real capital / production: not authorized.
