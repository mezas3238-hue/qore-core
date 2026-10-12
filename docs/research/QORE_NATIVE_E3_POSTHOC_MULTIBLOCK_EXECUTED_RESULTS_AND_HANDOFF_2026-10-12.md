# QORE Native E3 — auditoría científica multisemanal por metodología EJECUTADA (2026-10-12)

## Ejecución y testigos

- GitHub [Actions E3 #38262585848](https://github.com/mezas3238-hue/qore-core/actions/runs/38262585848) **SUCCESS 1/1**, `ruff` PASS, **8/8 pytest PASS** y ejecución E3 completada en el commit exacto `845a7e351c1641025a6131271ae3ada37ebf37f1`.
- Artefacto ejecutado firmado [#11753217479](https://github.com/mezas3238-hue/qore-core/actions/runs/38262585848/artifacts/11753217479), JSON `qore-native-e3-seven-method-block-shrinkage-posthoc.json` SHA256 **`bddfb37a859acbd4d607c18790c4ab752399e951e010e62a479f1597db941616`**; lado `.sha256` y `OUTPUT_SHA256SUMS.txt` coinciden tras extraer.
- Prereg **POSTHOC** de análisis E3 commit `2a053e762268c2f4f22238d200599a7adf4726f7`; firmado antes de nuevo E3, pero después de haberse observado E2 y FDR. **No llamar a E3 prospectivo.**
- Reutiliza **33 testigos E1 originales** (7 reglas cada uno) del [Actions E2 #38257207836](https://github.com/mezas3238-hue/qore-core/actions/runs/38257207836) head `dfe78f115957a40f4188c30e78bd7f88c2ce6c42` y fuente G0 SHA `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`, sin descargar M5 ni tocar el embargo 2024-09-17→2026-09-17.
- 231/231 celdas, siete modelos, grupos índice 3 / metales 2 / FX majors 7 / cruces21. Development **313** semanas y **278.983** eventos método×símbolo; diagnóstico **105** semanas y **94.628** eventos. Eventos inter-correlacionados, **NO independientes**.
- Bootstrap calendario circular con bloques **1, 2, 4 semanas**, sincronizado para todos 231 pares, **4.000** draws por longitud y época, Holm y Benjamini–Hochberg (BH) FDR a nivel **7 métodos**, estratos 4 grupos **solo descriptivos** y 231 indicadores de shrinkage MoM **no calibrados**.

## Hallazgo principal

**0/7 métodos positivos y con BH-FDR10% significativo simultáneamente en desarrollo y diagnóstico** para ninguno de los bloques 1/2/4. **0/7 métodos con simultáneamente retorno bruto positivo y ventaja positiva frente a control en ambas épocas.** 0/3 traders certificados, no NET ni LIVE.

| Método (33 símbolos peso igual) | DEV gross bps | DEV delta vs control bps | DIAG gross bps | DIAG delta vs control bps | Dictamen |
|---|---:|---:|---:|---:|---|
| Reversión 12h | +0,283 | −0,090 | +0,256 | +0,237 | Delta signo cambia, IC cruzan 0 |
| Continuación post apertura | +0,154 | −0,335 | +0,143 | +0,285 | Delta cambia signo, IC cruzan 0 |
| Persistencia 12h | −0,283 | +0,090 | −0,256 | −0,237 | Gross negativa ambas |
| Reacción inicial apertura | −0,146 | −0,181 | −0,193 | −0,422 | Gross y delta negativas ambas; diagnóstico negativo nominal |
| Sweep/reclaim | +0,151 | −0,033 | +0,100 | +0,146 | Pequeñísimo gross, delta sin soporte |
| Tendencia multidiaria | −0,245 | +0,119 | +0,338 | +0,316 | Delta positiva en ambos pero gross negativa DEV |
| Ruptura continuada | −0,531 | +0,100 | −1,636 | −0,807 | Gross negativa ambas |

*Este documento expresa medias por instrumento equiponderadas y retorno gross OHLC teórico, no fills ni beneficio NET.*

## Sensibilidad a 1 / 2 / 4 semanas

**Todo intervalo bilateral 95% de delta de las siete metodologías en desarrollo cruza cero** para L=1, 2 y 4. En diagnóstico, solo la reacción inicial muestra intervalos enteramente **negativos**; ninguna ventaja positiva queda con el IC>0. Tabla L=4:

| Método | DEV IC95 delta L=4 (bps) | DEV q BH siete L=4 | DIAG IC95 delta L=4 (bps) | DIAG q BH siete L=4 |
|---|---|---:|---|---:|
| Reversión 12h | [−0,526,+0,340] | 0,943 | [−0,371,+0,944] | 0,689 |
| Post apertura | [−0,833,+0,193] | 0,681 | [−0,620,+1,207] | 0,689 |
| Persistencia 12h | [−0,340,+0,526] | 0,943 | [−0,944,+0,371] | 0,689 |
| Reacción inicial | [−0,388,+0,034] | 0,649 | [−0,753,−0,072] | **0,0927, NEGATIVO** |
| Sweep/reclaim | [−0,956,+0,942] | 0,943 | [−1,531,+1,944] | 0,862 |
| Tendencia multidiaria | [−0,749,+1,100] | 0,943 | [−0,843,+1,505] | 0,689 |
| Ruptura continuada | [−0,769,+0,910] | 0,943 | [−2,099,+0,603] | 0,689 |

**Matiz esencial:** reacción inicial negativa en diagnóstico con BH10% y L=4 no implica ventaja positiva; el q BH al 10% en desarrollo es 0,649 y la prueba **NO se replica** como significativa. Las comparaciones se eligieron como sensibilidad posthoc, no un nuevo estudio prereg verdaderamente independiente. P-valores bootstrap son aproximaciones bajo dependencia serial temporal, incluso con bloques multisemana.

## Estratificación descriptiva 7×4 (SIN inferencia de subgrupos)

En **FX crosses 21**, tendencia multidiaria dio `delta DEV +0,440bps / DIAG +0,656bps`, con retorno gross DEV **+0,049bps** y DIAG **+0,601bps**: **ninguna supera un supuesto RT de 1bp en ambos**. Seleccionar crosses ahora porque fueron positivos es análisis ex post y requiere nueva muestra. En índices3, delta tendencia dev −1,128/diag +2,824bps con cambio signo; metales2 dev +0,030/diag −3,849; majors7 dev −0,286/diag −0,588.

Los 231 `shrunken_delta_descriptive_bps` son un **proxy de pooling no calibrado**, no un posterior bayesiano ni evidencia de 231 edges. En desarrollo `tau²=0` para TREND_MULTI_DAY, SWEEP_RECLAIM y RANGE_BREAK_CONT (todos sus mercados vuelven al mu); en diagnóstico `tau²=0` para REVERSAL_12H, PERSISTENCE_12H, POST_OPEN_CONT, SWEEP_RECLAIM y RANGE_BREAK_CONT. **No usar ranking de shrinkage para seleccionar un ganador.**

## Correcciones causales y de calidad

- Primera ejecución CI falló por dos imports sin uso. Segunda reveló una prueba estadística de datos sintéticos **sin varianza** que, con p-mínimo `1/(B+1)`, podía sugerir significación. Se endureció `summarize_bootstrap`: si `SE ≤ max(1e-12, 1e-10*abs(observed))` o draws inválidos, **rechazar inferencia y asignar p=1**. Se actualizaron pruebas para exigir rechazo en series constantes. Ejecución final **8/8 PASS**. No se modificaron estrategias ni las series originales, solo el control contra significación numérica espuria.
- Volvió a reutilizarse el E1 ya ejecutado, no se generó ni un precio nuevo; **no es validación OOS nueva**.
- Veredicto permitido: 0 métodos gross/delta positivos al mismo tiempo en ambos períodos, ninguna ventaja robusta después de BH método/semana y ya fallaron Holm231 y BH231. **No implica que todos los patrones posibles carezcan de edge**.
- No hay BID/ASK, comisión, slippage, horarios broker validados para ejecución, calendario noticias PIT, no Sharpe/PF/Sortino/DD netos; tampoco posibilidad de derivar PF de observaciones OHLC de cierre fijo como trader ya listo. 0/3 trader certificado, sin CIBO/Shared/QDLE/MT5/VPS/LIVE.

## Próximas tareas del siguiente arquitecto (priorizadas)

1. **Detener pruebas redundantes:** no ampliar 33 ni optimizar horarios/SL/TP sobre los 231 resultados observados. Aceptar cierre E2/E3 de SIETE reglas EXACTAS e hipótesis agrupadas, no condenar todos los mecanismos de mercado.
2. **Datos de fricción por instrumento:** identificar disponibilidad de BID/ASK, comisión RT, slippage y latencia point-in-time para los instrumentos/broker de potencial uso; diseñar captura forward con periodo, horario y SHA, sin inferir costes de screenshots ni supuestos fijos.
3. **Auditoría de mecanismos independientes:** flujo de reconstituciones Nasdaq-100 [ADR-001](https://github.com/mezas3238-hue/qore-core/pull/831) Gate E0 y otra hipótesis nueva motivada por causación exógena, siempre con fuente PIT y potencia por eventos **antes** de outcomes.
4. **Conservación prospective de un holdout realmente nuevo** (no afirmar que diagnóstico 2022–24 era virgen); si nunca está disponible, registrar `SOURCE_BLOCKED` y no certificar.
5. **Control de dependencia:** incorporar exposición a factores comunes (EUR/GBP/USD/JPY/índices) solo en auditoría de sensibilidad, sin retune para escoger parejas vencedoras.
6. **NO producción:** 0/3 traders Native certificados; consultar a DeepSeek Expert como auditor externo para ambigüedades, sin sustituir pruebas con sus opiniones.

**Estado final E3:** `POSTHOC_DESCRIPTIVE_RESEARCH_COMPLETE_NO_EDGE_CERTIFIED`.
