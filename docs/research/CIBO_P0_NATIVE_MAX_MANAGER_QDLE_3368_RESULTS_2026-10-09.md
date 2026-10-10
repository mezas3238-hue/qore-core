# CEO P0 — Replay completo 3.368: MAX Native cognitivo + CIBO administrador + QDLE

**Informe de ingeniería; 2026-10-09** · [GitHub Actions #37911594114 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/37911594114) · [artefacto completo de las 3.368 decisiones y dos brazos #11606736959](https://github.com/mezas3238-hue/qore-core/actions/runs/37911594114/artifacts/11606736959) · PR [#745](https://github.com/mezas3238-hue/qore-core/pull/745) · branch `agent/cibo-sovereign-integration-p0-20261008`.

## Alcance exactamente verificado

Se cargaron con hash SHA256 los 3.368 Traders originales (`11451743578`) y los 3.368 recibos de **inteligencia genuina MAX Native históricos** (`11588089131`, ZIP `eebf6de43da63aadc200a3783109246188d46e0fcdd7da127f07eff815d6cec6`). Script `scripts/cibo_p0_native_max_manager_advisory_3368.py` hizo una conciliación estricta de 3.368/3.368 IDs, reloj predecisión `decided_at` y `trader_id` con `native_maximum_intelligence=True`, `full_semantics_consumed=True`, `outcome_used_for_predecision=False`, 0 llamadas externas. Huella del set de recibos de administración `sha256:aee72a5401489c5938c803f04281156d0c26b443fc5f1638aaf4c81547b328f5`.

**Advertencia de procedencia:** el run exitoso #37911594114 leyó los **recibos MAX Native sellados preexistentes**, no volvió a ejecutar desde cero el algoritmo `cibo_single_account_historical_ceiling_replay.py`. El workflow se amplió posteriormente para ensayar también una reevaluación Native MAX fresca: no sustituir resultados verificados anteriores sin un run completado. La clasificación BANK/MEDIUM/ATTACK es una **política shadow nueva que traduce diagnósticos legados a propuestas de gestión**, no modos negociados/ejecutados físicamente por MAX Native.

### Recepción Native MAX sin su filtro obsoleto

| Registro Native MAX | Señales | Plan shadow propuesto |
| --- | ---: | --- |
| Cognición con abstención histórica `COGNITIVE_BLOCK` | 1804 | BANK (gestión prudente) |
| Cognición OK, antigua limitación de capital `CAPITAL_BLOCK` | 1553 | MEDIUM |
| Antigua disposición de revisión Risk `RISK_REVIEW_READY` | 11 | ATTACK |
| **Total** | **3368** | **3368 planes propuestos** |

La nota cognitiva Native se conserva por señal: 1629 `nonpositive-causal-expected-net-utility`, 140 `walk-forward-provisional-forecast-history-required`, 35 `walk-forward-cold-start-history-required` y 1564 `native-causal-state-bounded-confidence`. Es observación de calidad económica para planificar parciales/trailing/defensa, **no admisión de Trader**. El plan experimental BANK/MEDIUM/ATTACK prescribe umbrales distintos a medirse solo con barras bid/ask y causalidad; **no se aplicaron estos planes a cierres históricos**.

### QDLE con MAX Native: 3368/3368 señales

| Concepto | Cuatro motores con topes | PAPER CEO sin los cuatro topes discrecionales |
| --- | ---: | ---: |
| MAX Native evaluadas predecisión | 3368 | 3368 |
| CIBO administrador recibe Trader | 3368 | 3368 |
| Lotaje QDLE financiable con SL original (Trader exits proxy) | **359** | **430** |
| Cotizaciones QDLE con SL económico modificado, solo shadow | **209** | **2938** |
| No financiables bajo escenarios proxy | **2800** | **0** |
| Fills MT5 verificados | **0** | **0** |
| PnL del gestor MAX Native+CIBO completo | **NO MEDIBLE** | **NO MEDIBLE** |

**Qué significa "sin topes":** solo se omiten las cuotas *estratégicas* de Sizing, CIBO Compuesto, Adaptive Leverage y Portafolio Compuesto en el programa de replay con flag `--experimental-paper-bypass-strategy-caps`. QDLE mantiene su 5% de QORE NAV al stop protector, coste all-in (OPEN+CLOSE), margen de proveedor, broker lot grid, fuentes/Bank no reservadas y 0 orden SEND; no se modifica el runtime LIVE ni los módulos de producción. El 5% y los limites físicos pueden impedir LIVE aun si un proxy produce una quote.

## Capital y DD: métricas ÚNICAMENTE de operaciones SL original

| Subconjunto simulado con salidas estructurales previas | Con topes | PAPER sin topes |
| --- | ---: | ---: |
| Operaciones con SL estructural original y R histórico | 359 | 430 |
| Capital inicial de control proxy USD | 60 | 60 |
| Resultado neto **solo ese subconjunto** USD | **−50.48253250** | **−53.32571466** |
| Capital cerrado **solo ese subconjunto** USD | **9.51746750** | **6.67428534** |
| Profit factor del subconjunto | **0.78147160** | **0.77336808** |
| Max drawdown **closed equity** del subconjunto | **87.40357309%** | **93.19891524%** |
| Resultado CIBO Native MAX gestor tras nuevas 209/2938 stops | **DESCONOCIDO** | **DESCONOCIDO** |

**No atribuir los USD9.52 ni los USD6.67 como capital final de CIBO MAX Native administrador.** No hay trayectorias históricas ejecutables bid/ask para saber cuándo saltan SL económico, BE, trailing, TP, parciales o cierres defensivos en las nuevas 209/2938 propuestas. El NAV secuencial de estos escenarios usa **únicamente las operaciones SL original** y no actualiza NAV tras las quotes nuevas. El archivo fuente 2019–2022 está consumido como research, no certificación OOS. Drawdown de closed equity no mide intratrade MTM.

## Evidencia y limitaciones

- Run `#37911594114`: 17 tests de autoridad QDLE + 11 tests CIBO intake + 11 tests managed-exit unitarios, 3368 Native genuine evidence receipts, 3368 CIBO, 3368 QDLE por dos brazos, cero filtros legados aplicados, cero MT5 fills, ninguna reclamación de PnL/DD del administrador.
- El escenario FundedNext usa snapshot de margen 2026, fees FX USD14/lote ida y vuelta, NDX USD20/lote hipótesis y XAU notional proxy; volatilidad/ATR históricos no aportados; la distancia mínima histórica del broker se simula `0` y buffer gaps/slippage `0`, lo que puede inflar la financiabilidad.
- Los modos MAX Native son derivados de sus recibos y ejecutables solo como **plan shadow**, NO son un simulador de salidas realmente ejecutado. CIBO y QDLE tienen contratos independientes; no confundir recepción CIBO con autorizaciones de un bot sin límites.
- Estado **NO LIVE / NO CERTIFICADO**.

## Próximos trabajos imprescindibles para el verdadero capital final de CIBO MAX Native+QDLE

1. Bar data histórica y verificable bid/ask o ticks, seis instrumentos, timeframe causal por señal y histórico de spreads; ATR14 Wilder de velas cerradas para SL económico.
2. Reproducir las 3368 señales bajo MAX Native real con plan económico/cognitivo por señal, **ejecutar decisiones de parciales, trailing, break-even y reducción defensiva** en la trayectoria y modelo de orden conservador.
3. Vincular los cuatro motores y Bank/Cushion a cada fill/settlement real simulado para QORE NAV dinámico **del manager**, no del control; QDLE al margen, SL, fees, min lot y fuente en cada reentry.
4. Calcular cashflow final, PF/DD cerrado e intratrade, pérdidas, comisiones, factibilidad de 0.01, no-leakage y breach del proveedor. Solo entonces considerar políticas con/sin hair-cut de pérdidas por tres trades.
