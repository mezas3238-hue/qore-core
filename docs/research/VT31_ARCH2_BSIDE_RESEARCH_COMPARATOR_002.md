# VT31 NAS100 — B-Side Research Comparator Contract 002

**Owner:** Sergio Meza  
**Status:** FIXED RESEARCH COMPARATOR / NOT CANDIDATE FREEZE  
**Branch:** `agent/vt31-edge-position-cert-b-001`  
**Cross-fold evidence:** workflow `37470039752` — SUCCESS

## Comparator ID

`VT31_BSIDE_H3_W5_DOL2_PS2_CAUTION_STALE_EXIT_RESEARCH_COMPARATOR_002`

## Why Comparator 002 exists

Comparator 001 remains immutable for provenance. It contains H3 + W5 soft
DOL1 + full-cognition DOL2 + post-acceptance PS2.

Consumed-evidence research has now demonstrated an additional post-entry
survivor. It must therefore receive a new comparator identity rather than
silently mutating Comparator 001.

## Fixed B-side stack

Comparator 002 contains:

- H3 full-cognition post-1R management;
- W5 soft-DOL1 acceptance;
- full-cognition DOL2 extension;
- post-acceptance PS2 protection;
- causal `current_open_r` from frozen initial risk;
- full post-entry cognition rebuilt from closed market data;
- pre-DOL1 cognitive EXIT executed only at the next M1 open when:
  - maximum cognition is verified;
  - `current_open_r <= -0.50R`; and
  - either:
    - management context is `CAUTIOUS`; or
    - management context is `MIXED` and reference-reclaim age is
      `8 <= age < 15` minutes.

DOL1 touch retains ownership of target logic.

## Reference admission for measured economics

The evidence below uses the fixed admission survivor:

`A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`.

Future admission experiments must identify that they are being measured
against Comparator 002 rather than pretending Comparator 001 changed.

## Cross-fold result

`COG_EXIT_CAUTION_OR_STALE_MIXED` is a consumed-evidence development
survivor:

- PF non-degrade: 4/4;
- mean-R non-degrade: 4/4;
- observed DD non-degrade: 4/4;
- winner-count / winner-R preservation: PASS;
- half-year mean/DD non-degradation: PASS.

Recent consumed:

- PF: `1.6569183362`;
- mean: `+0.4997582400R/trade`;
- total: `+19.49057136R`;
- observed DD: `9.33975237R`;
- wins: `8`;
- losses: `31`;
- MC positive terminal: `84.74%`;
- MC p95 DD: `17.7678R`.

This is materially stronger than the prior A+B control, but it still fails
certification because:

- observed DD is above the sovereign `6R` maximum;
- recent MC positive terminal is below `90%`;
- recent MC p95 DD remains above the current robustness target.

## Sovereign invariants

Comparator 002 has no authority from:

- sizing;
- dynamic sizing;
- leverage;
- compounding;
- portfolio allocation;
- capital weighting;
- absolute volume;
- fold identity;
- future outcome labels.

R is used only as strategy-native live journey geometry.

## Governance

This comparator is not:

- a candidate freeze;
- a certification;
- a fresh-holdout opening;
- a LIVE authorization;
- a real-capital authorization;
- a production policy.

Fresh holdout remains sealed.
