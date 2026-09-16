# VT-08 INDEX V6 — TTRADES SOURCE-FAITHFUL FREEZE 001

Checkpoint: 2026-09-16
Status: PRE-HOLDOUT / SOURCE-BOUND / NO ECONOMIC RESULT CONSUMED
Candidate identity: `VT08_INDEX_V6_TTRADES_SOURCE_FAITHFUL_001`
Fresh holdout: `[2020-09-15, 2022-09-15)` America/New_York — SEALED

## Purpose

Rebuild VT-08 Index from the TTrades methodology itself instead of extending the rejected V2/V3/V5 economic filters. V3 geometry, daily-uniqueness, D1 simultaneous-signal counts, fixed 2.5R and one-H4 forced lifecycle are not inherited.

The governing rule is source fidelity. A mechanical rule may be mandatory only when it is explicitly stated or operationally demonstrated by TTrades. Qualitative concepts must not be converted into an optimized numeric threshold.

## Source authority

Primary lesson:
- TTrades, `Trading The 4 Hour Power Of Three - OHLC / OLHC`, 2025-09-20.
- Owner source identity: `youtube:FAKWJ-1NlLE`.
- Owner-source SHA-256: `bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271`.

Same-author mechanical clarifications used by V6:
- `The Only Trading Strategy You Need For 2026` — 2026-01-03.
- `The Best Timeframes for TTrades Fractal Model (Simple)` — 2026-01-31.
- `Relevant Swings: Which Swing Highs and Lows Matter in Trading?` — 2026-03-21.
- `How to Set Price Targets Using the Fractal Model` — 2026-05-23.
- `Intracandle CISD (IC-CISD) - Improve Your Entries` — 2026-06-13.
- `The Only Points of Interest That Actually Matter For Trading` — 2026-07-18.
- `Positional Entries - Enter Before The Expansion` — 2026-08-08.
- `Internal & External Liquidity Using the TTrades Fractal Model` — 2026-08-22.
- `Let The Wick Form, Trade The Body` — 2026-08-29.
- TTrades Candle-3 closure and CISD/protected-swing prerequisite lessons.

Later material is allowed only to formalize concepts already present in the primary H4/Fractal framework. It may not introduce a different strategy.

## Frozen market/data scope

- Markets: NAS100, SP500, US30 only.
- Operating timezone: America/New_York, DST-aware.
- Broker evidence: read-only cTrader DEMO M15 data.
- The CFD symbols are research proxies for the corresponding futures/index structure. This candidate claims methodology fidelity, not tick-for-tick identity with NQ/ES/YM.
- No Forex code or evidence is modified.

## Frozen source-faithful state machine

### 1. Daily bias

Use only completed source days available before the entry.

- close above previous completed day high -> LONG continuation bias;
- close below previous completed day low -> SHORT continuation bias;
- sweep previous day low and close back above that low -> LONG reversal bias;
- sweep previous day high and close back below that high -> SHORT reversal bias;
- conflicting/two-sided/unresolved state -> ABSTAIN.

Every lower-timeframe setup must align with this bias.

### 2. H4 timing and structure

Reconstruct the complete repeating futures H4 family shown by the source:
`18:00 / 22:00 / 02:00 / 06:00 / 10:00 / 14:00` New York.

`18:00` is also the futures daily open/context boundary. No H4 boundary is automatically a trade and there is no fixed trades-per-day cap.

### 3. Source point of interest

A setup must originate from a causal point of interest available before confirmation.

Use the same-author hierarchy mechanically:
1. Fair Value Gap if one exists between the relevant protected/reversal structure and current range;
2. otherwise a relevant swing high/low;
3. otherwise a causal CISD level/retest;
4. if no unambiguous source POI can be established -> ABSTAIN.

Relevant swing search uses the source three-higher-timeframe-candle window. No ATR, percentage-distance or optimized separation threshold is permitted.

Every retained trade records POI type, price/range and causal timestamp.

### 4. H4 Candle-2 closure

A C2 reversal closure is source-valid only when:
- price reaches/runs the relevant prior extreme/POI in the bias-consistent direction;
- the candle sweeps the prior candle extreme;
- it closes back inside the prior candle range;
- the lower-timeframe delivery shift required by the model is causal.

No V3 `risk_fraction`, range-ratio or opposite-extreme prohibition is inherited unless the source itself requires it.

### 5. H4 Candle-3 closure

If C2 does not provide the required reversal closure at the source POI, C3 may confirm:
- C3 closes through the body of C2 in the bias direction;
- it satisfies the author’s body-engulf/closure condition;
- it does not obtain validity by a new sweep of the C2 directional extreme when the source C3 rule says the closure must occur without that sweep;
- unresolved C3 geometry -> ABSTAIN.

After C3 closure the next expansion candle is treated with the same wick-then-body logic.

### 6. Intracandle wick confirmation / CISD / Protected Swing

V6 does not invent a numeric definition of `shallow` versus `deep` wick.

