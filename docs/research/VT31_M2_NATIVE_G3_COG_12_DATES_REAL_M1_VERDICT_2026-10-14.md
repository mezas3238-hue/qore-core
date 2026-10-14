# VT31 M2 — AUDITORÍA COG G3 AUTÉNTICO EN HISTORIA M1 (PR #942)
**Dictamen 14-OCT-2026: M2 NOT CERTIFIED, COG METHOD NOT CERTIFIED, NO LIVE.**
**Reproducción:** [GitHub Actions SUCCESS run #38645585592](https://github.com/mezas3238-hue/qore-core/actions/runs/38645585592), código ejecutado `acf152beefecfa3f1216cccc259b23a218ab405f`, **100/100 pytest PASS**. [Artifact #11932611179](https://github.com/mezas3238-hue/qore-core/actions/runs/38645585592/artifacts/11932611179), ZIP SHA256 `f47e2e5f6a287289e40d950a87e2cefa1a51c31b2711042b2479d060c96f2a0b`.
**Prerregistro anterior al código:** `2949a80886965d79fdf8d8908f058facaa14eb38`. **Fuente real** NAS100 1.059.784 M1 del artifact GitHub Actions #11459859004, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, desarrollo YA observado, NO OOS. 12 fechas fijas y perfiles London/NY AM/NY PM, G3 `QORE_G3_MSS_CLOSE_V1_PROPOSED` original sin modificar. P3 #930 y V1 #932 fuentes congeladas en hashes originales. **PR DRAFT #942**, NO MERGE a main, NO order/lotaje/economía/LIVE/VPS.

## Qué cambió respecto del PR #941
#941 probó **216 DTOs sintéticos** para comparar dos contratos DOL. Esta ronda alimenta M1 **cerradas en orden temporal al COG REAL `VT31CleanroomCognition`** con `framework_policy=G3_MSS_FRAMEWORK_POLICY`, una instancia limpia con calentamiento M1 previo de hasta 5 días NY por fecha, y llama a ambos verificadores **sólo sobre objetos CognitiveDecision realmente emitidos** y el prefijo de M1 existente al as-of. Esta distinción es esencial: no hay DTO inventado ni futuros, pero sigue siendo investigación de fuente QORE, no doctrina ICT original.

## Denominadores y resultados inmutables del CI
- **2.160/2.160 M1** de ventanas Silver Bullet en las 12 fechas fijas (3 ventanas × 60); **0 barras de ventana faltantes** en esos días. Esto NO significa que la trayectoria entera desde el pool DOL esté completa.
- **1.104 emisiones de COG** en 2.160 prefijos M1, incluidas tesis revalidadas que pueden aparecer en múltiples prefijos.
- **441 identidades de primera tesis** distintas por ventana/MSS/side/familia/target, NO 441 entradas/órdenes/trades. Una misma fecha puede generar múltiples tesis; no hay validación de prioridad/enrutado de operaciones en esta ronda.
- Matriz de **1.104 decisiones auténticas**:

| P3 testigo #930 | V1 testigo #932 | emisiones | Semántica |
| --- | --- | ---: | --- |
| SUPPORTED | SUPPORTED | **541** | Origen/contexto de precio QORE respaldado por ambos en el prefijo; NO autoría ICT ni orden ejecutable |
| UNKNOWN | UNKNOWN | **485** | Ambos testigos carecen de **cobertura M1 completa después del cierre del pool**; no adjudicar level como intacto |
| UNKNOWN | REJECTED | **78** | Contratos divergentes sobre origen y momento de cash previo; NO error probado de la dirección del COG |
| **TOTAL** | | **1.104** | 0 ACK, 0 fills, PF/Sharpe/DD no computados |

**P3 reason codes:** 541 `CONTEXTUAL_POOL_PRICE_AND_UNCONSUMED_SOURCE_OBSERVED_NOT_ICT_DOCTRINE`; **563** `POST_CONFIRMATION_M1_MONITORING_GAP` (= 485+78). **V1:** 541 `M2_QORE_CONTEXT_DOL_SOURCE_AND_AVAILABILITY_ONLY`; **485** `POOL_AVAILABILITY_UNVERIFIABLE / POST_SOURCE_M1_COVERAGE_GAPPED`; **78** `COG_DOL_ANNOUNCED_BEFORE_SOURCE_CLOSE`.

**Las 78 contradicciones se concentran en una sola fecha: 16-ENE-2024.** Se trata de **78 prefijos/emisiones temporalmente correlacionados**, NO 78 trades ni 78 días distintos. Las restantes 11 fechas no produjeron desacuerdos entre P3 y V1, aunque sí muchos UNKNOWN compartidos.

### Análisis causal del 16-ENE-2024
1. Fuente oficial [Nasdaq Equity Trader Alert #2024-2](https://www.nasdaqtrader.com/TraderNews.aspx?id=ETA2024-2), publicado **08-ENE-2024**: sus mercados cash/opciones cerraron **lunes 15-ENE-2024** por MLK Day; aviso también mantuvo feed de índices GIDS disponible. Esto puede explicar por qué V1 no encuentra 390 M1 en weekday inmediatamente anterior, mientras COG/P3 buscan el último cash completo previo.
2. **P3 UNKNOWN**, no VERIFIED: incluso si elige viernes 12-ENE como origen, hay **M1 sin cubrir después de la fuente**; no permite afirmar pool jamás tocado. **V1 REJECTED** porque interpreta la marca temporal anterior de un pool como previa al cierre del intervalo calendarizado lunes 15-ENE. Son semánticas históricas de calendario discrepantes.
3. La noticia del cash de Nasdaq NO homologa horario de `NAS100 CFD`/USTEC con Nasdaq cash y NO prueba ausencia real de transacciones/ticks el día 15. Es obligatorio obtener **calendario PIT del instrumento/broker exacto**, con cierres/paradas/event-time, más fuente completa de monitor M1/BID/ASK antes de promover el pool.
4. El problema de los **485 UNKNOWN compartidos** es distinto: cobertura post-fuente M1 incompleta. No ocultar la laguna porque el COG interno emita tesis revalidadas. El auditor externo se abstiene de declararla intacta.

## Dictamen para la arquitectura / Gates
- **B02 (COG auténtico):** ya existe muestra real de **emisiones G3** atestiguadas externamente en as-of, corrigiendo la limitación de los DTOs artificiales de #941. NO prueba fidelidad TTrades NY AM, porque el COG general puede elegir DOL de cash/Asia y TTrades exige opuesto H1 09 después de raid.
- **B03 (M2): BLOQUEADO.** 541 orígenes soportados en alcance, 563 sin corroboración completa (485 UNKNOWN+78 discrepancias por calendario/monitor). Se requiere reconciliación de política PIT de calendario, fuente CFD e integridad de trayectorias. No afirmar 541 trades válidos.
- **M3:** COG ha emitido cambios de estructura observables en el laboratorio, pero desplazamiento y fuente original por perfil no están certificados.
- **M4/M5/M6:** FVG proxy causal #938 permanece independiente; OB/Breaker, stop swing vs C2, secuencia ACK/fill, y gobernanza de doble autoridad aún pendientes. **Trader Lab L1–L10 no homologado**.
- **Comprobación de fidelidad:** un COG G3 general NO equivale al emisor TTrades research #933 ni a la metodología ICT original. Una tasa de emisión elevada no es densidad económica ni prueba rentabilidad.
- **Límite del experimento:** 12 fechas escogidas ex ante y hasta 5 días M1 de calentamiento por fecha, instancias limpias; NO representa persistencia exacta de un COG alimentado sin interrupciones durante todos los 3Y. NO extrapolar frecuencias a 775 días ni al conjunto del mercado.

## Trabajo prioritario siguiente sin tunear
1. **P0**: reconstruir tabla de `source_pool` POR sesión/fecha/side con calendario PIT del CFD broker y contrato Nasdaq cash vs USTEC; qué intervalos genuinamente cerrados no deben exigir M1 y qué huecos implican `UNKNOWN`. Separar `source_confirmed_at`, `cog_emitted_at` y `market_observed_at`. Sin autorización para alterar G3 congelado.
2. **P0**: cerrar 563 monitor-gap en un auditor *fail-closed* read-only por fuente; no contar niveles como intactos sin cobertura **o** justificación market-closed causualmente verificable. Conservar razones y testigos negativos; no rellenar M1.
3. **P0**: ejecutar otro ensayo independiente con COG **TTrades AM #933** y H1 09, con fuente as-of y prioridades de primer sweep→return→MSS; comparar decisiones verdaderas (no forzar que COG G3 adquiera identidad TTrades).
4. **P0**: revalidar M4 cuatro familias y M5 cronología. M6: firmantes independientes genuinos o gobernanza modificada por Owner; nunca fingir dos firmas.
5. Sólo tras candidatos congelados y gates metodológicos M0–M6 podrán evaluarse L1–L10, datos broker/ACK, Fresh Holdout intacto, riesgo CIBO y rentabilidad. **NO MERGE / NO LIVE / NO lotaje VT31.**

## Custodia/reproducción
PR #942 incluye script `scripts/vt31_m2_native_cog_real_m1_20261014.py`, tests `tests/infrastructure/test_vt31_m2_native_cog_real_m1_20261014.py`, workflow `.github/workflows/vt31-m2-native-cog-real-m1.yml`, prereg y este resultado. CI congela hashes G3 COG/OPS/documento, obtiene P3 #930 por Git SHA, coteja SHA256 del 3Y M1, verifica 100/100 tests, alimenta 12 fechas con M1 cerradas, guarda JSON y checksum de evidencias. El archivo ZIP Actions tiene retención limitada: issue #837 de custodia duradera continúa abierto.
