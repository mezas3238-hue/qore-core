# QORE CRT TRADER R1 — conversión del indicador original a estrategia Pine v6

**Corte 12 de noviembre de 2026 UTC · QA de investigación · NO LIVE · NO VPS · NO MERGE.**

## Entregable

`research/crt_r4a_holdout/pine/QORE_CRT_TRADER_R1_V34_12X_ORIGINAL_ENGINE_QA.pine`.

El objetivo es demostrar que el **motor original** del indicador detecta configuraciones que pueden operar con una hipótesis económica, sin recrear un detector alternativo. Se derivó directamente del archivo Pine V34.12X de 34 IC Markets en `mezas3238-hue/qore-deepseek-reviewer`, rama `qa/crt-34-v34-12x-integration-ci-20261109`, Git blob fuente **`693e3f49719e86e2ea0702f7b355af33bd0c4c7c`**.

La función original `f_engine()` fue copiada íntegra y **sus reglas geométricas, pivotes, ventanas H4/M15/M5, DST, sesiones, familia y selección no se reescribieron**. Solo dos cambios dentro del motor: eliminación del condicional `barstate.islast` que convertía `FamilyVisual.new(...)` y `Signal.new(...)` en `na` para la historia. El test `test_pine_strategy_r1.py` reconstruye los dos condicionales originales y compara el SHA-1 Git blob **`777fa066e7aea2274d236750d6475979b05042ce`** del cuerpo completo de `f_engine()` con el blob de origen. **Esto comprueba igualdad del texto del motor, NO la compilación o la paridad real de TradingView.**

## Diseño y restricciones

- `strategy()` Pine v6 independiente; el archivo original **no se modifica**. No existen llamadas activas a `request.security()`, `alert()`, webhooks ni brokers.
- Estrategia sobre **un solo símbolo abierto**. El catálogo inmutable incluye exactamente **34 `IC:`**, pero hay que abrir cada mercado por separado para obtener sus operaciones y métricas. TradingView no ejecuta `strategy.entry` en otros 33 símbolos desde un gráfico.
- Requisitos: gráfico **5 minutos**, proveedor exacto IC Markets (`syminfo.prefix == IC`), barras OHLC estándar (no Heikin Ashi/Renko), M5 cerrado y estado estructural ratificado. Por defecto exige fase M5 **0**; la fase nativa +1/+2 sigue pendiente de homologación.
- Entradas simuladas **apagadas por defecto**: el usuario debe activar manualmente `Habilitar SOLO ordenes simuladas`. No configura alertas de órdenes.
- Ejecución conservadora: `pyramiding=0`, `process_orders_on_close=false`, `calc_on_every_tick=false`, `calc_on_order_fills=false`. El motor consume `time[1]` y el emulador intenta completar la orden al comienzo de la barra siguiente. Comisiones **0,02 %** y slippage **2 ticks** se han fijado solo como supuestos visibles de QA, **NO como condiciones verificadas de IC Markets**. El usuario puede cambiarlos en Propiedades de la estrategia.
- Cantidad `qty=1` por defecto: **NO representa necesariamente un lote estándar forex/CFD**. Ajustar tras certificar multiplicadores, divisas y tick sizes del broker.
- El SL/TP de R1 es una **HIPÓTESIS NUEVA**, NO reglas de operación incorporadas al indicador: SL más allá del extremo de C1 (o mecha de retest M15 para F7) más 15 % del rango C1, TP en el lado opuesto de C1. Se exigen R:R >= 1.0, riesgo de precio <= 5 % del precio, brackets coherentes, ningún trade con SL/TP inválido. No se deben optimizar contra el holdout consumido.
- No hay matching individual de bid/ask, swaps, comisiones por contrato, tasas de conversión multimoneda, degradación de liquidez ni cartera multiactivo. **TradingView Strategy Tester = simulación aproximada, NO certificado de rentabilidad neta.**

## Siete hipótesis separadas

