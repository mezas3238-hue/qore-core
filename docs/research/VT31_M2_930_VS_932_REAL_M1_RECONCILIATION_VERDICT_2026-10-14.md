# VT31 M2 — RESULTADO: RECONCILIACIÓN DOL ICT GENERAL PR #930 vs #932
**Corte 14-10-2026** · **Research DRAFT #941** · **NO CERTIFICACIÓN METODOLÓGICA/COGNITIVA**
**Suite validada:** [run #38641997091](https://github.com/mezas3238-hue/qore-core/actions/runs/38641997091), código `b3d4ce185a4928026d30c63ee79bf1fe95994fe0`, **65/65 tests PASS**. Artifact [#11930716746](https://github.com/mezas3238-hue/qore-core/actions/runs/38641997091/artifacts/11930716746), ZIP SHA256 `b032363d7e16a8727d284ccf252f1c3d0a2b155204bdf12cd91f2f3ca167882a`.
**Prerregistro previo a scripts:** commit `8ddbdf3ba9c3728af5cdb6d34f95fe60ea29d484`.
**Verificadores NO MODIFICADOS:** #930 P3 @ `1c820086339323f79d4ec1cb5954fb53841064b2` blob `bb11d965e99666957378e9748e710360dc5bb9ac`; #932 V1 @ `e3f65b34599cc868d6cf1867dcc3df480e1e66d4` blob `eb3e39db84f487ac8f2f5cfac00ad3f8247683c2`.
**Fuente:** artifact GitHub Actions #11459859004, `NAS100/market-evidence.json`, 1.059.784 M1, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`. Desarrollo previamente explorado, NO OOS nuevo.

## Tabla de paridad (216 sondas fijadas antes de acceder al histórico)
12 fechas preespecificadas × 3 ventanas ICT × 3 familias (cash anterior/Asia/London) × 2 sides. 0 sondas carecían del cierre M1 elegido. Cada observación contiene barras **M1 históricas verdaderas**, pero el DTO COG se construyó para diagnóstico de contrato: **SYNTHETIC_PROBE_NO_METHOD_CERT**, NO lo emitió el COG real de VT31.

| Estado P3 / V1 | Sondas |
| --- | ---: |
| SUPPORTED / SUPPORTED | 31 |
| REJECTED / REJECTED | 118 |
| UNKNOWN / UNKNOWN | 37 |
| UNKNOWN_UNATTESTABLE_INPUT / UNKNOWN_UNATTESTABLE_INPUT | 24 |
| REJECTED / UNKNOWN | **6** |
| **TOTAL** | **216** |

Los 24 `UNKNOWN_UNATTESTABLE_INPUT` son fuentes no cerradas `as_of` y el DTO real rechazaría incorporar hechos futuros; se conservaron en la población sin inventar precios/timestamps.

## Causa raíz de las seis discrepancias
Las **6** pertenecen **a una sola fecha**, **16 de enero de 2024**, familia `PRIOR_NY_CASH_SESSION`, dos sides (HIGH/LOW), repetidas en las tres ventanas NY (London/NY AM/NY PM). **No equivalen a seis días o seis operaciones independientes.**

- P3 (#930): `REJECTED: COG_DOL_PRICE_DIFFERS_FROM_INDEPENDENT_M1_SOURCE`. P3 recorre hacia atrás días incluidos en history hasta hallar un cash de 390 M1 completo, que puede ser ANTERIOR al weekday inmediatamente precedente.
- V1 (#932): `UNKNOWN: SOURCE_POOL_NOT_CAUSALLY_ATTESTABLE / PRIOR_WEEKDAY_CASH_INCOMPLETE_OR_HOLIDAY_CALENDAR_UNKNOWN`. V1 fija el weekday anterior y no rellena la ausencia o incompletitud de M1 con una sesión más antigua.
- La prueba usa un **target sintético de prueba** cuando V1 no puede construir el pool; la etiqueta de P3 `PRICE_DIFFERS` no demuestra que el COG auténtico haya seleccionado un precio erróneo. Son semánticas distintas de gestión de la fuente, NO una falsación del trader en ese día.
- Existe además divergencia unitaria independiente: si la marca `draw_level_observed_at` se atrasa un minuto respecto del cierre fuente (pero sigue antes de as-of), P3 **REJECTS** porque exige igualdad exacta; V1 **CONFIRMS** un sello temporal tardío bajo cobertura completa. Reproducida en pytest con M1 sintéticas; NO afirmar frecuencia sobre M1 real.

## Decisión técnica de este ensayo (sin cambiar G3 ni ICT doctrinal)
1. **No sustituir #930 por #932 ni viceversa** en un trader candidato sin contrato PIT de calendario/festivos/early close aprobado y prueba causal con COG auténtico. Un fallback a viernes puede ser correcto si lunes es festivo REAL, pero es inseguro adivinarlo sólo por ausencias en el dataset CFD.
2. Contrato conservador interino: fuente cash anterior NO HOMOLOGADA = `UNKNOWN` si el weekday inmediatamente anterior carece de 390 M1 y no existe una prueba externa auditable de calendario/evento válida `as_of`. Esto es criterio de seguridad de la **auditoría**, no una alteración silenciosa al COG.
3. Fecha 2024-01-16 es un **testigo reproducible** para análisis de calendario; exigir evidencia PIT de si el lunes 2024-01-15 tuvo mercado, cierre anticipado o diferencia NAS100 CFD/cash antes de adoptar regla de retroceso. No inferirlo de la fecha solamente.
4. Congelar un timestamp único: `draw_level_observed_at` debe ser separado en `source_confirmed_at` y `cog_emitted_at` si en el futuro se permite sello tardío. Hasta entonces M2 no tiene paridad por contrato.
5. Ejecutar próxima prueba contra decisiones efectivamente emitidas por `VT31CleanroomCognition` sobre prefijos M1 cerrados de fechas fijas, sin DTO neutral. Los 216 probes NO satisfacen B02 sobre COG auténtico.
6. Mantener estados `UNKNOWN` cuando calendario/fuente no justifiquen `SUPPORTED`; cero tuning usando PnL y cero imputación de niveles.

## Dictamen Gates y límites
- **B03: causa de discrepancia LOCALIZADA, NO RESUELTA a nivel de contrato canónico.**
- **M2: PARCIAL, NO CERTIFIED.** Esto no otorga M0/M3/M4/M5/M6/M7, L1–L10, ni autoridad económica.
- **M4** FVG causal previo #938 independiente de esta reconciliación; OB/Breaker/Displacement pendientes.
- **M5** todavía sin broker ACK ni fills; **M6** firma dual genuina / cambio formal de gobernanza pendiente.
- **No órdenes, 0 fills, PF/DD/Sharpe no evaluados, NO sizing trader, no merge main, no LIVE/DEMO/VPS/FundedNext**.

## Reproducción
PR DRAFT #941 contiene script `scripts/vt31_m2_dol_reconciliation_20261014.py`, test `tests/infrastructure/test_vt31_m2_dol_reconciliation_20261014.py`, workflow `.github/workflows/vt31-m2-dol-reconciliation-20261014.yml` y prereg. CI obtiene el P3 original de Git SHA congelado con `git show` (sin fusionar ramas), verifica blobs G3+P3+V1 y checksum de datos, ejecuta 65 tests y las 216 sondas. Artifact retención 90 días; guardar hashes y vigilar su caducidad. El uso de `UNKNOWN` no significa edge negativo ni positivo.

## Adenda de fuente PIT: calendario de 15-ENE-2024 (verificación externa)
**Evidencia Nasdaq oficial y contemporánea:** [Equity Trader Alert #2024-2](https://www.nasdaqtrader.com/TraderNews.aspx?id=ETA2024-2), **publicado el 08-ENE-2024**, previo al 15-ENE y a la decisión del 16-ENE. Nasdaq anunció que sus mercados de **acciones y opciones** permanecerían **cerrados el lunes 15-ENE-2024** por Martin Luther King, Jr. Day. El aviso distingue que su feed `Global Index Data Service (GIDS)` **seguiría disponible** ese mismo día. Calendarios públicos de [NYSE/ICE publicados en 2022](https://ir.theice.com/press/news-details/2022/NYSE-Group-Announces-2023-2024-and-2025-Holiday-and-Early-Closings-Calendar/default.aspx) también fijan la fecha como feriado de cash US.

**Conclusión estrecha:** el hallazgo histórico **es consistente** con que el cash NY regular del lunes 15-ENE no tenga 390 M1. Esta es una evidencia de calendario **as-of verificable** para el mercado accionario de Nasdaq; NO prueba por sí sola que la fuente `NAS100 CFD` o el símbolo `USTEC` tuviera iguales horarios, ni que un pool de viernes esté intacto hasta el martes. La disponibilidad de un feed de índices el feriado evidencia por qué no puede generalizarse la regla `cash closed => no CFD ticks`.

**Siguiente chequeo antes de política nueva:** (a) vincular mercado de referencia Nasdaq cash vs CFD broker y especificación de horas; (b) comprobar 390 M1 12-ENE como cash anterior elegible y toda la cronología M1/bid-ask as-of, sin imputaciones; (c) registrar calendario PIT con versión y hash, override explícito de feriado con `reason`; (d) revalidar COG NATIVO, no probe. Se mantiene `M2_PENDING` y veredicto del código original intacto.
