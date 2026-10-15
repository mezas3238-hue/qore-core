# VT31 M5 — PRE-REGISTRO protegido swing source, no price/broker stop certification

2026-10-15. OWNER exige certificación por METODOLOGÍA y COGNITIVA, no PF, DD, retornos o conteos. Registrado antes de código/CI.

## Fuentes primarias verificadas
- [TTrades AM Silver Bullet NQ, 2025-06-19](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/): stop beyond displacement-causing swing, H1 09h raid/return NY AM; no definición cuantificada única de swing.
- [Protected Swings in Trading, 2025-08-06](https://ttrades.com/protected-swings-understanding-trends-and-invalidations/): swing protegido tras liquidar low/high o entrar FVG, luego cerrar por encima de serie de down-close candles bullish / bajo serie up-close bearish; hasta cierre NO protegido.
- [Stop Loss Mastery, 2025-08-07](https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/): inversión segura bajo protected low / sobre protected high; body alternative con riesgo distinto. No confundir con política G3 C2 wick/1tick/2tick. Estas fuentes posteriores a artículo AM son fuente auxiliar doctrinal, no licencia para reasignar su regla única silenciosamente.

## Gate semántico research pre-declarado
- Entrada: M1 sólo cerradas y contiguas en NY AM 10–11, lado LONG/SHORT, nivel H1 09h confirmado antes del raid, raid timestamp y extremo LOW/HIGH probado, series contigua de down-close/up-close candles dentro de raid→displacement, cierre desplazamiento que supere **todos** los cuerpos relevantes de la serie y ocurra después del raid, testigo causal `protected_low`/`protected_high` calculado a partir del wick de raid/series observado antes del cierre.
- Si falta raid en H1, serie opuesta, cierre MÁS ALLÁ de serie, información M1 futura, orden intrabar ambiguity, o límite temporal → `WAIT/UNKNOWN`, no habilitar SL. Si se satisfacen → `RESEARCH_PROTECTED_SWING_SOURCE_CONTEXT_WITNESSED`, invalidación CONCEPTUAL low/high, sin broker price, tick offset o ACK.
- `displacement_causing_swing_author_final_identified=false` incluso con contexto protegido, porque la identificación exacta de *qué swing causó desplazamiento* para stop del artículo AM y cuando existen múltiples cambios M1 requiere ejemplo autoral y revisión humana independiente. No usar min/raids genéricos como stop definitivo ni inferir que stop C2 de G3 sea autoral.

## Escenarios prereg
- LONG primer LOW raid bajo H1 09 low90 a89, serie down-close candles 10:01 y 10:02, confirmación cierre desplazamiento > máximos del cuerpo down-close, stop conceptual protected low89, C2 wick high/low puede ser 93 en 10:03: distintos; eliminar cierre > serie da WAIT.
- SHORT espejo HIGH raid sobre H1 09 high110 a111, serie up-close candles 10:01/10:02, confirmación cierre < mínimos del cuerpo up-close, protected high111; C2 wick high109 no equivale a 111; eliminar cierre rompe confirmación => WAIT.
- Hay serie opuesta faltante ⇒ WAIT; raid sólo wick de una M1 con BOTH high/low H1 extremos ⇒ UNKNOWN; M1 future ⇒ REJECT; fuente 09h incompleta ⇒ UNKNOWN; close confirmación antes de raid ⇒ REJECT; DST EST/EDT => hora fuente NY causal.
- Todos los resultados `source_context_not_stop_certified`, `method_certified=false`, `cognition_certified=false`, `live_authorized=false`, `orders=0`, `lots=0`, `pnl=None`; no retrofitting del original G3 ni M5 firma fake.

## Integridad
Original G3 blobs COG d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9, OPS 0ce9707314aecb71155de8b57044b6ec028847b2, acta e99c70b4e018d626fb620d9a21b9314a51abc36d immutable. PR DRAFT, no merge, VPS/FundedNext LIVE/OMS/sizing. M6 human source review and dual signatures #897 PENDING.