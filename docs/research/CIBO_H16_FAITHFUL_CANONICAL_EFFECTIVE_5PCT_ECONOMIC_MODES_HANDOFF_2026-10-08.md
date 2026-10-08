# CIBO H16 — FIEL AL CÓDIGO CANÓNICO, 5% EFECTIVO, REPLAY 3.368 / ECONOMÍA POR MODO

**08-10-2026 · RESEARCH ONLY · NO CERTIFICADO**

## Directiva vinculante
Copiar de modo exacto CIBO **desde** `agent/cibo-causal-expectation-leakage-fix-001` (branch vigente de ingeniería). No cambiar metodología, razonamiento de la cognitiva, decisión de modos, entradas de Traders, salidas, stop/R, Capital Compound, Portfolio Compound, Sizing, Leverage ni condiciones de riesgo existentes. El único cambio autorizado es el **monto de riesgo efectivo por entrada**, objetivo 5% del capital corriente (USD3 nominales a USD60) sujeto a restricciones originales. Usar benchmark **USD60, 3368 entradas**, no mezclar con Stellar Instant USD2k o su comisión solicitada USD14/lote.

## Por qué H15 no era suficiente
H15 run [37776873181](https://github.com/mezas3238-hue/qore-core/actions/runs/37776873181) fue SUCCESS y mostró CIBO SOURCE EXACTO, pero el cambio de constante `MEDIUM_RECOMMEND_RISK_FRACTION` de .04 a .05 **no afectó el presupuesto efectivo** de muchas entradas MEDIUM: `historical_risk_fraction` lo sobrescribe al seleccionar capital a asignar. H15 net USD3120.25024, DD36.91054%, BANK $0 (0 trades), MEDIUM +$276.52115 (2519 trades), ATTACK +$2843.72910 (849 trades), soberano incumple $77.10360. Estos no son la ejecución autorizada **MEDIUM 5% efectivo**; la comparación es un ATTACK cap 5% con MEDIUM prior viejo. Marginal H15 Sizing +$159.095; Portfolio Compound +$2597.817, no sumables ni atribuibles directamente a dólares ganados.

## H16 corregido: fuente canónica 100% intacta
- Branch `agent/cibo-faithful-effective-fivepct-h16-001` copia en línea desde H15, cuyo base fue clonado del **CIBO CANÓNICO VIGENTE**. No modificar ningún fuente dentro de GitHub (verificar compare).
- Workflow `.github/workflows/cibo-trader-lab-faithful-effective-5pct-h16.yml`, commit `dd89b93e864d867b892a9463a2fb099aa91a9769`, ejecución [37777655782](https://github.com/mezas3238-hue/qore-core/actions/runs/37777655782).
- Paso 1 copia `src/` exactamente dos veces; contrasta igualdad bit a bit. Solo en **copia TEMPORAL** de la variante inserta una línea `medium_risk_fraction = Decimal("0.05")` **después** del selector original del prior histórico y **antes** del multiplicador monetario MEDIUM. Afirmar que el diff tenga exactamente una línea añadida y ninguna eliminada.
- ATTACK emplea flag original `--ceiling-attack-single-trade-risk-fraction 0.05` vs control `0.20`. No otra lógica tocada.
- Cada modo sigue la cognitiva/ruta postentrada y la administración completa CIBO actual; no se impone 5% siempre si stop 1x, funding, margen y protección restringen el volumen. Medir riesgo efectivamente consumido antes de reclamar exactamente USD3 por cada entrada.
- Cuatro replays de 3368: original, 5%-efectivo, 5%-efectivo sin Sizing incremental y 5%-efectivo sin Portfolio Compound. Las 2 ablations son **comparaciones causales aparte**, no copias de CIBO ni propuestas de cambiar metodología.
- Banco realiza **0 trades**, net PnL 0. BANK crea y recupera working-capital seed. MEDIUM+ATTACK net receipts suman el PnL final; el informe desglosa comisiones de provider original, ganancias y pérdidas brutas. Sizing/Portfolio `delta full minus no-engine` no son utilidades adicionales ni aditivas.
- Instrumentos provienen de manifest histórico pinned (2019-22), original provider costs. **FundedNext USD2k 6% trailing, $60/day y $14/lot es otra simulación que este benchmark no representa**.
- Sovereign bank negatives o piso incumplido INVALIDAN certificación de ganancias, incluso si el balance final es positivo.

**Criterio**: 3368/3368, fuente idéntica, diff exacto 1 línea monetaria, conciliación `initial+sum(mode net)==final`, DD, GL, PF, soberano; solo resultados observados en el run, no anticipados. H16 resultado debe adjuntarse al terminar verificación.

## VERIFICACIÓN FINAL H16 — EJECUCIÓN SUCCESS

GitHub Actions [37777655782](https://github.com/mezas3238-hue/qore-core/actions/runs/37777655782) SUCCESS. Artifact `11550507522`; JSON auditado `docs/research/CIBO_H16_FAITHFUL_CANONICAL_5PCT_THREE_MODES_SIZING_PORTFOLIO_VERIFIED_RESULTS.json` @ commit `d2f354abb8b1d343bd196da846db124a2781440d`.

El control exacto reproduce USD60 → USD673146.525454 y DD36.910539%. La variante objetivo nominal 5% USD60 → **USD3180.250244** y **DD36.910539%**, **soberano breach USD77.103604**, final banco **−USD38.413807**: ¡NO CERTIFICABLE!

### PnL neto real del ledger del CIBO modelado, no cifras imputadas a motores dos veces

| Modo | Entradas | Positivos USD | Negativos USD | Neto USD | Provider fees USD |
|---|---:|---:|---:|---:|---:|
| BANK | 0 | 0 | 0 | **0.00** | 0 |
| MEDIUM | 2519 | 1993.67 | 1717.15 | **+276.52** | 259.79 |
| ATTACK | 849 | 13495.56 | 10651.83 | **+2843.73** | 1263.32 |
| Total | 3368 | 15489.23 | 12368.98 | **+3120.25** | 1523.12 |

USD60 + 3120.250244 = 3180.250244, reconciled at Decimal precision. Provider costs are those of original model and are already accounted for in net per trade; **NOT FundedNext USD14/lot**.

### Sizing and Portfolio Compound: marginal scientific ablation, not standalone trades

- Full original CIBO nominal5%: capital USD3180.250244; profit USD3120.250244, DD36.910539%.
- *Counterfactual without SIZING incremental* 3368 receipts: capital USD3021.155225; profit USD2961.155225; DD39.674878%. Sizing incremental contribution **+USD159.095019** in conditional replay and **−2.764338 percentage points drawdown** relative to no-Sizing.
- *Counterfactual without COMPOUND_PORTFOLIO* 3368 receipts: capital USD582.432989; profit USD522.432989; DD36.910539%. Portfolio Compound conditional marginal contribution **+USD2597.817254**. Without Portfolio Compound ATTACK has **0 entries** and all 3368 are handled as MEDIUM in the ablation. This is a different research counterfactual; does **not** imply Portfolio Compound individually receives USD2597.82 of cash.
- Bank issued USD4473.941393 and recycled USD4473.941393 as internal seed, not income. Medium-to-cushion USD374.934953 is transfer, not a separate PnL. Portfolio credit recycled USD21643.398940 is funding turnover, NOT profit.
- **Cannot add** Sizing +159 and Portfolio +2598 as if 2 independent new gains; their interventions interact causally with MEDIUM/ATTACK modes and compounding.

### H17 strict import diagnostic
H17 independent GitHub run [37778184947](https://github.com/mezas3238-hue/qore-core/actions/runs/37778184947) PASS: actual imported CIBO module `/home/runner/work/_temp/cibo-variant-src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py`, exact target source verified; `medium_risk_fraction = Decimal("0.05")` present in executable function. The canonical original module is unchanged. **H16 financial output remained EXACTLY equal to H15** despite effective MEDIUM 5% target loading. Therefore one must not claim every trade used USD3 or that MEDIUM effective physical risk changed. Original BANK seed, available capital, physical risk/margin and native intensity are possible binding constraints, requiring a separate instrumented constraint-binding audit to prove which one binds in each entry. It is incorrect to attribute this sameness to a Python import bug: H17 ruled that out.

### Limits and certification
The H16 replay reuses frozen em-s06745 config with the latest canonical source snapshot. It is **not** a newly calibrated latest best 36.44% carrier nor an actual USD2000 funded Stellar Instant 6% trailing drawdown / fee $14-per-lot replay. It is strictly a faithful method / risk-only comparison on $60 research account. Sovereign floor violation >USD77 makes it INVALID for live financial production claims; a positive model book does not prove the bank/portfolio survives margin calls. No deployment sign-off.
