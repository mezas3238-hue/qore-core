# ADR-QN-002 — Investigación transversal de siete metodologías × 33 mercados

**2026-10-12 — DECIDIDO por revisión de la dirección del proyecto.** Esta ADR **modifica la pausa general** de ADR-QN-001 sobre patrones intradía únicamente para autorizar un **programa cerrado y registrado de comparación transversal**. No invalida resultados negativos previos, no autoriza trading, no autoriza buscar parámetros por PnL y **no afirma ahora 231 tests realizados**.

## Por qué cambia el plan

El auditor/owner identificó correctamente un error de alcance: haber probado reversión 12h en **XAUUSD** no falsó la reversión 12h en 32 instrumentos restantes; probar continuación H4 en **EURUSD** no falsó la continuación en 32 restantes. La hipótesis de apertura **NAS100** solo probó una definición de apertura en NAS100, no en todos los mercados. El ensayo de sweep/reclaim [#830](https://github.com/mezas3238-hue/qore-core/pull/830) **sí cubrió 33/33**, pero contrastó una regla de barrido y recuperación concreta contra su baseline, sin demostrar nada sobre otras familias ni equivaler a 33 repeticiones independientes.

El error simétrico sería examinar **siete familias en 33 mercados** y escoger a posteriori las celdas con mayores beneficios. Resolver el déficit de cobertura exige un **factorial cerrado**, registro completo de aciertos/fracasos, benchmarks comparables, control de pruebas múltiples y separación del diagnóstico económico neto.

**Mandato:** estudiar, no presumir, la interacción `metodología × instrumento`. El mercado puede tener distintos mecanismos por clase, liquidez, sesión y coste. **Poner sobre la mesa todas las celdas no obliga a operar todas ni permite confundir la búsqueda con certificación.**

## Universo congelado — sin más descargas de CFDs

Inmutable G0 33/33: 24.377.420 barras M5 provider-native SHA, [Actions #38207337960](https://github.com/mezas3238-hue/qore-core/actions/runs/38207337960), [manifest SHA 1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85](https://github.com/mezas3238-hue/qore-core/pull/829). 3 índices, 2 metales, 7 mayores, 21 cruces: los 33 son **instrumentos**, no 33 ensayos independientes. Dos orígenes (12 cTrader DEMO CIBO vs 21 IC Markets cTrader DEMO) NO han demostrado equivalencia de cuenta/broker/fricción.

## Siete etiquetas del dueño → siete *definiciones operativas* distintas

Cada mecanismo fija una única implementación **ex ante**, sin rejilla de horas/ATR/stops/targets optimizados con PnL. Las definiciones detalladas y ventanas deberán pasar un **preregistro ejecutable E1** anterior a acceder a **nuevos** resultados para ese mecanismo. Esta ADR aprueba la **matriz**, no afirma que E1, costs/news/session verification o las pruebas económicas estén concluidas.

| Código | Familia solicitada | Pregunta económica distinta | Riesgo de solapamiento |
|---|---|---|---|
| `REVERSAL_12H` | Reversión | ¿Retorna una fracción del desplazamiento de 12 h previas? | Ya examinada en XAUUSD: [#825](https://github.com/mezas3238-hue/qore-core/pull/825), NO_SUPPORT |
| `POST_OPEN_CONT` | Continuación post-apertura | ¿La dirección del impulso tras un cambio de sesión persiste **después de esa primera reacción**? | NAS100 ya ensayado en [#827](https://github.com/mezas3238-hue/qore-core/pull/827), NO_SUPPORT |
| `PERSISTENCE_12H` | Persistencia | ¿La dirección de las últimas 12 h supera un control más reciente a igual exposición? | EURUSD ya ensayado en [#822](https://github.com/mezas3238-hue/qore-core/pull/822), NO_SUPPORT |
| `OPEN_INITIAL_REACTION` | Apertura: reacción inicial | ¿La **primera** reacción a una transición de sesión anticipa el tramo inmediato siguiente? Horizonte menor que post-open | Correlación con POST_OPEN_CONT; no se presenta como hipótesis estadística independiente |
| `SWEEP_RECLAIM` | Barrido y recuperación de rango | ¿Regreso dentro de un rango tras romper su máximo/mínimo previo predice reversión? | **TODOS los 33 con UNA regla YA PROBADOS** en [#830](https://github.com/mezas3238-hue/qore-core/pull/830), NO_SUPPORT. No rerun histórico como evidencia nueva |
| `TREND_MULTI_DAY` | Tendencia | ¿Una tendencia formada a lo largo de **días completos**, no horas, da información incremental sobre una sesión siguiente? | Correlación con PERSISTENCE_12H; definir control/régimen antes de OHLC |
| `RANGE_BREAK_CONT` | Continuación (ruptura) | ¿Una salida sostenida de rango horario predice continuidad, **sin recuperación**? | Complemento vs SWEEP_RECLAIM: evitar selección condicionada a dirección realizada futura |

**Nota sobre sesiones:** *Apertura* no es una entidad idéntica en 33 mercados: índices USA ~09:30 America/New_York cash reference; FX OTC no posee apertura de subasta, por lo que 08:00 Europe/London es solamente **transición de liquidez de sesión**, no «apertura de mercado»; metales OTC usan una ventana de liquidez USA **aún no certificada como apertura oficial**. Debe etiquetarse `CASH_OPEN_PROXY`, `LONDON_LIQUIDITY_TRANSITION` o `METALS_US_LIQUIDITY_PROXY_UNVALIDATED`, sin inventar hora broker/DST.

**Matriz planeada:** **7 × 33 = 231 celdas** que **DEBEN aparecer todas en el inventario**, incluso aquellas no aplicables, sin muestras, con resultado negativo o bloqueadas por calendario/coste. **231 NO son 231 hipótesis independientes.** Las familias ya expuestas en PRs anteriores quedan marcadas `PRIOR_EVIDENCE_NON_VIRGIN`; Sweep/Reclaim tiene 33/33 ya evaluadas y su resultado histórico no será maquillado como una prueba confirmatoria nueva.

## Diseño de evaluación, para evitar engaño por selección

1. **Gate D0 — metadatos hoy:** generar un registro 231/231 con símbolo, clase, familia, alias/broker de origen, reloj/proxy apropiado, exposición previa, benchmark requerido, evidencia disponible y estado `DESIGN_ONLY` o `ALREADY_TESTED_NOT_NEW`. El registro se construye por contrato de roster G0, **NO leyendo ninguna barra OHLC ni PnL**.
2. **Gate D1 — prerregistro técnico previo a outcomes:** para cada familia fijar exactamente un horizonte, trigger, entry-reference, exit-reference, señal nula/abstención, baseline **pareado mismo tiempo y nocional**, definición UTC/NY/London DST, exclusiones *conocidas antes del momento*, exigencia de 48/6/... M5 sin interpolación, embargo 2024-09-17 en adelante y n/semana mínimos según potencia. Si la definición depende de broker calendar no disponible, registrar **BLOCKED_SESSION_PROOF**, no atribuir apertura oficial.
3. **Gate D2 — exploración exhaustiva y honesta:** si D1 está aprobado, analizar **todas las celdas autorizadas y reportar incluso 0 operaciones** en development 2016-09-17→2022-09-17; usar 2022-09-17→2024-09-17 como **diagnóstico temporal ya expuesto**, no OOS virgen. Celdas idénticas a una regla pasada usar resultados anteriores y marca `REUSED_PRIOR_RESULT`: una repetición computacional NO es validación independiente. Segmentos posteriores 2024–26 siguen embargados. Nada de usar datos reservados para subir el porcentaje de aprobados.
4. **Dependencia transversal:** resampling de **semanas calendario sincronizadas en los 33 símbolos y siete metodologías**, de modo que shocks EUR, GBP, USD, JPY y mercado de índices permanezcan correlacionados. Considerar sensibilidad a dependencia entre semanas (2–4 semanas bloque), efecto de origen broker, denominador de tamaño muestral a nivel semanas/días, y efectos por factor; no declarar `n_eff = 3,000–5,000` sin estimarlo. El panel antiguo GROSS04 **YA utilizó bootstrap semanal sincronizado**: revisar sus limitaciones, no desacreditarlo por supuesta independencia de 18,669 eventos.
5. **Multiplicidad y reglas de GO:** nunca elegir una entre 231 sin corrección; para inferencia de celdas usar **Holm-Bonferroni FWER α=0.05 sobre el conjunto de pruebas realmente autorizadas y pre-registradas**, con p-valores adecuados a dependencia, idealmente versión bootstrap conjunta; usar FDR-BH solo como **exploración**, nunca como certificado net. Informar por separado **siete** agregados de familia, cada mercado y cada clase, y los cruces familia/activo; no ajustar diseño basándose en cuál ganó. Toda comparación con costos netos debe superar también el control y un umbral de coste creíble.
6. **Fricciones:** costos ida/vuelta bajo escenarios **hipotéticos** [0,1,3,5,10,20]bps y **coste máximo tolerable** por celda, pero nunca llamar *net broker real* a gross−coste supuesto. Fuente BID/ASK histórica o forward quotes/fills comprobados es requisito para G1. Comisiones, slippage, swap y horario de liquidez varían por instrumento/horario.
7. **Gates de rechazo y seguridad:** **NO-NEWS QORE #814** requiere calendario de publicaciones as-of y exclusión causal, sin filtros macro reconstruidos a posteriori. No live, VPS, CIBO, Shared, MT5, QDLE; **0/3 traders certificados**. No forzar cuota de 3. Source broker M5 OHLC no demuestra fills. La censura de resultados por símbolo está prohibida.

## Interpretación y decisión de arquitectura

**Se modifica ADR-001:** ya no prohibimos por sistema toda investigación sobre patrones de precio. **Sí prohibimos nuevos barridos improvisados** sin matriz cerrada, pruebas múltiples, protocolo causal y aprobación de salida. La línea alternativa de flujo forzado (E0) puede avanzar en **otro carril**, sin usarla para negar una investigación sistemática de los mercados existentes.

**Próximo entregable ejecutable:** registro `QORE_NATIVE_33X7_DESIGN_MATRIX_V1` y tests de completitud e historial de exposición. **No fingir que ya se ejecutaron 231 backtests.** Implementar D1 progresivamente por familia, revisando con DeepSeek Expert definiciones/controles (sus opiniones son propuestas, no evidencia), antes de distribuir jobs en GitHub Actions.

**Estado:** `D0_MATRIX_DESIGN_ONLY`. G0 33/33 histórico OK. Familia sweep ya NO_SUPPORT 33/33 según la implementación única probada. 4 ensayos Native previos cerrados. **No hay edge económico ni trader certificado nuevos por esta ADR**.
