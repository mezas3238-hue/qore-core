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


## 5. Resultado final observado — GitHub Actions nueve mercados

### 5.1 Test Candle 2/3 H1 POI [#38099880288 — 11/11 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38099880288)

- Libro original fijo: **2638 CANDLE2** y **238 CANDLE3**, total 2876/2876 reconciliados.
- **2538/2638 C2** y **227/238 C3** tienen evento original + geometría de closure + POI confirmado antes, compatible y tocado, reproducido por la infraestructura QORE; total **2765/2876** (96,14%).
- **100 C2 y 11 C3** = **111 IDs** carecen de testigo reconstruido en esta nueva ejecución. **NO** son por ello casos de POI invalidado, ausencia de fuente o no causalidad; requieren explicaciones por origen/temporalidad y cobertura del dataset.
- **2086 C2 y 181 C3 = 2267** muestran DOS velas H1 relevantes de **60/60** M1 nativos (78,82% del libro). Los otros **609** carecen de dicha prueba exacta: 498 reconstruidos con alguna hora parcial y 111 de evento de origen no reconstruido. La política V48 acepta agregación parcial >=45/60 M1. No usar 609 como veto ni como prueba de lag H1, pero nunca llamarlos velas completas sin evidencia.
- Los **1604 estados SESSION_INHERITED** continúan presentes; el test enlaza el origen QORE con señal anterior, pero no demuestra vigencia económica del POI superior del autor ni que un H1 previo con historial incompleto sea ejecutable.

**Conclusión:** C2/C3 no desaparece del H1 por ausencia de etiqueta. La mayoría tiene un POI QORE internamente reproducible; la fidelidad a POI **HTF fuente** (incluida vela contraria contextual), la calidad 60/60 y el protected swing permanecen **UNRESOLVED**.

### 5.2 Streaming first-global y observacionales [#38099916845 — 11/11 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38099916845)

- 2876/2876 oportunidades originales; **1786 (62,1%)** dan misma primera familia y mismo timestamp con un recorrido online en cada close; **1090 (37,9%)** cambian familia o primer instante detectado frente a V49.
- Las 381 diferencias FULL-vs-PREFIX del estudio previo son **sólo una parte** de las 1090 diferencias al preguntar por el primer evento DETECTADO minuto a minuto. Un snapshot de prefijo una vez al cierre original NO sustituye streaming.
- **0 descubrimientos retrofechados** registrados en el detector incremental sobre el libro source-anchored. Cada trade supuesto se observaría al close de detección, no en un timestamp posterior asignado ex-post.
- MAX3 original **2020** y MAX3 anclado reordenando las decisiones online **2020**, pero sólo **1989 identidades** se conservan en la intersección y **31** sustituyen IDs. Esto es prueba de sensibilidad de orden, **no** replay completo, pues V49 POI/M15/SL/target de un nuevo tiempo no se revalidó causalmente.

**Diferencia de favorable CLOSE+H (online menos V49), únicamente porcentajes de trayectorias ex-post, no win rate ejecutado:**

| Cohorte fuente y cobertura efectiva | +15m | +30m | +60m |
|---|---:|---:|---:|
| 381 FULL/PREFIX previas (N=381/381/380) | +1.8373pp | +3.4121pp | +1.3158pp |
| 1090 cambiadas en streaming (N=1087/1087/1083) | +10.3036pp | +9.4756pp | +6.5559pp |
| 2876 oportunidades (N=2870/2868/2859) | +3.9024pp | +3.5914pp | +2.4834pp |
| 2020 MAX3 original (N=2018/2016/2013) | +3.8157pp | +3.5218pp | +2.7819pp |

- Son diferencias **apareadas con el mismo H1 direction**, pero entradas medidas a dos instantes potencialmente diferentes; la combinación STOP/TARGET e intrabar BID/ASK/COST no se reejecuta.
- 381 originales muestran mejora observacional menor de 5pp; no concluir equivalencia estadística/real con este estimador de punto, especialmente por clustering de días. Los 1090 cambios muestran un diferencial más grande favorable al primer online, hipótesis económica de orden que exige replay causal completo.
- MFE/MAE y signed-return/R de referencia original están disponibles en los **2876 recibos por ID** para cada horizonte, no utilizar su magnitud para elegir filtros o autorizar trades.
- Nuevo estudio separado de intervalos por *operating-date cluster* `capitalizer_scalper_a2_thirteenth_paired_cluster_uncertainty_v1.py` usa exactamente estos dos libros congelados sin buscar nuevos parámetros. Sólo después de su ejecución correcta se interpretará robustez de bandas <5pp.

