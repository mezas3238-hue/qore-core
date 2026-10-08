# P0 OVERRIDE · 2026-10-08 · EL RIESGO ES 5% DINÁMICO, NO USD 3 FIJOS

**DOCUMENTO HISTÓRICO SUPERADO EN POLÍTICA DE RIESGO.** Leer primero el nuevo handoff maestro canónico:
[`docs/research/CIBO_P0_MASTER_CONTINUITY_HANDOFF_2026-10-08_DYNAMIC_5PCT_MT5_LOTAGE_AND_SOLVENCY.md`](./CIBO_P0_MASTER_CONTINUITY_HANDOFF_2026-10-08_DYNAMIC_5PCT_MT5_LOTAGE_AND_SOLVENCY.md).

**Regla vigente e implementada en rama `agent/cibo-p0-dynamic-equity-5pct-lotage-002`:** `0.05 * min(latest_causal_equity, latest_realized_balance)` antes de cada nueva entrada. USD60→USD3; USD100→USD5; USD1000→USD50; los topes agregados también escalan. Ejecución sigue NO CERTIFICADA sin VPS MT5 auténtico, sin broker-state reconcilation ni replay 3 años dinámico. Última suite CI **50 PASS**: https://github.com/mezas3238-hue/qore-core/actions/runs/37814146300.

---

> **OVERRIDE P0 — 2026-10-08: REGLA DE LOTAJE DINÁMICO DEL USUARIO**
> Esta versión contiene referencias históricas a USD 3 FIJOS que ya han sido REVOCADAS como política vigente. **CIBO ahora calcula 5% del capital causal de la cuenta POR CADA NUEVA ENTRADA**: USD60→USD3, USD100→USD5, USD1.000→USD50. Escala hacia arriba y hacia abajo, sin inventar lotes ni margen. Mantener advertencia H8 de solvencia NO CERTIFICADA.
> **HANDOFF MAESTRO ACTUAL OBLIGATORIO:** [CIBO P0 5% dinámico](docs/research/CIBO_P0_MASTER_DYNAMIC_5PCT_LOTAGE_CONTINUITY_HANDOFF_2026-10-08.md). Rama: agent/cibo-p0-dynamic-equity-5pct-lotage-002. Pruebas CI: [50/50 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/37814146300). Replay causal y MT5 real pendientes. No promover a producción.

# QORE CORE — P0 MASTER HANDOFF: FUNDEDNEXT MT5 REAL LOTAGE / SIZING · CIBO COMPOUND · ADAPTIVE LEVERAGE · COMPOUND PORTFOLIO

**2026-10-08 · Repo `mezas3238-hue/qore-core` · research branch `agent/cibo-p0-fundednext-real-mt5-lotage-financing-001`**
**STATUS: FIRST IMPLEMENTATION + UNIT/INTEGRATION TESTS SUCCESS, HISTORICAL 3368 INPUTS AUDITED. LIVE SERVER SPEC / EXECUTION REPLAY / FUNDABILITY CERTIFICATION REMAINS BLOCKED. NO PRODUCTION DEPLOYMENT.**

## P0 directive — what must NEVER be confused again

The Trader originates symbol, entry, side, SL/TP. CIBO must return a broker-compliant **volume in lots** to the Trader pre-order-send. The four economic engines coordinate one source of real capital and risk. `multiplier=10` is not leverage 1:10, nor is 10x automatically a legal LOT size. `$3` is a **maximum predicted TOTAL STOP LOSS** including commission + costs, not required exact loss or a fixed lot. **Round lot volume DOWN**, never exceed the budget to satisfy an exact target. If minimum lot cannot fit, the order is NOT FINANCEABLE; preserve signal as unfilled, not fake execution. NEVER use future PNL for decision.

Old replay H21/H31 models, and all circa USD670k extreme ceiling claims, cannot be certified executable: the canonical handoff has an H8 **physical cash solvency override**; original H8 found at least one executed mandatory base position requiring **$4.520000** while available sovereign capital was **$4.215535** and states of negative sovereign BANK. No promotion until a fully funded, server-executable replay.

