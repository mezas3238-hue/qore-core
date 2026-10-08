# CIBO H11 — $60 micro, 5% stop risk: realised feasibility and fees

**2026-10-08 / P0 SCIENTIFIC RESEARCH / NOT CERTIFIED**

This branch inherits H10. The owner target is $3 of stop risk per executed entry at $60 (5%), not a fake guaranteed profit. In a hypothetical 0.1 lot trade at $14/lot roundtrip, $1.40 fees must be added to gross stop loss. It does not automatically imply the historic NAS100 stop loss equals $3.

## Executable H10 result, original 3,368 signals

$60 seed, full ordered 2019–22 Trader manifest, $14/lot roundtrip, estimated broker minimum lots and margins: **0/3368 executed fills, $0 realized profit**. First NAS100 min lot 0.1 needs approx $77.7885 margin, larger than $60. Research status **NOT_FULLY_EXECUTABLE**, NOT evidence of broker stopout/bankruptcy. Never promote this to any positive 3y capital result.

## H11 structural R commission audit (NON-EXECUTABLE)

Historical original Trader gross structural R returns, NOT freshly CIBO-managed 5% exits. For every trade, commission in R = 14 divided by stop-dollar-per-lot. No legal lot steps, margins, futures settlement scheduling, balance constraints or micro financing were modeled in this normalization.

- **3,368 signals**. Gross summed R +546.0143770671; normalized USD14/lot fees 1561.0015818675R; net **-1014.9872048004R**.
- **1,702 gross winning signals**, reduced to **1,508 positive after fee**.
- Unrealizable fixed $3 stop for all 3,368: +$1,638.04 gross, -$4,683.00 commissions = **-$3,044.96** if new capital is constantly added after insolvency. This is NOT a $60 account PnL; account cannot fund those 3,368 positions.
- Hypothetical dynamic 5% stop compounding with arbitrarily fractional volumes and no broker restrictions ends at approximately **$1.38e-28** starting from $60 after charging $14/lot, with mathematical DD essentially 100%. A fully hypothetical 5% ALL-IN version ends near $1.10e-11. Neither should be marketed as a physical equity curve. Historical gross-only version without fees creates fictitious extreme growth but 83.22% DD.
- Median fee / stop R NAS100 ~1.386R (484 signals; summed net -686.21R); EURUSD .264R (-114.96R); GBPUSD .158R (-100.45R); AUDJPY .186R (-82.21R); GBPJPY .158R (-20.53R); XAUUSD .063R (-10.63R). All sums are diagnostic normalized R, not account USD.
- First NAS100 stop-per-lot $2.95; min 0.1lot => $0.295 stop, $1.40 roundtrip fee, -1R all-in **-$1.695**; still blocked by margin ~$77.79. $3 *stop* implies approx **1.017 lots**, ~$14.24 commissions, impossible lot step/margin at $60. Do not assume a 0.1lot historical NAS100 entry has $3 stop.
- H11 standalone arithmetic audit script locally reproduced these totals and **7/7 internal tests passed**. Not a validated live tick-level benchmark.

## Must fix before answering what CIBO can actually produce at 5%

(1) Obtain broker-confirmed legal micro contract/minimum lots, exact tick-value and leverage/margin for real trading. (2) Perform full causal CIBO stop/exit management plus true capital custody with original Trader entry set; do not censor signals that cannot be executed, mark incompatibility fail-closed. (3) Respect roundtrip fee/volume and spread, commission, slippage, MTM margin stopouts, calendar daily loss and aggregate exposure. (4) Rebuild from $60 under financing that actually exists, then evaluate net PnL, DD, fee burden, survival, sealed OOS. (5) Never apply micro 5% stop to Stellar Instant USD2k unchecked; that account has a distinct 6% trailing loss cap and owner's $60 daily cap.

**No positive USD60 5% CIBO profit is currently demonstrated.**

Source frozen historical manifest artifact 11389331836. H10 empirical JSON was cibo_microcapital_gradual_scaling_h10_risk3_results.json; reproducible H11 local artifacts cibo_h11_risk5_fee_forensics.py and cibo_h11_5pct_fee_performance_forensics.json.
