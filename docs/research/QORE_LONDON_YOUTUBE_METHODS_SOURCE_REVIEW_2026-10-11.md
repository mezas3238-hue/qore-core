# QORE / Londres EURUSD + GBPUSD — fuentes metodológicas en YouTube: barrido asiático, reversión vs continuación

**Fecha:** 2026-10-11 · **Documento: REVISIÓN DE FUENTES, NO PRERREGISTRO NI CERTIFICACIÓN**. Rama `research/london-after-asia-sweep-path-20261011` separada de V49/DCVC/producción. Estudio experimental previo [Issue #775](https://github.com/mezas3238-hue/qore-core/issues/775), [PR #776](https://github.com/mezas3238-hue/qore-core/pull/776), run #38146670174; censo EURUSD primer breach 169/206=82,0%, GBPUSD 197/222=88,7% de jornadas con Asia completa. Dos mecanismos mínimos L1/L2 negativos bajo el protocolo allí congelado; estos resultados **no** invalidan las variantes de los autores que exigen condiciones adicionales.

## Estado de verificación / cautela

Se localizaron títulos, autores, fechas y enlaces de vídeos mediante índices de YouTube y materiales de transcripciones parciales/descriciones accesibles; cuando es posible, se cotejó con **artículos oficiales del propio TTrades** que explicitan reglas. No afirmar que se ha auditado exhaustivamente minuto por minuto la totalidad audiovisual: los vídeos originales no estuvieron plenamente reproducibles mediante las fuentes de consulta de esta ronda. **PROVENANCE:** `AUTHOR_SITE_EXPLICIT` vs `PRIMARY_YOUTUBE_DESCRIPTION` vs `INDEXED_TRANSCRIPT_SUMMARY` vs `QORE_TEST_PROPOSAL`. El resumen de terceros NO reemplaza fuente primaria para implementar un detalle no especificado.

## A. Fuente primaria del autor TTrades (prioridad)

### A1 — ICT Daily Profile: London Reversal / New York Continuation
- **Autor:** TTrades. Vídeo YouTube **26 ago 2024**: https://www.youtube.com/watch?v=y6SnEdASVLY
- **Referencia textual del autor:** https://ttrades.com/london-reversal-and-new-york-continuation-daily-profile/
- **AUTHOR_SITE_EXPLICIT:** Asian session **20:00–00:00 EST**, London **02:00–05:00 EST**, NY AM **08:30–12:00 EST**, según su propia página; NOTAR que esto **no equivale** a nuestra Asia range `00:00–07:59 Europe/London` y London first breach `08:00–11:00 Europe/London` probadas en #776. "EST" del autor requiere adjudicar si es hora NY con DST o EST fijo antes de programar.
- Narrativa explícita: London desarrolla el extremo/mecha de la vela diaria, **CISD confirma entrega opuesta**, NY puede continuar distribución. London no siempre completa todo el recorrido; NO identificar toda continuación de NY como efecto ya logrado en Londres.
- Observables requeridos: precio NY midnight open/daily-open definido; sweep de extremo previo; CISD disponible; tipo de perfil Bullish/Bearish; llegada al otro extremo a una ventana futura. **UNRESOLVED:** swing/serie CISD exacta según vídeo, temporización extrema; consultar vídeo completo si se pretende etiquetar autor-exacto.

### A2 — Power of Three / AMD
- **Autor:** TTrades. Vídeo 31 oct 2023: https://www.youtube.com/watch?v=TCFvsZeYvV8
- **INDEXED_TRANSCRIPT_SUMMARY:** acumulación/rango → manipulación como ruptura falsa → distribución; **HTF bias / Draw-on-Liquidity (DOL)** previo a identificar dirección. Se enseñan **dos estilos diferentes**: entrar durante manipulación por señal de reversión o después de confirmada distribución mediante continuación. Un barrido sin desplazamiento no basta para detectar cuál ocurrirá.
- **Test propuesto QORE, NO regla textual del autor:** cronometrar la secuencia first breach → regreso al rango → desplazamiento de estructura → estado de distribución, con outcomes de rango/DOL; conservar `NO_DISPLACEMENT`, `BREAK_CONTINUES`, `AMBIGUOUS`. Jamás usar expansión futura como variable predictiva al instante del breach.

### A3 — Market Structure Shift vs Liquidity Grab
- **Autor:** TTrades. Vídeo 25 jul 2023: https://www.youtube.com/watch?v=ynFA6E3qHj0
- **PRIMARY_YOUTUBE_DESCRIPTION + TRANSCRIPT indexed:** distingue **MSS = desplazamiento con cierre atravesando swing/estructura** de **liquidity grab = intento sin ese desplazamiento**. Una mecha que cruza Asia high/low NO es suficiente para afirmar MSS o reversión. Se debe demostrar disponibilidad as-of del swing relevante (su vela derecha si es pivot) y del cierre de ruptura.
- **Test propuesto:** separar (i) raid sin confirmación, (ii) barrido y CISD temprano, (iii) MSS con desplazamiento confirmado y (iv) ruptura con aceptación y retest sin retorno al rango. Definiciones de desplazamiento y pivot requieren congelación antes de outcomes.

### A4 — MSS vs Change in State of Delivery (CISD)
- **Autor:** TTrades. Vídeo 12 dic 2023: https://www.youtube.com/watch?v=E89d1HArbgM
- **AUTHOR_SITE_EXPLICIT:** https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/
- MSS: **desplazamiento + cierre atravesando swing**. CISD: cierre a través del **open de la secuencia de velas a favor/en contra**, confirmando cambio de entrega; CISD puede llegar ANTES del MSS, con riesgo de falsas señales. No son sinónimos ni deben exigirse simultáneos en una vela M1.
- **Test propuesto:** evento as-of `CISD_ONLY`, `MSS_ONLY`, `CISD_THEN_MSS`, `NONE` tras primer raid y retardos; evitar que el swing se detecte ex post.

### A5 — SMT divergence (solo confirmación/contexto)
- **Autor:** TTrades. Vídeo 29 ene 2024: https://www.youtube.com/watch?v=27S9gjgcSlI
- **INDEXED_TRANSCRIPT_SUMMARY:** SMT compara extremos de mercados correlacionados/inversamente correlacionados y sirve como **confluencia**, NO como estrategia autónoma. Se ejemplifican ES/NQ y EURUSD/DXY. EURUSD y GBPUSD se pueden someter a una prueba correlativa propia, pero **no se atribuirá una regla EURUSD vs GBPUSD exacta al autor sin verificación textual y control de sincronización/normalización de swings**.
- **Nuevo contrato distinto si se autorizase:** ante primer raid de uno, observar causalmente si el otro confirma extremo en ventana fijada, controlar relación de correlación por sesiones, as-of de ambas fuentes; solo después evaluar asociación condicional con outcomes. No ajustar ventana tras resultados.

## B. Fuente original ICT (separada de TTrades, sin mezclar definición temporal)

### B1 — How to Use the Asian Range for Forex Trading
- **Autor:** The Inner Circle Trader. Vídeo 9 dic 2017: https://www.youtube.com/watch?v=JA0mLNJeytY
- **INDEXED_TRANSCRIPT_SUMMARY:** Asian Range definida **19:00–00:00 hora NY** (high y low en ese periodo), con contexto de sesgo diario; el propio autor indica que la idea del rango asiático **no fue inventada por él**. Esa ventana **difiere** de TTrades 20:00–00:00 y del estudio #776 00:00–08:00 UK. Fijar calendarios y DST. No reutilizar probabilidades 82–88% como base rate bajo una definición nueva.

### B2 — ICT Forex: Understanding the ICT Judas Swing
- **Autor:** The Inner Circle Trader. Vídeo 10 dic 2017: https://www.youtube.com/watch?v=xJMbva8SjzE
- **INDEXED_TRANSCRIPT_PARTIAL + bibliografía secundaria:** falsa extensión contra un sesgo diario antes de la dirección de entrega; el timing/daily-open y draw-on-liquidity importan. **No equiparar cualquier primer cruce de rango asiático a `JUDAS_CONFIRMED`**. Verificar vídeo original antes de formalizar criterios.
- Vídeo didáctico adicional aplicado a GBPUSD Londres, **21 feb 2025**: https://www.youtube.com/watch?v=WGGDbeRpo4w — ejemplo/explicación de ejecución, NO backtest ni regla de rentabilidad general.

## C. Variante mecánica distinta: breakout, aceptación, retest

### C1 — How To Spot Breakout Opportunities DAILY!
- **Canal:** Transparent Fx Academy. Vídeo **23 feb 2025**: https://www.youtube.com/watch?v=TfPTBAIhm8s
- **PRIMARY_YOUTUBE_DESCRIPTION:** identifica el rango Asia y distingue **rango consolidado vs Asia direccional** antes de buscar breakout durante Londres/NY. Habla de un Expert Advisor automatizado como demostración; no demuestra por sí solo edge.
- **Apoyo metodológico externo, NO YouTube primario:** https://www.quantparadox.com/blog/london-breakout-strategy (6 sep 2026) define alternativas break inmediato, confirmación al cierre, retest y fallo, cada una COMO REGLA DISTINTA. Evitar mezclar sus métricas.

### C2 — Forex Session Strategy: Asian Range to London Breakout
- **Canal:** Edge-Forex. Vídeo **27 feb 2026**: https://www.youtube.com/watch?v=j31onXXHd-0
- **PRIMARY_YOUTUBE_METADATA únicamente:** título y existencia, sin transcripción ni descripción verificable en esta investigación. **NO derivar normas ejecutables ni rentabilidad de este vídeo hasta obtener evidencia completa**.

## D. Qué cambia en la investigación real de Londres

1. **Mantener primero la pregunta del usuario como censo de estados de precio, NO trading:**
   - `ASIA_COMPLETE` con evidencia de M1 nativo;
   - `FIRST_RAID_HIGH/LOW`, tiempo del raid, penetración en **fracción de rango asiático** (no pip absoluto);
   - `RETURN_INSIDE` y primer timestamp;
   - `CONSECUTIVE_OUTSIDE_CLOSES` + eventual `RETEST_HOLDS` con primeras confirmaciones;
   - `CISD_CONFIRMED` y `MSS_DISPLACEMENT_CONFIRMED` con reloj causal y swings pivot-right; `NO_CONFIRMATION` y `UNKNOWN` trazables;
   - **outcomes separados, SOLO ex-post:** MFE/MAE direccional, exceso sobre Asia range, distancia a extremo opuesto, recorrido normalizado en ventanas después del raid (15/30/60/120m), hora de máximo/mínimo e inversión del recorrido. Los outcomes **no deben alimentar reglas de clasificación de trigger**.
2. **La base rate no identifica reversal/continuation:** EURUSD 82%, GBPUSD 89% primer contacto en #776 *bajo 00:00–08:00 UK*. La hipótesis interesante es la **probabilidad condicional de reversión/continuación dadas observaciones as-of posteriores al raid**. Hay que definir ex ante qué cuenta como reversión/continuación, qué horizonte temporal y qué benchmark no condicionado; no inventar etiquetas de rentabilidad.
3. **Dos escuelas NO compatibles por omisión:** ICT Asian Range 19:00–00:00 NY; TTrades 20:00–00:00 EST; QORE #776 00:00–08:00 UK. Su universo elegible, tasa de raid, sesgo y probabilidades diferirán. Si se investigan varios, diseñar un **estudio de definición** con familias multiplicidad explícitas, no mover el rango para cazar edge.
4. **MSS vs CISD**: invariante de causalidad primero. No llamar MSS al simple cierre dentro de Asia ni CISD al sweep. No colocar SL/TP, exigir BID/ASK o integrar QDLE para el primer análisis de rutas/precio que solicita el usuario. Estas fuentes metodológicas no establecen ni garantizan PF>1.
5. **Prerregistro a crear en siguiente etapa** separado de este review: pares EURUSD, GBPUSD, M1 native de #35548099334, reglas de horario fijo, censo FIRST-ONLINE de todos los días elegibles, rutas tras raid, convención para 2 extremos alcanzados en M1, límites de feed, muestra/periodos y potencia/IC por jornadas. Este documento **NO autoriza elegir umbrales según resultados ya vistos** ni declarar confirmatorio el histórico consumido.

### Fuente vs implementación, estatus

**Conclusión de la revisión de YouTube:** las metodologías examinadas enfatizan **contexto/bias + distinguir barrido fallido de ruptura confirmada + desplazamiento/CISD/MSS/retest**. El estudio anterior L1/L2 comprimió todo en una recuperación al rango o dos cierres M1, con stops muy estrechos; **no es una refutación de TTrades o ICT**.

**Estado:** revisión bibliográfica con enlaces directos, NO vídeo íntegro auditado segundo a segundo, NO trade nuevo, NO ejecución económica, NO certificación. Mantener producción/VPS intactos.
