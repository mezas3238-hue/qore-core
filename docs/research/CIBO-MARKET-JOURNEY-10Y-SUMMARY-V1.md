# QORE CORE — CIBO MARKET JOURNEY 10Y SUMMARY V1

**Status:** CONSUMED RESEARCH EVIDENCE — DESCRIPTIVE ONLY  
**Raw M5 source run:** `35166210458`  
**Raw M5 source SHA:** `ab782b8e9f890f86a2b6500070f0556b4b685e3d`  
**Journey run:** `35175979474`  
**Journey SHA:** `9cc0f17a2f30846d61b242132547f39391909656`  
**Summary run:** `35200408430`  
**Summary SHA:** `2bdd2fb3e050322fea49b2030e6844e3c9a1f289`

## 1. Authoritative retained totals

- Retained canonical M5 bars: **8,726,985**.
- Journey episodes: **1,425,723**.
- Structure-touch rows: **2,919,269**.
- Daily-path rows: **37,393**.
- Cross-index Journey rows: **108,558**.
- `TRADER_MARKET_SYNC_LEDGER`: **0 rows** in the current run because no trader decision stream was linked to this corpus.

## 2. Per-market descriptive result

| Market | Episodes | CISD departure resolved | Opposite source boundary reached <=24h |
|---|---:|---:|---:|
| AUDJPY | 126,031 | 35.97% | 62.80% |
| AUDUSD | 126,755 | 34.84% | 64.36% |
| EURUSD | 126,098 | 34.70% | 65.47% |
| GBPJPY | 125,664 | 36.66% | 63.62% |
| GBPUSD | 125,669 | 35.53% | 65.38% |
| NAS100 | 110,471 | 35.36% | 68.06% |
| SP500 | 102,863 | 30.57% | 66.98% |
| US30 | 109,341 | 34.80% | 68.13% |
| USDCAD | 127,116 | 35.18% | 66.45% |
| USDJPY | 123,120 | 35.14% | 62.78% |
| XAGUSD | 110,670 | 33.49% | 66.26% |
| XAUUSD | 111,925 | 36.31% | 65.16% |

The current resolved-departure field means only that the frozen causal CISD detector resolved a departure. An unresolved departure does **not** mean that price did not later move.

The current target statistic is specifically the **opposite source boundary** encoded by the Behavior/Journey event. It is not yet a complete study of every contemporaneous DOL candidate.

## 3. Timing observations

Across the 12 markets, the median resolved latency from source liquidity raid to causal CISD departure is approximately **35 minutes**.

For NAS100 specifically:

- episodes: `110,471`;
- resolved CISD departures: `39,060` (`35.36%`);
- raid -> resolved departure median: `35m`;
- raid -> resolved departure p25/p75: `20m / 50m`;
- reclaim latency median: `5m`;
- opposite source boundary reached within 24h: `68.06%`;
- among reached boundaries, median time to touch: `165m`.

These are descriptive consumed statistics only. They do not create clock filters or entry rules.

## 4. Cross-index Journey — NAS100 / SP500 / US30

The aggregate contains `108,558` departure rows. Pairwise comparisons use the nearest peer departure inside a frozen `+/-120 minute` window. Lead/lag remains **E1 association only**.

| Source -> Peer | Comparable coverage | Direction agreement | Median absolute lag | <=15m | <=30m |
|---|---:|---:|---:|---:|---:|
| NAS100 -> SP500 | 86.45% | 79.12% | 10m | 60.88% | 71.21% |
| NAS100 -> US30 | 91.86% | 73.16% | 15m | 52.42% | 66.28% |
| SP500 -> NAS100 | 94.57% | 83.46% | 5m | 67.79% | 78.22% |
| SP500 -> US30 | 94.48% | 82.48% | 5m | 67.33% | 77.08% |
| US30 -> NAS100 | 92.39% | 73.94% | 15m | 53.40% | 67.33% |
| US30 -> SP500 | 87.06% | 79.47% | 10m | 61.47% | 71.23% |

The signed lead/lag median is `0m` for all six ordered pairs. This does **not** establish a causal leader. The current matcher is event-nearest, not yet a same-liquidity/same-structure causal matcher.

## 5. Current structure coverage

Current manifest state is:

`DETERMINISTIC_SUPPORTED_SUBSET_FAIL_CLOSED`

The populated Journey layer currently has deterministic observations for the frozen Behavior Lab subset, including:

- prior high / prior low source boundaries;
- three-candle swing high / swing low boundaries;
- liquidity raid;
- same-source reclaim;
- causal CISD departure when resolvable;
- source/opposite-boundary destination path;
- MFE/MAE-derived destination outcomes;
- daily continuous path measurements;
- nearest-departure cross-index association.

Anything not deterministically supported is kept unresolved rather than guessed.

## 6. Remaining Journey precision gaps

The following items are **not yet complete** and must not be claimed as complete CIBO knowledge:

1. Full deterministic structure chronology for order blocks, breakers, FVG/imbalance, displacement origin and other ICT structures is not yet populated as a complete universal ledger.
2. Equal/stacked-liquidity chronology is not yet materialized as a dedicated Journey structure family, even though Behavior Lab retains exact-equality measurements.
3. `TARGET_DESTINATION_LEDGER` currently studies the opposite source boundary; it does not yet retain every valid contemporaneous DOL candidate and later objective order required by the Journey freeze.
4. `DAILY_PATH_LEDGER` retains continuous range/path/overlap measurements, but generic regime labels, compression duration, expansion duration and first-material-expansion remain `UNRESOLVED_STRUCTURE`/null because no frozen universal threshold has been approved.
5. `TRADER_MARKET_SYNC_LEDGER` is empty. Historical trader decision streams must be linked separately; no synthetic trader history may be invented.
6. Cross-index matching is nearest departure within 120 minutes and therefore remains E1 association. Same-boundary / same-structure / same-timeframe matching and temporal replication are still required before any stronger mechanism claim.
7. Session-aware market-calendar classification remains separate from raw payload integrity; calendar gaps must not be mislabeled as missing provider data.

## 7. Governance

This evidence is consumed research evidence. It cannot be reused later as fresh OOS evidence.

`DEMO_ELIGIBLE=false`  
`LIVE_AUTHORIZED=false`  
`REAL_CAPITAL_AUTHORIZED=false`  
`PRODUCTION_AUTHORIZED=false`

No statistic in this checkpoint promotes a trader rule, target rule, weekday filter, time filter, market filter, cross-index leader, or execution authorization.
