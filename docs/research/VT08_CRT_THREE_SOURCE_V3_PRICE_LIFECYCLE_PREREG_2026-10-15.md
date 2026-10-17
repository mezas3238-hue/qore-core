# VT08 CRT QORE — V3 CONFIRMED (THIRD CANDLE) — PREREGISTRO LIFECYCLE M5

**Fecha:** 15-OCT-2026. **Esta acta queda publicada ANTES de inspeccionar outcomes de V3**. Censo V3 ya conocido: 5.524 padres H4, **139 candidatos conceptuales: 61 AUDUSD, 78 USDJPY**, [CI #38749028744](https://github.com/mezas3238-hue/qore-core/actions/runs/38749028744), **ACEPTADO SOLO COMO DENSIDAD DE INVESTIGACIÓN, NO EDGE**. Código V3 no debe mutarse por resultados económicos.

**Identidad EXACTA:** `VT08_CRT_THREE_SOURCE_QORE_V3_CSD_THIRD_CANDLE`. Fuente-método combinada RomeoTPT + SpeculatorFL + TraderFlameseN con tercera vela y confirmación de cuerpo QORE engineering claramente etiquetada. Cuenta original Atlas M5 AUDUSD y USDJPY ya consumido, **NO holdout nuevo**.

## Hipótesis y regla de desenlace PRICE-ONLY — congeladas antes de leerlas

1. Replay genera exactamente los source event IDs de V3 **sin mirar el desenlace posterior**. Sólo procesar `CONCEPTUAL_CANDIDATE_V3`, reconciliar 61/78 source IDs con los outputs originales del run de GitHub. Cualquier discrepancia no se «corrige» eligiendo los ganadores.
2. **Nivel estructural invalidante:** low (bullish) o high (bearish) de **M15_SOURCE**, es decir, la vela anterior a M15_CONFIRM, que a su vez precede al reloj de decisión. Validar ese valor contra la geometría original precierre; rechazar cualquier fuente corrupta o falta de M5.
3. **Destino fijo:** midpoint H4 C1, `target_twice = H4_C1.high + H4_C1.low`, ya conocido al cierre de H4 C1. No usar un target nuevo adaptado retrospectivamente. Para V3, los casos en que ese nivel ya fue tocado antes de la confirmación fueron rechazados en el generador V3.
4. **Inicio de trayectoria:** primer M5 que ABRE al cierre de `M15_CONFIRM` exactamente. No inventar BID/ASK, spread, fill ni precio a M5 anterior. Si el primer M5 no existe o la apertura no está entre las barreras, devolver UNKNOWN.
5. **Final:** cierre de la **misma H4 C3**. Nunca leer el siguiente H4 para decidir el desenlace de la fuente. Primer nivel tocado cronológicamente por wick M5: `DESTINATION_FIRST`, `INVALIDATION_FIRST`; ambos alcanzados en una M5 → `INVALIDATION_FIRST_AMBIGUOUS_SAME_M5` conservador; datos ausentes → UNKNOWN; ningún nivel → `EXPIRED_WITHOUT_TOUCH`. Confirmación exacta al último M15 de C3 no es candidate, ya viene EXPIRED.
6. **Estado real:** NO trade, NO ejecución, NO rentabilidad, NO R-multiple, NO lotes, NO sizing, NO stop bróker, NO Profit Factor, NO Sortino, NO DD, NO Sharpe. Resultado de primer toque sólo representa **ruta de precio observada**, no economía neta.
7. Ledger TODOS los 139 casos: source ID, UTC, market, invalidación, destino, causa y observación M5. Conteos por mercado/año, zero lost IDs, SHA256 y **no fuente de retrospectivas**.
8. Falsación: si dominan las invalideces, dictaminar V3 adversa en vez de optimizarla; si no dominan, sigue SIN edge económico hasta disponer de BID/ASK broker/fills, umbrales PF/DD/Sharpe/Sortino preaprobados, OOS realmente no visto, WFO, stress/MC y revisión Risk/CIBO externa.

**No sizing CIBO-trader, no merge, demo/live/MT5/VPS ni órdenes. G-M1..G-M4 aún PARTIAL, G-M5 NOT_ISSUED, GLOBAL NOT_CERTIFIED.**
