# HANDOFF MAESTRO — LONDRES / TTRADES FRACTAL — QORE

**Fecha:** 11 de octubre de 2026. **Repositorio:** [qore-core](https://github.com/mezas3238-hue/qore-core). **Issue rector nuevo:** [#785](https://github.com/mezas3238-hue/qore-core/issues/785). **Rama:** research/london-ttrades-author-exact-master-handoff-20261011.

**Estado innegociable: LONDON_AUTHOR_FIDELITY_UNCERTIFIED / ORIGINAL_NET_EDGE_UNTESTED / NO_LIVE.**

## 0. MISIÓN CONCRETA DEL PRÓXIMO ARQUITECTO

**Determinar si la metodología ORIGINAL de TTrades para operar la sesión de Londres, reproducida sin lookahead y con fidelidad al autor, presenta ventaja económica neta de costes en EURUSD y GBPUSD.** Es legítimo y obligatorio responder POSITIVO, NEGATIVO, INCONCLUSO o BLOQUEADO conforme a evidencia. Nunca buscar rentabilidad a cualquier precio, nunca corregir una hipótesis con el resultado ya visto, nunca llamar «TTrades fiel» a una interpretación QORE. Trabajo únicamente GitHub/Trader Lab: no VPS, MT5 live, CIBO, QDLE, Shared, Master Frame, DCVC ni producción.

**Hallazgo nuevo de mayor importancia, comprobado durante este handoff:** existe una publicación ORIGINAL que trata exactamente de Londres, de **12-septiembre-2026**:

- [TTrades, How to Trade London Using TTrades Fractal Model — artículo](https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/)
- [TTrades, How to Trade London Using TTrades Fractal Model — vídeo YouTube](https://www.youtube.com/watch?v=tUbrCewFdCU).

**Esta fuente es ahora la ANCLA CANÓNICA LON-A de la misión Londres.** El artículo describe **sesgo Daily → formación de mecha Daily → estructura y mecha H4 → swing protegido y cambio de estado de entrega CISD en M15 → continuación hacia draw on liquidity / objetivo HTF**. Enseña que **la estructura importa más que una kill zone exacta**, el giro puede aparecer ya en Asia o al inicio de Londres, y SMT puede ser confluencia (no un requisito universal explícito). La fuente *no* proporciona automáticamente criterios numéricos únicos de entrada/SL/TP: eso hay que certificar.

**ALERTA:** el PR #784 anterior certificaba fuentes de otra publicación de **febrero 2026, Scalping Model**, con **H1→M15→M1**. No confundirlo con el MODELO DE LONDRES Daily→H4→M15 de septiembre. La falta de esta distinción ha alimentado falsaciones de proxies; solucionar identidad autoral es el PRIMER trabajo.

## 1. Identidades metodológicas: NO fusionar

| Modelo / identificación | Fuente primara | Arquitectura | Regla de inclusión |
|---|---|---|---|
| **LON-A: London Fractal sep-2026** | [London Fractal original](https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/), [vídeo](https://www.youtube.com/watch?v=tUbrCewFdCU) | **Daily bias → H4 wick/swing → M15 CISD/protected swing → expansión HTF** | **OBJETO PRINCIPAL A TESTEAR, AÚN NO IMPLEMENTADO** |
| **LON-B: London Reversal / NY Continuation jul-2025** | [Artículo de autor](https://ttrades.com/london-reversal-and-new-york-continuation-daily-profile/), [vídeo](https://www.youtube.com/watch?v=y6SnEdASVLY) | Perfil Daily: London crea wick/extremo, CISD confirma, NY puede expandir. Asia 20–00 EST, Londres 02–05 EST, NY 08:30–12 EST. | CONTEXTO posible, NO reemplazo de LON-A ni entrada mecánica completa |
| **SCL-A: Scalping Model feb-2026** | [Artículo autoral](https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/), [vídeo](https://www.youtube.com/watch?v=eywpZT3z6GQ) | Daily contexto, **H1 C2/C3 bias**, M15 swing, **M1 trigger** | Otra variante: [#772](https://github.com/mezas3238-hue/qore-core/issues/772), [PR #784](https://github.com/mezas3238-hue/qore-core/pull/784) |
| **M30→M3** | [Issue #768](https://github.com/mezas3238-hue/qore-core/issues/768) | Alineación/equilibrio distintos | No mezclar con Londres |
| **QORE L1/L2, E0–E3** | [Issue #775](https://github.com/mezas3238-hue/qore-core/issues/775) | Cruce simple Asia, RECLAIM/ACCEPTED, proxies CISD y MSS | **STOP_NO_PROMOTION**, no replica LON-A |
| **SMT-T0 QORE** | [Rama SMT-T0](https://github.com/mezas3238-hue/qore-core/tree/research/london-smt-synchronous-frequency-20261011) | Un par cruza Asia, otro no confirma en 10m | Definición propia no probada como SMT del autor, **sin run acreditado; PAUSADA** |

TTrades tiene asimismo un modelo «A Simple 3-Step Trading Model» de junio 2026 con perfil 7h 18:00/01:00/08:00; ese reloj y contrato NO entran en LON-A sin vínculo original. Si aparecen otras variantes, congelar sólo una versión ANTES de resultados; si no se puede fijar, SOURCE_UNDERDETERMINED.

## 2. LON-A: texto original y reglas que todavía NO están cerradas

El artículo del autor permite documentar estos pasos, NO pretender que ya son código:
1. **Daily Bias**: determinar dirección previamente con fases, cierres Daily, EQ, POI, Candle2/Candle3; evitar que el cierre Daily futuro se utilice retrospectivamente al abrir Londres.
2. **Daily Wick**: esperar mecha contraria antes de buscar cuerpo expansivo. «Mecha formada» y mecha pequeña/grande no tienen en ese texto una condición aritmética universal.
3. **H4 swing y wick**: hallar el extremo del que alejarse; posible cierre Candle2 anticipando Candle3. No conocer el extremo definitivo ni un cierre H4 antes de tiempo.
4. **M15 CISD**: una serie de velas lleva al low/high; un cierre a través de la serie confirma cambio de entrega y un protected swing. La dirección debe coincidir con Daily y H4.
5. **London Reversal y Failure Swing**: puede haber barrido u opposing run y giro durante Asia o Londres; failure swing requiere más evidencia, no aceptación mecánica indiscriminada. SMT aparece como posible confluencia.
6. **Continuation y objetivo**: desde protected swing hacia high/low de HTF o draw on liquidity, quizá runner. Entrada exacta, stop exacto y jerarquía de TP requieren adjudicación autoral.

**Pregunta a formular desde cero:** ¿este conjunto, realmente conocida cada pieza al instante, produce EV neto positivo frente a una exposición comparable? No «¿rompe Londres el máximo asiático?». En el histórico el barrido ronda el 96,6%: es base rate, NO evento discriminante.

## 3. Fuentes primarias — orden obligatorio de lectura e inspección

| ID | Fuente original | Para verificar |
|---|---|---|
| **L0 PRIORIDAD 1** | [How to Trade London Using TTrades Fractal Model, 12-sep-2026](https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/), [vídeo original](https://www.youtube.com/watch?v=tUbrCewFdCU) | Daily bias, wick, H4 Candle2, protected swing M15, CISD, hora, failure swing, dirección, stop/target/runner. Revisar párrafos y capturas/escenas del autor. |
| L1 | [London Reversal and New York Continuation, 21-jul-2025](https://ttrades.com/london-reversal-and-new-york-continuation-daily-profile/), [vídeo](https://www.youtube.com/watch?v=y6SnEdASVLY) | Perfil Daily, CISD London y posible NY continuation; **los horarios de este artículo NO prueban que sean filtros obligatorios LON-A**. |
| L2 | [How CISD Confirms Swing Points](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/), [Understanding CISD](https://ttrades.com/understanding-the-change-in-state-of-delivery-cisd/) | Cierre C2/C3 en TF mayor, secuencia de velas y su open inicial, CISD LTF dentro de estructura válida. |
| L3 | [MSS vs CISD](https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/) | MSS requiere displacement + cierre swing; un CISD NO es necesariamente MSS. |
| L4 | [Protected Swings / Stops](https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/), [Using Order Blocks for Continuations](https://ttrades.com/using-order-blocks-for-continuations/) | Qué protected swing invalida; stop wick/body y selección legítima, FVG/POI, continuación. |
| L5 | [Candle2](https://ttrades.com/how-to-trade-candle-2-ttrades-fractal-model/), [Candle3](https://ttrades.com/how-to-trade-candle-3-in-the-fractal-model/), [Daily Bias](https://ttrades.com/easy-daily-bias-a-mechanical-trading-framework/) | Cierre válido y criterio de wick, sesión/as-of y conflicto de bias. |
| L6 | [SMT](https://ttrades.com/mastering-smt-spot-divergences-in-trading/), [SMT Fractal Model](https://ttrades.com/how-to-use-smt-divergence-ttrades-fractal-model/) | Confluencia verdadera de swings entre EURUSD/GBPUSD, opcionalidad, sincronización; evitar «mate no rompe Asia en 10m» como regla autoral. |
| L7 VARIANTE | [Scalping Feb-2026](https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/), [Three-Step 7h Jun-2026](https://ttrades.com/a-simple-3-step-trading-model-full-breakdown/) | **Referencias cruzadas**, nunca seleccionar parámetros de estas variantes porque mejoran el PF. |

Para cada regla registrar: URL y fecha de autor, párrafo, screenshot/figura, min:seg **auténtico** del vídeo si accesible, acción observable y «available_at», ejemplos tanto exitosos como fallidos, nivel de certeza AUTHOR_TEXT_EXPLICIT / AUTHOR_VIDEO_EXPLICIT / AUTHOR_EXAMPLE_INFERRED / QORE_ENGINEERING / UNKNOWN_BLOCKING. **No inventar marcas de tiempo.** La transcripción vidIQ de vídeos previos fue bloqueada por crédito insuficiente, según [auditoría #784](https://github.com/mezas3238-hue/qore-core/blob/research/scalper-author-primary-source-certification-20261011/docs/research/QORE_SCALPER_TTRADES_AUTHOR_VIDEO_SOURCE_ACCESS_AUDIT_2026-10-11.md). DeepSeek puede auditar ambigüedades como APOYO externo, nunca aportar reglas atribuidas al autor sin fuente.

## 4. Historia real de los trabajos hechos (NO reabrir para optimizar)

### 4A. Primer replay QORE Londres L1/L2, NO metodología autoral

- [PR #776](https://github.com/mezas3238-hue/qore-core/pull/776), [run #38146670174](https://github.com/mezas3238-hue/qore-core/actions/runs/38146670174), [Issue #775](https://github.com/mezas3238-hue/qore-core/issues/775).
- Universo EURUSD y GBPUSD; Asia **00:00–08:00 Europe/London** (480/480 M1) y primer crossing Asia high/low 08:00–11:00 Europe/London. Frecuencia: **EUR 169/206=82,0%**, **GBP 197/222=88,7%** sobre días con Asia completa. Barrido NO discrimina suficientemente.
- L1 = sweep+reclaim y reversión; L2 = break+hold y continuación, reglas mínimas QORE. **358 operaciones**; **0/4 grupos económicos positivos** con coste **SUPUESTO** 0,025R y STOP_FIRST; stops típicos 1,1–2,0 pips; **34/358=9,5%** intrabar ambos SL/TP en la misma M1. No es PF certificado ni refutación de LON-A.

### 4B. Auditoría BID/ASK externa de subset L1/L2 (infraestructura no prioritaria para pregunta actual)

- [Issue #777](https://github.com/mezas3238-hue/qore-core/issues/777), [PR #778](https://github.com/mezas3238-hue/qore-core/pull/778); runs [#38148314083](https://github.com/mezas3238-hue/qore-core/actions/runs/38148314083), [#38148719772](https://github.com/mezas3238-hue/qore-core/actions/runs/38148719772).
- Cross-provider Dukascopy externo, **7 de 34** casos dual-touch con ticks recuperados en unión de ambos runs: 6 STOP-first y 1 TARGET-first *observados en quotes externos*, no fills broker. **27 sin recuperar**; gran cantidad de HTTP 503/timeout, no prueba que datos inexistentes. En 4/7 spread mediano de hora >= stop nominal.
- NO bloquear lectura y geometría del London Fractal por ticks; SÍ exigir un contrato de costes honesto antes de declarar EV neto cobrándose con stops cortos.

### 4C. Estudio de rutas tras raid, source-only, NO entradas de TTrades

- [PR #779](https://github.com/mezas3238-hue/qore-core/pull/779), [run #38150980682](https://github.com/mezas3238-hue/qore-core/actions/runs/38150980682), [informe](https://github.com/mezas3238-hue/qore-core/blob/research/london-after-asia-sweep-path-20261011/docs/research/QORE_LONDON_TTRADES_INSPIRED_AFTER_ASIA_RAID_REPLAY_EXECUTED_2026-10-11.md); [revisión de fuentes YouTube](https://github.com/mezas3238-hue/qore-core/blob/research/london-after-asia-sweep-path-20261011/docs/research/QORE_LONDON_YOUTUBE_METHODS_SOURCE_REVIEW_2026-10-11.md).
- Asia **20:00–00:00 America/New_York**, Londres **02:00–05:00** NY interpretando EST con DST, HISTORIAL **2025-09-17 a 2026-09-17**, provider-native M1 ya consumido. 261 fechas/mercado; Asia completa EUR **237**, GBP **241**. First-raid EUR **229/237=96,62%**; GBP **233/241=96,68%**. **458 checkpoints** válidos (EUR **227**, GBP **231**).
- Outcome QORE a +60 minutos de checkpoint 11 M1 tras raid: REVERSAL si close ≤−0,25 AsiaRange; CONTINUATION si close ≥+0,25; NEUTRAL resto. EUR **81 reversión /61 continuación /85 neutral**. GBP **80/69/82**. **No son 458 trades**. Proxies CISD/MSS no certificados. **Los 96,6% NO pueden compararse sin más con 82–88% por cambiar reloj/rango.**

### 4D. Divergencia EUR–GBP y control H4: E1 y E2

- [PR #780 E1](https://github.com/mezas3238-hue/qore-core/pull/780), [run #38152004136](https://github.com/mezas3238-hue/qore-core/actions/runs/38152004136): RECLAIM vs ACCEPTED 3 cierres fuera: EUR R **38/94 (40,4%)** vs A **40/115 (34,8%)**; GBP R **22/92 (23,9%)** vs A **50/123 (40,7%)**; interacción EUR−GBP **+22,38 puntos porcentuales**, bootstrap cinco fechas conjuntas 95% **[+7,34,+36,91]pp**. Histórico examinado = NO OOS, no efecto causal.
- H4 estricto E1 requería **720/720 M1** en tres H4 previas; **0/458** registros aptos. **NO demuestra H4 irrelevante, ni rotura de M1 Londres.**
- [PR #781 E2](https://github.com/mezas3238-hue/qore-core/pull/781), [run #38152552686](https://github.com/mezas3238-hue/qore-core/actions/runs/38152552686): H4 observacional con ≥45/60 M1 por hora y close final ≤5 min de extremo, previo al raid. **305/458** H4 proxy reconstruibles; **282/424** de estados R/A. Interacción sobre submuestra **+14,42pp**, ajustando por H4 en la MISMA submuestra **+14,33pp**, bootstrap 95% **[−5,97,+32,54]pp**. Reducir 22,38→14,42 por cambiar selección NO significa que «36% del efecto fue causado por datos defectuosos». Faltaba historia H4, no necesariamente vela Londres corrupta.

### 4E. E3 normalización ATR y falsaciones F1/F2: cierre definitivo de promoción QORE

- [PR #782 E3](https://github.com/mezas3238-hue/qore-core/pull/782), [run #38153593288](https://github.com/mezas3238-hue/qore-core/actions/runs/38153593288), [informe](https://github.com/mezas3238-hue/qore-core/blob/research/london-eurgbp-acceptance-atr-e3-20261011/docs/research/QORE_LONDON_ISSUE775_E3_ATR_NORMALIZED_ACCEPTANCE_EXECUTED_2026-10-11.md). Sustituir tres cierres fuera por ≥0,50 ATR14 M15 de Asia, manteniendo los mismos 458 outcomes QORE. EUR R **38/94** vs A_ATR **35/88**; GBP **22/92** vs **42/98**; interacción **+19,60pp**, IC95 **[+3,21,+35,67]pp**, exploratoria. No demuestra edge ni autoría.
- [PR #783 F1/F2](https://github.com/mezas3238-hue/qore-core/pull/783), [run #38156402305](https://github.com/mezas3238-hue/qore-core/actions/runs/38156402305), [informe definitivo](https://github.com/mezas3238-hue/qore-core/blob/research/london-e3-f1-f2-falsification-20261011/docs/research/QORE_LONDON_E3_F1_F2_FALSIFICATION_EXECUTED_RESULTS_2026-10-11.md), [artefacto 53 bloques](https://github.com/mezas3238-hue/qore-core/actions/runs/38156402305/artifacts/11708259260).
- **F1** E3 completo +19,60pp, bootstrap IC95 **[+3,45,+34,91]**; H4 reconstruible +15,22pp, IC95 **[−5,40,+34,47]**; H4 no reconstruible +33,54pp, IC95 **[+4,37,+62,45]**. La estimación known es positiva pero no precisa: no declarar «efecto inexistente» ni que grupo unknown es «mercado roto».
- **F2** dejar fuera uno a uno **53** bloques cronológicos de cinco jornadas NY (último de una): FULL 0/53 invierten signo y 0/53 IC cruzan cero; H4-known 0/53 invierten signo PERO 53/53 IC cruzan cero. El efecto histórico no parece depender de uno/dos bloques, pero no pasa gate estricto en cohorte H4 apta. **Veredicto contractual: STOP_NO_PROMOTION RECLAIM/ACCEPTED**, no autorización de trader.
- **Nunca** promover de nuevo este filtro por cuarto umbral o escoger solo días conocidos positivos. **NO** extender STOP de un proxy a LON-A.

### 4F. Certificación bibliográfica anterior para SCALPING, NO Londres

- [PR #784](https://github.com/mezas3238-hue/qore-core/pull/784), [run #38158101874](https://github.com/mezas3238-hue/qore-core/actions/runs/38158101874); [canon anterior](https://github.com/mezas3238-hue/qore-core/blob/research/scalper-author-primary-source-certification-20261011/docs/research/QORE_SCALPER_TTRADES_2026_AUTHOR_SOURCE_CANON_AND_BLOCKERS_2026-10-11.md), [JSON contrato](https://github.com/mezas3238-hue/qore-core/blob/research/scalper-author-primary-source-certification-20261011/docs/research/qore_scalper_ttrades_author_fidelity_contract_2026-10-11.json).
- 8 URLs autorales, 15 reglas TT01–TT15, **47 motivos de bloqueo**, **6/6 tests del gate** pasados, estado verdadero **BLOCKED_SOURCE_FIDELITY** y «economic_replay_authorized=false». **CI SUCCESS significa que impide certificar prematuramente**, NO que TTrades esté certificado. Su canon de febrero H1/M15/M1 **no es canon LON-A**.

### 4G. Contexto V49 no pertenece a ensayo Londres

- [Issue #772](https://github.com/mezas3238-hue/qore-core/issues/772), [Gate E0 run #38143687671](https://github.com/mezas3238-hue/qore-core/actions/runs/38143687671): 2.876 oportunidades, 2.020 trades V49 H1/M15/M1, PF bruto **0,664**, ganancia acumulada **−233,27R**, DD máximo **236,13R**. Sesgo H1 arrastrado en gran porcentaje y M1→HTF parcial, Gate C0. **NO** es prueba de Daily/H4/M15 Londres. No reutilizar sus trades/outcomes para probar LON-A.

### 4H. SMT T0, NO replay autorizado ni realizado

Se creó rama de estudio [research/london-smt-synchronous-frequency-20261011](https://github.com/mezas3238-hue/qore-core/tree/research/london-smt-synchronous-frequency-20261011) y [prerregistro](https://github.com/mezas3238-hue/qore-core/blob/research/london-smt-synchronous-frequency-20261011/docs/research/QORE_LONDON_SMT_SYNCHRONOUS_FREQUENCY_T0_PREREG_2026-10-11.md) para no-confirmación +10 M1; código y pruebas se subieron, **no hay resultado publicado de ejecución**. La regla 10 minutos fue una ELECCIÓN QORE, no el SMT autoral certificado. Pausar hasta adjudicar LON-A, donde SMT puede ser confluencia opcional.

## 5. PRIORIDADES DE AMBIGÜEDADES — resolver por fuente ANTES de escribir estrategia

| Prioridad | Problema | Peligro concreto / pregunta al autor y auditor |
|---|---|---|
| **P0-ID** | Canon L0 Sept-2026 versus L1 Jul-2025, Scalper Feb, 3-Step Jun | Mezclar modelos y luego atribuir éxitos/fracasos a TTrades de forma falsa |
| **P0-DAILY** | Sesgo Daily, C2/C3, POI, EQ, DOL | ¿Daily es una precondición operable y cuál es la información realmente conocida antes del día? |
| **P0-WICK** | Mecha Daily/H4 «ya formada» | Evitar conocer ex post el extremo; cuándo se confirma que mecha terminó, failure swings |
| **P0-H4** | H4 swing/cierre, ancla de barras y DST | Hora 22:00/02:00 del autor vs UTC/NY vs broker; no usar H4 aún abierta |
| **P0-M15** | Serie CISD y protected swing | Delimitar serie, cuál open, cierre M15 conocido, pivote confirmable por derecha, invalidación |
| **P0-ENTRY** | Entrada exacta y múltiples triggers | ¿En cierre CISD, retrace, OB/FVG, siguiente M15, o M1? No importar trigger Feb automáticamente |
| **P0-EXIT** | Stop/target/runners | Protected low/high, wick/body/buffer, cuál DOL primero, 1R vs HTF no elegir por PF |
| **P0-SOURCE** | Vídeos/ejemplos reales no auditados minuto-a-minuto | Recuperar evidencia con timecodes y ejemplos perdedores; no inventar author-exact |
| **P0-FEED** | Gaps H4 y M15, native vs agregada | 0/458 H4 strict y 305/458 H4 proxy no prueban corrupción: inventario de causa/timestamps y sesgo de censura |
| **P0-OOS** | 2025-09→2026-09 entero consultado | Exige holdout realmente no usado y prueba de origen, nuevo periodo si necesario |
| **P1-SMT** | Confluencia entre EURUSD/GBPUSD | Determinar si autor la exige y definición temporal de swings; no imponer proxy 10m |
| **P1-TIME** | Killzone versus estructura | L0 dice que setup manda; L1 ofrece horarios, especificar papel real sin fusionar |
| **P1-OPS** | Días sin trade, caducidad, solapes, news, costes, dual-touch | Contracts ingeniería QORE etiquetados, as-of y escenarios; no ocultar censuras |
| **P1-STATS** | Auto-correlación + USD compartido + poca densidad | Baselines equiexpuestos, MDE, test por jornadas emparejadas, evitar p-hacking |
| **P1-CLAIM** | Falta de reglas exactas discrecionales | Si no hay especificación única reproducible, declarar AUTHOR_UNDERDETERMINED, no disfrazar de fidelidad |

**Nota epistémica:** ni F1 con IC que cruza 0 demuestra efecto cero, ni H4 UNKNOWN demuestra datos corruptos. Tampoco «sobrevivió al bootstrap» confirma edge. Un backtest negativo sobre UNA implementación y DOS pares no prueba universalmente que toda idea TTrades sea falsa.

## 6. Plan de trabajo del sucesor: puertas obligatorias y evidencia que debe entregar

### GATE A — CERTIFICAR FUENTE LON-A (P0, BLOQUEA CUALQUIER BACKTEST)

Leer/anotar L0 artículo+vídeo+figuras, L1–L6 según necesidad. Crear documento de matriz RULE_ID → cita autoral exacta (URL/párrafo/timestamp real) → decisión operativa → available_at → ejemplo bueno/malo → test fixture → incertidumbre. Resolver 12–20 reglas críticas Daily/H4/M15/CISD/POI/protected, entrada, stop, target, H4 ancla, expiración y optional SMT. Cada regla AUTHOR_EXPLICIT / QORE_POLICY / UNRESOLVED. Elaborar 10–20 fixtures del vídeo u original con checks, no seleccionar solo ganadores ni hacer ingeniería inversa de P&L. **Si entrada o salida siguen ambiguas, STOP author-exact**. DeepSeek puede asistir cuestionando definiciones (documentar pregunta, respuesta, evidencias) pero no autoridad final.

### GATE B — DATOS H4/M15 FIABLES Y CAUSALIDAD

Inventario nativo/derivado por EURUSD,GBPUSD y fuente/proveedor, timestamp UTC, ancla H4, NY DST, sesión real, M15/H4 faltantes, duplicados, cierres. Comprobar H4 nativas si disponibles; si se agregan desde M1, no hacer forward-fill ni permitir «720 incompletas» como 720 íntegras. Distinguir H4 historial insuficiente vs oportunidad M15 realmente inválida; mostrar conteos por estación/feriado/session y sesgos missing. Auditoría de prefijos y disponibilidad de cierres; no usar día del futuro para sesgo Daily, H4 formándose sin regla explícita o swing M15 confirmado ex post. Si datos no dan cobertura suficiente, BLOCKED_DATA, nunca optimizar a ojo.

### GATE C — MOTOR NUEVO FIRST-ONLINE INDEPENDIENTE

Crear namespace dedicado de Trader Lab para LON-A, no importar lógica/sensores V49/L1/L2/M30-M3 ni usar 458 outcomes para construir triggers. **Se permite reutilizar un lector de datos neutro con prueba de proveniencia**, no detectores ni etiquetas. Emitir eventos D_BIAS → H4_WICK → M15_CISD_PROTECTED → ENTRY → STOP/TP o NO_TRADE con event_time, available_at, source_id, rule_id, motivo y barras efectivamente observadas. Test prefix invariance, no lookahead, gaps, fecha/zone, swing pivot-right, conflictos de órdenes, primeros targets, conteo de oportunidades excluidas. Comparar fixtures autorales. Si no hay regla clara, QORE_VARIANT etiquetada, no «autor fiel».

### GATE D — ÚNICO PRERREGISTRO Y HOLDOUT REALMENTE INÉDITO

Congelar versión exacta, pares, sesiones, parámetros legítimos, calidad de datos, muestra dev vs OOS NUEVO, N requerido/potencia, stop/target/cost stress, benchmarks equiexpuestos por símbolo y franja, tratamiento same-bar ambiguo, net EV primario, PF neto, DD si capital/riesgo definido, censura, autocorrelación por día, controles y corrección multiplicidad si hay variantes. Publicar SHA y barrera de acceso previo al holdout. **Toda data 2025-09-17→2026-09-17 ya vista NO se puede reciclar como OOS virgen**. Si el investigador no encuentra fuente o periodo genuinamente nuevo, BLOCKED_NO_VIRGIN_OOS y no inventar certificación.

### GATE E — ENSAYO ECONÓMICO UNA VEZ

Reproducir decisiones únicamente desde estados pretrade; separar (1) calidad/géometría OHLC de la señal; (2) EV neta bajo coste por símbolo realmente modelado, con incertidumbre de ejecución OHLC y spreads supuestos/medidos; (3) capturabilidad física posterior si stops ultracortos. Tick/BIDASK NO son prioritarios para decidir geometría, **pero sí potencialmente decisivos al certificar fills y costes netos físicos**. No decir que STOP_FIRST arbitrario sea fill real. Reportar para cada mercado y conjunto N, trades por año, tasa de rechazo/censura, PF, expectancy net R, bruto, costes, win/loss, DD R y (solo si cuenta/riesgo definidos) DD%, intervalos por jornadas compartidas, comportamiento temporal y controles. Veredicto: SUPPORTED_NET_EDGE_TESTED_SCOPE, NO_NET_EDGE_TESTED_SCOPE con potencia, INCONCLUSIVE_UNDERPOWERED, AUTHOR_UNDERDETERMINED, DATA_BLOCKED, OOS_BLOCKED o EXECUTION_COST_UNRESOLVED. Ninguno autoriza LIVE sin otro gate.

### GATE F — DOCUMENTACIÓN, AUDITORÍA Y RESPONSABILIDAD

Registrar en Issue #785 regla → fuente → línea código → prueba → run/artefacto → resultado → bloqueo. Subir PR, commits y hashes de dataset, preregistro, trazas y conclusiones negativas también; handoff actualizado. El próximo arquitecto puede consultar DeepSeek siempre como revisor crítico y registrar disensos. **Nunca** borrar PRs o resultados previos aunque hayan sido negativos. Reabrir un modelo diferente solo con otro protocolo/versionado, no retocar el que fracasó.

## 7. Inventario de enlaces/archivos clave para continuar sin preguntas

- **Issue de misión [#785](https://github.com/mezas3238-hue/qore-core/issues/785)**; **Issue experimental histórico [#775](https://github.com/mezas3238-hue/qore-core/issues/775)**.
- **Fuente oficial Sept-2026 [LON-A](https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/)**, [vídeo](https://www.youtube.com/watch?v=tUbrCewFdCU).
- [PR #776 L1/L2](https://github.com/mezas3238-hue/qore-core/pull/776), [PR #778 ticks](https://github.com/mezas3238-hue/qore-core/pull/778), [PR #779 458 rutas](https://github.com/mezas3238-hue/qore-core/pull/779), [PR #780 E1](https://github.com/mezas3238-hue/qore-core/pull/780), [PR #781 E2](https://github.com/mezas3238-hue/qore-core/pull/781), [PR #782 E3](https://github.com/mezas3238-hue/qore-core/pull/782), [PR #783 F1/F2](https://github.com/mezas3238-hue/qore-core/pull/783), [PR #784 canon Scalper febrero](https://github.com/mezas3238-hue/qore-core/pull/784).
- Dataset M1 fuente, [Actions #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), fuente SHA 18c338aedd5013ce65a6cb6408ffbc2e904a6217; **HISTÓRICO YA CONSULTADO**. Los resultados fuente con las 458 rutas están en [run #38150980682](https://github.com/mezas3238-hue/qore-core/actions/runs/38150980682).
- Código anterior solo REFERENCIA FORENSE: src/qore/infrastructure/trader_lab/qore_london_after_asia_raid_paths_v1.py (PR779); qore_london_eurgbp_h4_divergence_e1_v1.py (PR780); qore_london_eurgbp_h4_observed_e2_v1.py (PR781); qore_london_eurgbp_acceptance_atr_e3.py (PR782); qore_london_e3_f1_f2_falsification.py (PR783); qore_ttrades_author_fidelity_gate_v1.py (PR784 — gate del otro modelo).
- **SMT-T0**: rama research/london-smt-synchronous-frequency-20261011 contiene prerregistro y código, sin replay de frecuencia acreditado; PAUSADO.

## 8. SEMÁFORO AL ENTREGAR EL HANDOFF

| Componente | Estado actual | Acción inmediata |
|---|---|---|
| Artículo autoral exacto Londres Sep-2026 | **ENCONTRADO Y LEÍDO, vídeo original enlazado** | Auditoría audiovisual/figuras con timestamps reales |
| Definición completa y reproducible LON-A | **PENDIENTE** | GATE A; no inventar reglas |
| Datos H4 y M15 causalmente íntegros | **NO CERTIFICADOS para LON-A** | GATE B, revisar H4 nativa vs M1 |
| Motor first-online Daily/H4/M15 LON-A | **NO CREADO / NO EJECUTADO** | GATE C |
| Holdout realmente nuevo | **NO ACREDITADO** | GATE D |
| PF/EV económica de LON-A | **NO MEDIDA** | GATE E después de GATES A–D |
| RECLAIM/ACCEPTED QORE | **STOP_NO_PROMOTION** | Cerrado para trader, archivos preservados |
| SMT QORE 10m | **DISEÑO/CÓDIGO, SIN RESULTADO** | Pausar; fuente autoral primero |
| Tick BID/ASK real broker | **NO COMPLETO** | No bloquear fuente; sí contemplar costes físicos |
| V49 / Master / CIBO / VPS / MT5 | **INTACTOS / FUERA DE ALCANCE** | Continuar así |

**Mandato final al sucesor: descubrir si LON-A realmente funciona, aunque la respuesta sea NO. No proclamar que TTrades funciona o no funciona sin haber testeado su metodología concreta con trazabilidad de fuente, causalidad y un test económico independiente.**
