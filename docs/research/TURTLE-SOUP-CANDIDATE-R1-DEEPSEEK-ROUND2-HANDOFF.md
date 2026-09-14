# QORE CORE — DEEPSEEK ROUND 2 HANDOFF

## TURTLE SOUP CANDIDATE R1 — MANAGEMENT, RE-ENTRY & INTRADAY SEMANTICS CLOSURE

**Checkpoint:** 14 September 2026  
**Repository:** `mezas3238-hue/qore-core`  
**Issue:** `#551`  
**Research PR:** `#553` — DRAFT  
**Research identity:** `turtle-soup-candidate-r1`  
**Canonical Trader Code:** `CODE_UNASSIGNED`  
**Research owner:** DeepSeek — source reconstruction only

---

# 0. PURPOSE

This is **not** a fresh reconstruction of Turtle Soup.

QORE Engineering has adjudicated your Round-1 report against recoverable text from Connors/Raschke *Street Smarts*. Several Round-1 claims were materially wrong and are now CLOSED.

Your task is to research ONLY the residual source ambiguities that block a defensible economic replay.

Do not reopen closed findings unless you produce stronger direct-author evidence with an exact locator.

---

# 1. CLOSED SOURCE FINDINGS — TREAT AS BINDING PREMISES

## Classic Turtle Soup

The following are closed:

1. Previous 20-period extreme must be at least **4 trading sessions earlier**.
2. Classic is **same-session**, not next-day:
   - after price crosses beyond the prior 20-day extreme,
   - place a reversal stop 5–10 ticks beyond the prior extreme in the reversal direction,
   - order is valid for that session/day only.
3. Initial protective stop is **1 tick beyond the current breakout-session extreme**.
4. Source explicitly authorizes **re-entry at the original entry price on trade Day 1 or Day 2** if stopped.
5. Source management is a **trailing stop as profit develops**; no canonical fixed 5-period target was found.
6. Turtle Soup can be traded in **all timeframes**.
7. For intraday use, the book explicitly says entry is at the prior 20-bar high/low **minus/plus 1 tick**.
8. The book contains 10-minute examples.

## Turtle Soup Plus One

The following are closed:

1. Previous 20-period extreme must be at least **3 trading sessions earlier** in the printed rule set.
2. Breakout bar closes at or beyond the earlier 20-period extreme.
3. Entry stop is placed on the **next bar/day at the earlier 20-period extreme**.
4. If not filled on that next bar/day, cancel.
5. Initial protective stop is **1 tick beyond the lower/higher extreme of the breakout bar and entry bar**.
6. Source instructs taking **partial profits within 2–6 bars** and trailing the remaining position.
7. Intraday use is source-authorized, with prior 20-bar high/low **minus/plus 1 tick** entry language.

## Claims rejected as canonical

Do not reintroduce these without stronger primary/direct-author evidence:

- Classic Day-2 entry.
- A universal unresolved `3-or-4` age parameter.
- Plus One entry at the breakout-bar low/high.
- Daily-only Turtle Soup.
- Canonical 5-period target.
- FVG, Order Block or EMA as canonical Turtle Soup rules.
- TBS/TWS as Connors/Raschke terminology.

---

# 2. PRIMARY SOURCE LOCATORS ALREADY RECOVERED

Engineering recovered the relevant *Street Smarts* text around:

- Classic rules: printed pages around Chapter 4, pp. 12–21 in the recovered scan.
- Plus One rules: Chapter 5, printed pp. 21–30.
- Intraday note: immediately before the 10-minute Bonds and S&P examples in Chapter 5.

Do not claim `SOURCE_TEXT_UNAVAILABLE` for these sections. They are now recoverable.

---

# 3. RESEARCH QUESTION A — CLASSIC TRAILING STOP

We need to know whether Connors/Raschke ever define a deterministic trailing-stop algorithm specifically usable for Turtle Soup.

Search direct-author / primary material for any exact rule such as:

- previous bar low/high;
- n-bar low/high;
- fixed tick trail;
- ATR/volatility trail;
- breakeven trigger;
- percentage retracement;
- parabolic move rule;
- time-based tightening;
- partial-profit rule;
- end-of-day or multi-day exit.

For every finding provide:

`SOURCE → LOCATOR → EXACT CONTEXT → TURTLE-SOUP-SPECIFIC? → DETERMINISTIC? → FORMALIZATION`

If the source only says “trail aggressively”, “tighten stops”, or equivalent discretionary language, classify:

`CLASSIC_MANAGEMENT_DISCRETIONARY`

Do **not** manufacture a mechanical trailing rule.

---

# 4. RESEARCH QUESTION B — PLUS ONE PARTIAL PROFITS

The source says partial profits should be taken within **2–6 bars** and the rest trailed.

Find whether any primary/direct-author source specifies:

- percentage/position fraction to scale out;
- exact bar among 2,3,4,5,6;
- price condition for taking the partial;
- stop adjustment after the partial;
- break-even rule;
- exact trailing method for the balance.

Required output:

| Field | Exact source rule | Locator | Confidence | Mechanical? |
|---|---|---|---|---|
| Partial fraction | | | | |
| Earliest partial bar | | | | |
| Latest partial bar | | | | |
| Price trigger | | | | |
| Post-partial stop | | | | |
| Balance trail | | | | |

If not found, say explicitly:

`PLUS_ONE_MANAGEMENT_PARTIALLY_SPECIFIED_BUT_NOT_MECHANICAL`

---

# 5. RESEARCH QUESTION C — CLASSIC RE-ENTRY

The source authorizes re-entry at the original entry level if stopped on Day 1 or Day 2.

We need exact lifecycle semantics:

