# QORE Native G1 — 6 research E1 opportunity entry/target-close original native Protobuf results

**Date 2026-10-12, source-only. No economic trade inference.** [E1 original event clock source ledger PR #864](https://github.com/mezas3238-hue/qore-core/pull/864), [run #38293096998](https://github.com/mezas3238-hue/qore-core/actions/runs/38293096998) SUCCESS proved that in 5 markets and 2 historical dates, exactly 56 original E1 7-method research opportunities were present but previous 13:00–13:30 native quotes overlapped **0/56** complete entry+theoretical M5 target-close clocks. That identified six actual original E1 research opportunities starting 13:00 UTC and theoretically closing at 15:00 UTC after 24 M5 bars.

## Original sources and chain-of-custody

- [PR #865](https://github.com/mezas3238-hue/qore-core/pull/865), [GitHub Actions #38293565282](https://github.com/mezas3238-hue/qore-core/actions/runs/38293565282): **6/6** IC Markets cTrader DEMO source captures complete; source code SHA `7b7cd8339a4a1d135f531db90fd3931213708de4`, artifact [#11767003876](https://github.com/mezas3238-hue/qore-core/actions/runs/38293565282/artifacts/11767003876) ZIP SHA256 `01075ecd534de104caf4fb8702aebef86468b611aafb5fcec366722ac12eea9b` (temporary Actions retention to ~2027-01-10). Frozen dates and symbols BEFORE capture commit `f053be5188bceea0325db61829fb60c9790e54f6`.
- Actual source windows for **each** of six signed E1 research events: entry-side [12:55,13:05) UTC and target-close-side [14:55,15:05) UTC, historical date 2021-03-16 or 2023-03-21. Native original `ProtoOATickData` field bytes (account wrapper excluded), BID and ASK requests separate, binary page SHA and hasMore, raw integer price 1e5 and decimal witness. No new signals or PnL.
- [PR #866](https://github.com/mezas3238-hue/qore-core/pull/866), independent second audit [GitHub Actions #38294099883](https://github.com/mezas3238-hue/qore-core/actions/runs/38294099883) **SUCCESS**: Ruff, 6/6 synthetic negative tests, original E1 4 source artifact ZIP SHA + code `dfe78f115957a40f4188c30e78bd7f88c2ce6c42`, original native source ZIP SHA, 6 event IDs, all 13 original files per event SHA, field Protobuf decodificado independientemente con signed TIME+PRICE and hasMore partition exacto. [Source QA report #11767229334](https://github.com/mezas3238-hue/qore-core/actions/runs/38294099883/artifacts/11767229334), ZIP SHA256 `f8906269cf04a56aed8e6803ed540f636f141f9953fde588de9b9293914ee132`. **13.445 ticks integer source originales procesados**, parte solapa la muestra previa 2021/2023 de [13:00–13:05), NO sumar como observaciones estadísticamente independientes ni deduplicación aún.

## Findings over EXACT historical E1 research clocks

**Causal source gate**: at **13:00 UTC** and **theoretical** E1 24-bar M5 horizon close at **15:00 UTC**, the last known BID and ASK must exist with each side age <=5 seconds, ASK > BID and no future-price substitution. If zero/stale/crossed/absent => SOURCE BLOCKED (not a losing trade). Results from identical genuine native provider tick fields:

| Original E1 method / broker source candidate | UTC date | 13:00 entry quote | 15:00 theoretical M5 close quote | Pair result |
|---|---|---|---|---|
| SP500→US500, SWEEP_RECLAIM | 2021-03-16 | **STALE_SIDE** | OK positive | BLOCK |
| SP500→US500, SWEEP_RECLAIM | 2023-03-21 | OK positive | OK positive | SOURCE PASS |
| GBPUSD, RANGE_BREAK_CONT | 2021-03-16 | **ZERO_SPREAD** | **ZERO_SPREAD** | BLOCK |
| USDJPY, RANGE_BREAK_CONT | 2021-03-16 | **ZERO_SPREAD** | **ZERO_SPREAD** | BLOCK |
| USDJPY, SWEEP_RECLAIM | 2023-03-21 | OK positive | OK positive | SOURCE PASS |
| XAGUSD, SWEEP_RECLAIM | 2023-03-21 | OK positive | OK positive | SOURCE PASS |
| **TOTAL** | | **3 OK / 2 ZERO / 1 STALE** | **4 OK / 2 ZERO** | **3/6 PASS, 3/6 BLOCK** |

This is the first verified source-only bidask-at-original-E1-two-clock bridge on these six research opportunities. It is **NOT** an E1 execution-backtest result or model profitability, and it does not demonstrate availability across the originally studied eight years. For the three source-eligible events original broker account contract value/tick/fee equivalence **unproven**; all were E1 *theoretical target horizon closes*, not broker stop/target/exit orders. E1 event signs and post-decision gross outcomes were not exported, no real fills, news point-in-time, slippage, commission, swap, margin or funding. Alias SP500→US500 likewise requires original-CIBO contract adjudication.

## P0 follow-up for scientific promotion (not production)

1. Solve zero spread semantics [Issue #856](https://github.com/mezas3238-hue/qore-core/issues/856): original Protobuf confirms BID=ASK in the two 2021 E1 opportunities; the issue is source/executability, not SDK decoding. No ZERO→free cost.
2. Verify old CIBO broker original 12 source instruments vs IC Markets DEMO contracts, particularly SP500/US500, [Issue #857](https://github.com/mezas3238-hue/qore-core/issues/857).
3. Build signed causal E1 event ledger for **all 33×7** results with **bounded source sharding** around research entry/target-close time and a private licensed storage quota; do not blindly fetch millions of cTrader tick requests, [Issue #863](https://github.com/mezas3238-hue/qore-core/issues/863), [#837](https://github.com/mezas3238-hue/qore-core/issues/837).
4. Only after deterministic source availability, broker commission per symbol/size/period, slippage, swaps, financing, news PIT, execution simulators and embargoed holdout rules could historical NET be measured. The 231 original gross Holm/FDR/E3 designs have **zero positive replicated edge** and **0/3 traders certified**.
5. Preserve E1 old source SHA `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`, original method SHA and causal DST. Research draft only; no VPS/MT5/LIVE/CIBO/Shared/QDLE change.