| Modelo de investigación | Entrada condicionada a |
|---|---|
| F1 CRT 2C MSS15 C2 | CRT 2C ratificado + MSS M15 de la misma barrida/C1 confirmado en C2 |
| F2 CRT 2C MSS15 C3 | CRT 2C ratificado + MSS M15 propio y causal en C3 |
| F3 TRUE 3C MSS5 | La categoría TRUE 3C y su pivote + ruptura M5 propios, no el MSS del CRT 2C |
| F4 Inside Return MSS15 | Geometría Inside de su C1 y su propio MSS M15 |
| F5 Multi4 MSS15 | Geometría Multi4 y su MSS M15 propio |
| F6 Multi-N MSS15 | Geometría Multi-N, C1 propia y confirmación propia M15 |
| F7 Retest M15 | Retest posterior al MSS15 del CRT padre, M15 cerrada, mismo pivote y C1 |

Por defecto se selecciona **solo F1** para evitar mezclar estrategias y sesgar resultados. Modo `ALL`: si varias familias aparecen por primera vez en una misma barra, se bloquea el grupo entero; **NO selecciona la familia vencedora a posteriori**. Un contador separado registra los conflictos.

**Limitación de siete modelos:** la UDT del indicador original expone **solo una familia auxiliar seleccionada a la vez** (`extraFamilyKind` prioriza TRUE 3C, Inside, Multi-N, Multi4). Por ello este R1 **no demuestra que contabilice de forma independiente y completa todos los eventos de las siete familias** cuando se superponen; para certificar cobertura total debemos ampliar el contrato Pine para emitir siete series/identidades causales *sin alterar la detección*.

Se excluyen explícitamente los roles de catálogo QA pendientes, expansión rechazada, continuación Inside rechazada, históricos, MSS de otra C1, y toda forma de selección por `qaCatalogMask != 0` sin prueba causal.

## Uso en TradingView (una vez compilado)

1. Abrir TradingView, gráfico estándar de un símbolo `IC:` del catálogo, **M5**.
2. Abrir `Pine Editor`, pegar **el archivo R1** completo y ejecutar `Add to chart`/Agregar al gráfico.
3. **Primer gate:** registrar los resultados de compilación. Si muestra error, NO considerar la estrategia operativa ni alterar el indicador original; corregir el archivo separado.
4. Configuración: seleccionar familia F1..F7, verificar costos/tamaño ficticio, y activar `Habilitar SOLO ordenes simuladas`. Dejar desactivado para inspección sin entradas.
5. Abrir el `Strategy Tester`: verificar la lista de trades, timestamps de confirmación MSS, SL/TP, pérdida máxima, PF, expectancy y casos sin señal. Registrar resultados **para cada uno de los 34**, no solo el mercado donde se vea mejor.
6. Contrastar cada trade con el indicador original y su OHLC **mismo broker/mismo M5**; si divergen, investigar y bloquear certificación. Más adelante contrastar con nuestro ledger M5 original y costos bid/ask.

El código original era de aproximadamente 3.547 líneas y su retorno `Signal` estaba limitado al último estado; el R1 extrae el bloque completo `f_engine()` y evita ejecutar el pesado dashboard de 34 `request.security`. Esta reducción de trabajo es **una hipótesis de rendimiento**; no tenemos cronometraje real en TradingView.

## Comprobaciones y bloqueo de certificación

- QA GitHub en `test_pine_strategy_r1.py`: 12 pruebas estáticas del blob f_engine, fuente de 34 símbolos, siete familias, guardas causal-MSS/SLTP, ausencia de llamadas broker/alertas, perfil de ejecución y bloqueo por tipo de gráfico.
- Laboratorio general del branch incluye pruebas sintéticas independientes; son un control de código, **no equivalen a compilar Pine**.
- **NO verificable con GitHub Actions:** compilación en Pine Editor de TradingView, historial real del Strategy Tester, cero discrepancias evento a evento con el indicador, equivalencia histórica 34/34, costos IC, ni 24 meses de holdout virgen. El período 2024–2025 ya está consumido.
- La firma y la instantánea source están fijadas; **NO MERGE** sin orden expresa, NO VPS, NO ejecución automática ni capital real.

### Referencias oficiales

- [TradingView — Declaración `strategy()`](https://www.tradingview.com/pine-script-docs/language/declaration-statements/)
- [TradingView — Emulador, estrategia y entradas/salidas](https://www.tradingview.com/pine-script-docs/concepts/strategies/)
- [TradingView — Chart estándar](https://www.tradingview.com/pine-script-docs/concepts/chart-information/)
