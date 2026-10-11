# A2 — Dictamen de segunda auditoría (post-V49), MAX3 y obligaciones V50-G

**Fecha:** 2026-10-10. **Responsable:** Arquitecto B Metodología. PR #759, Issue #757, coordinación A1 PR #758 / issue #756, parent #623. **Estado:** investigación GitHub, sin merge/VPS/LIVE, Scalper NO CERTIFICADO.

## Evidencia primaria de EJECUCIÓN y documentación de fuente

**Control V49 bruto, 9/9:** [GitHub Actions #38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695), [artifact matriz #11670728222](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695/artifacts/11670728222), fuente M1 nativa [#35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), M1 source SHA `18c338aedd5013ce65a6cb6408ffbc2e904a6217`. Intervalo de desarrollo 2025-09-17 → 2026-09-17, H1→M15→M1, nueve mercados, MAX3/ sesión/día, sin costes BID/ASK reales.

**Nueve mercados:** 2,876 operaciones simuladas antes del MAX3; 2,020 después. 1,167 ganadoras, 852 perdedoras, 1 plana, 57.77% win rate; profit +461.942761832228869R, loss -695.212088908595379R, net -233.269327076366510R, PF 0.6644630742, DD secuencial 236.134284356335871R. **Media WIN +0.395837842186999888R, media LOSS -0.815976630174407722R**. El 57.77% es win-rate **post salida del simulador**, no evidencia independiente de que el H1 bias acertara dirección 57.77% de las veces. No concluir que el único fallo sea la calidad direccional H1; geometría/reward-to-risk, target, stop, gestión de salida y secuencia también pueden explicar el PF negativo.

## Revisión de la hipótesis MAX3 según auditoría DeepSeek

**Código ejecutado:** `capitalizer_v49_development_economics._portfolio_select` mantiene las tres primeras **por (session, operating_date)**, temporalmente ordenadas; no usa outcomes. `capitalizer_scalper_max3_counterfactual_audit_v1.py` lee **después del replay** exactamente los nueve libros V49 independientes y separa seleccionadas/excluidas. Rechaza duplicaciones, mercados ausentes, discordancia de informes y no cambia ni una orden, stop, target, riesgo o gate.

**Evidencia reproducible:** [GitHub Actions #38056081811](https://github.com/mezas3238-hue/qore-core/actions/runs/38056081811) contrato y cálculo completos GREEN, [artifact JSON detallado #11671880616](https://github.com/mezas3238-hue/qore-core/actions/runs/38056081811/artifacts/11671880616). Datos de origen V49 #38053946695 y SHA inmóvil `e356e7a52541e99533b25ecfef0ab9c4e9ce03c0`, lector análisis SHA `66e7f20046f176e0070e60f2a8567b556ffb98f1`.

| Métrica | Seleccionadas MAX3 | Excluidas contrafactuales |
|---|---:|---:|
| N | 2,020 | 856 |
| W / L / flats | 1,167 / 852 / 1 | 435 / 417 / 4 |
| Gross profit R | +461.942761832 | +161.211127583 |
| Gross loss R | -695.212088909 | -269.444736579 |
| Resultado bruto | **-233.269327076R** | **-108.233608996R** |
| PF bruto | **0.6644630742** | **0.5983086908** |
| Expectancy R | **-0.1154798649** | **-0.1264411320** |
| Mean winning R | +0.3958378422 | +0.3706002933 |
| Mean losing R | -0.8159766302 | -0.6461504474 |
| Median planned target | 0.4426229508R | 0.4942010309R |
| Session exits | 381 | 339 |

**Veredicto MAX3:** el conjunto excluido, en agregado y con resultados contrafactuales bajo el mismo simulador, tenía PF y expectativa **peores** que la selección cronológica. Por tanto, **la evidencia no corrobora** la afirmación categórica de que MAX3 está eliminando «los mejores» setups económicamente en agregado. El MAX3 sí censura 435 positivos hipotéticos y 161.211R de profit bruto de señales excluidas; también censura 417 negativos y 269.445R de pérdidas. **Ninguno de estos 856 es fill ejecutado**: son outcomes de replays independientes, no se afirma la capacidad real de llenar todos simultáneamente. No eliminar ni afinar MAX3 tras ver R: requerir pre-registro, competencia ex ante y validación OOS. El artifact incluye desglose por sesión, mercado, familia de trigger y sesión×familia.

## Auditor de identidad: no existe «filtro que elimina ganadoras»

`capitalizer_scalper_v49_v50_g_waterfall_v1.py` se invoca **solo después** de reconstruir V49, ejecutar V50-G y generar sus ledgers; su código no modifica listas de oportunidades ni autoriza órdenes. Un origen ambiguo, duplicado o faltante provoca un **fallo de certificación de la evidencia** del reporte, NO un veto de trading o un filtrado de entradas. En las pruebas negativas se alteran deliberadamente reportes y se confirma que sólo se aborta el *post-hoc audit*. Por ello no corresponde un A/B de política «identidad ON/OFF» atribuyéndole efecto de P&L. Sí corresponde medir y explicar cantidad de IDs sin unión y preservar cada evento source. Nunca afirmar que un auditor de datos por sí mismo destruye ganadores.

## Diagnóstico focalizado tras resultados V49

1. **H1/H2 stops-targets:** el signo económico no puede diagnosticarse solo con win rate. V49 M15 thesis stop + low median reward ~0.443R generan asimetría desfavorable de salida. V50-G M1 execution anchor frente a M15 stop debe informar coste intrínseco y R realizado, no asumir «M1 stop mejor» sin contar stops prematuros. Target H1 ya barrido: la reparación causal `_untouched_h1_target_fast` de B y seis casos de no-lookahead existen; falta contar incidentes por mercado y test de aceptación para cada source ID.
2. **MAX3:** la comparación agregada ya está medida. Atribución por trigger / session / market disponible como JSON artefacto; segmentos positivos son hipótesis exploratorias, no reglas de autorización automáticas.
3. **Costes:** un sistema de PF 0.6645 **bruto** no puede hacerse positivo por añadir costes no negativos; sin embargo, los costes BID/ASK+comisión física siguen siendo indispensables antes de certificar una configuración nueva potencialmente positiva, y para la robustez de stop M1.
4. **Sesgo H1:** requiere test independiente de dirección futura observada con MFE/MAE y target touch as-of; no interpretar ganadoras post-stop como medida directa del bias. Ninguna Daily/H4 admitida en el modelo genérico QORE H1/M15/M1.
5. **Preservación:** mantener cobertura de la misma población V49 (2,020 seleccionadas post-MAX3, 1,167 ganadoras, 461.943R masa), objetivos Owner ≥934 ganadores y ≥415.749R ganadora recuperada por source ID; distinguir baseline positive R preserved y realized candidate positive R sobre mismos IDs.
6. **V50-G pendiente:** [run #38053723674](https://github.com/mezas3238-hue/qore-core/actions/runs/38053723674), evidencia económica 9/9 no validada al producir este documento. Exigir antes de juzgarlo waterfall por ID, drop reasons, markets/sessions/triggers y stop types. V50-G tiene memoria vacía por candidato y `WELL_SUPPORTED` estático; **no es cognitivamente equivalente** al Master Frame A1 9-market sincronizado.

## Clasificación de recomendaciones de DeepSeek

| Afirmación | Estado de verificación |
|---|---|
| 934 winners/415.75R control para no destruir edge | **MATCH Owner QORE screening standard**, no source rule de TTrades |
| V49 PF bruto < 1 no certificable | **CONFIRMED** por evidencia 9/9, DD 236R |
| H1 sesgo equivocado identificado por PF negativo | **HYPOTHESIS UNRESOLVED**, no demostrado; analizar MAE/MFE/tiempos |
| Stop M15 demasiado amplio vs target | **PARTIAL**, razonable ante R mean, causa precisa pendiente |
| Target H1 barrido antes de entrada | **UNRESOLVED**, patch causal en B pero cero recuento empírico certificado |
| MAX3 elimina mejores setups en agregado | **NOT SUPPORTED** por contrafactual V49: PF excluido 0.598 < seleccionado 0.664 |
| Auditor identidad aplica gate económico y veta >5% ganadoras | **CONFLICT with code:** offline reader, no gate de traders |
| Exigir PF <1 o V49 certificación | **CONFLICT:** V49 pierde R bruto antes de costes |
| A1 V50-G parcial es Master Frame real | **CONFLICT:** mantener V50-G vs A1 scientific nine-market separados |

**No cambiar ninguna regla operativa en esta revisión.** Siguiente P0: terminar run V50-G 9/9, comparar por source ID y cuantificar target/stop. Si el run falla, no aceptar métricas incompletas; reportar traza y reparar sólo ingeniería de replay de manera causal. Coordinación con A1 para Master Frame observado y memoria settled-only. No merge, producción, VPS o LIVE.

## Segmentación adicional de MAX3 — auditoría post-hoc (sin cambiar reglas)

**GitHub Actions** [#38056328467](https://github.com/mezas3238-hue/qore-core/actions/runs/38056328467) PASS con la misma matriz de resultados V49 nativos ya congelada. El artifact y log publican y reconcilian estadísticas por sesión, mercado, familia y sesión×familia; ningún trade reordenado o admitido utilizando R futuro.

### Sesión

| Sesión | Selected N | PF selected | Excluded simulated N | PF excluded |
|---|---:|---:|---:|---:|
| ASIA | 725 | 0.6987 | 429 | 0.5831 |
| LONDON | 573 | 0.5857 | 88 | 0.8389 |
| NEW_YORK | 722 | 0.6951 | 339 | 0.5547 |

### Ruta de ejecución M1

| Familia | Selected N / PF | Excluded N / PF | R medio selected | R medio excluded |
|---|---:|---:|---:|---:|
| FVG_RETRACE_CISD | 1066 / 0.7480 | 445 / 0.7867 | -0.07613 | -0.05601 |
| LIQUIDITY_SWEEP_CISD | 954 / 0.5924 | 411 / 0.4540 | -0.15945 | -0.20270 |

**Lectura:** FVG+CISD es comparativamente menos perdedora en desarrollo, pero ninguna familia presenta PF >1 entre seleccionadas; no certificar ni convertir datos post-hoc en un gate FVG universal que falsearía fidelidad metodológica.

### Nueve mercados (seleccionadas / excluidas contrafactuales)

| Mercado | N selected | PF selected | N excluded | PF excluded |
|---|---:|---:|---:|---:|
| AUDJPY | 181 | 0.6596 | 101 | 0.7419 |
| AUDUSD | 171 | 0.6888 | 104 | 0.4503 |
| EURUSD | 285 | 0.6611 | 47 | **1.1352** |
| GBPJPY | 194 | 0.6942 | 106 | 0.6765 |
| GBPUSD | 288 | 0.5169 | 41 | 0.4978 |
| NAS100 | 258 | 0.5371 | 103 | 0.6159 |
| USDCAD | 215 | 0.9664 | 105 | 0.4577 |
| USDJPY | 179 | 0.7549 | 118 | 0.5184 |
| XAUUSD | 249 | 0.6361 | 131 | 0.5978 |

**Señal exploratoria:** las 47 oportunidades EURUSD excluidas presentan R medio +0.04302 y PF contrafactual 1.1352. **NO es evidencia de trading rentable aprobado**: fueron seleccionadas retrospectivamente por su resultado, no hay fills reales ni prueba OOS, y el segundo/tercer trade competía con otros mercados de Londres. Londres completo censurado PF 0.8389 sigue negativo. Para estudiar la propuesta habría que preregistrar un score ex ante basado exclusivamente en H1/M15/M1 observables y probarlo en un periodo OOS manteniendo MAX3 por sesión/día, preservación de ganadores y stop broker-real. Hasta entonces prohibido cambiar la selección cronológica o rescatar una familia que solo luce positiva ex-post.

**Razonamiento de causa:** el PF negativo ya presente en cada familia seleccionada con un ratio de ganancia media/derrota desfavorable dirige la investigación a calidad H1/M15, ratio geométrico stops vs H1 targets, lateralidad de M1 y dinámica de salida; no autoriza concluir que el sesgo H1 por sí solo sea erróneo.
