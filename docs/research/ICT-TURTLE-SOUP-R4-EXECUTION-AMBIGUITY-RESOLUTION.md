# ICT Turtle Soup R4 — execution ambiguity resolution

Date: 2026-09-15
Research line: ICT_TURTLE_SOUP_R4
Status: source adjudication only; no economics; no fresh OOS

This document resolves the six remaining deterministic implementation ambiguities that were left open after the three-source adjudication. Source hierarchy remains ICT primary -> TTrades public source -> QORE execution formalization only where the methodology does not specify exchange/backtest microstructure.

## 1. Multiple valid Daily DOLs simultaneously

### Source evidence
- TTrades target framework uses liquidity already present on the higher timeframe: untouched swing highs/lows and previous higher-timeframe candle highs/lows.
- TTrades explicitly allows multiple targets: short-term targets for partials and higher-timeframe targets for runners.
- TTrades liquidity guidance asks for the nearest obvious liquidity that has not yet been taken and shifts attention to the next clear high/low once a level is consumed.
- TTrades does not publish a universal ranking `weekly > daily > session`.

### R4 adjudication
For the selected H4 execution family, the target context is Daily.

1. Build all pre-entry untouched Daily liquidity candidates in the direction of the frozen Daily bias.
2. Remove levels already taken before entry.
3. The nearest relevant untouched Daily liquidity becomes `PRIMARY_DOL`.
4. Additional farther relevant Daily/HTF liquidity may be stored as `SECONDARY_DOL` / runner objectives, but is not used to change the primary candidate after entry.
5. If two candidates are indistinguishable at the same executable price, treat them as one stacked-liquidity zone with multiple labels.
6. If deterministic relevance cannot distinguish two materially different candidates at the same distance/priority, abstain (`AMBIGUOUS_PRIMARY_DOL`) rather than invent a ranking.

Status: TTRADES_CORROBORATED + QORE_FORMALIZATION_REQUIRED for exact ties.

## 2. One C2 sweeps multiple same-side liquidity pools

### Source evidence
- TTrades treats equal highs/lows as clustered liquidity and describes price running through multiple liquidity highs.
- Previous week/day/session highs/lows may coexist as liquidity references.
- No source says a same-side multi-pool sweep invalidates the setup.
- Relevant Swing/HTF POI remains the causal setup anchor.

### R4 adjudication
Do not abstain merely because one C2 swept several same-side pools.

- Freeze the `PRIMARY_SETUP_ANCHOR` from HTF context before C2 (Relevant Swing / POI).
- Record every pre-existing same-side pool swept by C2 as `SWEPT_POOL_SET`.
- The setup is valid only if the frozen primary anchor itself is swept and the source-valid C2 reversal closure completes.
- Extra same-side pools are confluence/metadata, not competing candidate identities.
- Opposite-side sweeps in the same causal C2 remain ambiguous and fail closed unless a separate source-backed rule is later established.

Status: TTRADES_CORROBORATED for clustered liquidity; QORE formalization for primary-anchor bookkeeping.

## 3. Stop exactly at Protected Swing or one native tick beyond

### Source evidence
TTrades repeatedly describes the protected swing as the invalidation anchor:
- bullish stop goes beneath the protected low;
- bearish stop goes above the protected high;
- if price trades through the protected swing, the expansion expectation has changed;
- default stop is at / just beyond the protected swing; fixed arbitrary buffers are not source-backed.

### R4 adjudication
The methodology supplies the structural level; exchange price discretization is QORE execution semantics.

- LONG: `stop = protected_low - one_native_tick`
- SHORT: `stop = protected_high + one_native_tick`

Rationale: this encodes the source concept of price trading *through/beneath/above* the protected swing rather than treating a mere touch at the protected price as structural violation. No larger fixed pip/ATR buffer is allowed.

Status: structural invalidation TTRADES_FORMALIZATION; one-native-tick offset QORE_FORMALIZATION_REQUIRED.

## 4. Dojis inside the CISD opposing candle series

### Source evidence
TTrades defines CISD using a series of `up-close` or `down-close` candles and says to use the full opposing series; when multiple opposing candles exist, the first candle open is the key level.

A doji (`close == open`) is neither an up-close nor a down-close candle. No public source located assigns dojis to either opposing series.

### R4 adjudication
- A doji does not belong to either opposing series.
- A doji terminates a contiguous opposing series.
- The CISD threshold uses the open of the first candle in the contiguous opposing series causally responsible for the selected swing.
- If the swing cannot be causally bound to one contiguous opposing series because neutral/doji structure makes the series ambiguous, abstain (`AMBIGUOUS_CISD_SERIES`).

Status: semantic consequence of TTrades definition + fail-closed QORE formalization. No doji direction may be invented.

## 5. Gaps

There are two different problems.

### A. Missing-data / timestamp gaps
ICT/TTrades methodology does not define how to reconstruct unavailable bars. Therefore:
- if a gap prevents construction of the relevant HTF candle, LTF CISD, entry path, stop/target path, or same-bar ordering, abstain;
- never interpolate OHLC;
- never assume continuity across missing evidence.

Status: QORE data-governance rule.

### B. Real market price gaps
The structural rules still apply:
- if the positional-entry open gaps through the protected swing, the setup is already invalid -> no entry;
- if the entry open is already at/through the frozen primary DOL, the objective has already been consumed -> no entry;
- after entry, if a new bar opens beyond the stop, execute `GAP_STOP` at the observed open (not the theoretical stop price);
- if a new bar opens beyond the target without first invalidating the trade, credit no better than the frozen target price for conservative historical replay.

These are execution/backtest semantics, not claims about ICT methodology.

Status: QORE_FORMALIZATION_REQUIRED.

## 6. Same M5 touches stop and target

ICT/TTrades methodology does not determine intrabar ordering from an OHLC bar.

### R4 adjudication
1. If lower-resolution evidence (M1/tick) is retained and was frozen as available before replay, use it to resolve the sequence.
2. If no lower-resolution evidence exists, the ordering is unknowable.
3. Fail conservatively: `STOP_FIRST`.
4. Never use target-first because it improves the result.

This is an evidence-resolution rule, not an ICT trading rule.

Status: QORE_FORMALIZATION_REQUIRED / conservative fail-closed.

## Final R4 deterministic semantics

Resolved for preregistration:
- multiple DOLs: nearest relevant untouched Daily liquidity = primary; farther levels secondary; exact unresolved tie -> abstain;
- same-side multi-pool sweep: allowed; frozen Relevant Swing/POI remains primary anchor; record all swept pools;
- stop: one native tick beyond the protected swing;
- doji: neither up-close nor down-close; breaks opposing series; ambiguity -> abstain;
- missing-data gaps: abstain; real price gap through PS/DOL before entry -> no trade; post-entry gap-stop fills at observed open;
- same M5 stop+target: resolve with frozen lower-timeframe evidence if available, otherwise STOP_FIRST.

Still not authorized:
- arbitrary pip/ATR stop buffers;
- target ranking by a universal weekly/daily/session hierarchy;
- target reselection after entry;
- same-side pool deletion because of consumed P&L;
- target-first same-bar assumptions;
- interpolation across missing data.

No economics were inspected or changed by this adjudication.
