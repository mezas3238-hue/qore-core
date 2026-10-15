# VT31 — M4-CLOSED-M1 V2: preregistro de retest causal antes de código

**Fecha:** 2026-10-15 · **Rama:** `agent/vt31-m4-closed-m1-source-admission-20261015` desde `92c0a1e224e46588e4d2642104db4a9115d80d57` (#978).
**Fuentes primarias:** [TTrades AM Silver Bullet NQ, 2025-06-19](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/), [Breaker Blocks Simplified, 2025-07-05](https://ttrades.com/breaker-blocks-simplified/), [Order Blocks Simplified](https://ttrades.com/order-blocks-simplified/). Los artículos no son una definición causal completa del stop único en cada trade.
**Código V1 de investigación auditado:** `scripts/vt31_m4_ob_breaker_author_evidence_gate_20261015.py` PR #961. **NO modificar V1 ni COG/OPS G3.**

## Bug verificable en V1
La primitiva `Candle.at` es el **timestamp de apertura** del minuto M1, pero `_clock()` solo rechaza `retest.at > as_of`; por tanto acepta un retest cuyos `high/low/close` aún son futuros cuando `retest.at == as_of`. El dossier sintético positivo de V1 contiene literalmente `as_of=anchor` y `retest=Candle(anchor, ... high/low/close...)`. La etiqueta `RESEARCH_OB_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING` no ha probado disponibilidad causal en ese minuto. La falla afecta de forma simétrica la ruta Breaker. Un PASS histórico V1 **NO** se transformará en PASS V2 ni será ocultado.

## Especificación preregistrada: V2 autónoma, fail-closed
1. Timestamps `as_of`, `first_raid_at`, `displacement_at`, `Candle.at`, `Swing.extreme_at` y `Swing.confirmed_at` **aware** UTC-comparables, M1 candle `at` alineada a minuto completo. Nunca interpretar datetime naive como timezone local del runner.
2. Exigir `as_of == retest.at + 1 minute` para un retest M1 **completamente cerrado y recién observado**. No usar la vela que abre en as_of, aunque el V1 la considere válida. Otros candles aportados deben haber cerrado antes de `as_of`; fuente OB opuesta debe cerrar no después de `displacement_at`.
3. Fuente TTrades **solo NYAM** 10:00–11:00 hora `America/New_York` (DST automático) y `retest` dentro del mismo día/ventana; raid debe ser previo al displacement y ambos confirmados antes del retest. En V2 `raid/displacement` son tiempos de confirmación, no intraminuto.
4. Validar side LONG/SHORT, perfil `TTRADES_NY_AM_2025`, retest tipado como `Candle`, confluencia y OB/Breaker mediante el **juez V1 intacto** solo después de los guards. Un rechazo temporal **no ejecutará adjudicate_ob/breaker**, comprobado con monkeypatch.
5. Los estados V1 `RESEARCH_OB_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING` y `RESEARCH_BREAKER_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING` siguen etiquetados como **estructura research incompleta**. La acción cognitiva V2 es siempre `WAIT` mientras M3/M4 autoral y M5 swing causante/stop permanezcan sin homologar. Ninguna respuesta de V2 emite DTO operable.
6. Bloqueo en `AS_OF` de vela incompleta, candle HTF/FVG/zone futura, gap temporal de vela M1 o confirmación de swing futura. No inferir retest, swing causante ni fills desde OHLC.
7. Falsadores positivos: OB y Breaker LONG/SHORT, EST(enero)/EDT(julio), restituir causalidad pasando `as_of=retest.open+1m`, sin alterar el `open/high/low/close` del testigo. Cualquier diferencia de juicio fuente V1 para testigos cerrados se documentará.
8. Falsadores negativos: misma vela con `as_of=retest.at`, naive, fecha/sesión incorrecta, intrabar ambiguous, vela OB no cerrada antes de displacement, zone future, retest caducado o antes de displacement, perfil ICT no autorizado, side wrong, swing confirmada en el futuro; no fabricar evidencia autoral.

## Evidencia exigida
Publicar módulo y tests nuevos, workflow Python 3.12 `pytest-xdist -n 4`, Ruff, 3 hashes G3 congelados y SHA del prereg ancestro de código, dossier JSON con estados y SHA256SUMS en artifact. Separar evidencia de gate estructural y certificado humano. Sin PnL, sizing, OMS, LIVE, merge a main ni firmas fingidas. Estado: **METODOLOGÍA PENDIENTE / COGNITIVA PENDIENTE**.

**Decisión metodológica de investigación:** no añadir política matemática de stop para salvar el edge. La ambigüedad del swing causante mantiene `WAIT` incluso si el OB/Breaker es visible después de cerrar M1.