Canonical H8 source documents (preserved untouched):
- `docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md`
- `docs/research/CIBO_H8_REAL_CAPITAL_SOLVENCY_BLOCKER_2026-10-08.md`
- Old H31 four-motor prototype `agent/cibo-h31-lotage-bank-floor-and-free-margin-001`; H31 enforced bank0 but maintained 1x fallback and was not MT5 certified.

## Official independently verified FundedNext sources

As checked **2026-10-08**:
1. https://help.fundednext.com/en/articles/8020350-what-is-the-contract-size-of-the-instruments — official contract sizes: Forex 100,000 units/lot, indices 10 units/lot, metals 100 units/lot (XAGUSD exception). **Contract size alone is not tick PnL or margin**.
2. https://fundednext.com/general-rules/cfds/symbols-and-conditions — NDX100 is official public Nasdaq symbol, Stellar Instant leverage FOREX 1:30 / INDICES 1:5 / COMMODITIES 1:7.5. No 10000x broker leverage. Server may label aliases; mapping NAS100 -> NDX100 must be VERIFIED.
3. https://help.fundednext.com/en/articles/11641300-what-are-the-commission-charges-for-the-stellar-instant-account — current Help Center describes **FOREX USD7/lot charged at OPEN only**, indices 0, commodities/metals **0.0016% OPEN NOTIONAL**. Note: General Rules has ambiguous 'per-side' prose, and fees changed during 2026; read the account's actual charges before certifying, do not assume $14/lot round-trip.

For the six QORE symbols:
|Core|Published underlying contract / 1 lot|Published leverage Stellar Instant|Final MT5 volume_min/step/max, tick_value, margin|
|---|---|---|---|
|AUDJPY|100,000 AUD|1:30|**UNVERIFIED**|
|EURUSD|100,000 EUR|1:30|**UNVERIFIED**|
|GBPJPY|100,000 GBP|1:30|**UNVERIFIED**|
|GBPUSD|100,000 GBP|1:30|**UNVERIFIED**|
|NAS100|10 units NASDAQ, candidate NDX100|1:5|**UNVERIFIED**|
|XAUUSD|100 oz troy|1:7.5|**UNVERIFIED**|

**Cannot supply 'certified six-spec table' yet**: Remote Desktop Commander connected device `vps-vrix` was OFFLINE when checked; no authenticated FundedNext MT5 snapshot available. Do not create or guess broker MT5 margin/volume.

## Implemented source files on P0 branch

1. **Unified money-at-stop lot calculator** `src/qore/infrastructure/trader_lab/cibo_fundednext_mt5_lotage_p0.py`.
    - Uses true current MT5 `symbol_info`, `symbol_info_tick`, `account_info`, `order_calc_profit(side,symbol,lots,entry,sl)` and `order_calc_margin`.
    - Checks account currency USD, fresh bid/ask tick, actual `volume_min`/`volume_step`/`volume_max`, symbol visibility, trade_enabled, side/SL, legal grid, margin_free, margin-level threshold, equity/sovereign floor, total/symbol/trader/correlation concentration budget.
    - Accounts EURUSD/GBPUSD USD-per-pip, JPY cross conversions **through server `order_calc_profit`** rather than guessed USDJPY, Nasdaq & XAUUSD with their actual server calculations.
    - Includes published commissions, adverse SL slip in price points, optionally additional costs, no fake fills, max total estimated risk $3 default, experimental $2.95.
    - Binary searches valid steps to find maximum fundable legal lots. NO rounding up over total risk budget. Emits full `Quote` audit, or explicit `FundingError` when provider/account/margin fails.
    - `AtomicPortfolioReservations` RLock, deterministic trade ID idempotency, one shared account risk ledger, released once, no double spend; not a broker deal confirmation.
2. **Coordinated four-motor funding** `src/qore/infrastructure/trader_lab/cibo_four_motor_fundednext_p0.py`.
    - SIZING computes the USD3 max total loss to SL and lots, CIBO_COMPOUND sources only realized BANK for MEDIUM or realized cushion for ATTACK, COMPOUND_PORTFOLIO handles one atomic risk/concentration account ledger, ADAPTIVE_LEVERAGE confirms broker `order_calc_margin` and margin level.
    - Each motor emits a separate `MotorDecision`, but there is **only one budget**. ATTACK cannot borrow sovereign BANK. `close_after_broker_receipt` requires explicit broker-close provenance claim and prevents negative capital mutation; must replace boolean proof with real broker ticket/transaction read before live certification.
    - No fractional capital compounded without realized broker receipts; $3 initial/per-entry **fixed ceiling** unless explicit versioned risk policy changes.
