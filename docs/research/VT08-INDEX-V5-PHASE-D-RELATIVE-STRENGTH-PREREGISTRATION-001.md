# VT-08 INDEX V5 — PHASE D RELATIVE-STRENGTH / PEER NON-CONFIRMATION PREREGISTRATION 001

Status: PRE-ECONOMIC PHASE-D TEST / CONSUMED-EVIDENCE ONLY

## Purpose

Test one causal hypothesis promoted from the completed V5 Phase-C regime forensics without opening the sealed 2020–2022 holdout and without changing the frozen V3 economic mechanics.

Phase C identified a reproducible regime difference in simultaneous cross-index structural confirmation. This document freezes the interpretation and acceptance gates before Phase-D economic falsification.

## Source rationale

Primary methodology source: TTrades.

Relevant source principles:

- Relative Strength & Weakness + SMT Divergence (2026-02-28): correlated assets normally form similar structure; structural non-confirmation/divergence contains information; use relative strength/weakness to refine trade selection.
- How To Use SMT Divergence — TTrades Fractal Model (2026-05-30): SMT is an additional confluence after a valid Fractal Model / change in state of delivery; it is not a standalone strategy.
- Ideal Formation (2026-06-27): Candle-2/Candle-3 closure and Protected Swing must be interpreted in structural context and at a meaningful POI.
- Positional Entries (2026-08-08): positional entry is allowed only after the fractal model is complete and a valid Protected Swing exists.

This Phase-D hypothesis is NOT claimed to be canonical price-extreme SMT. It is a mechanical cross-index structural non-confirmation proxy: the subject setup is accepted only when one correlated peer confirms the same completed fractal direction while the remaining peer does not resolve a valid signal. The proxy is falsifiable and entirely available at `signal_at`.

## Frozen base mechanics

No changes from the V3 geometry candidate mechanics used by the frozen 183-row V4 census:

- markets: NAS100 / SP500 / US30;
- timezone: America/New_York, DST-aware;
- anchors: 02 / 06 / 10 NY;
- LONG + SHORT;
- C2-or-C3 body-close resolver;
- farthest structural Protected Swing;
- Protected-Swing structural stop;
- geometry constraints already frozen by V3;
- 2.5R experimental replay target;
- next-H4 lifecycle / containment;
- same replay/fill semantics as V3;
- one-candidate constraints unchanged.

No market, side, anchor, closure family, target, stop or management selection is permitted in Phase D.

## Phase-D hypothesis D1 — peer confirmation plus one structural non-confirmation

At the subject trade's `signal_at`, reconstruct the same frozen V3 structural signal independently for all three authorized indices using only bars closed/available by that timestamp.

Retain the subject trade if and only if:

1. the subject itself resolves the frozen base signal;
2. exactly **two of the three** authorized indices resolve a structural signal in the subject trade direction;
3. **zero** authorized indices resolve a structural signal in the opposite direction;
4. therefore exactly one correlated peer is a fail-closed non-confirmation (no valid signal) rather than an opposite-side signal.

Operational predicate on the already-frozen V4 feature census:

`cross_index_simultaneous_same_side_signals == 2`

AND

`cross_index_simultaneous_opposite_side_signals == 0`

The count is not a tunable threshold. Phase D tests this single preregistered predicate only. Counts 1 and 3 are diagnostic comparators and may not be selected after the test.

## Leakage protection

- Only information available at or before `signal_at` may enter the predicate.
- No `outcome_*` column may enter candidate construction.
- No MAE/MFE, exit reason, target replay, future H4/M15 bars or post-entry state may enter the predicate.
- The sealed 2020–2022 tranche must not be read, downloaded, summarized or queried during Phase D consumed-evidence testing.

## Phase-D consumed-evidence acceptance gate

Primary friction: **0.05R/trade**.

D1 may advance to candidate freeze only if all of the following hold on the frozen 183-row consumed census:

1. retained sample >= 60 trades;
2. stressed mean R > 0 in each consumed window: 2022–23, 2023–24 and 2024–26, with >=10 retained trades per window;
3. aggregate stressed mean R >= +0.10R/trade;
4. aggregate stressed PF >= 1.20;
5. aggregate stressed max drawdown <= 10R;
6. both chronological halves have stressed mean R > 0;
7. at least 3 of 4 chronological quartiles have stressed mean R > 0;
8. NAS100, SP500 and US30 each have positive aggregate stressed mean when support >=10;
9. LONG and SHORT each have positive aggregate stressed mean when support >=15;
10. every leave-one-market-out stressed mean is > 0;
11. under secondary 0.10R/trade friction, aggregate mean R remains > 0 and PF > 1.0;
12. no post-hoc deletion is required to pass.

Semestral blocks are reported as stability diagnostics. A negative sparse block does not by itself fail D1, but any negative block with >=10 trades fails D1.

If any mandatory gate fails, D1 is rejected and candidate freeze is prohibited.

## Candidate freeze contract if D1 passes

Only after the Phase-D report passes all gates:

- assign canonical candidate identity `VT08_INDEX_V5_D1_RELATIVE_STRENGTH_001`;
- serialize exact rules and configuration;
- bind code SHA, config SHA, source provenance and data digests;
- generate deterministic fingerprint;
- assert no-lookahead and tie-breaking semantics;
- freeze execution semantics and stress assumptions;
- prohibit any rule drift before fresh validation.

## Fresh holdout gate — still sealed now

The 2020–2022 tranche remains SEALED until the candidate freeze above exists.

Once opened, it may be used exactly once for the frozen candidate. Before opening it, the following fresh acceptance criteria are fixed:

- retained sample >= 30 trades;
- primary 0.05R/trade stressed mean > 0;
- stressed PF >= 1.15;
- stressed max DD <= 15R;
- both chronological halves have stressed mean > 0;
- at least 3/4 chronological quartiles have stressed mean > 0, unless a quartile has <5 trades, in which case it is reported as sparse and not used as a pass/fail stratum;
- 0.10R/trade secondary stress remains positive in mean R and PF > 1.0;
- no supported market (n>=8) has mean <= -0.10R/trade;
- no supported side (n>=10) has mean <= -0.10R/trade.

Failure rejects the frozen candidate and permanently consumes the 2020–2022 tranche. No repair may use those holdout outcomes as development evidence.

## Post-holdout certification gates

A fresh-pass candidate is not yet certified. It must still complete preregistered:

1. walk-forward stability;
2. transaction/slippage stress;
3. block-bootstrap Monte Carlo;
4. correlated cross-index/account-wide drawdown qualification;
5. CIBO compatibility without using CIBO to manufacture base edge;
6. QORE Risk authorization-path verification;
7. deterministic execution/fail-closed testing;
8. prop-firm/account contract qualification;
9. immutable final audit.

Until those gates pass:

`LIVE_AUTHORIZED = FALSE`

`REAL_CAPITAL_AUTHORIZED = FALSE`

`PRODUCTION_AUTHORIZED = FALSE`
