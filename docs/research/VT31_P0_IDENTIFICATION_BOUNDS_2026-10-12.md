# QORE CORE — VT31 P0: límites identificables del ensayo pareado con spread 1,60

**Fecha:** 2026-10-12. **Rama:** `agent/vt31-p0-paired-bounds-20261012`. **Ámbito:** scientific read-only; un solo VT31 en Londres y Nueva York, FVG/MSS ejecutivo M1; ninguna modificación a entrada, stop, target, COG/OPS, broker, producción, VPS o Fresh Holdout.

## 1. Cadena de custodia efectivamente verificada

1. Documento de partida: [Handoff Maestro #872](https://github.com/mezas3238-hue/qore-core/pull/872), commit `b7004e08475c2c7ad71816102a638918a2f7ba4f`. Auditoría previa [#873](https://github.com/mezas3238-hue/qore-core/pull/873).
2. Artefacto original **11750991244** de [CI #38257774657](https://github.com/mezas3238-hue/qore-core/actions/runs/38257774657) fue recuperado con GitHub Actions, sin rehacer ni modificar los inputs; `SHA256SUMS` interno pasó, incluidos los bytes de `vt31-fixed-spread-1p60-source-3y.json`. Su código de origen se cotejó con `90deb73a47cbc09b88580595800607f2516323b7`, SHA de fuente M1 heredada `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, únicamente como huella documental previamente validada (este workflow NO recalculó SHA de las velas crudas).
3. **[GitHub Actions #38312155226 — PASS](https://github.com/mezas3238-hue/qore-core/actions/runs/38312155226)**, análisis en commit `b01e5b0eac783030452acea979056032cb1c136a`: **16/16 tests**, `ruff` y `py_compile`; análisis de exactamente **2.140 IDs pareados únicos**, conciliación de 766 London + 721 NY AM + 653 NY PM, revisión de 619 UNKNOWN de misma M1 + 51 geometría, prueba de protección de guardas LIVE/holdout; salida y manifiesto SHA256. Nuevo artefacto **11775401621**.
4. Run inicial del nuevo gate **#38312098236 FAIL** por convención de nombres de seis tests (Ruff N802), corregida exclusivamente en tests sin retocar la matemática, y reproducido con éxito en #38312155226.

## 2. Pregunta de identificación — no es todavía PnL

La observación A232/B577 del escenario fijo 1.60 es una condición **M1 precio-lateral sintética**, dado el supuesto explícito **M1 histórico tratado como MID** y **BID=MID−0.80, ASK=MID+0.80**. Un único snapshot MT5 NDX100 no verifica el MID NAS100 ni el contrato/histórico; el escenario nunca genera broker fills.

**Estimando:** ¿cuánto puede diferir el número de *primeros contactos potenciales de CE compatibles con el lado quote* de B respecto a A en los mismos 2.140 FVG fuente, antes de conocer el orden de los eventos indeterminados?

En cada pareja original de FVG:
- `VALID_CE` **y** lado cotización sintético compatible: valor exactamente 1, sólo como contacto proxy (NO fill).
- Cualquier clase terminal conocida sin contacto compatible: 0, dentro de esta métrica observacional, no como operación económica.
- `INDETERMINATE`: rango lógico 0 a 1; **no rellenar a posteriori** basándose en qué mejora el resultado.

Se suman mínimos y máximos **candidato por candidato** antes de contrastar B−A, conservando la pareja y la ventana. Es una envolvente algebraica permisiva, no intervalo de confianza ni probabilidad de ganancia. La física de un único camino de precios podría imponer restricciones adicionales, pero no se inventan sin orden intraminuto auténtico. Para certificar ventaja de contacto al menos +5pp con todos los casos inciertos, el límite inferior tendría que superar el umbral: NO lo hace. Aun si lo hiciera, el preregistro original sigue exigiendo B UNKNOWN ≤10%.

## 3. Resultados medidos de nueva prueba independiente

| Universo | N | A conocido 1.60 | B conocido 1.60 | A unknown | B unknown | B−A conocido | B−A mínimo | B−A máximo |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| London | 766 | 77 | 165 | 230 | 237 | +88 | −142 | +325 |
| New York AM | 721 | 97 | 231 | 216 | 223 | +134 | −82 | +357 |
| New York PM | 653 | 58 | 181 | 191 | 210 | +123 | −68 | +333 |
| **TOTAL** | **2.140** | **232** | **577** | **637** | **670** | **+345** | **−292** | **+1.015** |

**En todo VT31:** diferencia conocida +16.121495 pp; **límite lógico mínimo −13.644860 pp**, **máximo +47.429907 pp**. Como el intervalo contiene cero y valores inferiores a +5pp, la magnitud de mejora B NO queda identificada de forma robusta al tratamiento de UNKNOWN con la base fuente actual.

**Advertencia esencial:** los máximos no son contactos observados, y los mínimos no son pérdidas. Ningún elemento de esta tabla estima fill probabilidad, slippage, stop, target, win rate ni PnL. Corregir indeterminados por comportamiento posterior sería fuga de resultado. No se han abierto datos Fresh Holdout.

La rama B original incumplió su **gate preregistrado obligatorio de ≤10% unknown**: 670/2.140 = 31.308411%, descompuestos en 619 eventos de cronología CE/cancelación/target same-M1 y **51 geometrías de stop protegido invalidables sólo por método**. No reescribir umbral ni sustituir por el rango del nuevo análisis.

## 4. Qué se demostró y qué sigue siendo desconocido

**Demostrado:** las cuentas A/B del informe previo son reconstruibles a partir del ledger original, la custodia del artefacto pasa hashes, y la aparente ventaja B de contactos 1.60 depende de cómo se resuelvan casos que M1 no puede ordenar. Resultado lógico compatible tanto con B superior como con B inferior a A.

**No demostrado:** que el contacto sea una orden enviada/aceptada/ejecutada; que un CE LONG ejecutase por ASK o SHORT por BID reales; que stop/target se alcanzasen después de fill; que coste histórico o contrato NDX100 coincida con el histórico NAS100; ni expectancy, PF, Sharpe, Sortino y drawdown netos.

**Distinción crítica para OPS:** los 619 UNKNOWN de secuencia **pueden** reducirse con ticks auténticos sub-M1 y condiciones de orden/latencia, pero ticks de precio SIN logs de cancel/ACK no prueban fills. Los **51 UNKNOWN de geometría** NO se resolverán simplemente descargando ticks: requieren decidir qué swing protegido/stop constituye una regla causal válida, revisión ICT frente a formalización QORE y tratamiento preespecificado de casos metodológicamente no elegibles.

## 5. Criterios de siguiente etapa (sin seleccionar ganadores)

1. **OPS / Datos:** buscar inventario read-only de cualquier historial de ticks auténtico ya custodiado (mismo broker, symbol_info y timestamps). Si se obtiene, fuente segura offline, SHA privado, documentación de cobertura/secuencia, sin cuentas ni tokens en GitHub. Revisar identidad NAS100/NDX100 antes de cruzar datasets.
2. **OPS / OMS:** documentar oferta, aceptación, cancelación, expiración, confirmación externa y posición en ledger. Quote crossing **NO** es fill. El análisis de exposición post-CE sólo tiene significado después de probar elegibilidad y precio de ejecución.
3. **COG y OPS / doctrina:** examinar 51 stop-side-invalid y 619 disputas con definiciones separadas `ICT_EXPLICIT`, `QORE_FORMALIZATION` y `EXPERIMENTAL_B`. Revisión cruzada de `first FVG`, MSS opuesto, swing, target DOL, close de zona y vida de orden. No cambiar método después de observar PnL.
4. **Economía:** cuando haya fuente real comparable y costes acreditados, fijar reglas antes de examinar resultados y ejecutar un solo replay por identidad con todas las pérdidas/ganancias y abstenciones, sesiones en agregado, incertidumbre temporal cluster y control holdout. Si no hay datos adecuados, dictamen final `INSUFICIENTE_EVIDENCIA_POR_DATOS`, no certificación.

## 6. Estado vigente

| Gate | Dictamen |
|---|---|
| Ledger A/B reproducible, hash y fuente reportada | **PASS 2.140 registros; no replay de mercado nuevo** |
| 16 pruebas de límites pareados | **PASS** |
| Beneficio robusto de CE ante indeterminación | **NO DEMOSTRADO** |
| Rama B prereg unknown ≤10% | **FAIL 31.31%** |
| BID/ASK histórico, símbolo y contrato del broker | **PENDIENTE** |
| Fills/ACK/PF/DD neto + salida cronológica | **NO CALCULABLE** |
| Certificación, Fresh Holdout, VPS y LIVE | **NO AUTORIZADOS** |

**Decisión P0 provisional:** `INSUFICIENTE_EVIDENCIA_ECONOMICA`; preservar VT31 como investigación congelada, no añadir cognitiva ni promover rama B.

**Referencias:** [Issue #727](https://github.com/mezas3238-hue/qore-core/issues/727), [Handoff #872](https://github.com/mezas3238-hue/qore-core/pull/872), [Auditor cotizaciones #873](https://github.com/mezas3238-hue/qore-core/pull/873), [CI original 1.60](https://github.com/mezas3238-hue/qore-core/actions/runs/38257774657), [CI límites pareados](https://github.com/mezas3238-hue/qore-core/actions/runs/38312155226).
