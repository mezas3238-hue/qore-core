# ICT Turtle Soup R4 — pre-holdout candidate freeze

Date: 2026-09-16

Identity: `ICT_TURTLE_SOUP_R4_D1_IDEAL_C2_H1_CISD__H4_IDEAL_C2_M15_CISD__POSITIONAL_DAILY_DOL`

Status: frozen before fresh evidence access. No DEMO/live/real-capital/production authority.

## Source contract

This candidate implements the selected ICT/TTrades family exactly as adjudicated before economics:

1. Turtle Soup is the liquidity-raid / failed-breakout event, not a clock filter.
2. Forex source day opens 17:00 America/New_York, DST-aware.
3. Forex H4 source candles open 17:00, 21:00, 01:00, 05:00, 09:00, 13:00 New York.
4. Daily reversal family is **Ideal Candle 2** only:
   - LONG: Daily C2 low < Daily C1 low and Daily C2 close > Daily C1 low.
   - SHORT: Daily C2 high > Daily C1 high and Daily C2 close < Daily C1 high.
   - H1 must produce causal CISD inside the same Daily C2 through the exact opposing delivery series that created the Daily C2 extreme.
   - The Daily C2 extreme becomes the Daily protected swing.
   - Daily C3 is the expansion day. Ideal C3 -> C4 is a different candidate and is excluded.
5. Inside Daily C3, H4 uses the same Ideal C2 family:
   - the H4 C1 must be the current relevant extreme of the Daily C3 wick up to that point;
   - H4 C2 must sweep that C1 extreme and close back inside C1;
   - M15 must produce causal CISD inside the same H4 C2 through the exact opposing series that created the H4 C2 extreme;
   - the H4 C2 extreme becomes the H4 protected swing before H4 C3 opens.
6. Entry is the H4 C3 open (positional entry). No retracement optimization.
7. Stop is one native tick beyond the H4 protected swing. This one-tick discretization is QORE execution semantics; no pip/ATR buffer exists.
8. Target is frozen pre-entry untouched Daily liquidity in the bias direction. No rigid weekly/daily/session rank and no fixed R multiple exists.
9. Primary DOL is the nearest eligible untouched completed Daily high/low in the bias direction. Same-price levels are stacked labels; materially unresolved ties fail closed.
10. Asia, London, New York and other clock buckets are metadata only. There is no session inclusion/exclusion rule.
11. There is no minimum projected-R gate.
12. Dojis are neither up-close nor down-close and break an opposing series.
13. Missing source candles fail closed; no interpolation.
14. If entry opens through protected swing or through already-consumed DOL: no trade.
15. After entry, a gap through stop fills at observed open; favorable gap through target is capped at target.
16. Same M5 touches stop and target with no lower-resolution evidence: STOP_FIRST.
17. Re-entry is source-underdetermined: first qualifying H4 Ideal C2 only per Daily C3; no re-entry that day.
18. Frozen lifecycle for this candidate: target or protected-swing invalidation first; if neither occurs, close at the end of Daily C3. This is QORE formalization tied to the selected Daily-C3 expansion information set and is not claimed as a universal ICT rule.

## Fresh holdout

Frozen interval:

- acquisition/warm-up: `2018-05-01T21:00:00Z`
- evaluation open: `2018-07-02T21:00:00Z` (17:00 New York, 730-day boundary)
- evaluation close: `2020-07-01T21:00:00Z` (17:00 New York)
- exact evaluation span: 730 days
- symbols: AUDJPY, AUDUSD, EURUSD, GBPJPY, GBPUSD, USDCAD, USDJPY
- provider: existing cTrader DEMO read-only historical market-data connection
- raw execution evidence: M5, from which source-bound H4/H1/M15/Daily candles are deterministically reconstructed at the frozen New York boundaries.

Repository evidence audit before access:

- `[2020-07-01, 2022-07-01)` is consumed by ICT Turtle Soup R2/R3 and VT-08 retained evidence.
- the 2022-2024 Forex fresh-holdout line is also consumed by VT-08.
- repository code search, issue search and PR search found no documented 2018/2019 exposure for this ICT Turtle Soup line before this freeze.
- therefore the interval is classified as `FRESH_RELATIVE_TO_DOCUMENTED_REPO_EVIDENCE`, not as a claim that no human has ever viewed those market years.
- if the provider cannot supply the frozen interval, the run must fail. No replacement interval is authorized after the failure.

## Comparator

The workflow may compute a **legacy R3-like signal count on the exact same fresh evidence** only to answer whether the reconstruction changes the number of trades. The comparator is diagnostic only and cannot change R4 mechanics, select a subgroup, authorize post-hoc tuning, or become an alternative candidate.

## Friction and replay

- gross R is reported.
- primary friction: `0.05R/trade`.
- stress friction: `0.10R/trade`.
- STOP_FIRST for unresolved same-M5 ordering.
- no BE, trailing, partials or re-entry.

## Advancement governance

This holdout is one-shot evidence. Once any economic output is exposed, the interval is consumed for R4.

No result can authorize a mechanics change under the same identity. Any changed mechanics require a new identity and different untouched evidence.

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`
