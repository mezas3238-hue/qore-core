# VT31 — Dictamen de fuentes primarias M3 / M4 / M5 y precedencia de metodología

**Fecha de auditoría:** 2026-10-16. **Trader:** VT31 NAS100, ICT Silver Bullet. **Alcance:** certificación por **metodología y cognitiva**, no rentabilidad cuantitativa, sizing, órdenes ni PnL.

**Cadena de código de investigación verificada:** Handoff R5 #975 → preselect #971 → source-temporal #978 → OB/Breaker M4 closed M1 #979 → COG V2 #983 → COG V3 #986 → COG V4 #990, HEAD `2abd1407c627753a570593e5fec7ced2a318ae97`. La CI de V4 [#38902424162](https://github.com/mezas3238-hue/qore-core/actions/runs/38902424162) aprobó 234 pruebas sintéticas y de regresión. **Eso NO es validación independiente de casos autorales M3–M5.**

## 1. Jerarquía documental (no mezclar perfiles a posteriori)

**A — Definición primaria específica TTrades NY AM 2025, 19-Jun-2025**: [The AM Silver Bullet Strategy on NQ](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/). Afirma:
- Horario **10:00–11:00 America/New_York**. Tomar **H1 de 09:00–09:59** ya cerrada.
- Primero sweep de **un extremo de H1**; después confirmar entrada (no operar por sweep aislado). Sweep del alto => short y objetivo **H1 low**; sweep del bajo => long y objetivo **H1 high**.
- Familias admisibles explícitas: **displacement dentro del rango**, **breaker**, **order block**, **fair value gap dentro de estructura**.
- El **stop** está más allá del **swing high/low que causó el desplazamiento**, no del wick de retorno elegido arbitrariamente.
- La página **no estipula** que la confirmación MSS/CISD tenga que darse simultáneamente en todos los modelos ni suministra algoritmo exacto para seleccionar, entre varios, el swing causante del desplazamiento.
- No certifica las sesiones **London** o **NY PM**. No trasladar la H1 09/target contrario a esas ventanas.

**B — Tutoriales generales TTrades publicados en 2025**: sirven para **falsar** estructuras insuficientes, no para inventar requisitos nuevos al AM, redefinir sus objetivos ni anular una regla específica de A.

**C — QORE/G3/ICT general**: perfiles y convenciones propios, sujetos a **firma explícita**. El mínimo `MIN10` de G3 no es prueba de requisito de autor TTrades AM. Si conflicto ⇒ **WAIT con etiqueta de conflicto**, no adjudicar que TTrades incumple un criterio de QORE.

**D — Artículos TTrades de 2026**: pueden inspirar una revisión futura versionada, pero **no** reinterpretan retroactivamente el perfil congelado `TTRADES_NY_AM_2025`. Si se integran exigen nueva política M0 predeclarada y revisión independiente.

## 2. Matriz de pruebas, fuente y verdict

