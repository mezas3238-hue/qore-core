# Turtle Soup New Trader Candidate — Baseline Gap Audit

Status: **RESEARCH / CODE UNASSIGNED / NOT DEMO ELIGIBLE**  
Issue: #551  
Historical comparator: obsolete `VT-09` only  
Working branch (legacy-named): `agent/vt09-r2-turtle-soup-research-001`  
Parent baseline: PR #500 HEAD `9295d01f32ecd8335f226df9f5937f97c226fbc4`

## 1. Human Owner correction

On 2026-09-14 the Human Owner clarified that **VT-09 is obsolete**.

Therefore Turtle Soup MUST NOT be reconstructed, versioned, promoted, fingerprinted, or economically certified as VT-09.

The existing `Vt09TurtleSoup` implementation is retained only as an obsolete historical comparator showing prior QORE assumptions. It has no methodology authority for the new trader.

Research identity for the new work: `turtle-soup-candidate-r1`.
Canonical QORE trader code: `CODE_UNASSIGNED` until governance explicitly assigns a valid new identity.

## 2. Obsolete VT-09 comparator

The retired implementation used:

- M15 execution;
- continuous session;
- most-recent-first strict swing pivots with configurable `swing_strength` (default 2);
- latest closed M15 candle false-break of a prior pivot;
- entry at false-break close;
- invalidation at pivot price;
- hard-coded 2R target.

Those rules must not be inherited unless independently supported by the new Turtle Soup source adjudication.

## 3. Human Owner Turtle Soup report claims requiring adjudication

The supplied report contains at least four potentially non-equivalent families:

### A. Classic Raschke / Street Smarts Turtle Soup
Reported claims include 20-period high/low, minimum-age constraint, failed breakout, reversal entry, sweep-extreme stop and structural/shorter-period exits.

### B. Turtle Soup Plus One
Reported next-bar confirmation variant requiring independent source reconstruction.

### C. Modern NY M5 sweep model
Reported 06:00–08:59 New York reference range, 09:00–12:00 active window, M5 false-break confirmation and opposite-range target.

### D. Later implementations / overlays
WH SelfInvest ATR emergency stop, CRT H4/H1/M15 variant, TBS/TWS taxonomy, EMA/FVG/OB/volume filters, break-even management and session overlays.

These families must remain source-separated unless primary evidence proves equivalence.

## 4. Non-negotiable engineering rules

1. Do not reuse obsolete VT-09 identity.
2. Do not invent a replacement VT code.
3. Do not inherit VT-09 defaults without independent source support.
4. Account-level risk percentage remains Risk Manager authority, not Trader methodology authority.
5. Every surviving variant needs explicit methodology/config fingerprint after final code assignment.
6. No fresh holdout until candidate/config freeze.
7. After fresh holdout, no retuning of that candidate.
8. `TRADER LAB PASS != DEMO_ELIGIBLE`.
9. `DEMO_ELIGIBLE != LIVE / PRODUCTION / REAL-CAPITAL AUTHORITY`.
10. Final trader identity must be assigned before formal promotion evidence is generated.

## 5. Required evidence chain

`SOURCE -> CLAIM -> RULE -> FORMALIZATION -> CODE -> ADVERSARIAL TEST -> CAUSAL REPLAY -> ECONOMICS`

Every automatic SETUP must be reproducible from information available at decision time and must identify the exact Turtle Soup variant authorizing it.

## 6. Gate sequence

The new trader may only be called approved after:

`RESEARCH -> REPLAY -> FAST_FORWARD -> OOS -> STRESS -> MONTE_CARLO -> RISK_REVIEW -> CIBO_REVIEW -> INDEPENDENT_VALIDATION -> ECONOMIC_EVIDENCE -> DEMO_ELIGIBLE`

Before final promotion, governance must assign a canonical non-obsolete trader identity and regenerate all identity-bound fingerprints/evidence.

## 7. Immediate dependency

DeepSeek must perform the source adjudication from the existing research handoff, applying the supersession notice in `TURTLE-SOUP-DEEPSEEK-HANDOFF-SUPERSESSION.md`.