# Turtle Soup Candidate R5 — Classic Tick-Resolution Freeze

Status: **FROZEN BEFORE TICK-RESOLVED ECONOMIC OUTCOMES**

Research identity: `turtle-soup-candidate-r5`

Parent evidence: `turtle-soup-candidate-r1` final Forensics.

Canonical trader code: `CODE_UNASSIGNED`

## 1. Why R5 exists

R1 Classic remained dominated by unresolved causal ordering even after the governed native-M1 refinement:

- 14 deterministic fills;
- 293 cases still `M1-INTRABAR_PATH_AMBIGUOUS`;
- three additional M1 data-resolution limitations;
- the 14 resolved trades were all losing and the available forward sample was insufficient for advancement.

R5 does not alter the Classic trading method. It tests whether the 293 still-ambiguous source opportunities can be resolved from historical **BID tick data** rather than discarded or assigned an invented intraminute path.

## 2. External API capability

Current cTrader Open API documentation exposes historical tick retrieval through `ProtoOAGetTickDataReq` / `ProtoOAGetTickDataRes`. Historical tick requests specify account, symbol, BID/ASK quote type and from/to timestamps. One request window cannot exceed one week; `hasMore` indicates pagination when the backend response is truncated. R5 requests only one-minute windows.

R5 uses `ProtoOAQuoteType.BID = 1` to remain price-side consistent with the R1 BID-bar evidence.

## 3. Target selection is frozen without P&L

Targets are generated exclusively from the final R1 state:

`Classic source opportunity -> M15 ambiguity -> exact M1 refinement -> still M1-INTRABAR_PATH_AMBIGUOUS`

No winner/loser state, realized R, management policy, market ranking, side ranking, fold performance, or fresh-OOS price is used for target selection.

Frozen target census:

- EURUSD: 40
- GBPUSD: 47
- USDJPY: 35
- AUDUSD: 43
- USDCAD: 43
- GBPJPY: 44
- AUDJPY: 41
- total: **293 one-minute intervals**

Each target file contains only the exact UTC minute and source side needed to retrieve evidence. The source reference, trigger and incoming state are re-derived from the already-governed R1 D1/M15/M1 evidence during replay.

Frozen per-market target-file digests:

- EURUSD: `5edd16218e2467e98d50b82dc3ea684ef84c33e5e3c7df3fb7e4f2780100e278`
- GBPUSD: `e2cf6e0a940f3f15af53636d4242db7f20b24573633abac4031f2c096fd180e5`
- USDJPY: `aaccc53f2e0898969ac2afcd6731cf80d9bafdff0aa907f25ab93557bd11066a`
- AUDUSD: `ff302921c7348e34d178b794205beffbfbb10326e28ac2c9c34c92f9441151f1`
- USDCAD: `064b10085245fb482402e444c80a6ed1b71a4c568e5175991fa6b7f92a7db194`
- GBPJPY: `37efadfd2eddd330db70230465bb38a6412308b9e167700b0ddc074b1923978c`
- AUDJPY: `761e85459341ccde8a7c7a1253655659472d495264cbc8e5057856027f796a94`

## 4. Tick evidence contract

For every frozen minute R5 requests BID ticks from exactly:

`minute_opened_at <= tick_timestamp < minute_opened_at + 60 seconds`

The collector must:

1. authenticate through the existing read-only cTrader boundary;
2. resolve the exact enabled symbol;
3. request quote type BID only;
4. paginate when `hasMore = true` without crossing the frozen minute;
5. reconstruct cTrader delta timestamps into absolute UTC milliseconds;
6. retain ticks in chronological order;
7. reject contradictory duplicate timestamp/price evidence;
8. preserve equal-timestamp groups rather than invent an order that the timestamp cannot establish;
9. emit exact software SHA, target-file digest, account fingerprint and evidence SHA-256;
10. perform no order/trading mutation.

An empty response is valid evidence of `TICK_DATA_UNAVAILABLE` for that minute; it is not filled from another source.

## 5. Resolution discipline

Tick evidence may refine a targeted M1 minute only when its observable price range is compatible with the retained M1 BID OHLC and the causal event ordering can be established from chronological ticks.

If historical tick retention is unavailable for an old minute, if the tick sequence cannot reconcile sufficiently to the M1 evidence, or if decisive prices occur at the same timestamp without an observable order, the opportunity remains censored.

No synthetic tick, interpolation, random intrabar path, OHLC path assumption, or winner-favoring tie break is permitted.

## 6. Economic rules remain R1 Classic

If tick evidence resolves a Classic setup, it receives the same R1 source entry, initial stop, cost schedule and four already-frozen experimental management policies. R5 does not add an entry filter or a new management parameter.

Primary cost remains 1.0 bp and stress remains 2.0 bp. The six R1 forward folds and strict advancement gate remain unchanged.

## 7. Fresh OOS remains closed

`FRESH_OOS_EMBARGO_START = 2026-03-01T00:00:00Z`

All 293 targets are strictly pre-embargo. No post-embargo price data may be requested or consumed by R5.

## 8. Decision rule

If tick data cannot materially resolve the historical ambiguity population, Classic is rejected for the current data stack rather than guessed.

If tick data resolves enough opportunities to produce the preregistered forward sample, Classic must still pass the same absolute forward gate; resolution alone is not evidence of edge.

No FTMO/FundedNext/LIVE authority is granted by this data-resolution campaign.
