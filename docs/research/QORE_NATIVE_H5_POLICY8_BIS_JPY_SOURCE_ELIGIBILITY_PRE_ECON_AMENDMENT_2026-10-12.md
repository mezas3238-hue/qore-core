# H5 ENMIENDA PRE-ECONÓMICA — elegibilidad de fuente BIS JPY, NO cambio de estrategia

**12 oct 2026. Enmienda documentada después de conocer únicamente cobertura de FUENTE, antes de cualquier PnL H5.** La primera ejecución [Actions #38324000515](https://github.com/mezas3238-hue/qore-core/actions/runs/38324000515) verificó 28/28 M5 fuentes G0 SHA y cinco series BIS, pero detuvo ANTES del cálculo económico con `H5_BIS_NO_SINGLE_EIGHT_CURRENCY_SERIES_OR_LOW_COVERAGE` en JPY. La segunda corrida [Actions #38324456193](https://github.com/mezas3238-hue/qore-core/actions/runs/38324456193) reordenó preflight de BIS para no descargar M5 antes de las tasas y reveló `H5_BIS_INCOMPLETE_JPY_series=1_count=96_first=2016-09-01_last=2024-08-01`.

**Hecho estrictamente de fuente:** BIS `WS_CBPOL/M.JP` tiene 96 puntos mensuales de 2016-09 a 2024-08 (96 meses), sin meses faltantes dentro de ese intervalo. Los otros cinco primeros países ya fueron verificados 104/104; quedan NZD/USD por verificar en nueva corrida. Ningún Sharpe ni PnL devuelto antes de esta enmienda.

**Cambio mínimo único de elegibilidad:**
- Conserva DEV 2016-09-17..2021-12-31, DIAG 2022-01-01..2024-09-16, y el holdout desde 2024-09-17 cerrado. Reglas de señal, long6/short6, dos meses de lag, peso 1/12, mensual, 2bp por lado, universo FX28 y benchmark económico separados quedan INTACTOS.
- Como `m−2` para septiembre/octubre 2016 requiere julio/agosto 2016 inexistentes en serie histórica japonesa BIS, **no abrir posiciones durante esos dos meses iniciales; quedar cash** y comenzar primer rebalance elegible en noviembre 2016 usando septiembre 2016. **No imputar JPY** anterior ni usar valor 2026. El PnL DEV de los dos meses en efectivo es 0, con calendario original completo; DIAG intacto.
- En toda fecha elegible posterior, **las ocho tasas del mismo mes rezagado son obligatorias**. Si una falta, abortar antes de presentar un Sharpe, sin quitar activos ni reoptimizar.
- Código procesador original quedó anotado `FIRST_RATE_COMPLETE_DECISION_MONTH=date(2016,11,1)` y exige continuidad real en la fuente desde 2016-09 a 2024-07. Esto NO reinterpreta ni salva un resultado económico; no se ha observado PnL.

**No es un cambio de estrategia ni una búsqueda de Sharpe ganador.** Es una corrección de prereg al constatar fecha de nacimiento de una de las ocho fuentes oficiales, visible antes de leer resultados. Se publica incluso si falla el siguiente test, y debe acompañar todas las conclusiones de H5.

Concentración FX, BIS versión actual 2026 y diferenciales de política no broker swap quedan como caveats. **0/3 traders, producción intacta.**
