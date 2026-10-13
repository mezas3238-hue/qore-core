# QORE-Alpha 2 — Contrato metodológico propietario v0.1 (PRE-OUTCOME)

**Fecha:** 2026-10-12. **Issue:** #838. **Estado:** RESEARCH_ONLY / HYPOTHESIS_NOT_PROVEN / ZERO_ORDERS.  
**Rama:** research/qore-alpha2-original-intermarket-propagation-20261012.  
**Origen de datos (independiente de la estrategia):** PR #829, 33/33 mercados M5 IC Markets/CIBO Atlas, 24.377.420 M5, fuente manifest SHA256 1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85.

## A. Soberanía y originalidad

QORE-Alpha 2 es un trader cuantitativo nuevo, no una copia de TTrades, ICT, VT31, Scalper, DRIVE/RESET/RELATIVE, ni de las siete familias de E1/E2 QORE Native. Conceptos estadísticos generales (correlación, volatilidad, co-movimiento, beta, ATR) son conocimiento público; lo original es la combinación de hipótesis, observación causal, selección determinista y falsación antes de leer PnL. **Nadie puede prometer un edge antes de medirlo.**

Hipótesis primaria única **PATR (Propagación Asincrónica de Transmisión de Riesgo)**: una presión transitoria distribuida entre otros mercados líquidos puede transmitirse incompletamente a un instrumento, creando un pequeño retraso direccional explotable, si la magnitud es superior a las fricciones de su sesión. Contrahipótesis: el supuesto retraso es ruido de feed, riesgo no lineal, ilusión de dependencia FX, salto de spread o una relación estadística no estable. Si PATR no supera sus controles, no añadir filtros a posteriori para salvarlo.

**No es** una predicción de noticias; noticias macro programadas de alto impacto se excluyen prospectivamente, con calendario conocido as-of validado. El screening histórico sin calendario verdadero permanece NOT_EVALUABLE para despliegue.

## B. Universo, fuentes y cronología

- **33 mercados fijos**: índices NAS100/SP500/US30; metales XAUUSD/XAGUSD; 7 majors AUDUSD/EURUSD/GBPUSD/NZDUSD/USDCAD/USDCHF/USDJPY; 21 crosses AUDJPY/AUDCAD/AUDCHF/AUDNZD/CADCHF/CADJPY/CHFJPY/EURAUD/EURCAD/EURCHF/EURGBP/EURJPY/EURNZD/GBPAUD/GBPCAD/GBPCHF/GBPJPY/GBPNZD/NZDCAD/NZDCHF/NZDJPY.
- M5 nativo solamente; construir una H4 UTC de 48 velas M5 consecutivas y ordenadas: no interpolar, no usar H4 broker sintético ni candle parcial. El límite de 4 horas es UTC fijo, no apertura real de CFD o broker. Repeticiones, OHLC inválido, timestamp ambiguo => fail closed.
- Etapa DEVELOPMENT antes de 2022-09-17 UTC, empezando no antes de 2016-09-17, solo tras inspección de ventanas realmente no consumidas. Etapa DIAGNOSTIC 2022-09-17→2024-09-17 UTC, considerada **consumida para investigación**. Todo 2024-09-17→2026-09-17 queda bajo embargo sin abrir por Alpha 2; no reclamar que un período previamente abierto por otro proyecto sea nuevo holdout. Certificación final necesitará forward posterior al congelamiento / proveedor realmente independiente.
- Se evalúa **panel de 33**, sin ranking por PnL ni escoger un supuesto símbolo ganador. Los grupos índice/metal/FX mayor/FX cross se informan como diagnósticos, nunca autorizan exclusión retrospectiva.

## C. Features y regla de señal *única* (parametrización congelada v0.1)

Para cada H4 *t* completa y mercado i, retorno r_i(t)=ln(close_i(t)/close_i(t−1)), solamente si ambas H4 son contiguas.

