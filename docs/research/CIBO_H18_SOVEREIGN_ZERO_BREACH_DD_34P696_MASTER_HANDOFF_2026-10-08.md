# CIBO H18 — BANCO SOBERANO RESCATADO SIN CAPITAL FICTICIO / DD 34.696%

**2026-10-08 / Estado: VALIDACIÓN CIENTÍFICA PARCIAL (NO CERTIFICADO, DD > 25%).**

## Fuente canónica y soberanía

Copia temporal del código canónico desde `agent/cibo-causal-expectation-leakage-fix-001`, en la línea H16 fiel. No se modifica el código original de CIBO, entradas de Traders, cognitiva, stops como metodología nueva, motores Leverage, Sizing, Cibo Compound ni Portfolio Compound; solamente se ajustan **dos parámetros ya nativos**: distribución real de ganancias MEDIUM a bank/cushion y umbral del módulo de postentrada ADVERSE_PARTIAL_REDUCTION.

Experimento reproducible [GitHub Actions 37780120854 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/37780120854).
Resultados exactos `docs/research/CIBO_H18_BANK_FLOOR_ZERO_BREACH_DD_34P696_REAL_REPLAY_RESULTS.json`, commit `20ceebc7e6393cfb0c0f743dd52cdd91e9df485f`. Las 3.368 entradas se conservan exactamente.

## A/B + ridge (incluye costes nativos del modelo, NO tarifa FundedNext)

| Caso | Caja inicial USD | Capital final modelo USD | DD máximo | Banco brecha USD | Banco final USD | Bruto pérdidas USD |
|---|---:|---:|---:|---:|---:|---:|
| H16 control 100% cushion / −0.40R | 60 | 3180.25024 | 36.910539% | 77.103604 | −38.413807 | 12368.98058 |
| 25% MEDIUM al banco / −0.40R | 60 | 3304.54715 | 36.910539% | 52.528180 | 49.543684 | 12770.23106 |
| **50% MEDIUM al banco / −0.40R** | 60 | **3304.54715** | 36.910539% | **0.000000** | 176.307819 | 12770.23106 |
| 25% MEDIUM al banco / −0.25R | 60 | 3571.79859 | 34.696185% | 31.070871 | 96.485150 | 13322.49647 |
| **50% MEDIUM al banco / −0.25R** | 60 | **3571.79859** | **34.696185%** | **0.000000** | **273.561207** | 13322.49647 |

**H18 winner for research only**: `--economic-group-bootstrap-cushion-share 0.50` (i.e. 50% of MEDIUM distributable profits remains available to the sovereign rather than redirecting 100% cushion) + `--lifecycle-adverse-loss-cut-r -0.25` (original CIBO position lifecycle, causal Market Atlas bars). Same 5% stop-risk nominal sizing inputs as H16, 3368/3368 managed, BANK treasury zero trading entries. Protected floor through natural profit routing, **no inter-ledger rescue transfer, no minted cash**. All PnL reconciled to initial $60 at decimal numerical precision, 0 breaches in H18 model.

**BEWARE** gross losses increased to $13,322.49647 vs H16 $12,368.98058, so H18 does not dominate H16 on all strict-Pareto axes even though DD, capital and solvency improve. Profit factor and market realism require separate reports.

### DD forensics
H16/H18 first dominant episode peak 2019-07-19 $79.76394 to trough 2019-08-12 $50.32264: −$29.44130, equivalent 36.91054%, exclusively MEDIUM. 1x mandatory base positions are a large source of realized losses. Reaching 25% from that peak requires about $9.50 reduction in trough loss, beyond removing all extra 2x position net loss (~$4.06). The original post-entry risk engine must contain more 1x losses with causal recorded bar evidence without rejecting entries; stronger parameter-only DD sweeps H20/H21/H22 are separate research branches. Do not use future R labels for triggers.

### Pending checks
- Verify H21/H22 deeper DD tuning separately; only promote if 3368, bank no breach, capital >= meaningful valid floor and DD <=25% (ideal 20%). Catch overfitting to same 3y dataset, require sealed fresh OOS.
- H19 experimental inter-ledger transfer created a false-positive strict decimal equality failure on replay (precision noise). Do **not** merge it in lieu of already verified H18 natural routing; experimental H19 source is separate.
- Real account funding viability is NOT proven. Original CIBO $60 provider costs are NOT user's proposed $14/lot FundedNext fees; broker min lots, margin, slippage, swaps, floating MTM must be evaluated on funded USD2000 account separately. Past ATTACK account profitability under extreme leverage is NOT evidence of executable real profit.
- Do not overwrite `agent/cibo-causal-expectation-leakage-fix-001` or other architects' branches.

**CURRENT VERIFIABLE BEST FLOOR-SAFE RESEARCH:** $60->$3571.79859, 3368, bank breach0, DD34.696185%, below target NOT yet; never certify as live.
