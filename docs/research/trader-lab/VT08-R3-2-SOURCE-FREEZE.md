# VT-08 Revision 3.2 — Source Freeze

Status: **FROZEN RECONSTRUCTION INPUT / RESEARCH ONLY**  
Checkpoint: 2026-09-12  
Primary source: `1000854868.mp4` / `youtube:FAKWJ-1NlLE`  
Primary-source SHA-256: `bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271`

## Authority hierarchy

1. Primary TTrades video + primary audio + framebook.
2. Official later TTrades clarifications, when independently provenance-bound.
3. Frozen DeepSeek Revision 3.2 independent reconstruction.
4. QORE implementation.

DeepSeek R3.2 is an independent witness, not canonical source authority. No performance result may resolve a source ambiguity.

## Shared source semantics

The rebuilt shared kernel represents:

- bullish delivery as **OLHC**: Open -> Low manipulation -> High expansion -> Close;
- bearish delivery as **OHLC**: Open -> High manipulation -> Low expansion -> Close;
- qualitative C2/C3 separation: shallow/early opposing run with range available may permit C2 expansion; a large opposing run or materially consumed range requires waiting for C2 close and looking for C3 continuation;
- causal CISD after an important level/POI/liquidity interaction;
- protected swing formation after CISD;
- explicit 50% Equilibrium references;
- six entry-family identities: reversal, continuation, confident, positional, open, and POI-continuation;
- five stop-family identities: protected swing, 50% CISD/EQ, opposing candle, FVG, and body-low;
- contextual target-family identities: 2R+, external liquidity, -1 standard deviation, daily open, and session extreme;
- current-H4 lifecycle: a trade is not authorized to survive beyond the close of the current H4 candle; a continuation in the next H4 requires a fresh evaluation;
- independent M15, M5-fractal, and M3-fractal observation profiles;
- causal timestamps and source provenance for every executable component.

## What Revision 3.2 does **not** authorize

No numerical shallow/large threshold is source-authorized. No universal entry-family priority exists. No universal protected-swing-selection priority exists. No universal target-family priority exists. No blanket Cartesian product of six entry families x five stop families x target families is authorized.

Each executable combination must be represented as one provenance-bound `VT08SourceBundle`. A source bundle does not itself select the one daily trade.

## Timing profiles

Source-complete timing and current Human Owner operational timing are separate scientific dimensions.

| Family | SOURCE_COMPLETE | OWNER_OPERATIONAL_SUBSET |
| --- | --- | --- |
| Forex | 01:00, 05:00, 09:00, 13:00 New York | 01:00, 05:00, 09:00 New York |
| Futures/indices | 02:00, 06:00, 10:00, 14:00 New York | 02:00, 06:00, 10:00 New York |

The Owner subset must never be described as the full source timing profile. Four source windows increase diagnostic windows and candidate opportunity; they do **not** increase the one-trade-per-market-day execution ceiling.

## LTF profiles

`M15` is the standard H4 pairing. `M5` and `M3` are separate fractal alternatives. They are not cross-confirmation chains and must not be combined in one replay unless a separately versioned source/Owner contract explicitly authorizes that composition.

## Daily execution authority

The Human Owner policy remains:

`MAXIMUM_FILLED_TRADES_PER_MARKET_PER_NEW_YORK_DATE = 1`

This is `OWNER_EXECUTION_POLICY`, not a TTrades source rule unless independently demonstrated in primary evidence. Multiple windows, C2/C3 candidates, entry families, protected swings, stops, or targets may coexist diagnostically while selected/pending/filled/terminal trade counts remain at most one for the market-day.

## Ambiguity containment

SMT, failure swings, T-spot and “expansion met with expansion” remain research concepts unless their executable algorithms are source-resolved. They are not mandatory filters in this revision.

## Economics gate

All economics from PR #518 and earlier VT-08 campaigns are forensic baselines only. A new economic result becomes admissible for research only after the R3.2 source model, split Trader authorities, market-day cardinality, adversarial causality tests, and the full Ruff/Mypy/Pytest quality gate are green on one exact software SHA.

This freeze grants no Risk authorization, `DEMO_ELIGIBLE`, broker submission, LIVE/Production authority, or real-capital authority.