**Estado después del ciclo 13: NO CERTIFICABLE, World Model sin expandir, cero vetos, cero modificaciones del baseline V49, PR #759 DRAFT, GitHub-only.**


## 6. Incertidumbre pareada y cierre de supuestos H1 [#38100268079 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38100268079)

Estudio nuevo `capitalizer_scalper_a2_thirteenth_paired_cluster_uncertainty_v1.py`, que **no vuelve a seleccionar eventos**: cruza los artefactos originales de los 9 mercados de las runs #38099880288 y #38099916845, 2876/2876 source IDs, y hace 1000 remuestreos de los 313 días operativos disponibles, muestreando **días completos con todos sus símbolos** para conservar dependencia cross-market.

**Población 381: NO se certifica equivalencia dentro de ±5 pp**, pese a estimaciones puntuales menores de 5 pp:
- CLOSE+15: online menos V49 **+1.8373 pp**, 95% día-cluster **[-3.8147, +7.6294]**, N381, 212 fechas con cobertura.
- CLOSE+30: **+3.4121 pp**, CI **[-1.5666,+8.6294]**, N381.
- CLOSE+60: **+1.3158 pp**, CI **[-2.4213,+5.1151]**, N380.
- 247 con sensor estático anterior: -3.6437 pp a +15 (CI -11.2903,+3.7037); 134 de discrepancia de familia al MISMO cierre en el estudio estático: +11.9403 pp a +15 (CI +4.6512,+19.685). Esta última comparación es entre V49 y el **primer detector verdaderamente incremental**, que puede detectar otro evento a una hora diferente; NO equivale a decir que cambiar nombre de familia al mismo instante altera la trayectoria. Por eso se exige el reporte de timestamps en el ledger per-ID.

**Población 1090 cuya primera detección incremental difiere:**
- +15: +10.3036 pp, CI **[+6.7753,+14.0304]**, N1087, 301 fechas;
- +30: +9.4756 pp, CI **[+6.8966,+12.1270]**, N1087;
- +60: +6.5559 pp, CI **[+4.2991,+8.9317]**, N1083.
Las ventanas 15/30 tienen CI completamente por encima de +5pp en favorable **CLOSE**, no retorno neto o trades realmente ejecutados. Sin enumeración de todas oportunidades source y portfolio real reejecutado, no adjudicar “PF causal-first mejorado”. El cambio de cohortes posterior implica sesgo de composición; A/B full causal reconstituido es P0 posterior.

**P0 H1 adicional — nuevo hallazgo observable por cruce de fuentes nativas:**
- 2765 de 2876 eventos C2/C3 y POI reproducidos con el detector QORE.
- De esos 2765, **2614** tienen `origin_closed_at` en el cierre horario UTC canónico **HH:00**, **151** tienen un cierre H1 reportado **fuera del límite HH:00**.
- **111** sin origen reconstruido: **57** con estado directo, **54** `SESSION_INHERITED`. Estas 111 identidades no quedan marcadas causalmente “inválidas” hasta resolver la reconstrucción.
- **2267/2876** disponen de dos H1 relevantes 60/60. Es consistente con al menos **151 eventos originados en H1 de cierre no horario**, pero NO prueba que las 151 decisiones M1 ocurrieran antes del cierre real programado; hay que verificar `entry_at` versus siguiente límite horario y distinguir solo anomalía de proveedor/mercado sin cotización de señal realmente adelantada.
- Regla actual de ingeniería **>=45 M1 por H1** y cierre tomado del último M1 presente contrasta con concepto de vela de H1 cerrada en su timeframe real. Se requiere refutar/confirmar si esto permite activar sesgo sin cierre HTF causal en 151 ID, **no se impone veto ni se reescriben V49**.

**Próximo orden exacto:** (i) explicar 57+54 originales no reconstruidos; (ii) verificar cada H1 no-HH:00 contra entrada M1 as-of y HTF close real; (iii) confirmar POI del autor y M15 swing; (iv) reconstruir oportunidad raíz completa con first incremental + targets/stop y MAX3, y reejecutar su economía con fees/BID/ASK, fecha/mercado OOS sellado. Mientras tanto NO CERTIFICABLE.
