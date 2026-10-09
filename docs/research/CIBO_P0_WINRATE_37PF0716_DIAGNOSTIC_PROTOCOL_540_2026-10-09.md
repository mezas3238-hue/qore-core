# PROTOCOLO P0 — Diagnóstico causal del 37,17% de aciertos / PF 0,7166

**Trader Lab PAPER · 3.368 señales originales · cohorte congelada de 540 aperturas (538 terminales y 2 sin salida) · PR #748 · 2026-10-09**

## 0. Prioridad vinculante

**NO aumentar el número de entradas ni elevar el riesgo hasta demostrar expectativa neta positiva sobre señales ya financiadas.** Los cambios de cuatro motores y QDLE son de infraestructura y no certifican edge. CIBO Native MAX continúa con instrucción de modo/exit precomputada, por lo que no está certificado como administrador cognitivo total. Nunca tocar VPS, MT5 LIVE ni habilitar SEND durante estas pruebas.

No exigir «win rate > 50%» como condición universal: umbral de equilibrio depende de la magnitud media neta ganadora y perdedora, fees y otras fricciones. La prioridad es expectancy > 0 y PF > 1 *fuera de muestra*, con incertidumbre explícita.

## 1. Cohorte y primer resultado extraído de artefacto REAL del run PAPER

Fuente: GitHub Actions #37956379198, SHA de runner verificado `7e65c3e5be7d5ccabbba4b165e21b6fb926cf601`, artifact `11628042022`, `trader-lab-cibo-qdle-spread-3368.json`. Este archivo NO contiene OHLC completos intratrade, MAE ni MFE, por lo que las cinco preguntas no pueden contestarse en este artefacto sin volver a procesar Atlas M5.

**540 PAPER abiertas → 538 cerradas, 2 censuradas.** De 538: 200 ganancias (37,1747%), 335 pérdidas (62,2677%), 3 resultado exactamente nulo. Media neta ganadora $0,64700679; media neta perdedora $0,53903281; ratio de payoff medio ≈1,20031; **win rate de equilibrio ≈45,4481%** en esta distribución de magnitudes, no automáticamente 50%.

PF neto total 0,7166033. PnL neto cerrado -$51,17463427. Las 2 abiertas no se imputan como ganadas o perdidas, y no existe PF/DD MTM certificado.

| Motivo de cierre PAPEL | n | Ganadoras | PnL neto USD | Interpretación cautelar |
|---|---:|---:|---:|---|
| `TAKE_PROFIT` | 155 | 146 | +94,1944 | Algunas posiciones con gestión parcial pueden terminar con PnL < 0 a pesar del rótulo |
| `STOP_FIRST_OR_SL_ONLY` | 235 | 54 | -82,2303 | Los stops PROTECTORES pueden cerrar con ganancia; **no** equivale a 235 SL iniciales |
| `DEFENSIVE_CLOSE_NEXT_OPEN` | 143 | 0 | -61,0275 | Hipótesis prioritaria a testear: cierre defensivo prematuro vs evita pérdidas mayores |
| `GAP_OPEN_STOP` | 5 | 0 | -2,1112 | Gap/salto de apertura |
| TOTAL | 538 | 200 | -51,1746 | Confirmado por CSV lógico del artefacto |

Por símbolo: NDX100 89 cierres, 15 ganadores (16,85%), PnL -$24,7075; AUDJPY 204, 87 (42,65%), -$2,5609; GBPJPY 89, 32 (35,96%), -$13,1125; EURUSD 93, 39, -$5,15; GBPUSD 58, 26, -$4,85; XAUUSD 5, 1, -$0,7937. Son correlaciones, no prueba de que un Trader/símbolo sea la causa por sí solo.

## 2. Cinco hipótesis falsables — orden de pruebas

