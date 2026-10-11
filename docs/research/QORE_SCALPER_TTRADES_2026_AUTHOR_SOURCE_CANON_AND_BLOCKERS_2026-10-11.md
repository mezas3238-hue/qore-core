# SCALPER — Canon de FUENTE PRIMARIA TTrades y bloqueo de fidelidad (2026-10-11)

**Estado real:** `SOURCE_CANON_CREATED / AUTHOR_FIDELITY_NOT_CERTIFIED / ECONOMIC_REPLAY_NOT_AUTHORIZED`. Investigación GitHub/Trader Lab. No muta V49, DCVC, Master Frame, #768, #772, CIBO, QDLE, VPS o producción. El resultado F1/F2 de Londres #775 cierra RECLAIM/ACCEPTED **para promoción**, no refuta la estrategia TTrades.

## 0. UNA sola definición de modelo a certificar

**ID** `TTRADES_2026_02_07_SCALPING_MODEL_DAILY_CONTEXT_H1_BIAS_M15_SWING_M1_EXECUTION`, fuente canónica inicial de autor:
- **A0**: [TTrades, «TTrades Scalping Model – Simple Day Trading Strategy», 07-feb-2026](https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/); [vídeo YouTube primario publicado por TTrades](https://www.youtube.com/watch?v=eywpZT3z6GQ). El artículo explica Daily = contexto general, H1 = bias por C2/C3, M15 = swing / posible C2 alineado, M1 = ejecución con FVG, CISD o protected swing. Describe operar la expansión corporal de vela H1, SL en swing protegido, TP en objetivos HTF. **No afirma que Daily sea un veto mecánico inequívoco; no se puede simplemente borrarlo del canon.**
- **A1**: [«How Change in the State of Delivery (CISD) Confirms Swing Points», 10-ene-2026](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/), [vídeo del mismo autor](https://www.youtube.com/watch?v=vn1RYjhJUnQ): **CISD lower TF es válido al acompañar closure C2/C3 HTF, y debe estar DENTRO de la vela HTF que confirmó la estructura; sin ambos no se toma continuación**. C2 sweep high/low previa con cierre de vuelta en rango; C3 ocurre si C2 no cerró adecuadamente y C3 cierra más allá de open y rango de C2. El texto describe calidad cualitativa de CISD ("V shape"/desplazamiento/ausencia de chopping) **sin umbral aritmético**.
- **A2**: [«Understanding The Change in State of Delivery», 29-jun-2025](https://ttrades.com/understanding-the-change-in-state-of-delivery-cisd/): para bearish CISD cierre más allá del OPEN de la **primera** vela up-close en la serie relevante; bullish lo simétrico sobre primera down-close. 
- **A3**: [«Market Structure Shifts vs Change in the State of Delivery», 01-jul-2025](https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/): MSS = DISPLACEMENT + CLOSE más allá de swing; CISD no equivale a MSS y puede confirmarse antes; no exigir ambos si el autor no lo exige en este setup. 
- **A4**: [«Stop Loss Mastery – Using Protected Swings for Precise Invalidations», 07-ago-2025](https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/): protected swing = llegada a PD array/nivel significativo y cierre a través de velas que formaron el swing; stop por debajo de protected low en largos / por encima de protected high en cortos. El autor menciona *alternativa de stop en cuerpo de vela* y nuevas continuaciones, **no da un criterio universal para elegir la alternativa**.
- **A5**: [«Using Order Blocks for Continuations», 01-ago-2025](https://ttrades.com/using-order-blocks-for-continuations/): retest FVG/sweep a POI → closure through opposing candle series → protected swing → entrada de continuación; "series" primero, solo vela única si no hay serie. En ejemplos objetivos daily/hourly, no un take-profit universal.
- **A6**: [«How to Trade Candle 2», 16-ago-2025](https://ttrades.com/how-to-trade-candle-2-ttrades-fractal-model/) y [«How to Trade Candle 3», 06-sep-2025](https://ttrades.com/how-to-trade-candle-3-in-the-fractal-model/): wick pequeño/grande influye en elegir C2 contra C3, pero los artículos **no aportan un % canónico de wick que pueda programarse sin interpretación**.
- **A7**: [«The Only Trading Strategy You Need For 2026», 03-ene-2026](https://ttrades.com/the-only-trading-strategy-you-need-for-2026/): estrategia FRACTAL **Daily→H1→LTF** con sesgo Daily mecánico, TP inicial 2R y posible HTF; es **otra variante publicada**. No transferir 2R o veto Daily a A0 sin demostrar que el propio autor lo incorporó en Scalping Model A0.

**Procedencia editorial:** A0-A7 son textos primarios oficiales y enlaces directos originales; son material **de fuente**, NO interpretación confirmada del vídeo minuto a minuto. La revisión audiovisual de ejemplos (timestamps, entrada/stop, cualificadores) está pendiente. **No falsificar timecodes de vídeos.** Los artículos pueden incorporar variantes/actualizaciones, y no se asume que cada regla en A7 pertenece automáticamente a A0.

## 1. MATRIZ DE REGLAS: lo que sabemos y lo que NO sabemos

| ID | Tema | Afirmación respaldada por autor | Bloqueo determinístico causal para versión EXACTA |
|---|---|---|---|
| TT01 | Identidad | Un único scalping model A0 fechado 07-feb-2026 | No mezclar otra variante ni M30→M3 #768 |
| TT02 | Daily | Contexto general previo a H1 | **BLOQUEO**: Daily es condicionante obligatorio/veto o información narrativa? Qué cierre y qué calendario? |
| TT03 | H1 C2/C3 | Sesgo por closure C2/C3 tras interacción liquidez/FVG | **BLOQUEO**: definición exhaustiva de C3 y selección en conflicto, cómo se conserva/expira bias |
| TT04 | M15 | Swing formando wick de H1, C2 M15 alineada | **BLOQUEO**: qué POI es válido y cómo se adjudica hora as-of/swing en vela derecha |
| TT05 | M1 | Entrada por continuación FVG, CISD y protected swing | **BLOQUEO**: OR o AND, orden exacto FVG→CISD, modo y precio entrada, retest/market |
| TT06 | CISD | Cierre cruzando open de primera vela secuencia contraria / cierre HTF asociado | **BLOQUEO**: determinación unívoca de serie, límites de secuencia, ubicación dentro vela H1/M15 as-of |
| TT07 | MSS | Displacement + cierre swing distinto CISD | **BLOQUEO**: displacement cuantitativo y si MSS obligatorio/optativo; NO sustituir por simple pivote |
| TT08 | Protected swing | Level significativo + close through opposing candles; stop fuera de swing | **BLOQUEO**: qué POIs cuentan, stop wick vs body alternativo, buffer? |
| TT09 | Target | HTF objectives / liquidity, no TP universal | **BLOQUEO**: elegir primer objetivo válido, qué sucede si se alcanza antes de entrada o R:R negativo |
| TT10 | C2 vs C3 | Pequeña mecha/expansión vs mecha grande -> esperar C3 | **BLOQUEO**: umbral/medición wick, no retocar después de outcomes |
| TT11 | Horario y universo | Modelo intradiario, fuentes no establecen universal única killzone del A0 | **BLOQUEO**: periodo, días, zonas horarias, mercados; si se limita a los 9 QORE sería especialización |
| TT12 | Caducidad y simultáneos | La fuente no especifica reglas universales para huecos/same-bar conflict | **BLOQUEO**: vencimiento / conflicto / datos incompletos, convertir en contrato de ingeniería **QORE**, etiquetado |
| TT13 | Costes | Fuente no certifica spread/slippage/commission de broker | **BLOQUEO DE PF NETO**, modelo de costes externo predefinido y análisis sensibilidad; no exigir tick al estudio de estructura |
| TT14 | Datos inéditos | Histórico 2025–2026 M1 de QORE ya inspeccionado | **BLOQUEO DE OOS**: reservar nuevo periodo/proveedor no examinado, prueba única y preregistrada |
| TT15 | Ejemplos originales | A0 texto y vídeo enlazados; vídeo original íntegro no adjudicado fotograma a fotograma | **BLOQUEO DE FIDELIDAD**: al menos ejemplos con vela, cierre, disponibilidad y orden contrastados con A0 sin inferir posterior |

## 2. REGLAS NO NEGOCIABLES DE RECONSTRUCCIÓN FIRST-ONLINE

Este trabajo no autoriza todavía la codificación author-exact; **cada TT02–TT15 bloqueante debe resolverse con cita primaria o quedar etiquetado `QORE_INTERPRETATION` / `AUTHOR_UNRESOLVED`**. Prohibido mezclar una variante QORE con autor-100%-fiel. Una vez decididas:
1. Entrada nativa M1 independiente; H1 y M15 se forman exclusivamente de M1 observada, con cobertura/contigüidad auditadas, timestamp UTC y reloj mercado (sin usar vela HTF en formación salvo regla explícita intra-candle). Cada evidencia tiene `event_time / available_at / source_id`.
2. H1 C2/C3 se conoce tras cierre H1; M15 swing y C2 tras su cierre; CISD/entrada M1 tras cierre validante. El sistema **no puede tener permiso de usar una noticia que ocurre dentro de vela HTF si ese cierre HTF todavía es futuro**. Si autor requiere intrabar HTF, crear contrato explícito con origen lower TF y `available_at` correcto; no rescatar mediante fechar retrospectivamente a la apertura.
3. A/B tests de **prefix invariance** (añadir barras posteriores jamás cambia decisiones pasadas), sesiones DST, gaps, duplicados, pivote con confirmación derecha, nested candles y OP/candle conflicts, source provenance.
4. Ejemplos del autor → fixtures trazables con `URL + timestamp de vídeo o figure` → pruebas unitarias; solo entonces generar los eventos first-online. **No reutilizar detectores V48/V49, el ledger de 2.876/2.020, ni sus estados predecididos como oráculo**.
5. Congelar signal spec, instrumentos, fechas, comisiones supuestas/calibradas, decisiones de censura, modelo de OHLC dual touch, benchmark control, error de familia y gates estadísticos **antes** de abrir resultados del nuevo holdout. La economía neta es distinta de edge bruto; a SL muy estrechos, M1 no basta para fills físicos. No prometer que OHLC puede certificar ejecución neta.
6. Si el resultado de **esa formulación exacta** no es positivo, refuta esa implementación y periodo/mercados, **no prueba que todas las variantes de TTrades jamás tengan edge**. Un solo backtest no valida universalidad ni falsación universal.

## 3. Criterio verificable de autorización

Contrato machine-readable asociado: `docs/research/qore_scalper_ttrades_author_fidelity_contract_2026-10-11.json`. La puerta está `BLOCKED` en el estado publicado: no existe una fuente y decisión causal cerrada para todas las reglas TT02–TT15, ni OOS realmente no inspeccionado.

**Entregables posteriores en orden**: (1) evidencias originales de los ejemplos y respuesta por cada regla; (2) adjudicación independiente por revisión de fuentes, con dudas reproducidas ante DeepSeek *como apoyo externo*, no como autoridad; (3) especificación inmutable `AUTHOR_EXACT` únicamente donde hay regla comprobada, `QORE_VARIANT` si es una elección de ingeniería; (4) first-online limpio y tests; (5) único ensayo OOS preregistrado. **No ejecutar ninguna prueba económica nueva entretanto.**

**Situación certificada a fecha 2026-10-11**: *fuentes primarias iniciales identificadas y canon provisional A0 fijado; fidelidad completa NO verificada, pendientes TT02–TT15; replay económico autoral NO autorizado.* Es preferible un NO-GO explícito a declarar un resultado negativo sobre otra proxy.
