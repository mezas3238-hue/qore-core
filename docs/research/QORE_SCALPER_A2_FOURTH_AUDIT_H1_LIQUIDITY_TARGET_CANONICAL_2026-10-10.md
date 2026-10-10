# QORE Trader Scalper — 4ª auditoría DeepSeek: destinos H1, fidelidad TTrades y prueba causal

**Fecha:** 2026-10-10. **Arquitecto B:** PR #759, issue #757. **Arquitecto A:** PR #758, issue #756. **Padre:** PR #623. **Estado: RESEARCH ONLY / NO LIVE, NO VPS, NO MERGE, NO CERTIFICACIÓN.**

## 1. Resolución de afirmaciones de la cuarta auditoría

La aritmética V49 es **real y perjudicial**: de 2.020 operaciones seleccionadas con MAX3, 1.569 tienen target planificado <1R, y de 1.030 salidas por TARGET completo, 949 pagan menos de 1R, 779 <0.5R, 517 <0.25R. Media TARGET +0.392147R, mediana +0.246547R; no hay parciales del 50% ni stop BE en V49. Ver el [auditor 9/9 #38059512447](https://github.com/mezas3238-hue/qore-core/actions/runs/38059512447). Esto determina una **asimetría desfavorable del payout en el control V49**, pero no demuestra por sí solo que el H1 bias, M15 CISD, M1 entrada, riesgo del stop y timing sean correctos. La tasa de equilibrio `1/(1+0.2465)` para target mediano vs stop 1R aplica a un **juego binario hipotético**, no a toda la mezcla de R, STOP/TARGET/SESSION_EXIT.

### Fuentes **PRIMARIAS** verificadas

- **SRC-TGT-026**: TTrades [How to Set Price Targets Using the Fractal Model](https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/), 2026-05-23. Los objetivos se establecen en **swing highs/lows previos no barridos** y también **previous candle highs/lows de temporalidad superior**; no descarta todos los high/low individuales de velas H1. Los objetivos no se deben seleccionar arbitrariamente después de saber el resultado. Confirma que targets parciales y runners son *posibles*, **no obligatorios**.  `SOURCE_EXPLICIT`.
- **SRC-TGT-027**: TTrades [Internal & External Liquidity Using the TTrades Fractal Model](https://ttrades.com/internal-external-liquidity-using-the-ttrades-fractal-model/), 2026-08-22. Liquidez **EXTERNA = swing high/low con pivot confirmado a derecha**; liquidez **INTERNA = FVG**. Un movimiento de interna a externa precisa reacción/Candle 2 o 3; el FVG no se convierte universalmente en target de continuación. Se contempla en contexto reversión tras sweep, no autoselección incondicional. `SOURCE_EXPLICIT`.
- **SRC-TGT-028**: TTrades [Scalping Model](https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/), 2026-02-07: H1 sesgo de scalp, M15 swing, M1 ejecución, target HTF, protected swing stop. Daily en autor es contexto más amplio, pero **NO se ha añadido** como gate QORE. `SOURCE_EXPLICIT`.
- **SRC-TGT-029**: TTrades [Using Order Blocks for Continuations](https://ttrades.com/using-order-blocks-for-continuations/), relevancia Sweep+CISD: espera cierre sobre/por debajo de **la serie de velas OPUESTAS** después del sweep/POI, no mera penetración del swing barrido. El código `capitalizer_ttrades_m1_cisd_observer_v48.py::_series_ending_at` y `observe_first_m1_cisd` ya usa serie opuesta y `bar.close > series[0].open` LONG / inverso SHORT. Hay que auditar ejemplos multivela y *as-of*, pero **no se encontró en esta lectura un gatillo que equivalga solo al sweep**. `PARTIAL` hasta fixture/9 market.

**Corrección material a la propuesta DeepSeek:** la secuencia **Weekly/Daily > H1 FVG > H1 swing > último high** no aparece como jerarquía obligatoria en estas fuentes y viola la arquitectura exclusiva H1→M15→M1 acordada. El motor no infiere D/H4/W desde M1 como sustituto de autorización ni introduce filtros Daily/H4. Un H1 FVG es interna, un swing H1 es externa: mezclar destinos de diferente narrativa sin cierre causal sería distorsionar el autor. La jerarquía nueva es una **HIPÓTESIS DE QORE** con categoría explícita.

## 2. Prerregistro causal: revisión de targets sin filtrar nuevas entradas

Código implementado en B:
- `src/qore/infrastructure/trader_lab/capitalizer_scalper_h1_liquidity_target_v1.py`: catálogo as-of, selección estructural **primero swing H1 externo confirmado y aún no barrido**, y **extremo H1 V49 original como fallback** cuando no hay swing válido. Los FVG H1 internos se inventarian pero NO se convierten automáticamente en objetivos de continuación.
- `tests/infrastructure/trader_lab/test_capitalizer_scalper_h1_liquidity_target_v1.py`: confirma derecha del pivot H1 antes de entrada, veto de toque previo, decisión M1 aún no cerrada, fecha H1 futura, contradicciones de source y fail-closed.
- `src/qore/infrastructure/trader_lab/capitalizer_scalper_h1_liquidity_paired_replay_v1.py`: escenario M1 native 9 market fuente congelada **GitHub Actions #35548099334** y V49 original **#38053946695**, comparando **`V49_FROZEN` vs `H1_EXTERNAL_FIRST`**.
- [Contrato causal #38061214136](https://github.com/mezas3238-hue/qore-core/actions/runs/38061214136) **GREEN**.
- [Ensayo económico objetivo SOLO #38061448754](https://github.com/mezas3238-hue/qore-core/actions/runs/38061448754) **en ejecución cuando se redacta el contrato**. NO publicar PF/DD nuevos antes de la agregación 9/9 GREEN.

Selección de target nueva:
1. Construir H1 desde M1 nativo, solo `h1.closed_at <= trigger_confirmed_at`. Confirmar `H1_EXTERNAL_CONFIRMED_SWING` en el **cierre de la vela derecha H1**; verificar que ese high/low sigue no mitigado en los M1 **cerrados antes/igual al trigger**, nunca el high/low de la vela M1 abierta en el instante de decisión.
2. Elegir la referencia H1 externa **más cercana en precio dentro de la clase de pivotes ya confirmados** para no asumir objetivos artificialmente lejanos. Es un ranking técnico QORE, no source universal ni un filtro por distancia/R; no escoger según MFE futuro.
3. Si no existe pivot externo apto, mantener el testigo original: el high/low de la más reciente entre las 24 velas H1 cerradas que se mantenga sin consumir. La reconstrucción de ese testigo con M1 nativo debe **coincidir exactamente** con `source.structural_target_witness_price` (en caso contrario abortar la investigación, nunca eliminar silenciosamente la entrada).
4. M15 protected swing original, M1 entrada original, first-three-per-session/day MAX3 original, SL-first intrabar y cierres de sesión V49 **inalterados**. Cero umbral R mínimo y cero veto a Sweep/FVG.
5. Mantener FVG interno disponible como **contexto/alternativa no admitida automáticamente** hasta que exista documento de reversión con cierre CISD y test preregistrado. No reemplazar el swing externo por un FVG interno indiscriminadamente.

Controles de admisión/economía: **misma población source 2,876**, mismas **2,020 seleccionadas** al MAX3, idéntico baseline trade `dataclass` en cada mercado (stop, entry, target, fechas, R, salida); reportar solo *diferencia por target* en el brazo alternativo. Retención por source ID original `1,167` ganadores, R ganador base `461.9427618`, límites Owner `>=934` ganadoras y `>=415.74849R` masa ORIGINAL ganadora. Explorar tasa `TARGET_HIT`, PF bruto, DD secuencial, coste-stress 0.01R/0.05R sin confundirlo con BID/ASK físico. Todos resultados IN-SAMPLE, no certificar sin OOS, costos broker, A1 Master Frame FULL.

### 3. Protección contra HARKing y falsas certificaciones

**Prohibido** editar elección de pivot, ranking, dirección, stop, umbral R o familias basándose en resultados del replay actual; si falla causalidad, solo se permite reparar ingeniería y reiniciar con changelog. El motor NO reinterpreta últimas señales y no toca funciones de producción. Un target alternativo con PF alto a costa de perder el 80/90% de ganadores sigue **NO CERTIFICABLE**. Un target alternativo con recuperación de ganadores pero PF<1 bruto sigue **NO CERTIFICABLE**. Un resultado 9/9 exitoso tampoco implica que Shared/CIBO/Cognitiva A1 real hayan decidido trades.

**Pendiente**: fidelidad M1 Sweep+CISD sobre velas opuestas, fuente H1 maturity/as-of y rangos de sesiones como alternativas explícitas, no priorizar por HARKing; test de retención y MFE/MAE por target se discutirán después del resultado, siempre con separación OOS.

**Ramas:** PR #759 DRAFT, PR #758 DRAFT, parent PR #623 DRAFT, sin merge. TODO se ejecuta en GitHub, no VPS ni LIVE.
