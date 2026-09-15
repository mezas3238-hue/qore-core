# ICT Turtle Soup R2 Forex — Post-Holdout Forensics Freeze

Status: FORENSICS-ONLY / HOLDOUT ALREADY CONSUMED
Issue: #577
Parent holdout: PR #576 / run `35030690033` / HEAD `3cb3d789eb73aa346affad7a80fe5214942ca992`
Identity under diagnosis: `ICT_TURTLE_SOUP_R2_ALL_SESSION_MULTI_ASSET`

## Purpose

Explain the failure mechanism of the already consumed seven-pair Forex holdout. This work may describe causal failure but may not select a replacement threshold, market, side, liquidity family, session, hour, stop, target or management policy.

## Immutable forensic questions

1. **Structural stop vs genuine failed reversal**
   - For stop/gap-stop/stop-first exits, measure conservative pre-stop MFE.
   - After the stop, using only bars strictly after the stop-containing M5, measure whether price later revisits original entry, reaches +0.5R, +1R, or the original target before New-York midnight.
   - Report final-session-close R after the stopped trade as a diagnostic counterfactual only.

2. **Failure timing**
   - sweep-to-CISD latency;
   - entry-to-exit latency;
   - stop latency for stopped trades;
   - continuous quantiles and fixed descriptive buckets (<=15m, <=30m, <=60m, >60m) only. These buckets are diagnostic and cannot become candidate filters under R2.

3. **Risk geometry**
   - structural risk in basis points of entry;
   - projected R;
   - distributions by outcome and exit reason;
   - no risk-width or projected-R cutoff may be selected from this evidence.

4. **Liquidity mechanics**
   - swept-family outcome;
   - target-family outcome;
   - swept-family × target-family matrix;
   - no family can be removed retrospectively.

5. **CISD persistence**
   - share of stopped trades with little favorable excursion before stop;
   - share later recovering after stop;
   - distinguish confirmation that immediately fails from premature structural invalidation.

6. **Target reachability / survivor behavior**
   - target-hit rate;
   - time-exit behavior;
   - MFE to +0.5R / +1R / +1.5R before session end where deterministically observable;
   - no alternative target is chosen.

7. **Breadth and concentration**
   - symbol, side, year, quarter, session/hour diagnostics;
   - positive-gain concentration and top-winner dependence;
   - no retrospective selection.

## Conservative path rules

- Use the immutable `trades.json` from artifact `10420839755` as the authoritative trade census.
- Reuse the same retained Core M5 market evidence from run `34759027136`; never recollect it.
- For pre-stop MFE, exclude the M5 bar containing the stop unless ordering is known; this produces a lower bound.
- For post-stop recovery, exclude the stop-containing M5 and begin with the next M5; this produces a conservative lower bound.
- No M1/tick upgrade is introduced after seeing outcomes.
- Do not recompute or modify entry, stop, target or trade eligibility.

## Root-cause labels

The final report may support one or several of:

- `STOP_PREMATURE_RELATIVE_TO_RECOVERY`
- `CISD_CONFIRMATION_NOT_PERSISTENT`
- `LIQUIDITY_POOL_DEFINITION_TOO_BROAD`
- `TARGET_GEOMETRY_MISMATCH`
- `NO_GENERAL_FOREX_EDGE`
- `MIXED_OR_UNDERDETERMINED`

These are explanatory labels only, not new trading rules.

## Governance

No candidate promotion, no new R3 candidate, no filters, no fresh OOS access, no Risk/CIBO/Monte Carlo/prop qualification in this forensic identity.

Any correction must become a separately preregistered research identity and use different untouched evidence for economic adjudication.

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`