| Hipótesis | Experimento causal | Evidencia a favor | Evidencia contraria / limitación |
|---|---|---|---|
| H1: señales sin edge | **A**: mismas 540 entradas, lotes/precios/fees congelados, SL económico y TP originales fijos; sin defensivo, trailing, breakeven, parcial. Comparar con gestión existente pareada por fingerprint y sin introducir nueva señal | A tiene PF < 1 y expectancy neta < 0; robustez por símbolo/año/trader | A tiene PF > 1 consistentemente: las señales quizá sí tengan edge pero gestión actual lo destruye |
| H2: stops demasiado estrechos | SL predefinidos = 0,5 / 1,0 / 1,5 ATR14 M5 **causal calculado solo antes de entrada**; TP original fijo. Medir primera visita SL, recuperación posterior al TP, MAE/MFE, coste riesgo de SL alternativo | Aumentar SL reduce falsos barridos y mejora PnL **después de costos y nueva validación QDLE** | Mejora únicamente al permitir pérdida/riesgo excesivo, o deja PF < 1 |
| H3: targets demasiado lejos | TP predefinidos = 1 / 2 / 3 ATR14; SL económico original fijo; proporción que alcanza 0,5×TP ANTES de cierre; MFE normalizado | TP cercano aumenta PnL/expectancy pareada sin falsear riesgo | Mayor win rate con ganancias demasiado pequeñas y PF <=1 |
| H4: temporalidad/regla de origen errónea | Estudio independiente: reconstruir señales H1 y H4 de sus Traders usando solamente OHLC previos al momento de entrada (señales NUEVAS). No etiquetar una señal M5 como H1/H4 por simple resampling | Edge se recupera en H1/H4 fuera de muestra | Diferencias por composición/cantidad impiden atribución sin control pareado |
| H5: régimen/spread no comparable | Primero sensibilidad a spread 0, 1×, 2× y comisión ±25% como **escenarios**, nunca llamarlos «históricos reales». Después importar bid/ask fechados y conversiones USDJPY reales solo con procedencia verificable | Rentabilidad muy sensible al spread/JPY/fees | Si permanece negativa bajo supuestos benignos, fricción no explica toda la pérdida |

**Importante:** H1 no se puede «descartar» con la sola Prueba A si sus 540 operaciones están seleccionadas por QDLE/capital/periodo; probar además el universo de oportunidades con geometrías válidas, separando edge condicional de financiabilidad, sin simular órdenes imposibles.

## 3. Cinco métricas obligatorias por fingerprint

1. **SL seguido de TP**: registrar instante en el que stop original fue tocado, si posteriormente llegó al TP dentro de una ventana predeclarada y si el camino es continuo. Diagnóstico **a posteriori**, NUNCA una operación rentable ficticia ni información disponible para CIBO en el instante de abrir. No inferir orden intrabar M5: STOP-FIRST conservador cuando coinciden.
2. **>=50% del recorrido al TP antes de girar**: sobre la dirección de salida ejecutable (bid para BUY, ask para SELL), separar «barra estrictamente anterior a salida» vs «misma barra indeterminada». Comparar frente a TP y stop originales.
3. **MFE favorable máximo por entrada**: USD y unidades ATR/R, sobre barras observadas durante la vida del trade; por vela OHLC resulta intervalo potencial, no tick-real.
4. **MAE adverso máximo por entrada**: mismas unidades, descontando spread y fees con presupuesto per-lot; registrar gaps/MAE por símbolo y modo.
5. **Duración winners vs losers**: minutos desde PAPER fill a último PAPER exit; mediana, P25/P75, tasas de defensa temprana, win/loss, año/símbolo/Trader/modo.

En cada fila: `signal_fingerprint`, broker symbol, Side, entry, SL económico, SL estructural, TP, lot, opening fee, timestamp entry/exit, censurado flag, exit reason, MFE/MAE observado, R/ATR predecisión, razón `MFE>=0.5TP`, `SL_then_TP_lookahead`, `AMBIGUOUS_BOTH_IN_ONE_BAR`, `NO_CONTIGUOUS_PATH`, `NOT_BROKER_VERIFIED`, y pruebas de coste físico del lote en cada SL alternativo.