1. Calcular retorno/volatilidad del mercado i usando máximo 160 H4 pasadas (t−1...t−160), al menos 96 retornos disponibles. No usar retorno t para entrenar beta/correlación.
2. Cada posible donante j ≠ i requiere retorno contemporáneo t y al menos 96 fechas históricas simultáneas. La correlación de Pearson y beta cov(i,j)/var(j) se estiman únicamente con pares **pasados**; beta truncada a [−2,+2].
3. Donante válido: |correlación| ≥ 0,55. Elegir máximo 7 por |correlación| descendente, desempate símbolo alfabético. Se requieren al menos 5 donantes. Cada aportación a la presión es beta_ij × r_j(t).
4. P = mediana de las aportaciones tras quitar el mínimo y máximo. Exigir |P| ≥ 0,90 × desviación poblacional de retornos pasados del i; ≥80% de donantes alineados con el signo de P.
5. Definir retraso como 0 ≤ sign(P) × r_i(t) ≤ 0,25 × |P|. Esto exige subrespuesta, no reversión del activo. Dirección candidata sign(P). Comparador horario pareado sign(r_i(t)), o sign(r_i(t−1)) si r_i(t)=0; sin comparador se abstiene.
6. Stop previsto: 1,25 × media de True Range de 20 H4 completas contemporáneas/pasadas en las últimas 40 franjas, cada una con close previo contiguo; sin 20 TR no hay señal. El stop es **distancia**; nivel exacto depende de futura cotización de entrada. Objetivo fijo = 2× distancia del stop; expiración = 12h después del primer momento admisible de entrada. Prohibido transformar la distancia calculada sobre mid OHLC en precio ejecutable sin BID/ASK.
7. Decisión **solo** al cierre H4: si t es inicio de H4, decisión t+4h y primera entrada **no antes** de t+4h+5min. No se permite usar futuro para dirección, stops o selección. Se emitirá un ledger de intenciones investigativas, **no órdenes**.

Ningún umbral se cambiará tras mirar outcomes de esta versión. Si se necesita nueva hipótesis, un ADR nuevo y evidencia genuinamente independiente.

## D. Controles para invalidación

- **Control A:** en exactamente las mismas fechas/instrumentos/señales, seguir el signo del retorno H4 propio (comparador de momentum propio); misma geometría de stop, expiración y costes. Medir delta de PATR vs A, por operación y calendar-week.
- **Control B:** donantes desplazados 5 días de calendario **solo como placebo analítico de investigación**, destruyendo la sincronía real sin consultar futuro; no usar ese resultado para optimizar señales. Evitar extrapolar la mecánica de días festivos.
- **Placebo temporal:** desplazamiento causal e independiente pre-registrado de donantes sin alteración de i, y reporte de sospecha de causalidad espuria por triángulos FX/cotizaciones compartidas.
- **Falsación:** resultados gross vs control no positivos y replicados, bootstrap por bloques de calendario semanal (1/2/4 semanas), fragilidad a clusters, p-valores apropiados predefinidos, sensibilidad a costes reales y delay. **La unidad muestral NO son 24 millones de velas ni 33 activos independientes**.
- Una sola hipótesis primaria de panel. Se informan todos los símbolos incluso con 0 señales; cuatro clases solo diagnóstico. No usar Holm de 231 estrategias heredadas: Alpha 2 tiene un único contraste primario, pero los 33 mercados y subgrupos siguen siendo dependientes y ninguna celda se declara ganadora sin ajuste.

## E. Arquitectura del trader (responsabilidades separadas)

