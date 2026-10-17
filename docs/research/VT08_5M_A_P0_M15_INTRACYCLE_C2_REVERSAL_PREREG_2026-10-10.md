# VT08 5M P0-A — PRERREGISTRO M15 INTRACYCLE C2 REVERSAL — Fuente TTrades
Fecha 2026-10-10. **CONTRATO DE INVESTIGACIÓN PRE-PNL**. No producción, no certificación. Arquitecto A #762 / Arquitecto B #763 / PR #765, #634. Base SHA `77dcce2b4c6a104c714f15c929fa8c2fab1c6f33`.

## Falla metodológica investigada

El B01 histórico exige que una C2 anterior completa tenga un único barrido y vuelva a cerrar dentro del rango de la referencia H4, que haya PS confirmado antes del nuevo H4 open, y supone fill exacto en ese open. El autor **sí describe operar intraciclo de una vela C2** tras formar wick→CISD→protected swing, antes de terminar ese H4. Esta ruta no es capturada por el modelo open-positional estrecho.

**Autoridades oficiales consultadas antes de cualquier nuevo PnL**:
- TTrades (2025-09-20) https://ttrades.com/trading-the-4-hour-power-of-3-open-high-low-close-strategy/ — secciones "Identifying Candle Types", "Using Lower Timeframes", "Continuation vs. Reversal Scenarios": C2 con wick poco profundo puede expandir dentro de la misma vela tras formar protected swing; C3 cuando el opposing run es grande. No aporta umbral numérico de shallow/large, NO INVENTAR.
- PDF oficial https://ttrades.com/wp-content/uploads/2025/09/H4-PO3-TTrades-PDF.pdf — pp. 7–10 (PDF índices 7–10) muestran CISD y ejemplos intra-candle de continuation/reversal H4. PDF timing incluye 13:00 entre las seis velas H4 Forex; no es licencia para extender las ventanas del Owner.
- TTrades (2025-08-16) https://ttrades.com/how-to-trade-candle-2-ttrades-fractal-model/ — apartado "Execution": esperar a wick, CISD en entry timeframe y target condicionado por wick; 15M/5M en NY.
- TTrades (2025-08-07) https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/ — PS como invalidación, no entrada prematura.
- TTrades (2025-09-06) https://ttrades.com/how-to-trade-candle-3-in-the-fractal-model/ — vía C3 distinta y requiere confirmación de contexto. No se incorpora como C2.

Estas fuentes verifican identidad de **reversal intracycle C2** pero NO garantizan que un fill exacto next-M15-open con TP 2R sea una regla original. Esas son **formalizaciones QORE de investigación**, no SOURCE_EXPLICIT. El video original completo/frame SHA todavía falta verificar; no afirmar auditoría audiovisual acabada.

## Bundle P0-A M15-C2-REVERSAL-INTRACYCLE-RESEARCH-V1 (preregistro sin optimización)

1. Universo exacto EURJPY USDCHF NZDUSD CADJPY USDCAD; tres anchors del Owner 01/05/09 America/New_York. Cada anchor define ventana **[H4 open, H4 open+4h)** sin añadir otras horas.
2. Observación independiente **M15_STANDARD** con barras OHLC M15 completas, con referencia H4 inmediatamente anterior completa (C1), y bias previo de los **dos source-day** disponibles a la apertura de H4 (mismo helper congelado `resolve_bias`, día 17NY→17NY marcado CONTENCIÓN QORE). Bias irresoluble implica NO nuevo trade.
3. Reversal C2 intracycle: esperar sweep de extremo C1 contrario a bias (importante nivel) durante la nueva H4; una serie M15 opuesta y una vela M15 de confirmación que **cierra cruzando open de la primera opuesta** confirma CISD/PS. Reutilizar `protected_swings_in_candle2` y requerir que `opposing_series_opened_at < confirmed_at <= decision_at`. No requerir que la **C2 misma cierre dentro de C1** antes de operar, porque todavía está en curso.
4. **Entrada:** elegir primera confirmación causal y primer M15 open siguiente (no mismo cierre sin coste). Este next-open es **QORE exact-OHLC-fill research assumption**, no promesa de broker BID/ASK.
5. **SL:** extremo del protected swing, de lado correcto; sin spread-offset en primera investigación; ese offset es QORE provisional y el broker coste sigue no medido.
6. **TP:** 2R fijo solo como **comparador QORE provisional**, NO meta universal del autor; destinos y wick size requieren adjudicación de fuente y pruebas separadas.
7. **Caducidad:** no generar señal si no queda al menos una vela M15 completa en H4; posición abierta se cierra al final del mismo H4 en simulación, etiquetado `QORE_FILLED_H4_LIFECYCLE_UNRESOLVED`.
8. **Cardinalidad Owner:** aceptar en cada mercado y día NY **solo el primer evento cronológicamente ejecutable**, sin resultado/score/filtro de ganador; señalar competidores por día y registrar todos los first-fail. La elección de primer evento es formalización de investigación, no regla TTrades universal.
9. **Ambigüedad OHLC:** si en la misma M15 son posibles SL y TP, ejecutar el **SL primero**; no optimismo. Falta coste BID/ASK y comisión en la evidencia si no está; sin su medición no hay certificación.
10. Nunca mirar futuro para confirmar PS, valorar riesgo ni elegir operación; se puede recorrer la ventana H4 para **descubrir cuando ocurren** confirmaciones, pero un trade sólo es evaluado desde `entry_at >= confirmed_at`.
11. **Reporte separado obligatorio:** 1) base B01 488 mechanical/457 terminal históricos, 2) nuevos eventos intracycle 3) elegibles post-risk 4) seleccionado por día 5) terminales simulados 6) raw equal-risk R/PF/DD etiquetados metodología-solamente, costos desconocidos. Nada de PF cognitivo hasta B adapte CandidateEvent y pruebe 100% de consumo real.
12. Rechazos: no source H4, no source-day, unresolved bias, incomplete M15 window, no PS, no valid next bar, invalid risk geometry; múltiples PS diagnosticados y primera confirmación **causal** fija, no selección ex-post. Ningún FVG universal artificial.
13. **Identidad v1 única:** no se cambiarán parámetros al ver PnL; si falla, falsificada. Investigación solo en corpus **consumido** 1095D original run 35934924907. Archivo 7Y sellado, Owner density gate pendiente.

### Asimetría que hay que documentar, no borrar
Una entrada M15 C2 intracycle no es un atajo hacia un C3 válido y no justifica abrir ambas direcciones. `C2_CLOSE_NOT_INSIDE_REFERENCE=3987` es primera exclusión del B01 terminado, no volumen de señales C2 intracycle validadas.

### Coordinación cognitiva
Architect B PR #764 deberá consumir nuevos CandidateEvents con `source_event_id` estable, `event_fingerprint` snapshot, método/tiempos/PS/SL/TP/expiry, ausencia de inventos de bias-fingerprint as-of y motivo separado de WAIT/ABSTAIN. **Este preregistro NO modifica CandidateEvent V1 todavía**; contrato fuente efectivo de expansión será propuesta revisada por B antes del replay cognitivo. No clonar la clase estrecha si fuerza `decision_at = H4_open` para esta identidad nueva.

La ruta más rápida no es retirar todas las protecciones sino **completar entradas que el autor explica pero nuestro replay nunca ejecutó**.
