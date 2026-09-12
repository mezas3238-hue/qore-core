# VT-08 R3.8 H01 — Blinded DeepSeek Explorer PS/CISD adjudication

Status: RESEARCH ONLY / SOURCE QUESTION ONLY

This packet is intentionally blinded from economic outcomes. Do not provide DeepSeek Explorer with P&L, win rate, stop concentration, market/hour ranking, winner/loser labels, or any replay comparison until the source question is answered.

## Authority boundary

DeepSeek Explorer is an independent adversarial source witness. Authority remains:

1. primary VT-08 video + audio + visual evidence;
2. official TTrades sources;
3. DeepSeek Explorer independent adjudication;
4. QORE implementation.

No implementation change is authorized by this packet.

## Current R3.8 executable formalization to attack

For the narrow B01 research subset, QORE currently formalizes a protected swing inside Candle 2 as follows:

- identify an opposing M15 candle series after interaction with the relevant prior-H4 important level;
- retain the first opposing-series open as the CISD level;
- retain the series extreme as the candidate protected-swing price;
- require a later non-opposing M15 candle to close through the opposing-series open;
- require that the series extreme actually crossed the important level;
- if exactly one such protected swing exists, keep it; zero or multiple candidates abstain;
- historical research stop uses the protected-swing structural price with no execution offset, explicitly as a QORE containment because broker stop offset remains unresolved.

This formalization must be independently source-adjudicated, not defended from replay outcomes.

## Exact blinded questions

Inspect the primary VT-08 video/audio/transcript, extracted frames, and official TTrades protected-swing/CISD material and adjudicate:

1. After an important-level interaction, does the source require the **first** opposing candle series/open to define CISD, or can another later opposing series become the causal CISD/protected-swing reference?
2. Is CISD confirmation source-explicitly the first candle **close through the opening price of that opposing series**, or is another body/wick/level relation required?
3. When the opposing move contains multiple candles, is the protected swing source-explicitly the extreme of that complete opposing series, the candle that actually swept the important level, the broader Candle-2 extreme, or another structural point?
4. Does the source impose any explicit timing/latency condition between opposing-series formation, CISD confirmation, and the new-H4 entry? If no numeric timing rule is stated, classify that boundary unresolved rather than inventing one.
5. Does a longer multi-candle opposing series change the semantic quality/validity of the protected swing, or is duration irrelevant once the causal CISD is valid?
6. If multiple source-valid protected swings exist inside Candle 2, does TTrades specify which one has authority, or is QORE correct to abstain until source authority exists?
7. Is any stop buffer/offset beyond the structural protected-swing level explicitly specified for this methodology? Distinguish historical structural invalidation from broker execution offset.

## Required inspection

For each source example used, report:

- exact video timestamp/frame;
- important level shown;
- opposing candle series start/end;
- exact price/open/body/wick used as CISD reference;
- candle that confirms CISD and whether confirmation is by close, wick, or another condition;
- protected-swing price/provenance;
- entry timing relative to confirmation;
- any explicit treatment of multiple protected swings;
- any explicit stop offset/buffer.

If visual resolution cannot distinguish the relevant prices or candle boundaries, say so.

## Required classification

Classify each disputed rule as one of:

- `SOURCE_EXPLICIT`
- `SOURCE_VISUALLY_EXPLICIT`
- `SOURCE_SUPPORTED_FORMALIZATION`
- `QORE_OPERATIONAL_CONTAINMENT`
- `FUNDAMENTALLY_UNRESOLVED`

## Adversarial falsification

Try to falsify all of these competing models rather than choosing the most convenient one:

- `FIRST_OPPOSING_SERIES_OPEN_IS_CISD`
- `ANY_LATER_OPPOSING_SERIES_MAY_SUPERSEDE`
- `SERIES_EXTREME_IS_PROTECTED_SWING`
- `SWEEPING_CANDLE_EXTREME_IS_PROTECTED_SWING`
- `CANDLE2_EXTREME_IS_PROTECTED_SWING`
- `CLOSE_THROUGH_SERIES_OPEN_CONFIRMS_CISD`
- `TIMING_LATENCY_HAS_SOURCE_AUTHORITY`
- `MULTIPLE_PS_HAS_SOURCE_SELECTION_RULE`
- `STRUCTURAL_PS_HAS_SOURCE_STOP_OFFSET`

## Output constraint

Do not propose numeric latency cutoffs, distance thresholds, ATR filters, volatility filters, stop widening, alternative protected swings, or market/session filters unless they are explicitly supported by primary/official source evidence. If the source does not resolve a disputed dimension, preserve it as unresolved.

QORE must independently compare the returned adjudication against source and implementation before any pre-registration or methodology mutation.
