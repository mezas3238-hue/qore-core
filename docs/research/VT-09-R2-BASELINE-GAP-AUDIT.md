# VT-09 R2 — Turtle Soup Baseline Gap Audit

Status: **RESEARCH / NOT DEMO ELIGIBLE**  
Issue: #551  
Working branch: `agent/vt09-r2-turtle-soup-research-001`  
Parent baseline: PR #500 HEAD `9295d01f32ecd8335f226df9f5937f97c226fbc4`

## 1. Purpose

Freeze the engineering delta between the current QORE `vt-09` implementation and the Human Owner-provided Turtle Soup report before any optimization, backtest tuning, or fresh holdout consumption.

This document is intentionally source-conservative. It does **not** decide which variant is canonical. DeepSeek is the Human Owner-designated research authority for the source adjudication. Any unresolved methodological choice must fail closed until that adjudication is returned.

## 2. Current QORE VT-09 v1 behavior

Current implementation lives in `src/qore/infrastructure/traders/evaluators.py` as `Vt09TurtleSoup`.

Frozen v1 behavior:

- trader code: `vt-09`;
- methodology id: `turtle-soup`;
- execution timeframe: M15;
- session: `continuous`;
- structure: most-recent-first strict swing pivots with configurable `swing_strength` (default 2);
- setup: latest closed M15 candle must false-break a prior pivot and close back through the pivot price;
- entry: false-break candle close;
- invalidation: **pivot price**;
- target: **hard-coded 2R**;
- no explicit 20-period Donchian reference;
- no explicit minimum age rule for the reference extreme;
- no Turtle Soup Plus One / next-bar confirmation path;
- no NY 06:00–08:59 range model;
- no 09:00–12:00 NY execution window;
- no source-separated TBS/TWS taxonomy;
- no ATR emergency stop variant;
- no opposite-range structural target;
- no 5-period exit;
- no H1 path;
- no per-variant provenance.

The existing architecture file `docs/architecture/QORE-TRADER-FAMILY-MODEL-001.md` already records VT-09 false-break/session semantics + M15/H1 path as formalization work, and also records the 1:2 risk multiple as a frozen default requiring formalization. Therefore v1 must be treated as a historical deterministic witness, not as source-certified R2 authority.

## 3. Human Owner report claims requiring source adjudication

The report supplied on 2026-09-14 contains at least four apparent families that must not be silently merged:

### A. Classic Raschke / Street Smarts Turtle Soup

Reported claims:

- identify a 20-period high/low;
- the reference extreme occurred at least 4 days earlier;
- price breaks that level intraday and fails;
- trade in the reversal direction;
- stop beyond the sweep extreme;
- target/retest logic may use prior range/extremes and/or a shorter-period exit.

### B. Turtle Soup Plus One / one-candle confirmation

Reported claims:

- wait for the candle after the setup;
- LONG only after that candle breaks and closes above the setup candle high;
- SHORT only after it breaks and closes below the setup candle low;
- discard otherwise.

Exact original semantics and order type must be recovered from source.

### C. Modern NY M5 sweep model

Reported claims:

- reference range: 06:00–08:59 America/New_York;
- active window: 09:00–12:00 America/New_York;
- one side of the range is swept;
- M5 confirmation false-breaks the immediately prior candle and closes back;
- entry at confirmation close;
- target opposite side of the 3-hour range;
- minimum 1R.

This may be a modern derivative rather than the canonical Raschke strategy. It must be source-separated.

### D. Other later implementations / overlays

Reported claims include:

- WH SelfInvest 3×ATR(20) emergency stop;
- CRT Turtle Soup H4/H1/M15 midpoint/opposite-extreme targets;
- TBS vs TWS body/wick taxonomy;
- EMA trend filter;
- FVG and Order Block confluence;
- volume confirmation;
- break-even management;
- one trade per day;
- session-specific killzones.

These must be classified as primary Turtle Soup rules, later authored variants, third-party implementations, or unsupported community overlays.

## 4. Material mismatches: v1 vs report

| Area | Current VT-09 v1 | Human Owner report | Engineering status |
|---|---|---|---|
| Reference level | swing pivot strength 2 | 20-period high/low, age constraint | **MATERIAL GAP** |
| Timeframe | M15 only | classic + M5 + H1/H4/M15 variants | **AMBIGUOUS VARIANT** |
| Session | continuous | several session models | **AMBIGUOUS VARIANT** |
| Entry | same-bar false-break close | same-bar and Plus One variants | **MATERIAL GAP** |
| Stop | pivot price | sweep extreme; ATR emergency variant | **MATERIAL GAP** |
| Target | fixed 2R | structural/opposite range/5-period/fixed R variants | **MATERIAL GAP** |
| Confirmation | false-break only | optional next-bar confirmation | **MATERIAL GAP** |
| Lookback | pivot algorithm | 20 periods | **MATERIAL GAP** |
| Reference age | none | at least 4 days/bars reported | **MATERIAL GAP** |
| Provenance | one generic ruleset | multiple source families | **MATERIAL GAP** |
| TBS/TWS | none | reported body/wick taxonomy | **SOURCE STATUS UNKNOWN** |
| Risk sizing | outside Trader | 1–2% reported | **KEEP OUTSIDE TRADER** |

## 5. Non-negotiable engineering rules

1. Do not promote current v1 as R2.
2. Do not invent missing source semantics.
3. Do not combine classic, Plus One, NY M5, WH SelfInvest, CRT, or community variants into one universal ruleset unless Tier A/B evidence explicitly supports equivalence.
4. Account-level risk percentage remains Risk Manager authority, not Trader methodology authority.
5. Every variant that survives adjudication needs an explicit methodology/config fingerprint.
6. Market-transfer experiments must be labeled transfer research; source-demonstrated markets and QORE test markets are distinct facts.
7. No fresh holdout until the candidate and config are frozen.
8. After fresh holdout, no retuning of that candidate.
9. `TRADER LAB PASS != DEMO_ELIGIBLE`.
10. `DEMO_ELIGIBLE != LIVE / PRODUCTION / REAL-CAPITAL AUTHORITY`.

## 6. Required R2 evidence chain

`SOURCE -> CLAIM -> RULE -> FORMALIZATION -> CODE -> ADVERSARIAL TEST -> CAUSAL REPLAY -> ECONOMICS`

Every automatic SETUP must be reproducible from only information available at decision time and must carry enough provenance to identify the exact Turtle Soup variant that authorized it.

## 7. Gate sequence

R2 may only be called approved after completing the canonical QORE chain:

`RESEARCH -> REPLAY -> FAST_FORWARD -> OOS -> STRESS -> MONTE_CARLO -> RISK_REVIEW -> CIBO_REVIEW -> INDEPENDENT_VALIDATION -> ECONOMIC_EVIDENCE -> DEMO_ELIGIBLE`

The final promotion decision must be produced by the canonical `evaluate_demo_eligibility` path with matching economic evidence.

## 8. Immediate next dependency

DeepSeek must return the claim-level source adjudication defined in `VT-09-R2-DEEPSEEK-SOURCE-ADJUDICATION-HANDOFF.md` before the R2 executable contract is frozen.