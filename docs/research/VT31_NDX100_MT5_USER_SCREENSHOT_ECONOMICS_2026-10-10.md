# VT31 ICT cleanroom — owner-supplied MT5 execution facts (NDX100 0.01 lot)

**Evidence received:** 2026-10-10, two user-provided mobile MT5 History screenshots of the SAME account/transactions (one expanded, one collapsed). This is **one NDX100 closed operation**, NOT two independent samples. Screenshot paths are private chat attachments, not published in GitHub. Ticket/order IDs are intentionally not copied. No broker name or account currency is visible to independently verify. Evidence is limited to displayed **closed-position records**, not a historical bid/ask tick archive or an MT5 `symbol_info` response. **Research only / no LIVE.**

## Screenshot transcription (reported values in unknown account currency, USD only if separately confirmed)

| Closed operation | Side / lots | Entry execution | Exit execution | Reported gross result | Reported commission |
|---|---|---:|---:|---:|---:|
| **NDX100** | **BUY 0.01** | **30852.60** | **30848.08** | **−0.45** | **0.00** |
| EURUSD | SELL 0.01 | 1.13455 | 1.13439 | +0.16 | −0.07 |
| GBPJPY | BUY 0.01 | 209.522 | 209.503 | −0.12 | −0.07 |
| AUDJPY | BUY 0.01 | 110.471 | 110.454 | −0.11 | −0.07 |
| XAUUSD | BUY 0.01 | 4185.46 | 4185.11 | −0.35 | −0.07 |

Display-time of NDX100 exit: 2026-10-09 17:35:18 as presented in mobile MT5 history. Display timezone/server timezone NOT independently known; do not map these timestamps to NY-clock source windows without a verified server/timezone offset. The screenshot NDX100 opening/closing executions are transacted deal prices, NOT a paired contemporaneous bid-and-ask quote observation.

MT5 account summary reconciliation from the five visible closed records:
- Initial deposit: **2,000.00** on 2026-09-14.
- Sum of displayed GROSS closing results = **−0.87**.
- Sum of displayed commissions = **−0.28** (four non-NDX symbols show −0.07; NDX100 shows 0.00).
- `2,000.00 − 0.87 − 0.28 = 1,998.85`, exactly reported **Balance 1,998.85**.
- The history header `Beneficio: 1,999.13` reflects the gross figure after the initial deposit and shown closed gross P&L, NOT profit of 1,999.13.

## NAS100/NDX100 point-value empirical calibration — **NOT a broker contract**

On NDX100 `BUY 0.01`, signed change `30848.08−30852.60 = −4.52 index points`. Closed gross `−0.45 account-currency units` implies a point-move effect `−0.45/−4.52 ≈ 0.0995575221 account-currency units per index point for **0.01 lot**`. Per nominal full lot, assuming linear scaling for this *same verified symbol*, the empirical ratio would be `≈ 9.9557522` account-currency units per point. Given displayed prices and P&L rounded to two decimals, a provisional nominal model **10 units per index point per 1.00 lot** predicts `(−4.52)×0.01×10 = −0.452`, which displays as **−0.45**. This is **consistent**, but does not uniquely establish the official `trade_contract_size`, tick size/value, `SYMBOL_TRADE_CALC_MODE`, account currency, market-execution fill tolerance, or lot steps.

**Observed NDX100 commission 0.00 in this ONE completed sample.** Do NOT transfer the −0.07/0.01 lot commission seen on FX/gold to NDX100. Conversely, do NOT assert zero NDX100 commission for every time, volume tier, account or broker based on one sample, or infer precise *opening-side versus closing-side* posting timing.

## What this evidence fixes versus what remains blocked

New code `src/qore/infrastructure/traders/vt31_ict_cleanroom/observed_broker_economics.py` and direct tests `tests/infrastructure/test_vt31_ict_cleanroom_observed_broker_economics.py` provide an explicitly **non-authoritative, research-only** NDX100 observation; they reproduce the five-trade balance and detect potential cross-asset fee contamination. This is an empirical anchor for future QDLE/MT5 broker configuration verification, NOT a currently enabled lot engine. Strategy label `NAS100` is not automatically the same contract as the actual broker symbol `NDX100`. A canonical broker mapping must be verified using MT5 instrument properties and broker account details.

To run a **true 3Y changed-execution VT31 PAPER replay**, still REQUIRED:
1. Account currency + correct broker/server + exact `symbol_info(NDX100)`: `trade_contract_size`, `trade_tick_size`, `trade_tick_value`, `volume_min`, `volume_step`, `volume_max`, margin/execution mode, stop levels; ideally observed `order_calc_profit` comparison.
2. Timestamped NAS100/NDX100 bid/ask **tick** history or equally verifiable historical executable quotations for the same exact broker symbol, with timezone mapping; screenshot gives only two executed prints for ONE trade, no spread or 3Y tick history.
3. Explicit commission schedule and whether NDX100 or other symbols charge at OPEN, CLOSE or roundtrip, together with swap/slippage, broker account-type context; NDX100 sample gross `−0.45` and fee `0.00` cannot calibrate every future month.
4. A QDLE-only lot sizing/real risk validation and one-VT31 CIBO portfolio exposure book in PAPER; bid/ask limit match and stop/target chronology; proper price-level trading R and drawdown. Do not infer `filled` from M1 OHLC price crossing.

**Frozen 3Y original ICT cleanroom remains:** one VT31, London + New York as internal sessions; M1 primary MSS/FVG, higher timeframes context only. Previous [3Y real source replay](https://github.com/mezas3238-hue/qore-core/actions/runs/38018856150) verified causal COG+OPS sensors and **0 pending sources without COG**; prior [offer audit](https://github.com/mezas3238-hue/qore-core/actions/runs/38018602495) emitted 2,140 candidate-source offers **not fills**. None of these 2,140 become confirmed broker orders from this single MT5 screenshot. Fresh holdout untouched, live authority FALSE, PF/DD still unavailable.

**Coordination:** Share with Architect 1 via [Issue #727](https://github.com/mezas3238-hue/qore-core/issues/727); Architect 2 OPS owns the broker evidence, order contract and economic integration. Do not publish screenshot/account identifiers without user request or scrub. 