1. Is only one re-entry allowed, or multiple attempts?
2. If stopped on Day 1 and re-entered on Day 1, may another re-entry occur on Day 2?
3. Does the original stop price remain valid, or is stop recalculated from the newest session extreme?
4. If the market makes a new adverse extreme after the first stop, what becomes the new protective stop?
5. Does re-entry require price to make another excursion beyond the 20-period reference first, or is a resting stop at the original entry enough?
6. Exact expiry at end of Day 2?
7. Does “Day 1 / Day 2” mean calendar trading sessions even for intraday Turtle Soup?

Return an event-state machine if evidence supports one.

If source is silent, mark each field `UNRESOLVED` separately.

---

# 6. RESEARCH QUESTION D — INTRADAY AGE SEMANTICS

This is a key blocker.

The book says the strategies work in all timeframes and gives 10-minute examples. The daily rules use:

- Classic: previous extreme at least **4 trading sessions earlier**.
- Plus One: previous extreme at least **3 trading sessions earlier**.

We need to know how the authors map this condition to intraday bars.

Investigate whether direct-author material clarifies that intraday means:

A. previous 20-bar extreme at least 4/3 **bars** earlier;
B. previous extreme at least 4/3 **trading sessions/days** earlier despite intraday bars;
C. another rule;
D. examples implicitly demonstrate the intended mapping.

Specifically inspect the 10-minute Bonds and S&P examples and any other intraday examples.

Required verdict separately for Classic and Plus One:

`INTRADAY_AGE = BARS / SESSIONS / OTHER / UNRESOLVED`

Do not infer silently.

---

# 7. RESEARCH QUESTION E — DAILY VS INTRADAY ENTRY OFFSET

Already established:

- Classic daily/futures rule: reversal stop **5–10 ticks** from earlier 20-period level.
- Intraday note: enter at earlier 20-bar high/low **minus/plus 1 tick**.

Research whether:

1. Plus One intraday also uses exactly the one-tick offset, or whether it enters exactly at the prior level.
2. Classic intraday always uses one tick regardless of instrument.
3. Futures with different tick sizes change only monetary distance, not tick count.
4. Equities use the approximately 1/8-point convention only in the original pre-decimalization context.
5. Any later direct-author material updates the equity convention for decimalized stocks.

Return exact versioned entry profiles suitable for engineering.

---

# 8. RESEARCH QUESTION F — DAY-SESSION / NIGHT DATA

Search *Street Smarts* and direct-author material for whether Turtle Soup specifically excludes overnight/night-session data when constructing:

- 20-period highs/lows;
- current breakout-bar high/low;
- protective-stop extremes.

The book contains statements elsewhere that night data are omitted for strategies in the book. Determine whether that statement is intended as a universal methodology rule and whether later author material modifies it.

Return:

`DAY_SESSION_ONLY = CONFIRMED / NOT_CONFIRMED / SOURCE_CONFLICT`

and specify instrument classes/time period if relevant.

---

# 9. RESEARCH QUESTION G — GAP EXECUTION

Find direct-author examples/rules for:

- Classic opening already beyond the reversal entry stop;
- Plus One opening through the entry stop;
- gap through protective stop;
- fill price assumptions.

We need to know whether source assumes:

- fill at stop level;
- fill at opening price when gapped through;
- discretionary/slippage handling.

Do not use modern backtester conventions unless clearly labeled QORE execution policy.

---

# 10. RESEARCH QUESTION H — MECHANICAL RESEARCH EXITS

Even if the live methodology is discretionary, determine whether Connors/Raschke or an authorized/direct-author research source ever published a **mechanical test exit** for Turtle Soup or Plus One, for example:

- N-bar exit;
- fixed holding period;
- fixed risk multiple;
- trailing previous-bar extreme;
- volatility stop;
- close-based exit.

This distinction is important:

`AUTHOR_LIVE_MANAGEMENT` may remain discretionary while an `AUTHOR_RESEARCH_EXIT` could be suitable for source-bound economic characterization.

Do not substitute WH SelfInvest, Oxfordstrat, MQL5 or another third-party exit and label it authorial.

---

# 11. REQUIRED CLAIM-LEVEL MATRIX

Return:

| ID | Question | Claim | Tier | Source | Locator | Evidence | Confidence | Deterministic Formalization | Residual Ambiguity | Safe to Automate |
|---|---|---|---|---|---|---|---|---|---|---|

Every unresolved item must remain unresolved.

---

# 12. REQUIRED FINAL VERDICTS

End with exactly these blocks:

## A. Classic Management Verdict

State whether a complete deterministic exit exists.

## B. Plus One Management Verdict

State whether partial/trailing management can be fully automated from source.

## C. Classic Re-entry State Machine

Exact if possible; otherwise list unresolved transitions.

## D. Intraday Semantics Verdict

Age rule + entry offsets + session-data policy.

## E. Mechanical Research Exit Verdict

State whether any direct-author mechanical research exit exists.

## F. QORE Engineering Blockers

Only remaining blockers, no already-closed questions.

---

# 13. PROHIBITIONS

- Do not reintroduce the old VT-09 implementation.
- Do not merge Classic and Plus One.
- Do not use future-bar operations such as `shift(-1)` in executable pseudocode.
- Do not use a 5-period exit unless direct-author evidence is found.
- Do not use WH SelfInvest/ICT/CRT rules to fill source gaps.
- Do not choose 2R or another fixed target for convenience.
- Do not optimize parameters.
- Do not declare profitability or approval.

Your authority is source reconstruction only.

---

# 14. DELIVERY STANDARD

QORE needs enough evidence to decide whether:

1. the source itself can produce a fully mechanical economic replay; or
2. QORE must create a clearly labeled experimental management layer.

If the answer is (2), identify exactly which management dimensions QORE must predeclare before any fresh holdout is opened.