3. **Trader pre-send hook** `src/qore/infrastructure/trader_lab/cibo_trader_presend_mt5_p0.py`.
    - Trader sends signal/side/SL/TP, CIBO answers broker-symbol/order payload with tested lotage. Actual `order_send` remains outside this module and under Trader-owned gateway. `check_broker_execution` tests retcode, deal, filled volume and filled price. Rejects mismatched/partial volume or slippage from certification pending risk recalc and requires cancelling unfilled reservations after a broker rejection.
    - **Not yet wired into production Trader send path**: research adapter only. Must integrate with real broker gateway, and broker ticket/order-history reconciliation before a live deployment.
4. **Read-only connected MT5 spec collection** `scripts/cibo_p0_mt5_specs_readonly_probe.py`. Uses already signed-in MT5 terminal, records six symbols' server minimum/step/max, tick values, contract, Bid/Ask, order_calc_profit/margin sample and account free margin without credentials/order sending. It will fail closed offline. Verify server model/tariff before treating as authoritative.
5. **3 year full input forensic risk audit** `scripts/cibo_p0_three_year_offline_lotage_audit.py`. Consumes immutable 3368 Trader decisions and historical per-volume USD stop/margin predecision data; computes step-legal risk-max lots for **both $3 and $2.95 including conservative historical spread + estimated published provider commissions + slippage reserve**. Historical spread can already be included in market stop-price, so this is a conservative screen, not MT5 PnL proof. PnL/DD after resizing **NOT COMPUTED** and certainly not certified.

## Verified scientific tests and actions

