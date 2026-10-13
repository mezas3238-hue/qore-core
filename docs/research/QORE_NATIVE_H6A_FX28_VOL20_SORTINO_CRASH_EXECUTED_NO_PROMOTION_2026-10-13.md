# QORE Native H6a — GLOBAL VOL20 carry FX28 sobre universo existente: EJECUCIÓN ECONÓMICA FINAL

**Ejecutado el 13 oct 2026 UTC. Resultado: `NO_PROMOTION_EXPLORATORY`. No repetir H6a variando target, Sortino, lag, pares, nocional, seed de bootstrap o ventanas después de ver estos datos.**

## Linaje inmutable

- [PR de investigación H6a #890](https://github.com/mezas3238-hue/qore-core/pull/890), rama `research/qore-native-h6a-existing-window-vol20-sortino-20261012`, DRAFT sin merge a producción.
- **[Prereg H6a ANTES de PnL](QORE_NATIVE_H6A_EXISTING_G0_FX28_VOL20_SORTINO_CRASH_PREREG_2026-10-12.md), commit `8a2b9605e562a243fc2f79b48367d946f062ae13`**, derivado de H6 previo #888 pero con ventana **2016-09-17 a 2024-09-16** en vez de 2010–2015. No se afirma independencia estadística: DIAG 2022–2024 estaba expuesto H1–H5, análisis adaptativo.
- **[GitHub Actions #38328728365](https://github.com/mezas3238-hue/qore-core/actions/runs/38328728365), COMPLETED SUCCESS 2/2 jobs**: 10/10 controles sintéticos PASS (incluyen no mirar cierre de sesión decisoria en vol20, límite apalancamiento, costes, embargo, cálculo mensual, bootstrap) y prueba económica histórica 28 FX originales G0 SHA11 particiones + 8 tasas BIS política m−2.
- **Código económico EXACTO ejecutado: `c1de69772bd798c3b379ad37966ce65a293973ef`**. La única modificación entre el primer CI fallido y SUCCESS fue arreglar que un precio **SINTÉTICO** en los controles tests cruzaba cero después de ocho años; no se cambió regla ni datos económicos.
- [Artefacto Actions #11782127979](https://github.com/mezas3238-hue/qore-core/actions/runs/38328728365/artifacts/11782127979), digest ZIP `sha256:17330dc28483647c3af14b44f391ece3246a6f2bcdb317528b6e57d989a6e8c7`, caduca **2026-11-12T00:48:38Z**. Archivo JSON con estadísticas, 28 source SHA manifests y 8 BIS SHA; no raw M5 o tasas ni precios del holdout. Antes de la caducidad copiar prueba a vault licenciado per #837.

## Hipótesis, contabilidad y sesgos

8 tasas mensuales reales BIS para monedas AUD CAD CHF EUR GBP JPY NZD USD; ranking FX28 por tasa(BASE) − tasa(QUOTE) mensual con **dos meses de lag m−2**; abrir seis pares largos y seis cortos, ±1/12 antes de sizing. Primer rebalance **noviembre 2016** (JP serie BIS no tiene tasas suficientes para sep/oct 2016), cash inicial. En cada primer open del mes, `vol20=RMS` de siete majors USD usando 20 log-returns de **cierres de días completos anteriores** al open y `multiplier=min(2.0,0.10/vol20)` congelado hasta rebalance mensual. No equivale a target del portfolio de 10%: target es RMS majors. Coste `2bp × SUM(abs(cambio de peso))` al rotar y al liquidar cada era.

**A = SPOT-only** menos 2bp supuesto, **B = SPOT + rendimiento DIARIO IDEAL de política** (diferencia BASE-QUOTE de mes m−2 sobre peso anterior, calendarios /365), menos 2bp supuesto. B **NO es un retorno financiado de forwards ni swaps reales IC Markets**; BID/ASK, slippage, swap charges, taxable rates, historical broker contracts siguen faltando. Tasas BIS actualizadas ahora (2026) pueden incluir empalmes/revisiones, sin PIT completo; calendario de sesiones 28FX por completitud diaria M5 puede seleccionar retrospectivamente, no es autorización para producción. No leer 2024-09-17+.

El mismo DIAG ya fue usado para diseñar el experimento después de H5, por lo cual los IC bootstrap cuantifican VARIACIÓN DENTRO DE LA MUESTRA observada, no validación independiente. No existe inferencia legítima "segundo test de carry independiente" solo por cambiar función sizing o métrica.

## RESULTADOS VERIFICADOS: métricas de retornos MENSUALES (Sortino MAR=0), no Sharpe diarios de H5

| Métrica | DEV SPOT (A) | DEV ideal (B) | DIAG SPOT (A) | DIAG ideal (B) |
|---|---:|---:|---:|---:|
| Meses (incluye septiembre-2024 parcial DIAG) | 64 | 64 | 33 | 33 |
| **Sortino anualizado mensual** | **−0.5279641197** | **−0.1435794919** | **+0.0334402020** | **+0.8072221227** |
| Sharpe anualizado mensual | −0.4135667560 | −0.10416604696 | +0.0241101155 | +0.5088114346 |
| CAGR mensual compuesto | **−2.6228735261%** | **−0.7960600591%** | **−0.0265889460%** | **+2.8867800588%** |
| MaxDD mes fin de mes | −16.9365858799% | −10.0126333230% | **−8.2534978915%** | **−7.3775498083%** |
| Calmar (CAGR/abs maxDD) | −0.1548643596 | −0.0795055640 | −0.0032215367 | +0.3912925204 |
| Peor mes | −4.6554986435% | −4.4597025487% | −4.8681049423% | −4.4637989938% |
| Expected shortfall mes peor 5% (2/33 DIAG) | −3.5991473535% | −3.4158932569% | −3.4533857921% | **−3.1689978038%** |
| Skew de meses (momento poblacional) | −0.1205778328 | −0.0662222713 | −0.4720469222 | −0.3513720913 |
| Media mensual aritmética | −0.2064686518% | −0.0518973490% | +0.0118019748% | +0.2517026381% |
| Meses negativos | 33 | 32 | 17 | 17 |
| **IC95 bootstrap bloques 6 meses, MEDIA mensual** | [−0.502235%; +0.083986%] | [−0.340760%; +0.226378%] | [−0.502653%; +0.535665%] | **[−0.289920%; +0.819129%]** |
| **IC95 bootstrap bloques 6 meses, Sortino anualizado** | [−1.120; +0.255] | [−0.810; +0.763] | [−1.157; +2.366] | **[−0.768; +4.379]** |
| IC95 bootstrap bloques **12 meses**, MEDIA mensual (sensibilidad) | [−0.487995%; +0.077723%] | [−0.323643%; +0.218689%] | [−0.406961%; +0.479600%] | **[−0.232454%; +0.793405%]** |

**Operación DEV:** 62 decisiones mensuales, acumulado de coste 36.2080913 bps de NAV sin capitalizar (mayor que H5 por sizing apalancado). **Operación DIAG:** 33 decisiones mensuales, coste 29.5828443 bps sin capitalizar; 28 fuente originales y ocho tipos BIS verificados. Este costo modelado NO es costo completo del broker.

**Números relevantes, sin ocultar signo:**

- En **DIAG**, H6a obtiene Sortino B 0.807>0.5 y Sharpe mensual B 0.509, CAGR B +2.887%, con MDD B −7.378%, ES5 B −3.169% y peor mes B −4.464%. **Criterio estadístico conjunto FALLA** porque CI95 inferior de media B (bloques 6m) **−0.289920% mensual** y de bloques 12m **−0.232454%**; ambos incluyen cero. Estado **`NO_PROMOTION_EXPLORATORY`**.
- En **SPOT-only DIAG**, H6a Sortino apenas +0.033, CAGR −0.0266% — sin ventaja estable. Las ganancias hipotéticas B vienen del componente de política NO acreditado como cash flow. En DEV ambas A y B pierden bajo H6a, lo que no sugiere estabilidad temporal.
- Un Sortino de 0.807 con skew negativo **NO transforma** carry en operable ni elimina crashes; el drawdown de −7.38%, peor mes −4.46% y ES5 −3.17% siguen siendo pérdidas materiales con riesgo de cola.
- H5 DIAG (sin vol scaling, Sharpe diario aproximado) ideal Sharpe +0.313 y CAGR +1.383%, H6a DIAG (vol scaling, Sharpe mensual) Sharpe +0.509 y CAGR +2.887%. Los CAGR son comparables descriptivamente con caveats (varían retornos agregados y fechas de marcado), los Sharpes **no son idénticos** en estimación (H5 daily252 vs H6a monthly12) y la ventana es la misma. No usar diferencia como nueva evidencia OOS.

## Dictamen y próximo paso, sin optimización encubierta

**Se ejecutó H6a ahora con los datos existentes, sin necesidad del hueco japonés 2013–2015.** Se conserva su salida: B ideal positivo pero estadísticamente inconcluso y NO NET; spot solo plano en DIAG, negativo DEV; no cumple IC95 conjunto. **NO ejecutar otra variante ajustando target vol 8/12%, window 10/60D, 5/7 L/S o tasa lag** tras observar H6a. La opción H6b siete divisas/21 pares 2010–15 requiere datos completos de esos pares, los 27/56 archivos muestra Dukascopy no justifican afirmar cobertura continua; no se ejecutó y queda opcional, no un segundo test real.

**Se conserva la posibilidad de FX carry como mecanismo, pero no está demostrado ni certificado**. Si continúa el proyecto, el paso de valor económico verificable es reunir financiación forward/swap real o un nuevo dato independiente válido, no variar reglas dentro de 2022–2024.

**Estado operativo: H6a ejecutado/no promoción; H6 2010–15 bloqueado por fuente; H4 forwards auténticos bloqueado por fuente; H5 cerrado. CERO traders certificados (0/3). Holdout desde 2024-09-17 sellado, VPS/MT5/LIVE/Shared/CIBO/QDLE intactos.**
