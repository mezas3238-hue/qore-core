# VT-08 V3 — CRT 1-5-9 source freeze

Status: **research-only / no DEMO authority**

VT-08 V3 is a new additive methodology candidate. VT-08 V1 and VT-08 V2 remain unchanged historical/research lineages.

## Primary evidence supplied by the Human Owner

The source package consists of three uploaded videos. The binaries are not committed to the repository; their immutable SHA-256 identities are:

- `9968f10cee6b5c94d7406c3cdc31bef2623221a5a6e6529f7b4293c1bbe97664` — 2066.297324 seconds.
- `fceacd2b59039bc94aea3b7390804c1c68f1ac10b1e7bc3e318a7645d867a5ee` — 1477.392834 seconds.
- `57206b5c3e48a2281b4648da7c69b1c20c39ea5c1edd34c689a1a9080341c225` — 984.804717 seconds.

Observed source concepts include CRT range construction, liquidity sweep/re-entry, the four common CRT candle-range models, the explicit H4 `1-5-9` sequence, a higher daily range that remains to be fulfilled, nested H1 confirmation, and M15 entry refinement. M5/M3 is shown as an optional sniper refinement.

Public corroboration used only to resolve terminology—not to override the supplied videos—includes the video `Este Nuevo Método De Trading Está Cambiando Vidas (CRT)` and TradingForexSP's CRT educational material describing CRT as a range/liquidity-sweep model with multi-timeframe nesting.

## Deterministic V3 operationalization

The videos teach a discretionary visual method. They do **not** uniquely specify every machine-level edge case. V3 therefore freezes the following falsifiable choices rather than pretending they are direct quotations from the source:

1. Use the last two fully closed provider D1 candles before the H4 `01:00` New York candle as the higher-timeframe reference and manipulation pair.
2. A valid CRT manipulation sweeps exactly one edge of the reference candle and closes strictly back inside its high/low range.
3. H4 `01:00-05:00` New York is the reference candle; H4 `05:00-09:00` is manipulation; H4 `09:00-13:00` is distribution.
4. Inside the H4 distribution candle, H1 `09:00-10:00` is reference and H1 `10:00-11:00` is manipulation.
5. Inside the next H1 distribution hour, M15 `11:00-11:15` is reference and M15 `11:15-11:30` is manipulation.
6. D1, H4, H1 and M15 must all imply the same CRT direction. Any disagreement causes abstention.
7. Entry is the open of the next M15 candle at `11:30` New York. This is lookahead-safe and represents the source's third-candle distribution concept without inventing an unseen intrabar fill.
8. Stop is the M15 manipulation extreme. Primary target is the opposite edge of the H4 `01:00` reference range. The opposite D1 edge is retained as an outer contextual target for Story Forensics.
9. The research opportunity expires at `13:00` New York, the end of the source H4 distribution candle. If neither stop nor target has resolved, the trade is censored rather than assigned an invented exit.
10. Same-bar stop and target uses conservative stop-first resolution.

## Research governance

- Eleven Core markets: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, XAUUSD, NAS100, SP500, GBPJPY, AUDJPY and US30.
- Long-horizon broker evidence: at least 730 days, using cTrader DEMO read-only M15 plus provider D1.
- Chronological 70/30 IS/OOS packaging; OOS is consumed for this research cycle.
- Stress and Monte Carlo are descriptive research evidence only.
- Story Forensics keeps decision-time evidence separate from post-outcome oracle fields.
- Parameter search is prohibited in this source-frozen V3 campaign.
- Any methodology change after observing OOS requires preregistration and a fresh previously unseen holdout.
- No CI result, backtest result, Stress/Monte Carlo result or economic screen grants `DEMO_ELIGIBLE` without the governed authority chain.
