# QORE-TRADER-FAMILY-MODEL-001 — First DEMO Trader Cohort Deterministic Family

Status: **ENGINEERING FAMILY MODEL** (deterministic contracts for the five first-cohort Traders).

Package: `HARNESS-ENGINEER-QORE-DEMO-FIRST-TRADER-COHORT-001`
Parent: #469 · Adaptive cognition: #492 · Trader Lab: #473 · Issue: #493

## 1. Boundary law

`DETERMINISTIC METHODOLOGY FIRST -> COGNITIVE INTERPRETATION SECOND`

The cognitive model must never invent or replace a deterministic setup. Phase B
(cognition/voice) is admitted only after the corresponding Phase A (deterministic
Trader) output is exact.

## 2. Causal family

One cohort-level primitive family, not five unrelated witnesses:

- canonical OHLC/candle identity (exact `Decimal` prices, closed-candle only);
- closed-candle timeframe aggregation (M1/M5/M15/H4) with no partial-candle leakage;
- DST-aware New York session/window membership (`America/New_York`);
- exact fixed-window boundary semantics (half-open `[open, close)` local wall clock);
- swing pivots; liquidity sweeps / false-break; PDH/PDL and session extrema;
- FVG/imbalance primitives; AMD structural context; opportunity-density semantics;
- deterministic 90-minute cycle (VT-17); canonical evidence lineage;
- exact runtime types; deterministic replay; no silent backfill / no lookahead;
- false-positive controls and abstain behavior; exact Trader version/config lifecycle binding.

## 3. Deterministic methodology contracts

Every rule is classified `DETERMINISTIC_NOW` (frozen and implemented) or
`REQUIRES_FORMALIZATION` (recorded; conservative deterministic default chosen and
fingerprinted, to be re-confirmed against the project ficha before Trader Lab).

| Rule | Classification |
|---|---|
| Closed-candle identity, exact interval, Decimal prices | DETERMINISTIC_NOW |
| Closed-candle aggregation (M1→M5→M15→H4) | DETERMINISTIC_NOW |
| DST-aware NY membership via `America/New_York` local wall clock | DETERMINISTIC_NOW |
| Swing pivot (strength-k strict comparison) | DETERMINISTIC_NOW |
| Liquidity sweep (false break then close back through) | DETERMINISTIC_NOW |
| FVG (three-candle disjoint-wick imbalance) | DETERMINISTIC_NOW |
| AMD (accumulation/manipulation/distribution over closed H4 range) | DETERMINISTIC_NOW |
| 90-minute cycle (epoch-aligned 5400s UTC grid) | DETERMINISTIC_NOW |
| Session/window minute boundaries (NY AM 07:00–11:00; Silver Bullet 10:00–11:00, 14:00–15:00) | REQUIRES_FORMALIZATION (frozen defaults) |
| Risk multiple (1:2) and entry geometry | REQUIRES_FORMALIZATION (frozen defaults) |

### VT-01 NY Precision Core (M5, NY AM session)

Sweep-and-FVG reversal: detect the most recent swing high/low (strength 2); the
latest candle must false-break a level; a Fair Value Gap must confirm in the
reversal direction; entry at FVG midpoint, invalidation at the swept level, take
profit at 2× risk. Abstains (`no-session`, `no-sweep`) otherwise.

### VT-08 CRT 4H AMD (M5 execution, closed H4 context)

Closed-H4 AMD context over the most recent `range_length` H4 candles; only the
DISTRIBUTION phase sets a bias (direction of the distribution). M5 execution
requires an FVG in the bias direction. Invalidation is the manipulation-side
extreme of the H4 range; take profit is the opposite H4 range extreme.

### VT-09 Turtle Soup (M15 required)

False-break reversal on M15: the latest candle must false-break a prior swing
high/low; entry at the false-break close, invalidation at the swing extreme, take
profit at 2× risk.

### VT-17 QT Scalper (M5, deterministic 90-minute cycle)

The 90-minute cycle is an epoch-aligned 5400-second UTC grid. Within the NY AM
session, the current cycle's closed M5 candles define the cycle range; the latest
candle must false-break the cycle high/low for a reversal setup. Cycle identity,
open/close, and index are exact and timezone-independent.

### VT-31 Silver Bullet (M5/M1, fixed NY windows)

Fixed windows 10:00–11:00 and 14:00–15:00 `America/New_York`. Sweep-and-FVG
reversal identical to VT-01's primitive, but gated on Silver Bullet window
membership.

## 4. Cognitive wrapper (#492)

Routing is decided ONLY from a typed `TraderCognitiveSituation`, never from prompt
text; voice/text/UI share the same routing. `gpt-5.6-terra` medium (routine) /
high (ambiguous); serious internal contradiction → governed escalation request
(no self-grant); material Trader conflict → CIBO adjudication `gpt-5.6-sol` high;
unresolved material multi-Trader conflict → CIBO `COUNCIL_ADVERSARIAL` `gpt-5.6-sol`
max. Opinions bind the deterministic output fingerprint and evidence subset, carry
an immutable model/effort receipt, and no order/account/quantity/Risk/Production
authority.

## 5. Safety invariants

`DETERMINISTIC SETUP != COGNITIVE OPINION` · `OPINION != SIGNAL/ORDER` ·
`TRADER LAB PASS != DEMO_ELIGIBLE` · `CIBO ADJUDICATION != EXECUTION AUTHORITY` ·
`NO PRODUCTION ACCOUNTS / NO REAL CAPITAL / NO REAL-MONEY AUTONOMOUS EXECUTION`.

## 6. Residual ambiguities (reported, not fabricated)

The exact session/window minute boundaries and the 1:2 risk multiple are frozen
deterministic defaults; the structural semantics (closed-candle, sweep, FVG,
false-break, AMD, 90-minute cycle) are fully defined. These defaults are
fingerprinted into the config, so any later re-confirmation against the project
ficha requires a version bump, never an in-place mutation.

False-break classification is **side-aware**: a sweep/false-break is only
recognized against the level's own kind (a HIGH/resistance level swept by an
upside false break, a LOW/support level swept by a downside false break). A
genuine breakout (a close beyond the level) is never misread as a false break,
and a degenerate setup geometry abstains rather than raising.

VT-31 Silver Bullet is labeled "M5/M1" in the catalog; the frozen deterministic
path is **M5-only** (swing sweep + FVG on M5). The M1 refinement/confirmation
path is a `REQUIRES_FORMALIZATION` gap and is not fabricated: M1 execution
candles are rejected fail-closed until that rule is confirmed against the
project ficha.

Swing-pivot precedence is frozen as **most-recent-first**: evaluators scan
detected swing pivots newest-to-oldest and act on the first pivot that produces
a side-aware false break (plus FVG confirmation where required). When the latest
candle validly breaks the nearest pivot while false-breaking an older opposite
pivot, the older pivot's setup is still emitted. Whether the nearest valid
breakout should abort the scan is a `REQUIRES_FORMALIZATION` precedence question
not yet confirmed by canonical evidence; it is recorded, not fabricated.
