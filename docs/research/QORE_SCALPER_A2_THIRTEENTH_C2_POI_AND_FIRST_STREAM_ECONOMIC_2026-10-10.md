# A2 AUDITORÍA 13 — C2/POI autor vs V49, CISD primera detección online y equivalencia económica

**Ciclo:** 2026-10-10 | **Repo/PR:** mezas3238-hue/qore-core PR #759 DRAFT | **Autoridad:** RESEARCH ONLY, 0 nuevos vetos, 0 nuevas operaciones, 0 cambios de riesgo/MT5/VPS/LIVE/MERGE.

## 1. Adjudicación de auditoría independiente

- H17 fuerte, "8,3% de fidelidad", RETIRADA. Libro de 2876 oportunidades conserva **2638 Candle2 reversal (91,7%) y 238 Candle3 confirmation (8,3%)**; 1604 heredaron estado H1, 1272 no.
- Diferencia FULL/PREFIX CISD **381** reproduce selección distinta, no inexistencia de evento. En 2876/2876 la ruta original QORE confirma una CISD al cierre en su propio prefijo, pero la **primera familia global** sólo coincide en 2495/2876; esto no equivale a fuente POI/swing certificada ni a replay económico streaming.
- Mantener diagnósticos anteriores válidos como **descripción de la población V49 original**, y NO afirmar invariancia ante reconstrucción alternativa causal-first. Nada ha probado nueva economía equivalente o contaminación directa de retornos.

## 2. Ledger de autor Candle2, regla formal

**Fuentes primarias**:
1. TTrades, *Understanding Candle 2 Closures Within the Fractal Model*, publicado **15 Nov 2025**: https://ttrades.com/understanding-candle-2-closures-within-the-fractal-model/ . Candle2 de reversión: sweep del extremo previo + cierre de vuelta al rango previo + POI superior, p. ej. swing, fair value gap o en ciertos contextos vela contraria. Sin POI, no es señal válida. C3 después de C2 como continuación o evento propio cuando no hubo cierre C2.
2. TTrades, *Candle 3 Closure*, publicado **3 Dec 2025**: https://ttrades.com/candle-3-closure-a-complete-guide-to-identifying-continuations-and-reversals/ . C3 puede confirmar después de fallo C2, cuerpo C2 y falta de sweep C2 en este contexto.
3. TTrades, *How Change in the State of Delivery Confirms Swing Points*, publicado **10 Jan 2026**: https://ttrades.com/how-change-in-the-state-of-delivery-confirms-swing-points/ . HTF closure primero, LTF CISD después para proteger un swing; sweep aislado no confirma swing.
4. TTrades, *TTrades Scalping Model*, publicado **7 Feb 2026**: https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/ . Bias H1 mediante Candle2 O Candle3.

**Código V49 realmente auditado**:
- `capitalizer_generic_scalp_census_v48._build_h1_bias_events` usa `detect_candle2_reversal_closure` con barrido/cierre y `detect_candle3_confirmation` tras fallo de C2, y requiere POI direccional previo e interacción.
- `capitalizer_source_poi_v2` implementa SOLO FVG H1 de tres velas y swing H1 de tres velas. La opción autor de vela contraria y la posible exigencia estricta de POI de un timeframe **superior al H1** siguen como **source coverage/adjudication gap**, no motivo para rechazar el libro sin confirmar contexto.
- `capitalizer_generic_scalp_census_v48._aggregate(... minutes=60)` acepta **>=45 M1/minutos por barra H1** y marca `closed_at` como último minuto recibido, que puede ser antes del cierre horario verdadero. Esto es una decisión de ingeniería verificable, **NO evidencia de que 2876 cierres H1 sean todos 60/60 completos**. Distinguir exact 60/60 de partial/UNKNOWN; reconstruir as-of timestamps y qué POI existía.
- `capitalizer_h1_context_state_v49.build_h1_context_states` hereda la última señal antes del inicio de sesión; estado `active_until` se reconstruye retrospectivamente a posteriori y NO puede proporcionarse como timestamp de futuro conocido al Trader en una decisión anterior.