**Observador M5**: lector nativo, calidad OHLC, UTC, falta de data y hash de staging; jamás inventa barras.  
**Sincronizador H4**: genera bloques completos y exige retornos contiguos.  
**Motor PATR**: relaciones beta/correlación estrictamente históricas; presión donante contemporánea cerrada y retraso propio.  
**Gobernador local**: abstención ante as-of NEWS/horas/spread no verificado, stale prices, conflicto y pérdida de trazabilidad; no puede optimizar PnL mediante filtros retrospectivos.  
**Ejecución (pendiente)**: primer M5 futuro admisible con BID/ASK, comisión, spread variable, lag/slippage, stops/take/expiración, fill o no-fill y tratamiento worst-case de dobles toques.  
**Libro de posiciones (pendiente)**: una exposición por mercado, límite indicativo 0,25% de equity conciliado por trade y 1% abierto agregado, máximo 0,5% por familia; **sujeto a QORE Risk**, sin martingala ni compounding para rescatar pérdidas. Niveles definitivos solo tras riesgo y capacidad aprobados.  
**Inteligencia cognitiva (posterior)**: lee evidencia causal e incertidumbre, explica presión, contradicción, antigüedad, fragilidad y decide abstención documentada; no se autoriza una red entrenada con futuros ni una cognitiva que invente edge.  
**CIBO/Shared**: sin integración hasta pasar los Gates; CIBO administra capital luego, Shared aporta contexto sin decidir metodología.

## F. Gates — UTC-001 manda; no reescribirlos

Por **cada año obligatorio y cada fold OOS individual**: Profit Factor ≥1,50; expectativa ≥+0,15R; Sharpe ≥1,50; Sortino ≥2,00; payoff ≥1,50; drawdown observado ≤6R; MC positivo ≥90%; MC p95 DD ≤15R; post-cost PF>1, post-cost E>0; supervivencia de clusters y muestra suficiente. Más controles de MAE/MFE, costes, deterioro, retención de ganadores (≥80% cantidad y ≥90% R si inteligencia altera la cartera), ausencia de lookahead, revisiones de riesgo, CIBO e independiente. Fresh holdout real único, pasado limpio; si falla se quema. Sin compensación entre símbolos, años, folds o Gates. Un panel conjunto no tapa un año negativo.

### Gates de ingeniería — estado al crear v0.1

| Paso | Estado inicial | Prueba de salida |
|---|---|---|
| G0 fuente 33/33 | Evidencia reutilizable PR #829 | SHA original + trazabilidad CSV y revisiones independientes de todo staging |
| G1 mecanismo/PATR | Definido, no demostrado | pruebas de causalidad y ledger con cobertura completa |
| G2 económico gross | NO EJECUTADO | backtest bidireccional + control/semana/panel, sin tune |
| G3 ejecución NET | BLOCKED | BID/ASK PIT, comisión, spread, slippage, swap/roll, sesiones reales, noticias as-of |
| G4 robustez | NO EJECUTADO | calendario-clusters, Monte Carlo, estrés, 4 familias, estabilidad por año |
| G5 certificación UTC-001 | NO EJECUTADO | cada gate cada año/fold y Fresh OOS prospectivo |
| G6 operación | PROHIBIDO | autorización separada de OWNER y QORE Risk, nunca inferida por un PR |

## G. Evaluación y reporte obligatorio

Ledger inmutable por decisión y entrada: source run/artifact/hash, símbolo, timestamp M5 y H4, feature timestamp, donantes/sus coeficientes, latencia, spread/commission/slippage, decisión, precio BID/ASK, sizing/risk, stop, target, expiry, MAE/MFE y evento de salida. Hashes de configuración/código/dataset, resultado de cada uno de los 33, PF/Sharpe/Sortino/DD/R por año/fold, placebo, controles y riesgos de dependencia. Si alguna fuente o coste falta, distinguir **UNKNOWN/SOURCE_BLOCKED** de **NO_SUPPORT**.

**Nunca publicar porcentaje de rentabilidad como resultado de Alpha 2 antes de correr pruebas económicas reales.** Sin importar cuán prometedor parezca un ledger bruto, no desplegar en VPS, MT5, LIVE, ni mezclar CIBO/Shared, ni fusionar la rama a main sin autorización explícita.