- Unit/integration CI: [GitHub Actions 37810500072](https://github.com/mezas3238-hue/qore-core/actions/runs/37810500072) — **SUCCESS**, 34 broker-profit/margin/coordinator/concurrency tests + 6 Trader pre-send tests = **40 tests passed**, includes BUY/SELL, fixed $3/$2.95, 6 classes, gold %, USDJPY conversion, spread, SL, slippage, lot step, margin, stale quote, concurrent/duplicate reservations, PNL only after broker proof, budget, bank, concentration, order rejection and execution mismatch.
- Three-year manifest diagnostic: [GitHub Actions 37809999723](https://github.com/mezas3238-hue/qore-core/actions/runs/37809999723) — **SUCCESS, all 3368 original signals**, 2019-07–2022-06, artifact ID `11564337531` with *every signal risk/SL/quote and aggregate per symbol*. This is an **offline sizing audit**, NOT a genuine full adjusted-economic-replay of broker fills.

### 3368 signals, $3 risk cap, historical provider proxy, ORIGINAL 2019–22 model

|Symbol|Signals|At least 1 step-valid volume (historical risk proxy)|No valid risk-bounded volume|
|---|---:|---:|---:|
|AUDJPY|673|651|22|
|EURUSD|495|494|1|
|GBPJPY|618|589|29|
|GBPUSD|606|570|36|
|NAS100|484|459|25|
|XAUUSD|492|308|184|
|**Total**|**3368**|**3071**|**297**|

$2.95 experimental: **3060** provisional step/risk-compatible, **308** not; details in complete workflow artifact. Some historical NAS100 0.1 lots require more margin than USD60 static base, which is an additional independent fundability constraint. All 3071 are **NOT VERIFIED BROKER EXECUTIONS**. **Number certified executable from attached authentic MT5 server = 0 until server is connected**. No achieved trading income, capital or DD claimed on new funded lots.

Compare prior H21/H31 amounts only as benchmarks of LEGACY ledger ($60->$3589.26 / DD34.35%, H31 $60->$2997.39 / DD34.35%), **NOT** results of these new P0 lots. H8 and H31 report broker-unfunded custody/floor breaches.

## Explicit acceptance check — current

A. Central MT5-funded lotage engine — **IMPLEMENTED/TESTED AS STANDALONE RESEARCH COMPONENT**, requires live adapter check.
B. Six **actual authenticated MT5 contract, tick, volume and margin specs** — **BLOCKED: VPS offline, missing connected broker snapshot**; only published general reference verified.
C. Four economic motor integration — **IMPLEMENTED AS RESEARCH COORDINATOR AND PRE-SEND INTERFACE**, not merged into actual runtime order-send.
D. Automated tests — **40/40 CI SUCCESS** with synthetic MT5 mock (never confused with live broker).
E. Before/after broker-executable three-year PnL/DD replay — **BLOCKED until six real historical/server-cost datasets and causal funding**, offline input-size analysis supplied instead.
F. Non-financeable signals — **297 risk/step invalid at $3 proxy**, more may fail real margin; per-signal CSV and JSON artifact available. **NOT COMPLETE BROKER FAIL REASON REPORT** without MT5.
G. Profit/loss/DD impact — **NOT CERTIFIED OR PRODUCED**; recalculation of trade closes with new lots must use server quotation, fees, partial close lifecycle, open positions and intra-trade stop-out.
H. Master handoff — this document.

## Urgent next 1-2 iterations

1. Restore authorized vps-vrix access and run read-only `scripts/cibo_p0_mt5_specs_readonly_probe.py --output <path>` on FundedNext MT5 logged into the EXACT Stellar Instant account. Validate NAS100->NDX100, exact leverage/margin per symbol, min/step/max, tick profit/loss and commission actual opening transactions. Attach JSON to GitHub artifact without account personal IDs/passwords.
2. Integrate `prepare_trader_order` through the existing Trader execution gateway with submit ACK and rejection/partial fill broker history, lock reservations before sending; no fake trade records. Replay predecision 3368 timing with price evolution, opened positions and funding, and broker fee hist.
3. Create a fully causal broker-price/margin 2019–22 replay that computes each position's live and realized PnL using actual executed L O T S (and open floating, stops, costs), full bank/cushion ledger and broker margin stop-out. Fail closed when an order is unfinanceable; preserve all *signals*, not necessarily 3368 *executions*. Distinguish 3/2.95 risk policy, return 1/3/6/12-month and 3-year net capital, PF, gross losses, DD, symbol/trader breakdown and genuine execution-vs-signal counts.
4. Resolve H8 $4.52 required / $4.215535 bank cash gap, all negative bank states, concurrent capital risk/correlation. New DD ideal 20%, max25%, no performance claim over ceiling until it is genuinely funded and solvent.
5. Fresh sealed holdout (separate from reused 2019–22 tuning) and cost/slippage stress before certification.

## Source quality, trust and warnings

- FundedNext states in its published site that this program uses **virtual simulated funds**, not live market assets. Thus 'real broker lotage' means executable through account's MT5 simulation, not a claim of guaranteed real investment returns or withdrawable gains.
- Current exchange rates and historic spreads/ticks unavailable from authenticated account; DO NOT hardcode USDJPY=158.21 for 2019 forex.
- The **$7/lot opening only** FAQ may conflict with separate generic General Rules "per side" description; resolve with actual trade ledger before high-stakes production.
- A code SUCCESS or 3368 SIGNAL replay does not mean successful profit performance or certification.

**RELEASE VERDICT: KEEP RESEARCH BRANCH ONLY, NOT MERGE / NO VPS LIVE ORDERS.**


## Final fail-closed release restriction — latest code

After broker portfolio rehydration audit, `CoordinatedCiboCapital` now defaults
`complete_broker_positions_reconciled=False` and sets
`ExecutionAuthorization.can_submit_to_broker=False`. Until a real authorized MT5
session reconstructs **all already-open positions' risk, volume and reserved margin**
and verifies fee model, the Trader must NOT execute a staged P0 intent.
Although tests use simulated `MockMT5`, they deliberately prove the default
authorizations are NOT live-submittable.

Last verified CI on code containing this fail-closed behavior:
**[GitHub Actions 37810894912](https://github.com/mezas3238-hue/qore-core/actions/runs/37810894912) —
SUCCESS — 34 unified MT5/compound tests + 6 Trader presend tests = 40 green**.
This newer run supersedes the original CI link in the preceding section.

Broker position rehydration, broker-deal/close proof (do not accept a mere
boolean flag), actual partial fills / SL slippage repricing, timestamp check
and account's actual funded model ID are still required before release.