**Test**: código `capitalizer_scalper_a2_thirteenth_h1_poi_native_audit_v1.py`, GitHub Actions `qore-scalper-a2-thirteenth-h1-poi-nine-market.yml`. Para cada ID requiere source event C2/C3 reconstruido y verifica geometría, clase de POI, POI confirmado antes y tocado por la vela de origen; anota si vela del evento y anterior son 60/60. Evento de sesión heredado se enlaza a última señal previa. Es un **self-check QORE reproducible**, no una prueba independiente de autor o POI HTF; no veta las incompletas.

## 3. Preregistro: 381 y 2495, comparación sin selección por beneficios

**Universo fijo:** nueve mercados; 2876 IDs originales; subgrupo 381 observado FULL vs PREFIX versus 2495 no discordantes; 2020 seleccionados cronológicamente MAX3 global original. No excluir operaciones. Definiciones fijas antes de reportar resultados.

**Causal-first**: en cada minuto M1 completamente cerrado desde la confirmación M15, consultar con **sólo el prefijo cerrado** ambas rutas (Sweep+CISD y FVG retrace+CISD). La primera *detección* manda; desempate determinista por (confirmed timestamp, family) entre lo visible *ese minuto*. **No retrotraer la operación** a `confirmed_at` si el observador descubre tarde esa misma señal. No leer siguiente M15 ni H1.until, MFE, MAE o trade outcome para elegir. Esta política es experimental QORE, no regla publicada de prioridad TTrades, pendiente de adjudicación.

**Paired outcomes observacionales**: a partir de close V49 original y del close online *detectado*, medir ambos retornos direccionales CLOSE+15/+30/+60 usando M1 provider-native; MFE/MAE observadas con high-low en cada horizonte y cobertura completa de minutos. Normalizar únicamente para comparación por riesgo de referencia V49 congelado (denominador potencialmente ex-post para la alternativa). NO se crea una nueva orden, costo, stop, target, fill ni `realized_R` de la política online. Si faltan minutos marcar NO COVERED, jamás rellenar con interpolación. Reportar diferencia online - V49 en proporción de retornos direccionales positivos (puntos porcentuales), diferencial medio de R normalizado y diferencias MFE/MAE. El usuario propuso bandas <5pp / 5–15pp / >15pp; esas bandas se usan como interpretación exploratoria de **estimaciones observacionales**, no prueba estadística de equivalencia sin CI o replay físico.

**Ejecutadas MAX3**: reportar N auténtico de source IDs en ambos libros, intersección y churn de una selección contrafactual anclada; NO asumir que las 381 se ejecutaron todas ni que 2876 oportunidades seleccionadas max3 son un replay causal-full. El replay en firme deberá recomputar elegibilidad completa (POI/H1/M15/objetivo/SL) en cada decisión.

**Implementación:** `capitalizer_scalper_a2_thirteenth_cisd_stream_pairs_v1.py`, GitHub Actions `qore-scalper-a2-thirteenth-online-paired-nine-market.yml`. Ledger adicional une la clasificación FULL/PREFIX congelada por ID y retorna grupos FROZEN_381, FROZEN_2495, ORIGINAL_MAX3 y FIRST_ONLINE_*. Se rechaza la entrada si falta uno de los libros/fuente/timestamp.

## 4. P0 restante y condiciones de cierre

1. Adjudicar fuente POI superior H1, vela contraria, exactitud de H1 60/60, swing protegido. El self-match no es PASS autor.
2. Verificar online true-first, especialmente late discovery, no usar sensor as-of-original como sustituto de stream.
3. Comparar 381 y población completa, reportar paired n por horizonte y MAX3, no filtrar.
4. Revisar baseline H1 random, 12.56pp Sweep->CISD y target bajo universo causal-first sin outcome-fit. Los diagnósticos anteriores siguen como baselines históricos.
5. Sólo entonces diseñar replay físico coste BID/ASK y OOS antes de certificación; nueva cognitiva World Model sigue congelada.

**STATUS:** NO CERTIFICABLE; fuente TTrades y rutas presentes pero requieren confirmación de causalidad conjunta. Sin nuevo PF/DD medido.
