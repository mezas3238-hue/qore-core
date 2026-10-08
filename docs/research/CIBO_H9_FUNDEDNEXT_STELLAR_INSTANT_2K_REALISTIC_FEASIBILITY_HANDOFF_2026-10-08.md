> **OBSOLETO — ERROR DE COMISIONES CORREGIDO (2026-10-08):** Este H9 preliminar calculó USD7 **FIJOS por operación** y sus ocho resultados NO deben usarse como base económica. El usuario exige un escenario principal de **USD7 por lote al abrir + USD7 por lote al cerrar = USD14 por lote round-trip**. Se ejecutaron 12 replays corregidos y publicaron los resultados canónicos en [H9b — corrección de costes proporcional a lotes](./CIBO_H9B_STELLAR_INSTANT_2K_PER_LOT_FEE_CORRECTION_2026-10-08.md). Ejemplos correctos: 2 lotes→USD28; 0,10 lotes→USD1,40. La cifra de USD2,80 a 0,10 lotes se probó solo en sensibilidad USD28/lote. La tarifa oficial FundedNext también se distingue del escenario conservador. **CIBO NO CERTIFICADO.**

---

# QORE CIBO — H9 FundedNext Stellar Instant USD2,000: forensic funded feasibility replay

**Date** 2026-10-08. **P0 status: NOT CERTIFIED / NO LIVE AUTHORITY / NO CLAIMED PROFIT.**
Isolated branch `agent/cibo-fundednext-stellar-instant-2k-h9-001`, based on H8 physical-solvency fail-closed work. Do NOT change other architects' work.

## User requirements vs verified product
- FundedNext Stellar Instant account **USD2,000**.
- Official **6% TRAILING maximum-loss limit**, not daily-loss. Initial floor USD1,880; trailing advances with achieved balance highs and stops at USD2,000. Floating equity breaches count. No mandatory daily loss for this product.
- User-imposed **USD60 voluntary daily risk/loss envelope (3% initial)**, including realized PnL, opening commissions and pending planned stop liabilities.
- FundedNext general **3% aggregate risk at any time** = USD60 from USD2k initial, including open exposures.
- User demands **USD7 per executed entry** as total roundtrip cost. Do so as **flat7 sensitivity**. Real official Stellar Instant fee is USD7 per LOT forex (at entry), zero index and 0.0016% commodity notional. The broker rules and effective date must be checked at account opening.
- Forex leverage 1:30, indices 1:10, commodity 1:10, NOT old simulated 10,000x.
- Preserve original 3,368 Trader signals; physical infeasibility is **SCIENTIFIC FAIL**, not permission for CIBO to selectively reject/defer/censor a Trader entry.
- Source exact historical manifest: artifact `11389331836` ZIP digest `sha256:30177639f660c9647ab70257c2d12c541bdade49ab5582347a3890f920070fee`.
- Source exact frozen em-s06745 historical receipt replay: artifact `11542321736` ZIP digest `sha256:0e14d059be5053f453861ef02d119a7290d803d01ca3c74735a94e3a0f127d52`.
- Both sources have 3,368/3,368 unique matching fingerprints. Historic 2019-07-01 to 2022-06-29, NOT sealed OOS.

Official documentation: https://help.fundednext.com/en/articles/17253243-stellar-instant-account ; https://help.fundednext.com/en/articles/11641300-what-are-the-commission-charges-for-the-stellar-instant-account

## Genuine preliminary replay H9: eight fully chronological **attempts**; ALL stopped on first unfundable Trader signal

Entry sizing used predecision minimum lot, step, stop risk and margin; future settlement R consumed only on settlement. Pending stop risk and margin were reserved; opening fees debited immediately. Trailing floor updated on new closed balance high. The replay halts when stop+fees+margin of broker minimum lot cannot fit. NOTE *only terminal settlement equity known*; not tick-by-tick FLOATING compliance proof.

