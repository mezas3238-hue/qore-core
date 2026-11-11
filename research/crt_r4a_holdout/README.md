# QORE CRT RADAR PRO R4-A → trader de investigación 34 instrumentos / holdout 24 meses

**Estado: CANDIDATE / RESEARCH ONLY / NO LIVE / NO MERGE / NO VPS / NO BROKER ORDERS.**

## Propósito y estado real

Construye la etapa de **ejecución simulada de un trader** para hipótesis del indicador Pine R4-A. La lógica de `f_engine()` de Pine (3546 líneas) **no está portada ni certificada** por este módulo. Por seguridad, el simulador exige una cinta `events.csv` que solo puede producirse con un detector/replay externo que demuestre **paridad 100%** con `f_engine()`, incluyendo H4 NY, M5 provider phase, DST, gaps, pivotes causales y los 34 símbolos.

- Source Git: `mezas3238-hue/qore-deepseek-reviewer`, rama `qa/crt-34-v34-12x-integration-ci-20261109`, `crt-radar-pro/qa-integrated-34/QORE_CRT_34_R4_AB_400_M5_AUTO_BUFFER_QA.pine`.
- SHA Git **blob** exacto: `693e3f49719e86e2ea0702f7b355af33bd0c4c7c`.
- El indicador Pine R4-A usaba `calc_bars_count=400` M5; **400 M5 no equivalen a un histórico de 24 meses**. El replay independiente requiere toda la secuencia con precalentamiento (warmup) y datos del mismo proveedor.
- La compilación histórica / runtime TradingView R4-A tiene incidente RE10110 reportado por Owner; CI de este trader no lo corrige.

## Hipótesis, separadas y aún NO certificadas

| Modelo | Estructura | Primera información completa | Entrada candidata |
|---|---|---|---|
| `A_2C_MSS15` | C2 H4 barre un extremo de C1, cierre interior; MSS M15 propio | `max(C2_close, MSS15_close)` | límite al punto medio del cuerpo C2 |
| `B_TRUE3C_MSS5` | C1 → C2 sin barrida → C3 barre C1 y retorna; MSS M5 propio durante C3 | `max(C3_close, MSS5_close)` | límite al punto medio del cuerpo C3 |

El importador de eventos exige `available_at >= max(ratified_at, mss_at)`. Para B exige `mss_at <= ratified_at`. Nunca infiere que `phase == 2 && modelKind == CRT_2C_RETURN` forme parte de TRUE 3C. La implementación actual se apoya en **eventos confirmados externamente**; NO identifica por sí misma CRT históricos ni MSS.

Hipótesis iniciales de gestión (de DeepSeek, **NO parámetros implícitos del Pine**):
- Precio límite = `(H4_open + H4_close)/2` de C2 para A o C3 para B, disponible solo tras ratificación H4.
- Distancia máxima a H4 close: `0.5 × ATR(14) H4`. El evento externo debe traer ATR confirmado, causal.
- Orden caduca tras 12 horas **de calendario UTC**. Esta aproximación no equivale exactamente a 3 velas H4 negociadas; se debe certificar la caducidad H4 exacta antes de promoción.
- SL LONG = `min(C1.low, sweepH4.low) - max(0.25×ATR_H4, bid_ask_spread)`; SL SHORT = `max(C1.high, sweepH4.high) + buffer`.
- TP LONG = `C1.high`, SHORT = `C1.low`, siempre del lado rentable de la entrada. Si hay SL/TP inválidos, no se abre trade.
- Fill LONG con **ask**, salida LONG con **bid**; fill SHORT con **bid**, salida SHORT con **ask**. Comisión y slippage provienen de un archivo independiente; se expresan en unidades equivalentes de precio, con evidencia del broker.
- Si la barra previa al fill toca nivel de SL, la orden se cancela por ambigüedad; si ya hay trade y SL y TP tocan misma M5, SL primero (conservador).
- Al faltar datos para cerrar trade, la evaluación **falla** y no llama ganadora/perdedora a una operación abierta.

**Limitaciones importantes:** no hay simulación de ticks intrabar ni cola de órdenes, stop-level real, fills parciales, conversión monetaria de contratos, tamaño de posición, margin, correlación cross-market, ni cartera conjunta con solapes. Las métricas que emite son R netas por instrumento/modelo, **no curva de capital ni rentabilidad sobre una cuenta**. No afirmar PF económico total certificado sin resolver estas limitaciones.

