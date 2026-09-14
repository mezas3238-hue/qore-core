# QORE CORE — TURTLE SOUP CANDIDATE R1 — ENGINEERING ADJUDICATION

Status: **SOURCE-ADJUDICATED / PRE-IMPLEMENTATION**  
Issue: #551  
Research identity: `turtle-soup-candidate-r1`  
Canonical trader code: `CODE_UNASSIGNED`  
Branch: `agent/turtle-soup-candidate-r1-001`

## 1. Purpose

Adjudicate the DeepSeek source-reconstruction return against recoverable text from *Street Smarts* before any executable candidate is frozen. The obsolete QORE VT-09 implementation has no authority here.

## 2. Critical corrections to the DeepSeek return

DeepSeek's report is useful for variant discovery but is **not executable as returned**. The following statements are contradicted by the recoverable *Street Smarts* text and are superseded here.

### 2.1 Classic Turtle Soup is same-day, not next-day

Chapter 4 states that once price falls below the prior 20-day low, the trader places a buy stop **5–10 ticks above the previous 20-day low**, and that order is **good for today only**. Therefore Classic is an intrabar/same-session reversal entry. It is not a Day-2 entry model.

Shorts are the exact reverse.

### 2.2 Classic age rule is four trading sessions

Chapter 4 explicitly requires the previous 20-day low/high to have occurred **at least four trading sessions earlier**.

This is not an unresolved 3-vs-4 parameter for Classic.

### 2.3 Plus One age rule is three trading sessions

Chapter 5 explicitly uses **at least three trading sessions earlier** for Turtle Soup Plus One.

The 3-vs-4 difference belongs to two different source variants; it is not a single-source conflict requiring Human Owner parameter selection.

### 2.4 Plus One entry is at the earlier 20-period extreme

For buys, Plus One requires a new 20-day low whose close is at or below the earlier 20-bar low. A buy stop is placed on the following bar/day at the **earlier 20-day low**. It is not placed at the Day-1 low.

If not filled on that next bar/day, the trade is cancelled.

### 2.5 Plus One stop uses the two-bar extreme

If filled, the protective stop is one tick below the **lower of the Day-1 and Day-2 lows** for a long; shorts reverse this rule.

### 2.6 Intraday use is explicitly source-authorized

Chapter 5 states that Turtle Soup and Turtle Soup Plus One work in **all time frames**, gives 10-minute examples, and specifies intraday entry at the previous 20-bar high/low minus/plus one tick. Therefore the DeepSeek classification `Daily only / intraday unresolved` is rejected.

### 2.7 The canonical Classic exit is not a 5-period target

Chapter 4 instructs using a **trailing stop as the position becomes profitable**. It does not define a canonical fixed 5-period target. The DeepSeek assignment of a 5-period target to Classic came from a later third-party implementation and is rejected as canonical source authority.

### 2.8 Plus One management is partially explicit

Chapter 5 says to take partial profits within **two to six bars** and trail a stop on the remaining position. This is source-authorized management for Plus One, though the exact partial percentage and exact trailing algorithm remain discretionary/unresolved.

### 2.9 Classic re-entry is source-authorized

Chapter 4 allows re-entry at the original entry level if stopped out on Day 1 or Day 2. This is a real source rule and must be represented in a source-faithful replay or explicitly disabled in a separate simplified experiment.

## 3. Source-bound executable contracts

### 3.1 Canonical Classic — LONG

At bar `t`, define the prior 20-bar low using bars available before the current breakout bar.

Requirements:

1. Current bar makes a new 20-bar low.
2. The previous 20-bar low occurred at least **4 trading sessions/bars earlier**.
3. After price trades below the prior 20-bar low, place a buy stop **5–10 ticks above that prior low**.
4. Entry order is valid for the current bar/session only.
5. If filled, initial stop is **1 tick below the current bar's low**.
6. As trade becomes profitable, management is a trailing stop; exact trailing algorithm is source-discretionary.
7. If stopped on trade Day 1 or Day 2, source permits re-entry at the original entry level.

For shorts, reverse all price relationships.

### 3.2 Canonical Plus One — LONG

1. Current bar/day makes a new 20-bar low.
2. Previous 20-bar low occurred at least **3 trading sessions/bars earlier**.
3. Current bar/day closes at or below the prior 20-bar low.
4. On the next bar/day, place buy stop at the **earlier 20-bar low**.
5. If not filled on that next bar/day, cancel.
6. If filled, stop is 1 tick below the lower of Day-1 low and Day-2 low.
7. Take partial profits within 2–6 bars and trail the balance; exact fraction and trailing algorithm are unresolved.

Shorts reverse the rule.

## 4. Remaining genuine ambiguities

The following remain open and must be handled as versioned QORE policies rather than attributed to the authors:

- exact `5–10 tick` choice for Classic entry offset;
- exact equality/tie semantics when multiple prior extrema share the same price;
- exact method for mapping `trading sessions earlier` on non-Daily bars;
- exact trailing-stop algorithm for Classic;
- exact partial-profit fraction and exact trailing-stop algorithm for Plus One;
- gap execution model when a bar opens through entry or stop;
- same-bar entry/stop ordering when only OHLC resolution is available;
- transaction-cost/slippage model;
- market-transfer economics.

## 5. Candidate architecture

Do **not** combine source variants.

Freeze at least these research candidates:

- `TS_CLASSIC_SOURCE_R1`: age=4, same-bar entry, prior-extreme + entry offset, setup-bar extreme stop, trailing-exit family, re-entry allowed.
- `TS_PLUS_ONE_SOURCE_R1`: age=3, next-bar entry at prior extreme, two-bar extreme stop, 2–6-bar partial + trail family.

Derived NY-M5/WH-SelfInvest/CRT/ICT variants remain separate experiments and may not contaminate these source-faithful candidates.

## 6. DeepSeek claims explicitly rejected for canonical engineering

- `Classic Day-2 entry` → **REJECTED**.
- `Classic age 3-or-4 unresolved` → **REJECTED**; Classic=4, Plus One=3.
- `Plus One entry at Day-1 low` → **REJECTED**.
- `Daily-only / intraday unauthorized` → **REJECTED**.
- `Classic 5-period target` → **REJECTED AS CANONICAL**.
- `TBS/TWS canonical terminology` → remains **NON-CANONICAL / COMMUNITY**.
- `FVG/OB/EMA canonical filters` → remains **NON-CANONICAL / DERIVED**.

## 7. Governance

No fresh holdout may be consumed until the candidate mechanics and QORE execution policies are frozen. Development may use only already-consumed or explicitly development-designated evidence.

`SOURCE-ADJUDICATED != PROFITABLE`  
`BACKTEST-PROFITABLE != DEMO_ELIGIBLE`  
`DEMO_ELIGIBLE != LIVE/PRODUCTION AUTHORITY`