| Fee case | Single-entry stop+cost envelope | Additional slippage shock | Financed fills before stop | Cash balance at halt USD | Paid fees USD | First inability |
|---|---:|---:|---:|---:|---:|---|
| USD7 flat per entry | 10 | 0R | **20** | 1885.95 | 140.00 | 2019-07-08 |
| USD7 flat per entry | 20 | 0R | **25** | 1885.05 | 175.00 | 2019-07-10 |
| USD7 flat per entry | 40 | 0R | **8** | 1984.75 | 56.00 | 2019-07-03, estimated margin |
| USD7 flat per entry | 20 | +0.25R | **13** | 1887.72 | 91.00 | 2019-07-04 |
| Category/lot fee | 10 | 0R | **70** | 2091.04 | 66.86 | 2019-07-29, estimated margin |
| Category/lot fee | 20 | 0R | **35** | 2120.47 | 56.55 | 2019-07-16, estimated margin |
| Category/lot fee | 40 | 0R | **8** | 2026.67 | 17.01 | 2019-07-03, estimated margin |
| Category/lot fee | 20 | +0.25R | **35** | 2010.29 | 48.55 | 2019-07-16, estimated margin |

**Crucial**: these are *balances at interruption*, with possibly open/unsettled trades; never market them as final portfolio profit. Nothing validates all 3,368 fills; no new accepted 3yr economic ceiling; nobody should promote those attempts into a CIBO carrier.

Full signal/fee audit: 3,368 signals, 774 broker-local (EET/EEST proxy) signal days; 34 days contain >=9 entries, so the hypothetical flat7 charge alone would exceed user daily USD60 without offsets. Full hypothetical USD7 fee on all 3,368 entries = **USD23,576**; paid fees in actual aborted replay are much lower. Seven Trader identifiers, six symbols. Both fee structures intentionally reported.

## P0 repairs actually exercised locally by simulator

1. 6% MLL **trailing, never lowered, capped initial account**.
2. USD60 simultaneous reserved stop risk and USD60 voluntary daily worst-case budget, including fees.
3. Broker min volume / lot increments; estimated real leverage 1:30 forex, 1:10 index/commodity, and margin from notional and provider.
4. USD7 **at opening exactly once PER entry** user scenario; second scenario official per-lot/by-category fee.
5. Exit evidence consumed after position close only; no future outcome/trader blacklist/ID to select exposure.
6. Every unfinanceable mandatory Trader entry causes **FAIL CLOSED** before it is booked; no fake minimum 1x funding and no fabricated portfolio capital; prevent “favorable results after bankruptcy.”
7. Additional adverse 0.25R slippage stress; full 3,368 source identity audit.
8. Local six synthetic regression tests: fee calculations, min margin, no lookahead, MLL floor cap, opening cost, unfundable mandatory entry halt: **6/6 PASS**.

### Unresolved P0 blockers / next architect must NOT hide

**This is NOT yet a tick-level broker-certified replay.** 2019–22 decisions reference 2026-10-01 broker spec snapshot; JPY Forex USD conversions are fixed estimates, broker historical spread/slippage/swap and true live symbol min-lot/spec missing. No MTM bid/ask path, so no proof floating equity obeyed trailing MLL. In particular, USD2k + flat fee USD7 + no entry censorship may be **mathematically incompatible** with all original 3,368 signals. The correct response is to *show impossibility*, not credit nonexistent winners.

Next tasks:
1. Publish reusable replay source and structured artifacts to repo from isolated branch. Local generated outputs verified: `cibo_stellar_instant_2k_replay.py`, `test_cibo_stellar_instant_2k_replay.py`, `CIBO_FUNDEDNEXT_STELLAR_INSTANT_2K_MASTER_REPLAY_REPORT_2026-10-08.md`, `cibo_stellar_instant_2k_results.json`, `cibo_stellar_instant_2k_scenarios.csv`, full 3,368 signal-fee CSV and 774 broker-day density CSV. Do not claim these are already present in GitHub unless uploaded and verified.
2. Obtain **actual** Stellar Instant account contract specs/fee effective date/bid-ask historical/requotes and explicit 3% risk rule; implement intratrade MTM equity barrier and margin/forced close simulation.
3. Keep all Trader signals in research; investigate upstream Trader signal execution capacities with proper authority, never make CIBO block selectively. If a base entry is impossible under volume/margin, certification **FAIL** rather than silent trade removal.
4. Add daily (server timezone + overnight floating) boundary and simultaneous risk stress, net market spread, swaps, Monte Carlo, walk-forward.
5. Rebuild realistic Sizing + Leverage + CIBO Compound + Portfolio Compound on **single funded account equity**, honor sovereign reserve separately as accounting not fictional capital.
6. Complete multi-regime loss forensics, risk of ruin, sealed OOS and integrated QORE CIBO+Traders+Shared test. Rule for this FUNDED account is **6% trailing MLL**, much stricter than prior ideal 20–25% research DD.

H9 is a **negative but genuine scientific feasibility finding**, not a trading result and not certification.