| Gate | Fuente principal verificable | Lo que sí exige la fuente | Qué no debe darse por probado | Dictamen actual |
|---|---|---|---|---|
| M0-TTrades NYAM | AM Silver Bullet, Jun-19-2025 | Tiempo NY 10–11, H1 09 cerrada, primer sweep, objetivo extremo opuesto, perfil antes del ingreso | Que el selector M0 QORE cuente con firma Owner o que `MIN10` sea regla del autor | `RESEARCH_CONTEXT_ONLY / POLICY_OWNER_UNSIGNED` |
| M3-MSS | [MSS vs CISD, Jul-01-2025](https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/) | **MSS**: desplazamiento y cierre más allá de un swing relevante. **CISD**: cierre más allá del **precio de apertura** de serie de velas opuestas. Son pruebas de estructura distintas | Que cualquier cierre CISD sea un MSS; o que **ambos** sean obligatorios en cada entrada Silver Bullet 2025 | `M3_AUTHOR_SPECIFIC_AM_APPLICATION_PENDING` |
| M4-Displacement | AM Silver Bullet, Jun-19-2025 | Después del sweep, displacement **de regreso al rango H1** para esa familia, con dato M1 cerrado | Que cualquier vela fuerte = displacement causado por un swing identificable | `M4_DISPLACEMENT_AUTHOR_CASE_PENDING` |
| M4-FVG | [Understanding Fair Value Gaps, Jun-15-2025](https://ttrades.com/understanding-fair-value-gaps/) + AM Silver Bullet | Patrón **3 velas**, no-solapamiento entre wick de velas 1/3, dirección BISI/SIBI, dentro de estructura AM | Que FVG geométrico aislado sea entrada AM; inversión FVG futura como entrada por sí sola; que todo retest al 50% sea fill ejecutable | `M4_FVG_SOURCE_CONTEXT_PENDING` |
| M4-OB | [Order Blocks Simplified, Jul-04-2025](https://ttrades.com/order-blocks-simplified/) + AM Silver Bullet | Serie final de velas opuestas, **POI/confluencia HTF**, retest posterior, mean threshold **50% body**, invalidación por **cierre** más allá del mean | Que escoger siempre la última vela `opposing[-1]` represente la zona multivela autoral; que un wick a través del mean invalide por sí solo; que cualquier HTF tag arbitrario sea confluencia | `M4_OB_MULTICANDLE_AUTHOR_SELECTION_PENDING` |
| M4-Breaker | [Breaker Blocks Simplified](https://ttrades.com/breaker-blocks-simplified/) + AM Silver Bullet | LONG: Low→High→Lower Low→Higher High; SHORT: High→Low→Higher High→Lower Low; block candle(s) causal y retest posterior; displacement como contexto | Que único pivot M1 o `breaker_level=level` basten; que tutorial general fije un único stop idéntico al AM; que zona multivela esté adjudicada | `M4_BREAKER_AUTHOR_ZONE_PENDING` |
| M5-Protected swing | [Protected Swings, Aug-06-2025](https://ttrades.com/protected-swings-understanding-trends-and-invalidations/) y [Stop Loss Mastery, Aug-07-2025](https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/) | Swing tras sweep o FVG confirmado por **cierre** sobre/bajo serie opuesta; el nivel protege la tesis, wick/beyond swing de referencia estructural | Que cualquier protected swing encontrado sea el **swing que causó** el displacement de la entrada AM; que el proxy G3 C2 FULL WICK, vela anterior al retest o un stop fijo sean equivalentes por definición | `M5_DISPLACEMENT_CAUSAL_SWING_UNVERIFIED_WAIT` |
| M0 London/NY PM ICT | Requiere material primario **específico de ICT** y caso separado por sesión | Ventanas canónicas London NY 03:00–04:00 y NY PM 14:00–15:00 NY local están contempladas como perfiles generales de investigación | Que **TTrades AM H1 09**, su DOL y sus reglas de stop sustituyan doctrina ICT London/PM | `ICT_AUTHOR_CASE_UNDERDETERMINED_WAIT` |

## 3. Aclaraciones y contradicciones que bloquean promoción

1. **MSS ≠ CISD:** el artículo primario de TTrades distingue explícitamente un **cierre de displacement más allá de swing** de un **cierre más allá del open de una serie de candles**. No son nombres para una sola condición. M3 debe guardar el **timestamp causal de confirmación**, clase de pivote y origen del swing, sin barras futuras. No crear `MSS=TRUE` sólo por `CISD=TRUE`.
2. **Stop de AM tiene precedencia:** [Stop Loss Mastery](https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/) menciona alternativas generales como stop en cuerpo en ciertos casos y swing protegido posterior. [Breaker Blocks Simplified](https://ttrades.com/breaker-blocks-simplified/) presenta alternativas de stop general. Sin embargo, **el Silver Bullet AM específico** fija stop **más allá del swing que causó displacement**. Es incorrecto promover un cuerpo o wick cualquiera para salvar una prueba de riesgo-retorno. Primero mapear ese swing a un evento y prueba autoral; si falta ⇒ WAIT.
3. **Orden causal estricto de M4:** H1 09 cerrada → raid 10h confirmada → retorno/desplazamiento y su causa → formación del arreglo estructural específico → confirmación/familia → retest/foco M1 completamente cerrado. Nada de elegir vela al cierre o completar swing con datos posteriores a `as_of`.
4. **HTF POI y multivelas:** aunque los gatekeepers #961/#979 comprueben un proxy de POI y una sola vela OB/Breaker, no se ha demostrado **cómo elegir la serie autoral** en presencia de 2+ velas candidatas. No optimizar selección mirando PnL; abstener hasta caso independiente anotado.
5. **Perfil temporal sin contaminación:** [MSS vs CISD Jul-2025](https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/) es un tutorial general **posterior** al artículo AM Jun-2025, así que no transformar su comparación en un nuevo gate universal obligatorio sin justificar explícitamente el enlace entre fuentes. Fuentes publicadas en 2026 no son prueba de la especificación de junio de 2025.

## 4. Protocolo operativo de adjudicación pendiente (sin operaciones)

Para cerrar **por metodología y cognitiva** cada una de las cuatro familias, se requiere un expediente con (1) URL exacta, fecha de publicación y extracto/paráfrasis del autor, (2) gráfico del autor con hora NY y OHLC legibles, (3) reconstrucción con `M1Bar` realmente cerrado y procedencia hash, (4) swing/POI/serie/candle(s) con timestamps de **confirmación**, (5) adjudicación independiente COG y OPS **humanas** de ambigüedades y conflictos, (6) dos casos negativos adversariales con `WAIT` reproducible, y (7) comparación sin alterar código G3. Todos los casos se exponen en NAS100 y sessions EST/EDT, LONG/SHORT cuando la fuente los cubra.

**Status de esta revisión:** criterio autoral **parcialmente documentado**, sin paquete completo de casos primarios adjudicados; **ningún M3/M4/M5 promocionado**. Una CI sintética no reemplaza firmas de metodología/cognitiva. Deben mantenerse `METODOLOGÍA=PENDIENTE`, `COGNITIVA=PENDIENTE`, `LIVE=DENIED`, `SIZING=0`, `ORDERS=0`.

**Próximo trabajo en código después de este dictamen:** implementar testigos M3 MSS y CISD **separados y causales** (no afirmar que ambos sean requisitos universales del AM), cuatro familas M4 con source-bound M1 y swing causante M5 inequívoco o WAIT, más comparación contra ejemplos del autor; luego llevar candidato transaccional V4 a un COG nativo **versionado** con revisión, sin editar silenciosamente el G3 congelado.
