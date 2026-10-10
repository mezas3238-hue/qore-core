# VT31 ICT cleanroom — A/B causal preregistration / opposite protected swing

**Date:** 2026-10-10. **Architect:** COG, one `VT31` shared London / New York trader. **Mode:** PAPER source-research only; **NOT** a certified trading replay.

## Hypothesis, not a verified ICT stop doctrine

The user's independent technical review correctly identifies a potential source-logic mistake: a bullish MSS *breaks a prior swing high*, but returning through that high during a FVG retracement need not imply violation of the *opposite protected swing low*; symmetrically for shorts. This can only be tested objectively with an as-of protected swing label. The Silver Bullet 2023 source examples [lesson notes](https://edgeofict.com/learn/mentorship-2023/29-silver-bullet-time-based-trading-model-may-15) support the return to the FVG, bodies respecting the inefficiency, next directional draw, and NY time windows. They do **not** certify any arbitrary "three-M1 opposing pivot" swing, CE-only order, complete-FVG-close, or fixed displacement criterion as universally prescribed stop rules. Those are **explicit research assumptions** requiring source review.

## Why the existing 2,076 invalidations cannot yet be recoded into six mutually exclusive outcomes

Verified prior [real-3Y COG forensic #38020203387](https://github.com/mezas3238-hue/qore-core/actions/runs/38020203387):
- 2,140 first suitable M1 source FVG offers (766 London, 721 NY AM, 653 NY PM);
- 2,076 final source cancellations (1,587 COG unavailable; 489 changed DOL), 46 ambiguous M1 paths, 17 expiry, 1 touch-not-fill;
- 1,645 *overlapping* old-pivot-close flags, 1,019 overlapping opposite-MSS flags, 57 DOL swept on same cancellation M1, 698 cancellations contain multiple flags.
- The previous OPS replay also observes **301 M1 OHLC CE overlaps while source eligible** and **737 same-M1 CE/cancel overlaps with unknowable chronology**. Therefore the phrase "97% invalidated BEFORE FILL" is **unproven**, not a proper trading loss rate.

The data does NOT yet timestamp:
- A causally confirmed opposing protected swing corresponding to every original MSS;
- The tick-ordering of CE, DOL, FVG crossing or stop inside a single M1;
- Actual bid/ask, broker ACK, entry/stop/target execution and realized PnL.

Hence it is impossible to reclassify all 2,076 as *stop reached, unresponsive gap, expiry, opposite MSS+FVG, protected opposite pivot breach or target before entry* **from old aggregate logs alone**. Forcing all events into these bins would invent evidence. Instead retain `UNKNOWN` and `MULTIPLE_FLAGS_SAME_M1` where required.

## Pre-registered matched experimental design

**A** is the unchanged integrated OPS + native COG `VT31Trader` decision stream; NO changing source FVG detection, M1 window bounds, native DOL, original MSS threshold, chosen CE or target.

**B** is an independent, passive **counterfactual source-offer shadow only**, constructed from the *exact same first suitable FVG* as A, NEVER searching for a superior hindsight FVG. For a bullish original MSS, protected price is the last **three-M1 locally confirmed low** whose right-confirmation candle closed **before the MSS breakout M1 began**; bearish uses the last confirmed high. If such causal opposite swing cannot be proved in the source tail, B is `UNPROVEN_PROTECTED_SWING`, not `VALID`.

Within the original source window, B labels outcomes conservatively:
1. `TARGET_BEFORE_CE` is **thesis fulfilled without any price-only CE crossing**: *not* stop or directional invalidation.
2. `PROTECTED_SWING_CLOSE_BROKEN` means the completed M1 **close** breaks the previously confirmed opposite pivot, not merely the broken MSS pivot.
3. `OPPOSING_MSS_DISPLACEMENT_AND_FVG`: opposite native displacement-confirmed `_confirmed_break` plus same-closing-M1 opposite verified FVG. **Important limitation:** the initial B code requires joint confirmation on the SAME M1; the proposed complete version must additionally preserve an opposite MSS hypothesis until a *later* closed-M1 FVG; this is not yet a full independent opposite-thesis doctrine.
4. `FVG_FULL_CLOSE` (close below full bullish FVG / above full bearish FVG) before any clean CE observation; not every wick in the zone is invalidation.
5. `CE_OVERLAP_NOT_BROKER_FILL` for first M1 OHLC overlapping the CE, if no simultaneous cancellation/target, treated as midpoint research hypothesis, **NOT an executable quote fill**.
6. `CE_AND_CANCELLATION_SAME_M1_UNKNOWN` for same-minute target / structure / gap / opposite-thesis and CE: do not invent ordering. Only **following M1** after a clean CE may contribute `MID_ONLY_TARGET_AFTER_CE` vs `MID_ONLY_STOP_AFTER_CE` or `SAME_M1_TARGET_STOP_UNKNOWN`; this is an explicitly conditioned price-path proxy, not fill or PnL.
7. `WINDOW_EXPIRED_BEFORE_CE` is distinct from a canceled direction. Post-CE price may remain unresolved at the hour end: the 2023 lesson describes moves continuing after the setup hour, so do not label those as failed trades.

**Hypothesis risk:** A's current COG pivot and B's researched protected pivot can both be too sensitive because the existing `_confirmed_break` uses a 3-bar local pivot and the unverified QORE 1.25x median-body displacement. A paired test of invalidation alone does **not** certify original ICT methodology. The same-market A/B replay can test source survival and market-price overlap, **not real win rate, spread/commission net expectancy, Sharpe or drawdown**. Robustness must be checked separately London vs New York AM vs NY PM (same one trader book).

## Implementation status

The source-only A/B module is published in research branch `agent/vt31-ab-research-20261010`:
- `scripts/vt31_shadow_opposite_pivot_ab_v1.py`: independent as-of opposite-swing capture, shadow state, CE/stop/target path unknown.
- `scripts/vt31_shadow_ab_3y_runner.py`: replay streaming wrapper consuming same frozen `VT31_NAS100_OWNER_3Y_BASE_001` M1, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, outputs per-window A/B source statuses and conditional mid-only research observations.

**RUN STATUS:** source files committed; the new A/B pipeline is not yet a completed verified three-year execution and no A/B numerical differences are claimed here. Run independently under reviewed scientific CI, add adversarial fixtures, test source candidate parity 766/721/653 and no pending-without-COG, then publish exact terminal numbers before deciding any production logic. Existing base `main` and VPS untouched. Historic holdout sealed.

## What remains

1. Architect OPS to review and execute new A/B source shadow with strict as-of protected pivot test and no future retrieval. Resolve same-bar vs later opposite MSS+FVG structure and use baseline original ICT lesson to confirm protected swing semantics before a production rule.
2. Separate source order lifecycle from *post-fill position*: no invalidation of a proved filled position simply because a pre-entry pending setup expired.
3. Original 3Y source has no historical timestamped bid/ask ticks or broker ACK; any true fill, stop, net PF/DD/Sharpe/Sortino requires that data and independent physical specifications. An NDX100 0.01-lot MT5 screenshot is only a single actual broker example and must not be retrofilled across 3Y NAS100 prices.
4. Do not choose B merely because it preserves more source candidates. Do not apply old R2.2 logic, legacy perf targets, outcome-based threshold optimization or open the holdout. ONE `VT31`, M1 operative, London and NY sessions, research-only.
