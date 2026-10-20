# VT08 CRT tres fuentes V2 — pre-registro de verificación de destino/invalidez sobre ruta M5 (SIN SIZING)

**Fecha:** 15-OCT-2026, antes de ejecutar lifecycle. **La V2 de generación de hipótesis queda INMUTABLE** (commit `ad190683b91298cf07b6b7aefe87779f56146401`), no modificar para mejorar resultados.
**Datos consumidos:** Atlas original AUDUSD y USDJPY 296.372 M5 2024–2026, NO OOS. [Lab source V2 #38711787794](https://github.com/mezas3238-hue/qore-core/actions/runs/38711787794): **745 candidatos conceptuales (353/392)** sobre 5.524 H4 C1/C2. Ni estos candidatos ni un outcome de precio son operaciones. No hay sizing ni exposición, PF ni rentabilidad.

## Experimento pre-fijado (fuente→invalidez→destino, observación de precio únicamente)

- Tomar **SOLO** eventos `CONCEPTUAL_CANDIDATE` originales V2, clave `source_event_id + first_conceptual_decision_clock_utc`; prohibido añadir o eliminar candidatos según desenlace.
- **Nivel de invalidación físico:** low M15 de la segunda vela del par M15 confirmado para tesis bullish; high de esa segunda vela para bearish. Es una definición QORE de condición estructural para investigación, **NO stop broker ni sizing/SL monetario**.
- **DOL:** midpoint H4 C1 preexistente (2× relative price = C1.high+C1.low); objetivo de observación de precio, no orden TP.
- **Punto inicial de observación:** primer M5 que ABRE exactamente al reloj `M15 C2.closed_at` original. Es **un proxy de precio**, NO bid/ask ni fill. Si ausente/atrasado o ya más allá de destino/invalidez, declarar `UNCERTAIN`; nunca inventar apertura ejecutable.
- **Prueba primera trayectoria:** desde ese primer M5 y sólo hasta **cierre H4 C3**, observar cronológicamente si toca primero la invalidez o el DOL. Ambos alcanzados dentro de una misma M5 → **`INVALIDATION_FIRST_AMBIGUOUS_SAME_M5`**, juicio conservador; si el cronograma tiene gap antes de terminal → `UNKNOWN_MISSING_M5`, no optimismo.
- **Sin toque antes de fin de C3:** `EXPIRED_WITHOUT_TOUCH`. La fuente no puede rearmar al mismo padre después de invalidez/target/expiración. Nunca reutilizar C3 como criterio para emitir el evento original.
- **Publicar para TODOS los 745 candidatos**: mercado, año, hora, flags y conteos por outcome; ninguna pips PnL/R/lote/equity/PF/DD/Sharpe/Sortino como sustituto de economía real. Un hit rate es diagnóstico de precios, no edge neto.
- Requiere pruebas con fixtures positivo, negativo, toque dual, missing, gaps, reloj; invocar Runner read-only original con SHA, sin credenciales broker.

## Resultado necesario para certificar (AÚN NO EVALUADO)

G-M1..G-M4 deben probar metodología tri-source QORE y cognitiva, G-M5 acta; un ciclo de precio sin tamaño no alcanza. La certificación global aparte requiere **ejecución realizable y costes BID/ASK**, política de métricas PF/DD/Sharpe/Sortino *preaprobada*, OOS limpio/walk-forward, stress/MC, Risk/CIBO e independiente; **DD patrimonial solo en módulo CIBO/Risk**, ningún sizing del Trader. Si el modelo V2 falla el test de precio, declarar NO_SUPPORT de V2, no retunar los mismos datos para garantizar edge.
