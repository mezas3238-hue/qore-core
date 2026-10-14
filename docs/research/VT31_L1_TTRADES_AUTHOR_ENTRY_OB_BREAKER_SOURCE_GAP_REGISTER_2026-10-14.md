# VT31 — L1 source-family register: TTrades AM, Order Block, Breaker · 2026-10-14

**SCOPE: independent SOURCE STUDY (not rule change, not certification).** Source material crosschecked with PR #906. This is an additive documentary registry after the 119-stop audit of PR #943, **no new backtest and no experiment selection**.

## Primary-source precedence
1. [TTrades AM Silver Bullet NQ, 19-Jun-2025](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/): NY 10–11, prior 09h range, mandatory raid then displacement, target opposite 09h boundary, four entry families (displacement, FVG, OB, breaker); stop beyond swing responsible for displacement. The text does not supply one unique machine-readable swing selector, entry tie-break or universal Order Block/Breaker formula.
2. [TTrades Order Blocks Simplified](https://ttrades.com/order-blocks-simplified/): describes last opposite-color **candle(s)** as a sequence into a reversal, higher-timeframe context, and 50% **body** mean threshold with invalidating close. This article supports OB semantics but is **not** a closed executable specification for NY AM Silver Bullet 2025.
3. [TTrades My Favorite Reversal Pattern: Orderblocks, 19-Jun-2025](https://ttrades.com/my-favorite-reversal-pattern-orderblocks/): liquidity sweep, a series of opposing candles, confirmation by closing back through them, displacement and opening-price sensitivity. The event cannot be reduced by source identity alone to the most recent candle with a raw overlap.
4. [TTrades Breaker Blocks Simplified](https://ttrades.com/breaker-blocks-simplified/): failed prior structure respected after change of narrative, bullish Low→High→Lower Low→Higher High, bearish inverse High→Low→Higher High→Lower Low. Whole candle including wick may define breaker zone; displacement matters.
5. [TTrades Unicorn Entry Model](https://ttrades.com/the-unicorn-entry-model-explained-breaker-blocks-and-fair-value-gaps/): describes a breaker-zone failure paired with FVG confluence and consequent retest. This **unicorn** subset must not silently become a mandatory restriction on EVERY NY AM breaker without author source saying so.

## Audited difference from [PR #906](https://github.com/mezas3238-hue/qore-core/pull/906), code exact `scripts/vt31_ttrades_am_all_entry_sources_20261013.py`

| Family | What the research detector currently implements | Source fidelity still unresolved |
|---|---|---|
| DISPLACEMENT_DIRECT | one first closed inside-range reversal candle post-raid with ATR20 body >1.5× and body/range ≥0.70 | no attribution of numeric ATR/body thresholds to TTrades in AM 2025; not proven separate executable order policy |
| FVG_3M1 | first direction-compatible 3-M1 gap after displacement, source midpoint | author AM source does not specify universally CE vs first touch vs order event; no broker/contract tick/ACK |
| ORDER_BLOCK_RETEST | chooses a SINGLE last opposing candle from sweep to displacement, retest OHLC through body midpoint | TTrades source permits a SERIES of opposing candles, requires closure-based validation and context; body 50% may relate to invalidation, not proof any overlap is a new order/fill |
| BREAKER_RETEST | confirmed 3-bar 09h pivot broken/reclaimed; retest at one **price level** | not independent proof of Low→High→Lower Low→Higher High (or bearish inverse), failed block body/wick ZONE and transition; structural breaker identity is unproved |
| Stop | PR #906 uses a sweep-based candidate stop proxy; PR #935 uses G3 C2 full wick; author AM says beyond displacement-causing swing | three non-equivalent semantics and no verified author swing ID; see PR #943 audited 116/2/1 relative pre-MSS observed extrema |

**The PR #906 author explicitly labelled its formulas QORE_FORMALIZATION_PROXY**, so this review is not a claim the original researchers concealed fidelity gaps. It is a promotion boundary: neither the 212 DIRECT /205 FVG /116 OB /84 breaker signals (possibly overlapping) nor 119 different-context G3 FVG can be relabelled TTrades-certified or added into 617 trades.

## Pass criteria before L1 author-fidelity certification (NOT met)
- Produce a primary positive and primary negative case for each OB/Breaker family with context, timestamps, which candle(s) form block, whether they are confirmed by CLOSED M1, exact zone and invalidation rule, and counterexample of a geometric 3-M1 pivot NOT actually being a breaker.
- Identify a causal displacement-causing protected swing level with explicit as-of before entry, considering sweep extrema, post-sweep extremum, OB/BB; distinguish a swing from C2 merely by explanation and independently labeled source.
- Decide whether AM setup may have 4 competing entry families or one family per trade; preregister priority and stop policy before observing PnL. Do not select OB/breaker just because prior exploratory means were +1.86/+1.66 pts with wide confidence intervals crossing zero.
- Exact-source dataset license, NAS100 cTrader USTEC identity, quote/tick/ACK and Risk/CIBO separation remain M5/M7/L7 blockers. No sampling on OOS until truly frozen, no adding live/size.

**Verdict:** SOURCE_PRIMARY_ARTICLE_SUPPORT_AVAILABLE, **AUTHOR_ALGORITHM_FOR_OB_BREAKER_AND_SWING_STOP=UNDERDETERMINED**. Research definitions are versioned QORE hypotheses rather than certified copies; methodology L1, M4 and M5 remain PENDING. All original G3 frozen files and QORE Trader Lab core untouched. No merge/live/OMS/sizing.