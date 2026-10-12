# QORE Native G1 — Preregistro del Gate causal de cotización (NO simulador NET)

Fecha: 2026-10-12. Este Gate se define **antes de ejecutar los checkpoints reales**; se ha observado previamente la distribución histórica de spreads cero en estos cinco mercados, así que el ensayo de ingeniería de cobertura es descriptivo, **no holdout virgen**. No hay todavía datos de señales/órdenes de los traders certificados, ni de comisiones, tamaños de lote o swaps.

Fuente: únicamente [PR #859](https://github.com/mezas3238-hue/qore-core/pull/859) original 5 mercados BID+ASK y su Protobuf tick field source [artifact #11764163362](https://github.com/mezas3238-hue/qore-core/actions/runs/38288411671/artifacts/11764163362), verificados primero por segundo decodificador [PR #860](https://github.com/mezas3238-hue/qore-core/pull/860). Fechas de la fuente: 2021-03-16 y 2023-03-21, 13:00–13:30 UTC; mercado EURUSD/GBPUSD/USDJPY/XAGUSD/SP500→US500.

## Decisiones de fuente ficticias congeladas
Por cada una de las 5×2 ventanas, **2 pares de checkpoints**, horarios exactos y fijos, escogidos por reloj, no PnL:
- Par A: inicio +05min (*entrada ficticia*) y +15min (*salida ficticia*);
- Par B: inicio +10min y +25min.

Total 5×2×2=**20 pares de checkpoints de calidad fuente**. **NO son operaciones, NO son entradas/salidas reales de las 231 estrategias, NO estiman PF/Sharpe/DD.** Es una prueba del motor y de la posibilidad técnica de encontrar cotizaciones BID+ASK vigentes en ambos tiempos.

## Contrato fail-closed
- En cada instante, elegir únicamente el último BID y último ASK con `market_timestamp <= decision_time`, nunca el próximo ni interpolar datos M1/M5.
- Bloquear si falta cualquier lado; bloquear si el último lado es >5000ms antiguo (parámetro de ingeniería preregistrado), si BID>ASK (crossed), si BID=ASK (zero) o duplicados conflictivos en mismo milisegundo.
- Un par entra a `PAIR_SOURCE_ELIGIBLE_NO_NET` **solo si ambos timestamps** tienen `OK_POSITIVE_BIDASK`. Contar rechazados por etapa; prioridad status de entrada sobre salida, pero guardar los dos.
- Cualquier mismatch de ticker/provider/sha/protobuf/time UTC => abortar, no imputar precio ni escoger ventana alternativa. Preservar SHA de informe. No publicar precios, tokens ni cuenta.
- Los tick-field protobuf de este artefacto fueron capturados bajo cuenta DEMO y no son testimonio de latencia/receipt-time real; NO autorizar negociación/ejecución aunque ambos lados sean positivos.

## Cierre aceptable
CI pasa regresiones sintéticas sin lookahead y verifica las 20 identidades de par, source data SHA+segundo-decoder, y publica solo estadísticas de `OK/MISSING/STALE/ZERO/CROSSED`. Eso avala únicamente un **Gate de calidad fuente y decisiones ficticias**, no futuros precios en instantes reales de una estrategia, no costos, ni NET. G1 sigue bloqueado por [#856](https://github.com/mezas3238-hue/qore-core/issues/856) spread cero, [#857](https://github.com/mezas3238-hue/qore-core/issues/857) contratos y [#837](https://github.com/mezas3238-hue/qore-core/issues/837) vault privado para los datos crudos. No VPS/MT5/LIVE/CIBO/Shared/QDLE.
