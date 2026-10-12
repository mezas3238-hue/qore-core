# QORE CPI EVENT — PRE-G1 source-only power & PIT feasibility: EJECUTADO Y BLOQUEADO

**2026-10-11 (America/Asuncion; GitHub runner UTC 2026-10-12). Estado: `BLOCKED_NOT_EVALUABLE_INFRASTRUCTURE`.** No es una afirmación sobre el mercado ni sobre la existencia o ausencia de retorno CPI. Fuentes consultadas en el ensayo: **únicamente metadatos calendarios/headers y presencia de timestamps** ya validados en G0/G0B. CERO valores CPI, FORECASTS, BID/ASK, OHLC, retornos, PnL y costes importados.

## Evidencia realmente ejecutada

- PR [#813](https://github.com/mezas3238-hue/qore-core/pull/813). [Actions **#38192536589**](https://github.com/mezas3238-hue/qore-core/actions/runs/38192536589) **2/2 SUCCESS**, calidad **16/16 Pytest PASS**, Ruff PASS, ejecución exact head **`1c8f17546c7193152a08c9130f8343f53a3c0b7c`**.
- Artefacto inmutable [**#11722106398**](https://github.com/mezas3238-hue/qore-core/actions/runs/38192536589/artifacts/11722106398), contiene `cpi-pre-g1-feasibility-power-scenarios.json`, `cpi-pre-g1-24-date-source-verification.json`, SHA individuales y `OUTPUT_SHA256SUMS.txt`.
- El motor validó los SHA exactos del calendario BLS de G0 [#11720651765](https://github.com/mezas3238-hue/qore-core/actions/runs/38189483643/artifacts/11720651765), de la presencia M1 CIBO [#11720822239](https://github.com/mezas3238-hue/qore-core/actions/runs/38189483643/artifacts/11720822239), y de las 119 cabeceras de comunicados oficiales G0B [#11721212991](https://github.com/mezas3238-hue/qore-core/actions/runs/38191275999/artifacts/11721212991). Ninguna fecha sustituida ni ajustada.
- Confirmados independientemente **119 originales** BLS archivados y **113/119** eventos con 71/71 velas M1 por timestamp; la muestra de consenso **24/24 fechas** se encuentra en la cohorte sellada, y **23/24** tienen ventana M1 completa; el CPI del **2017-03-15** tiene faltantes de M1, pero sigue siendo dato válido PARA auditoría de consenso (no para replay de precio sin justificación previa).
- **No se consultaron forecast values** ni se simuló una señal de trading; `PIT_vintage_verified=false`, `CPI_window_0835_0905_cost_verified=false`, `G1_economic_authorized=false`, `macro_pooling_authorized=false`.

## Potencia — números de planificación, NO resultado económico

Fórmula bajo i.i.d. evento y test bilateral alfa 5%: `MDE=(1.95996+0.84162)σ/√n`. `σ` aquí es la **desviación estándar hipotética del estimando firmado/pareado**, no la amplitud total de velas ni varianza medida desde el archivo.

| n supuesto | σ hipotética (bps) | MDE aproximado para 80% (bps) | Potencia si ventaja verdadera 5 bps |
|---|---:|---:|---:|
| 113 CPI plenamente cubiertos (techo, aún sin filtro consenso) | 20 | **5,27** | **75,7%** |
| 113 | 40 | **10,54** | **26,4%** |
| 56, si partición de signos/estratos | 20 | **7,49** | **46,5%** |
| 56 | 40 | **14,98** | **15,5%** |
| 560 macro agregados SOLO ejemplo matemático, NO autorizados | 40 | **4,74** | **84,1%** |

Estos poderes son del **test de cero**, más permisivo que certificar **IC inferior neto >0 o >2 bps tras costes**. Ningún resultado económico debe declararse `NEGATIVE` si la fuente es imposible o la potencia no está demostrada.

## Prioridad y ley económica

1. **P0 — G0C Vendor proof**: exigir de Trading Economics demostración licenciada CPI con snapshots verdaderamente anteriores a T0 (2016/2020/2025), vintages T−24h y T−5min, panel y metodología `Forecast` vs `TEForecast`, cobertura mensual/definición MoM headline/core y licencias. El [portal documenta PIT](https://docs.tradingeconomics.com/economic_calendar/point-in-time/), pero su ejemplo de intervalo histórico no demuestra resolución pre-release minuto a minuto. Validar segundo proveedor realmente independiente sobre [24 fechas ya congeladas](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-event-cpi-g0b-archive-release-check-20261011/docs/research/QORE_NATIVE_EVENT_CPI_G0C_TWO_SOURCE_24_EVENT_PIT_COMPARISON_PREREG_2026-10-11.md). Si 24/24 consenso coinciden, es solo control de comparabilidad, no prueba absoluta. **No hay datos/licencia TE verificados aún.**
2. **P0 — G0D Coste real reloj fijo**: una sola ventana candidata de *fricción para sourcing* **entrada 08:35 NY → salida 09:05 NY**, sin señal ni retest. Coste de roundtrip del **mismo NAS100/USTEC CFD IC Markets**, histórico CPI, BID/ASK, spread at both ends, comisión, slippage, latencia, contrato, lotes, moneda y desviaciones en 1×/1,5×/2×, fuente DEMO vs LIVE claramente separada. M1 MID/OHLC no sustituye ejecuciones ni spread.
3. **P0 — Modelado potencia neto**: tras source vintage y costes pero **ANTES de mirar returns de G1**, definir signo de sorpresa y respuesta causal first-online, un único benchmark, efecto mínimo neto relevante, sigma defendible solo de historia de desarrollo/externa, n después de missingness, dependencia y multiplicidad. Establecer capacidad mínima 80% para el umbral económicamente relevante o `BLOCKED_OR_INCONCLUSIVE_POWER`.
4. **CPI-only** para primer G1 futuro; no sumar NFP/PCE/PPI/FOMC por sed de tamaño muestral. Una estrategia macro jerárquica nueva requiere mecanismo común, fuentes, clustering y prereg separado. 5× número eventos ≠ 5× precisión.
5. **Resultado económico permitido** solo si (1)–(3) se resuelven, consentimiento sobre costes/proveedor, G1 frozen y OOS eventual independiente. Hasta entonces: **NO EVALUABLE (infraestructura)**, no `NO_EDGE`.

**Seguridad**: GitHub research only, no cambios CIBO/Shared/QDLE/VPS/MT5, sin importar datos sensibles, 0 traders nuevos certificados. Nunca guardar claves o forecasts licenciados en repo público sin derecho explícito.
