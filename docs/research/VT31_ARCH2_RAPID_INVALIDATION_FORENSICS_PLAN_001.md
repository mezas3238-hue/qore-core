# VT31 NAS100 — Rapid Invalidation Forensics Plan 001

**Owner:** Sergio Meza  
**Status:** OBSERVATION-ONLY CONSUMED-EVIDENCE FORENSICS  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Why this forensics exists

Comparator 002 plus residual context exits improved recent PF above 1.70 while
the observed drawdown remained about 9.34R.

Exact peak-to-trough reconstruction shows that many full-stop trades inside the
maximum-drawdown episode never produced a fully closed M1 observation at
`current_open_r <= -0.50R` before invalidation.

Therefore additional post-entry adverse-close exits cannot, by construction,
repair those losses.

## Question

Do those rapid invalidations share a stable **pre-entry causal state** that can
be addressed by admission/confirmation quality without deleting winners?

## Observation-only fields

For every max-DD-episode trade that exits before a material-adverse closed M1,
record only facts already frozen at entry:

- entry family and side;
- decision minute;
- confirmation latency;
- entry evidence age;
- reclaim age;
- H4/H1/M15;
- premarket and cash-open state;
- prior-day state and location;
- reference volatility;
- path ratio / efficiency / overlap;
- raid depth;
- risk/destination geometry;
- fill-to-exit minutes;
- exit reason.

The episode membership and terminal result are retrospective forensic labels
only and have **zero runtime authority**.

## Governance

This plan does not authorize a filter or threshold.

Any mechanism discovered here must be predeclared separately and then replayed
cross-fold. No fold identity, date lookup, future outcome, sizing, leverage,
compounding, capital weighting or fresh holdout may become runtime authority.
