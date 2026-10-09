# CIBO P0 — Ablation PAPER de cuatro restricciones estratégicas para 3.368 entradas

**Reproducción:** [GitHub Actions #37910444519 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/37910444519) y [artifact #11606054452](https://github.com/mezas3238-hue/qore-core/actions/runs/37910444519/artifacts/11606054452).
**PR:** #745 · branch `agent/cibo-sovereign-integration-p0-20261008`.
**Estado:** INVESTIGACIÓN OFFLINE / NO LIVE, **SIN MODIFICAR** los motores económicos de producción ni el servicio QDLE.

## Solicitud de CEO y alcance seguro

CEO pidió eliminar inmediatamente todas las reglas que afectan a Core. La implementación segura **solo para PAPER RESEARCH** crea el interruptor `--experimental-paper-bypass-strategy-caps` en `scripts/qdle_3368_dual_ledger_replay.py`.

En este brazo se ejecuta el procesamiento de **todas las 3.368** señales Trader por CIBO administrador, se registran los votos originales de cuatro motores para comparación pero se sustituyen sus *topes discrecionales* por el máximo económicamente respaldado: `Sizing=5% NAV`, `Compound=5% NAV` (sin el hair-cut de pérdidas), `Portfolio=free QORE source`, `Adaptive Leverage=max broker lots and available margin`. QDLE conserva su **5%** de NAV causal, grid min lot/step/max, comisiones OPEN+CLOSE, valoración riesgo a SL, fuente no reservada, no sobregiro de margen y ninguna orden `order_send`. No se cambia `src/qore/infrastructure/cibo_compound_capital.py`; la regla `THREE_SETTLED_LOSSES_HAIR_CUT` de producción permanece intacta.

Parámetros: `--motor-policy independent_four_motors --min-policy broker_grid --ndx-roundtrip-fee-proxy-usd-per-lot 20 --provider-trailing-usd disabled --swap-proxy off --experimental-cibo-administrator --experimental-paper-bypass-strategy-caps`.

**LIMITACIÓN IMPORTANTE:** El provider floor FundedNext no ha sido modelado/confirmado (así lo indica `provider-trailing-usd disabled`); no equivale a cumplirse las reglas del proveedor. SL económico sin distancia mínima histórica verificable = distancia broker mínima **simulada cero**, buffer de slippage/gap **cero**. Este no es un LIVE preflight válido.

## Resultado comparativo de 3.368 señales

| Indicador | Control actual con 4 topes | Investigación PAPER sin cuatro topes |
| --- | ---: | ---: |
| Recepción CIBO, IDs únicos | 3368 | 3368 |
| Propuestas QDLE SL original, tratadas con R histórico Trader (proxy) | 359 | **430** |
| Cotizaciones QDLE con SL económico NUEVO; nunca filled/settled | 209 | **2938** |
| No financiables en **modelo** | 2800 | **0** |
| Resultados de la estrategia CIBO administrada PnL/DD/PF | **No medible** | **No medible** |
| Fills reales MT5 | 0 | 0 |

**ATENCIÓN sobre USD6,67, DD93,20%, PF0,77:** el ensayo *sin topes* liquida únicamente las **430 operaciones con SL original** mediante `gross_structural_outcome_r` histórico. Su `qore_ending_capital_usd=USD6.674285339129795797615610877`, `max_closed_equity_drawdown_pct=93.19891523911788094132176844`, `profit_factor_proxy=0.7733680829433232834159110673` son métricas de una **cartera incompleta de control híbrido**, que excluye 2938 quotes nuevos y todos sus posibles resultados. No representan el capital final ni la calidad del CIBO real. La diferencia frente a los 359 originales corresponde a haber cambiado secuencia/financiabilidad bajo el flag de investigación.

Los resultados CIBO administrador se mantienen explícitamente `cibo_manager_full_real_strategy_NAV_USD=null`, `cibo_manager_full_real_strategy_DD=null`, `cibo_manager_full_real_strategy_PF=null`, y `real_fundednext_fills=0`.

## Interpretación y prohibición de sobreinferencias

1. La ablation demuestra que la suma de **cuatro topes estratégicos** era el binding cuantitativo que impedía cotizaciones, pero **NO** que aumentar entradas sea positivo. Una operación con nuevo SL no se puede liquidar con el R del viejo SL.
2. `2938/3368` son simples QDLE `ECONOMIC_STOP_QDLE_PHYSICAL_QUOTE_SHADOW`, dependientes del NAV de la cartera de control de los 430 exits y de condiciones de bróker no autenticadas; no hay cartera simultánea de 3368 fills.
3. NO suprimir riesgo 5%, Bank/Cushion, protecciones de posición, validación de lotes, margen o comprobación de órdenes de producción. Sin ellas puede haber pérdidas superiores al capital de Core.
4. Antes de elevar algo a producción: reconstrucción de price-path bid/ask, stops ATR causales y `order_calc_profit/order_calc_margin` reales, reglas FundedNext, comisiones ambos lados, salidas CIBO A1 (parciales/trailing/BE/adversa), NAV secuencial real por brazo y comparación DD MTM con límites CEO 20%-25%.

## Código y pruebas

- [Script de replay](../../scripts/qdle_3368_dual_ledger_replay.py) implementa el flag `--experimental-paper-bypass-strategy-caps` condicionado al modo CIBO administrador + cuatro motores y sin directivas live/native.
- [Workflow PAPER](../../.github/workflows/cibo-p0-3368-paper-no-strategy-caps.yml) obliga 3368/3368 decisiones, override en cada oportunidad válidamente recibida, conserva 5% all-in en cada propuesta, cero broker fills, métricas CIBO auténticas NULL.
- En la ejecución: tests QDLE **17**, tests administración **11** PASS y workflow completo SUCCESS. El intento previo de CI tuvo un error YAML de nombre de job, ya corregido, sin afectar al experimento exitoso.

**Decisión:** usar este brazo únicamente para diagnóstico de las restricciones. El usuario no ha aprobado una modificación de seguridad que se pueda representar como despliegue validado; PR #745 sigue DRAFT.