## 4. Rigurosidad experimental

- **Congelar cohorte** de 540 señales CON LOTES positivos del run #37956379198; 538 cierres válidos, 2 censurados. Comparar en cohortes pareadas, NO cambiar cantidad de entradas entre A y cada SL/TP grid. Explicitar cuando A/variantes quedan censuradas por falta de M5. Reportar coverage pareado y never impute censored PnL=0 como trade cerrado.
- Misma comisión, bid/ask sintéticos con spread fijo, EUR/JPY proxy, reglas STOP-FIRST y gaps en todos los brazos. No cambiar método por modalidad.
- ATR14 requiere **14 TR completos anteriores** al instante de entry, y **15 cierres anteriores** para referencia del primer TR. Si no existe cadena continua, ATR no medible. Jamás tomar ATR calculado desde barra que inicia en el instante del fill.
- Comparar variantes de stop con **presupuesto all-in (stop loss+comisión+fricción)** y volumen QDLE: congelar volumen para diagnóstico geométrico pero marcar **INVIABLE CON QDLE**, y para conclusión operativa volver a calcular lote real por brazo sin asumir apertura.
- No elegir mejor SL/TP basándose en ganancias de las mismas señales y luego llamarlo out-of-sample. Predefinir 2019-20 exploración; 2021 validación; 2022 holdout, salvo que la cobertura por año requiera nuevos cortes cronológicos; informar tamaños por año. Bootstrap por bloques temporales/semana y sensibilidad por símbolo, régimen y distintos spreads.
- Para concluir rentabilidad, reclamar PF neto >1, expectancy neta >0, intervalo de confianza por encima de 0 en holdout independiente, costes consistentes, cohorte cubierta, DD MTM estimado con sensibilidad. Win rate 50% por sí solo no es aceptación.
- Si ningún brazo pasa, NO elevar riesgo a 5% automáticamente. Derivar si el problema central es señales, gestión, fricciones o falta de información; proporcionar evidencia contraria.

## 5. Criterio de causa dominante

Primero attribution contable del PF <1: pérdidas netas por **stop inicial vs trailing, cierre defensivo, gaps, parcial y TP**, además de símbolo/periodo/Trader. Determinar qué componente explica mayor fracción de -51,17 USD, con intervalo de incertidumbre.

Causa *gestion de salidas* solo si brazo A fijo sobre misma cohorte y mismo fill/fee mejora materialmente PF y expectancy neta, con contribución especialmente de los 143 cierres defensivos. Causa *SL* solo si variar SL en cohortes pareadas mejora expectancy respetando riesgo físico. Causa *TP* solo si lo mismo para TP, no basándose en winrate. Causa *señales* si ni gestión fija ni grid predeclarado rescatan edge en OOS. Causa *timeframe* exige nuevas señales cronológicas y OOS. Causa *spread* exige bid/ask auténticos fechados, o reportar solo sensibilidad de escenario.

## 6. Bloqueos y salida obligatoria

El informe presente demuestra composición de cierres y ratios, **NO** MFE/MAE, barrido luego de TP ni verdadero efecto de gestión frente a benchmark fijo: requieren corrida sobre Atlas M5 con posiciones e historial de cada señal. El operador debe publicar `diagnostic_rows.jsonl`, `experiment_grid.json` y `protocol_gate.json`, hash de manifiesto/replay/Atlas, prueba anti-lookahead y decisión `PASS/FAIL/INCONCLUSIVE`.

**Este protocolo tiene prioridad sobre optimizar el tamaño de lote o abrir 1.096 operaciones nuevas.** Un cambio a CIBO Native MAX es necesario arquitectónicamente, pero la variación de *riesgo* no puede darse por buena hasta entender y validar el edge. Mantener PR #748 DRAFT, NO LIVE.
