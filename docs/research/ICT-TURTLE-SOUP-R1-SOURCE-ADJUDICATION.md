# ICT Turtle Soup R1 — Source Adjudication

Issue: #572
Research identity: `ICT_TURTLE_SOUP_R1_CISD_SESSION`
Canonical trader code: `CODE_UNASSIGNED`

## Separation from rejected Turtle Soup lineage

This research is **not** R7 of the rejected Connors/Raschke Turtle Soup line. The former 20-day-extreme / fixed-tick-entry lineage remains rejected. No old Turtle Soup result is promoted, rescued, or relabeled as ICT evidence.

## Public source status

A directly verified primary Michael Huddleston specification defining every machine-executable Turtle Soup state transition has not been recovered in this adjudication. Therefore QORE separates public source-supported concepts from explicit engineering formalizations.

### Source-supported core

Current public TTrades education describes the reversal sequence as:

1. `Purge / Turtle Soup`: price sweeps liquidity at a high or low.
2. Rejection / reclaim context.
3. `CISD`: price closes through the opposing candle series and confirms a change in delivery.
4. Later confirmations such as FVG / Breaker may add confirmation but are not required to define the initial purge.

TTrades also describes New York AM as a principal index window and uses a 5-minute chart in its reversal-sequence teaching. Its New York manipulation examples use a sweep of prior session liquidity, CISD through the opposing candle series, structural stop beyond the sweep, and opposing liquidity as the objective.

Current 2026 secondary ICT-oriented material (FX Replay) independently describes ICT Turtle Soup as a 5-minute NQ/ES liquidity model using time-based liquidity such as Asia/London highs and lows or previous-day extremes, with CISD or FVG retest entries and opposing liquidity / minimum-R objectives.

### Explicit QORE R1 formalizations

The following are deterministic QORE research choices, **not universal claims about ICT**:

- research proxies: `NAS100`, `SP500`, `US30`;
- timezone: `America/New_York`, DST-aware;
- London-kill-zone liquidity pool: completed M5 bars with opens in `[02:00, 05:00)` New York;
- New York AM event window: M5 bars with opens in `[08:30, 11:00)` New York;
- only the completed London high/low may serve as the R1 liquidity pool;
- bullish event requires a sweep below London low and a completed M5 close back above it; bearish is the mirror;
- CISD is the only confirmation family in R1;
- CISD opposing series is the maximal contiguous series of opposite-body M5 candles immediately feeding the sweep leg; the confirmation threshold is the **open of the first candle in that contiguous series**;
- entry is the next completed M5 bar open after the CISD close (causal, no same-close fill assumption);
- stop is one instrument tick beyond the most adverse sweep extreme observed through CISD;
- target is the opposite completed London-range extreme;
- target must provide at least `1.5R` from actual entry or the setup abstains;
- if both stop and target are reachable in one M5 bar and no finer chronology is available, STOP wins (fail-closed);
- unresolved/missing bars, simultaneous opposite-side candidates, or multiple same-session candidates abstain;
- one trade maximum per symbol / New-York date;
- no trailing, break-even, partial, re-entry, FVG, breaker, order-block, NWOG, CIBO signal selection, or retrospective market/side filtering in R1;
- any position still open at the end of the NY-AM window exits at the last completed M5 close before 11:00 New York.

## Rationale for a minimal R1

R1 intentionally uses **one** confirmation mechanism (CISD) rather than combining CISD + FVG + Breaker + Order Block. This preserves causal attribution: if the research succeeds or fails, QORE can attribute the result to a comprehensible liquidity-sweep + delivery-shift contract rather than an unidentifiable stack of PD arrays.

## Ambiguity policy

Any source ambiguity that changes economic behavior is `FAIL_CLOSED` until separately adjudicated. A new rule after outcomes are observed requires a new research identity and a new pre-economic freeze.

## Authority

This document grants no trading authority.

- `DEMO_ELIGIBLE=false`
- `LIVE_AUTHORIZED=false`
- `REAL_CAPITAL_AUTHORIZED=false`
- `PRODUCTION_AUTHORIZED=false`
