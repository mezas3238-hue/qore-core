# QORE CORE — SHARED B MASTER HANDOFF · ARCHITECTOS 4/5/6

**Fecha:** 2026-10-02  
**Owner:** Sergio Meza  
**Repositorio fuente de verdad:** `mezas3238-hue/qore-core`  
**PR soberano Shared:** #635 — OPEN / DRAFT / UNMERGED  
**Architect B checkpoint:** `fbf40f35f2c662dbe55930e59ac4dab4937f5b6a`

> El checkpoint es sólo punto de partida. Cada arquitecto e integrador debe revalidar HEAD antes de trabajar.

## 1. Misión

Dividir toda la deuda abierta del antiguo Architect B entre tres carriles independientes, sin duplicados:

- **Arquitecto 4 — World Foundation & Temporal Truth:** B-06..B-10
- **Arquitecto 5 — Relational Science & Asset Worlds:** B-11..B-15
- **Arquitecto 6 — Active Perception, Provenance & Freeze:** B-16, B-21, B-22, B-24

Integración:
- **Integrador 2 = Arquitecto 3 + Arquitecto 4**
- **Integrador 3 = Arquitecto 5 + Arquitecto 6**

Los work IDs B ya terminales no se reabren salvo regresión demostrada.

## 2. Leyes invariantes

- GitHub es la fuente de verdad.
- NO merge de PR #635 sin orden Owner.
- NO LIVE / producción / capital real / VPS.
- NO broker mutation.
- NO BUY/SELL, sizing, Risk, CIBO ni Execution authority.
- NO final Shared holdout.
- NO outcome-aware tuning.
- Provider schedule != canonical market calendar.
- Provider symbol/name != canonical identity proof.
- UNKNOWN/UNRESOLVED es una salida válida.
- CI GREEN no equivale por sí solo a capability closure.
- Todo cierre requiere evidencia, lineage y blockers = 0 para ese work ID.

## 3. Estado B que NO debe reabrirse

Terminales:
`B-01 B-02 B-03 B-04 B-05 B-17 B-18 B-19 B-20 B-23`

B-04 Full R8 ya está COMPLETE_AND_PROVEN:
- run `36765098842`
- artifact global `11129732922`
- 16/16 US2000 + 16/16 XAUUSD
- 2,948 ventanas por familia
- source-only; fresh holdout CLOSED; broker mutation FALSE.

## 4. Arquitecto 4 — B-06..B-10

Ownership exclusivo:
`B-06 B-07 B-08 B-09 B-10`

Objetivo:
1. cerrar identidad global provider-neutral o UNKNOWN explícito;
2. cerrar calendarios/market-hours canónicos sin promover provider schedules;
3. cerrar cadence/liquidity/skew/comparability policies con evidencia;
4. terminar STALE_RELATION empirical isolation;
5. poblar el relational graph sólo donde comparability esté autorizada.

Arquitecto 4 es la única superficie B que cruza con Arquitecto 3. Debe producir facts versionados, causales, timestamp-safe, provenance-bound y authority-free.

## 5. Arquitecto 5 — B-11..B-15

Ownership exclusivo:
`B-11 B-12 B-13 B-14 B-15`

Objetivo:
1. empirical relationship lifecycle population;
2. lead-lag observability population;
3. structural-divergence empirical population;
4. agricultura: mantener KNOWN BLINDSPOT si no existe proveedor autorizado; no inventar cobertura;
5. commodity world: identity/venue/front/roll/continuous-series semantics sólo con evidencia explícita.

No puede depender de outcome labels para descubrir relaciones.

## 6. Arquitecto 6 — B-16, B-21, B-22, B-24

Ownership exclusivo:
`B-16 B-21 B-22 B-24`

Objetivo:
1. convertir el 177-sensor qualification frontier en qualification científica real;
2. mantener manifest total de provenance/replay;
3. preparar WORLD_PERCEPTION_FREEZE únicamente cuando todos los work IDs obligatorios estén terminales;
4. preparar el handoff final B → integración.

B-22 y B-24 son downstream gates. Arquitecto 6 no puede cerrarlos adelantándose a B4/B5.

B-23 ya está cerrado y se consume como auditor; no se reabre.

## 7. Integrador 2 — Arquitecto 3 + Arquitecto 4

Tres verbos obligatorios: **INTEGRAR · REPARAR · AVANZAR**.

Debe:
- absorber continuamente A3 + B4;
- reparar contratos, schemas, temporal semantics, provenance, typing, tests y CI;
- avanzar trabajo seam cuando A3/B4 esté bloqueado por incompatibilidad;
- garantizar que A3 no convierta B UNKNOWN en certeza;
- impedir relation claims sin comparability;
- ejecutar master regression por slice;
- no tocar A1/A2 ni B5/B6 salvo bug cross-boundary probado;
- no abrir holdout final ni mergear #635.

## 8. Integrador 3 — Arquitecto 5 + Arquitecto 6

Tres verbos obligatorios: **INTEGRAR · REPARAR · AVANZAR**.

Debe:
- intake continuo B5+B6;
- reparar interfaces entre relational/asset-world evidence y qualification/provenance;
- avanzar work IDs de B5/B6 cuando exista trabajo integrable;
- reconciliar provenance total y zero-open B;
- impedir que B22/B24 se cierren antes de terminalidad real;
- ejecutar regression y deterministic replay;
- no tocar A1/A2/A3/B4 salvo bug cross-boundary demostrado.

## 9. Fronteras de archivos

Preferencias de ownership:
- A4: `shared_b_*identity*`, `*calendar*`, `*temporal*`, `*data_health*`, `*relational_graph*`.
- A5: `shared_b_*relationship*`, `*lead_lag*`, `*structural_divergence*`, `*agri*`, `*commodity*`, `*metals*`, `*energy*`.
- A6: `shared_b_*qualification*`, `*provenance*`, `*freeze*`, `*open_work_ledger*`, B-only audit/handoff.

Si un cambio necesita cruzar ownership, el integrador correspondiente coordina el cambio.

## 10. Gates finales reservados

`X-20 X-21 X-22` siguen reservados al Consejo de Integradores 1+2+3 y Owner.

Ningún Arquitecto 4/5/6 puede declarar Shared certificado.

## 11. Definition of Done

Un work ID sólo es terminal cuando:
- implementation + tests + contract = GREEN;
- evidencia real requerida existe;
- run/artifact/hash/provenance están ligados;
- no leakage;
- no authority leakage;
- blockers propios = 0;
- no depende de un gate downstream todavía abierto.

## 12. Orden operativo

1. A4 ataca B-06→B-10.
2. Integrador 2 absorbe A3+A4 continuamente.
3. A5 ataca B-11→B-15.
4. A6 avanza B-16 y B-21 en paralelo; B-22/B-24 permanecen cerrados.
5. Integrador 3 absorbe A5+A6 continuamente.
6. Cuando B4/B5 estén terminales, A6 ejecuta closure de provenance/freeze.
7. Integradores 1/2/3 convergen en master por slices pequeños.
8. Sólo después de STRICT ZERO OPEN se prepara pre-certification.
