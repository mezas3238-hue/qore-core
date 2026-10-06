# VT31 NAS100 — Comparator 007 Post-Entry Trajectory Findings 001

**Status:** CONSUMED-EVIDENCE FORENSICS / OBSERVATION ONLY  
**Comparator:** `VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR`  
**Workflow:** `37512388808` — SUCCESS  
**Evaluated head:** `dcad2df2ec3bd3e1bb637137d2708a029d3465ef`

## Purpose

Explain the remaining exact recent drawdown using the already-wired causal
post-entry cognition before adding any new policy authority.

## Exact DD path

The fixed max-DD path remains 9 trades from the peak after
`2023-12-01T15:04:00Z` through the trough at
`2024-03-01T15:05:00Z`, with exact stressed DD
`6.593383112613881844651075420R`.

## Post-entry findings inside the path

Two still-open losing Breakers show the same economically relevant state before
their final structural invalidation:

### 2024-01-29 LONG

At `2024-01-29T15:51:00Z`:

- current_open_r: `-0.5259259259R`;
- management_context: `MIXED`;
- protection_urgency: `MODERATE`;
- support_margin: `8`;
- recent_path_efficiency: `0.2181818182`;
- recent_overlap_rate: `1`;
- reclaim age: `46m`;
- H4 bearish / H1 mixed / M15 bearish.

Current Comparator-007 policy did not exit because the MIXED route is currently
authorized only for the pre-existing stale reclaim bucket 8–14m.

### 2024-02-08 SHORT

At `2024-02-08T15:19:00Z`:

- current_open_r: `-0.7395833333R`;
- management_context: `MIXED`;
- protection_urgency: `MODERATE`;
- support_margin: `8`;
- recent_path_efficiency: `0.2961672474`;
- recent_overlap_rate: `0.9285714286`;
- reclaim age: `18m`;
- H4 bearish / H1 bullish / M15 mixed.

Again, the current stale-reclaim route does not authorize an exit.

## Matched-winner protection

The rejected broad admission class provided an essential counterexample.

The R5 +6.808219R winner did reach material adverse territory:

- current_open_r: `-0.5205479452R`;
- management_context: `MIXED`;
- urgency: `MODERATE`;
- reclaim age: `20m`.

However its recent-path efficiency at that adverse observation was:

`0.5369458128`

which is well above the already-existing weak-efficiency threshold
`0.30`.

The R6 +21.50R winner never reached the existing material-adverse threshold:
its worst observed current_open_r was approximately `-0.470588R`.

The R8 +4.645833R winner also never reached material adverse territory; its
worst observed current_open_r was `-0.125R`.

## Existing thresholds, not newly optimized numbers

Two thresholds already exist in the current causal cognition:

- material adverse: `current_open_r <= -0.50R`;
- weak path by efficiency: `recent_path_efficiency <= 0.30`.

Therefore the next hypothesis does not invent a new numeric cutoff after seeing
outcomes.

## Predeclared next hypothesis

For a still-pre-DOL1 Breaker, preserve all existing Comparator-007 cognitive
exit authority and additionally allow a next-M1-open cognitive exit only when:

- maximum cognition is verified;
- current_open_r <= -0.50R;
- management_context == MIXED;
- recent_path_efficiency is available and <=0.30.

This is intentionally side-agnostic and does not reuse the rejected broad
entry filter.

The hypothesis must now prove itself unchanged on R5, R6, R8 and recent
consumed.

Fresh holdout remains sealed.