## Ventanas y congelación

- Desarrollo propuesto: 2022-01-01 a 2022-12-31 UTC.
- Validación propuesta: 2023-01-01 a 2023-12-31 UTC.
- Holdout **candidato**: **2024-01-01 00:00 UTC (incluido) → 2026-01-01 00:00 UTC (excluido)**: 2024 y 2025 completos.
- **HOLDOUT UNTOUCHED NO DEMOSTRADO.** Es obligatorio un certificado explícito de no exposición previa. Si 2024-25 ya fue usado para ajustar modelos, el estado es **BURNED** y debe definirse una ventana nueva de 24 meses nunca usada. No aceptar un SHA de dataset como prueba de virginidad.
- Nunca mirar ganancias de holdout para ajustar parámetros y reusar los mismos 24 meses como si fueran una prueba independiente.

## Datos requeridos; no presentes en esta rama

Directorio `data/` contiene **solo `manifest.json` de bloqueos**. Los datos históricos no están depositados en GitHub. `runner.py preflight` devuelve `BLOCKED` hasta que existan **todos**:

1. `data/quotes/IC_<SYMBOL>.csv` para cada uno de los **34** mercados en el orden inmutable. Encabezados:
   `opened_at,bid_open,bid_high,bid_low,bid_close,ask_open,ask_high,ask_low,ask_close` con barras M5 **UTC** ordenadas y `YYYY-MM-DDTHH:MM:SSZ`. Cobertura de **dos años completos y warmup**; mínimo 50k barras por feed y extremos a 10 días de los bordes (solo pre-chequeo, no certificación de continuidad).
2. `data/events.csv`: columnas
   `event_id,symbol,model,side,sweep_at,mss_at,ratified_at,available_at,c1_high,c1_low,body_open,body_close,sweep_high,sweep_low,atr_h4`.
   Todos los eventos deben estar confirmados y ser causales por detector independiente con paridad Pine. Incluye **todos** los elegibles y motivos de N/V en reporte científico externo.
3. `data/costs.json`: objeto con 34 claves, cada una `{"commission_price": float, "slippage_price": float}`, convertidos desde comisiones y contrato del broker a unidades de precio para la posición.
4. `data/manifest.json`: SHA-256 de los 36 archivos individuales, fuente, datasheet de sesiones/cobertura, evidencia de costos, 100% paridad temporal y evidencia externa de que holdout permanece virgen. Los flags no son por sí mismos una certificación: deben acompañarse de referencias realmente verificables y auditadas.

**Se prohíbe generar CSV sintéticos y etiquetarlos como mercado real.**

## Ejecución en GitHub Actions

El workflow `CRT R4-A 34 - 2Y holdout research QA` arranca en el PR aislado y:
1. Ejecuta pruebas deterministas **sintéticas** de cálculo LONG/SHORT, secuencialidad y fail-closed.
2. Produce el artefacto `crt_r4a_preflight.json` de preflight del holdout.
3. Verifica que no se reportó `READY` sin evidencias, y publica el estado **BLOCKED**.

Manual cuando estén disponibles y certificados **todos** los insumos:

```bash
python research/crt_r4a_holdout/runner.py preflight \
  --root research/crt_r4a_holdout/data --out reports/preflight.json

python research/crt_r4a_holdout/runner.py run \
  --root research/crt_r4a_holdout/data --out reports/holdout.json
```

Si falta una precondición, `run` sale con código 2 y produce `BLOCKED`, nunca cifras.

## Estado de aceptación

- **Programa de trader / simulador de ejecución**: implementado en investigación; tests synthetic no equivalen a rendimiento.
- **Detector Pine portátil / parity**: NO CONSTRUIDO, requisito previo.
- **34 históricos M5 bid/ask + costos**: NO DISPONIBLES en este repositorio.
- **Holdout de 24 meses**: VENTANA CANDIDATA, **NO ABIERTO**.
- **Modelo A / Modelo B rentables**: DESCONOCIDO, no medido.
- **DEMO/LIVE**: NO AUTORIZADOS; Trader Lab conserva sus propias puertas gobernadas.

Cuando se cumplan las precondiciones, los números se auditarán instrumento por instrumento, por modelo, y con control de múltiples pruebas y solapes, antes de cualquier veredicto.
