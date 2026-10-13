# VT31 G5 — Dictamen SOURCE real de 30 horas Silver Bullet: 483.103 BID/ASK, M1↔BID exacto, SIN edge declarado

**Ejecutado y auditado 13 octubre 2026.** Owner authorized cTrader history research from QORE Native. NO firma G3, NO reconstrucción V1, NO replay económico, NO holdout nuevo, NO órdenes. Investigación exclusivamente de integridad/homologación **del precio** y cobertura de fuente.

## 1. Evidencia ejecutada, prereg y control de incidencia

**OLA 1 (6 horas, 2 días, 2024-06-12 y 2025-01-15):** [PR #899](https://github.com/mezas3238-hue/qore-core/pull/899); prereg commit `e4835cce13f19e1787b0ec24bad330a13832e471` antes de quotes. [Run #38374757273 PASS](https://github.com/mezas3238-hue/qore-core/actions/runs/38374757273), source artifact [#11801205225](https://github.com/mezas3238-hue/qore-core/actions/runs/38374757273/artifacts/11801205225), ZIP digest SHA256 **`7c599294f3853c684f05ee17941b530f35b80bee832e115f51d3d5ff6c3c6f03`**. Manifest 6/6 hours, 20 native queries, 49.661 BID+49.661 ASK=**99.322 source ticks**; 25/25 internal SHA256 file hashes correct.

**OLA 2 CORREGIDA (24 horas, 8 días, febrero 2024 a abril 2025):** [PR #901](https://github.com/mezas3238-hue/qore-core/pull/901); prereg **`08bd4e24b23f8faa02fdbbf51f11e59b5cd518cd`** committed BEFORE source. [Run #38377233495 PASS](https://github.com/mezas3238-hue/qore-core/actions/runs/38377233495) code SHA **`6079ea713177455415c4591a8ad81ef29875ce2a`**, artifact [#11801263502](https://github.com/mezas3238-hue/qore-core/actions/runs/38377233495/artifacts/11801263502), ZIP SHA256 **`a0cb3e62f2c889b414e7283d7d426576468e753b34f60351d0c9aa1965fc1edf`**. Manifest reports 24/24 hours, **191.877 BID +191.904 ASK=383.781 source ticks**, 72 native provider queries; 97/97 internal SHA256 file hashes correct. This artifact is NOT in public Git tree, expected to expire **2027-01-11**.

**BLOQUEO DE REPETICIÓN DETECTADO Y REPARADO:** first wave2 workflow run [#38376936002](https://github.com/mezas3238-hue/qore-core/actions/runs/38376936002) was GREEN **but mistakenly invoked wave1 `vt31_g5_ustec_sb_quote_capture_v1`** and produced exactly the original six-hour sample, ZIP SHA `040f254f49c256d450f6b9758b95318ce1264099eac8d49eadece06a0f8bab72`. This is a **DUPLICATE, zero new observations**, excluded completely from counters. Fixed workflow line in commit `6079ea713177455415c4591a8ad81ef29875ce2a`, re-executed correct module `vt31_g5_ustec_sb_quote_wave2_v1`; inspected 24h manifest and distinct days. A GREEN CI without source manifest audit is NOT proof of new data.

**TOTAL SOLO DATOS ÚNICOS:** **241.538 BID +241.565 ASK =483.103** tick-side updates, **30/30 hours NY Silver Bullet on 10 distinct development days**, **92 broker native side requests**, two mutually distinct source ZIP digests. Source IC Markets cTrader DEMO exact USTEC symbolId10014, alias NAS100 provisionally, contract NAS100↔USTEC↔NDX100 NOT homologated.

## 2. Testigo cruzado independiente: original VT31 NAS100 3Y M1 vs USTEC BID

Original consumed development 3Y 2023-10-01 to 2026-10-01, source [artifact #11459859004](https://github.com/mezas3238-hue/qore-core/actions/runs/38018856150), `NAS100/market-evidence.json` **SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`**, 1.059.784 M1 in original source. Downloaded original ZIP and recomputed SHA256 directly from member bytes (MATCH). Scanned original M1 and extracted **30 full source hours = 1.800 minute bars**, chosen BEFORE downloading quotes. For each historical M1 minute, aggregate side-REAL cTrader USTEC **BID** ticks strictly in `[opened_at, closed_at)` without touching a future quote. Compare OHLC of M1 against first/max/min/last BID tick *within same minute*.

| Exact match | n/1800 |
|---|---:|
| M1 High == max BID tick of minute | **1800/1800** |
| M1 Low == min BID tick of minute | **1800/1800** |
| M1 Close == last BID tick of minute | **1800/1800** |
| M1 Open == first BID tick of minute | **1789/1800** |
| Minute availability | **1800/1800** |

All **11 open mismatches** occur on 2025-04-16 (London 7, NY AM 1, NY PM 3). Preserve them as source discrepancies; no imputation or rewriting M1. This is strong empirical sampled **price-stream continuity** between original NAS100 M1 and archived USTEC historical BID, superior to guessed alias. Does NOT prove economic contract identity, account equality, quote executability, previous-side receipt timestamps, or broker fills; quoted history and trendbars may come from the same upstream engine.

## 3. Real BID/ASK side quality — as-of 5s event-time pairing, NOT fills

Independently re-read all original source ZIP integer JSONL (not summary-only). Sorted union BID and ASK event timestamps for each of 30 hours, carry latest observed prices independently by side, classify `MISSING_SIDE`, `STALE_SIDE` (>5s), `CROSSED` (ASK<BID), `ZERO`, `POSITIVE`. Per timestamp sequence contains no duplicate same-side ms; event-time-only reconstruction cannot certify independent delivery/visibility `received_at` or actual tradeable quotes.

- **242.554 unique source event instants**.
- **242.552 with positive source spread**, **2 CROSSED (QUARANTINE)**; **0 same-event zero**, **0 stale or missing at recorded event instants**. Both crossed events on **2025-04-16 NY PM**.
- Recorded *source-event* positive spread **min 0.30, median 0.80, p95 1.40, p99 2.00, max 8.40 index pts**. These are **descriptive source feed prices**, not cost assumptions for a trader; do not substitute any percentile into NET model without broker contract and chronology.
- **184** gaps between sequential BID events >5s over the 30 hours, despite zero `STALE_SIDE` at actual union events; sample-grid (e.g. every 1s) exposure cannot be called 100% continuous. **25/30 hours** have identical full BID vs ASK event timestamp sequences; the five remaining hours include asynchrony, so do not assert streams always identical or spreads always fixed. Some hours show constant synthetic-looking spreads: NEED source interpretation before fills.
- Price and source time exactness above do NOT prove liquidity size, matching engine acceptance, limit CE fill, broker order ACK, entry or exit execution, adverse slippage, fees, or executable commission regime.

**Crucial:** original VT31 M1 **is BID-aligned, NOT MID** on 1800/1800 close/high/low samples. Thus the previous directional 3Y screen using `M1` as MID ±0.80 spread (PR #874) remains **a hypothetical cost stress only** and its net scenario cannot be relabeled broker-real. The **gross directional return** result for that distinct proxy is unchanged; do not rerun/tune its model retroactively or claim this finding validates a CE LIMIT strategy.

## 4. Gate verdict

**`G5_DEV_SOURCE_PRICE_LINEAGE_STRONGLY_SUPPORTED_30H`**; **`G5_EXECUTABLE_QUOTES_AND_CONTRACT_UNVERIFIED`**; **`VT31_CE_NET_EDGE_NOT_IDENTIFIED`**; **`G3_PENDING_DUAL_SIGNATURE`**.

Next: freeze and audit 11 M1 open discordances, 2 crossed quotes and same-time/fixed-spread provider semantics. Exact contract symbol lot/tick/point currency, commission/swap/slippage, 15:55 NY exit quote *outside Silver Bullet source hour*, cancelled orders and OMS missing. For actual CE-limit PnL, requirement includes **entry-window ticks PLUS all post-entry SL/TP/time-exit ticks** (15:55 NY), not merely 30 source hours. Develop licensed durable vault to avoid 90d expiration [#837](https://github.com/mezas3238-hue/qore-core/issues/837) before full 3Y bulk; source identity #857; cross-source anomalies #856. Do not open holdout.

G3 document `a446afa17ed6e411b8f0b6fc182b103a78959a97` and MSS code `78d4cdac0e09d1a6eef37b99c505ffc5098031fc` unchanged. No dual signatures fabricated; no PAPER/NET, PF or DD certified.