Instead, source-authorized IC-CISD/protected-swing evidence confirms when an H4 wick has mechanically formed:
- price reacts from the causal POI / runs relevant short-term liquidity;
- identify the causal series of opposing M15 candles that creates the swing;
- a bias-direction M15 close through that opposing series confirms CISD;
- the resulting extreme is the Protected Swing/invalidation.

No `0.30%`, ATR, wick/body ratio, volatility percentile or optimized cutoff is permitted.

A deep C2 that does not produce the required causal continuation is not forced into a same-C2 trade; V6 waits for the source C3 path.

### 7. Standard execution — PRIMARY holdout execution

Positional entry is not the primary V6 execution.

After the HTF model and M15 CISD/Protected Swing are valid, wait for the source continuation confirmation on M15. The primary deterministic V6 entry is the **close of the valid continuation confirmation**. TTrades explicitly authorizes continuation entry on the close or retest; V6 freezes the close path so the holdout has one non-optimized execution rule.

- Entry: continuation-confirmation M15 close.
- Stop: exact Protected Swing extreme; no buffer.
- Initial target: fixed `2R`, explicitly source-authorized.
- No 2.5R optimization.
- No forced next-H4-boundary exit.
- If neither stop nor target resolves before holdout boundary, mark to market at the frozen boundary and flag `boundary_mark`; this is validation accounting, not a strategy exit rule.
- Conservative historical ambiguity: if stop and target are both touched in the same M15 bar and tick ordering is unavailable, STOP is adjudicated first.

### 8. Same-C2 expansion

The primary H4 lesson allows manipulation and expansion in the same Candle 2 after the wick is confirmed. Therefore an entry may occur inside C2 when the complete causal chain is already present before the entry:
`daily bias -> POI -> IC-CISD/Protected Swing -> continuation confirmation`.

The model must not wait for the H4 close if doing so would add future information to an already valid same-C2 setup.

### 9. C3 / later expansion

When same-C2 continuation does not form and the source C3 requirements resolve, execution is sought only after the C3/next expansion state is source-valid. The exact same M15 continuation-entry, Protected-Swing stop and 2R initial target rules apply.

### 10. Positional entry — source-valid but not primary holdout path

A positional entry at a new HTF open is source-valid only after the full fractal model and Protected Swing already exist. It is retained as a diagnostic/source-supported alternate execution, but it does not enter the primary V6 holdout return series. This prevents mixing execution techniques after seeing results.

### 11. Relative strength / SMT

SMT is source-valid confluence/refinement, not a mandatory foundation of the trade. V6 therefore does **not** require D1 `2 same-side / 0 opposite` counts.

If relative-strength diagnostics are recorded, they must use actual pairwise structural divergence/separation/closure information available before entry. They may not gate the frozen primary holdout candidate.

## Explicitly removed QORE rules

The following are not part of V6:
- V3 protected-risk fraction >= 0.003;
- V3 closure/reference range ratio >= 1.2;
- `FARTHEST_STRUCTURAL` as a universal swing-selection doctrine;
- `unique-raw-signal-only` daily rejection;
- D1 exact peer-count gate;
- mandatory positional-only entry;
- fixed 2.5R target;
- forced one-H4 lifecycle;
- retrospective market/side/anchor removal.

## Holdout protocol

Fresh validation window: `[2020-09-15, 2022-09-15)` New York.

This window remains sealed until:
1. V6 implementation and focused tests are committed;
2. source-parity assertions pass;
3. Ruff + Mypy + Full QORE gate pass;
4. deterministic replay on already-consumed evidence proves no lookahead and schema/data integrity without selecting rules by P&L;
5. V6 code/rules are fingerprinted and frozen.

No economic result from 2020-2022 may be observed before those conditions are satisfied.

### Frozen fresh gates

Use the already-established QORE fresh-validation gates rather than inventing thresholds after this reconstruction:
- closed/marked sample >= 30;
- primary friction stress `-0.05R/trade`: mean R > 0;
- stressed PF >= 1.15;
- stressed max drawdown <= 15R;
- both chronological halves have positive stressed mean R;
- at least 3 of 4 chronological quartiles have positive stressed mean R; a quartile with n < 5 is sparse and does not count as a pass;
- secondary `-0.10R/trade` stress: mean R > 0 and PF > 1;
- no supported market with n >= 8 may have mean R <= -0.10R;
- no supported side with n >= 10 may have mean R <= -0.10R.

Frequency is reported separately and may not rescue a failing economic gate.

## One-shot governance

- A holdout failure rejects `VT08_INDEX_V6_TTRADES_SOURCE_FAITHFUL_001`.
- No repair may use 2020-2022 outcomes and call that same period fresh again.
- No market, side, H4 boundary, POI family or closure family may be removed after seeing holdout results.
- No merge without Owner order.
- `LIVE_AUTHORIZED=FALSE`.
- `REAL_CAPITAL_AUTHORIZED=FALSE`.
- `PRODUCTION_AUTHORIZED=FALSE`.

## Post-holdout

A passing holdout is necessary but not sufficient for certification. Before any final certification V6 must still pass frozen Walk-Forward, stress, Monte Carlo, correlated/account-wide risk, CIBO compatibility, QORE Risk authorization-path, deterministic/fail-closed execution, and prop-risk qualification.
