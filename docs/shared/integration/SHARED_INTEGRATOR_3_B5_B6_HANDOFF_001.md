# SHARED — INTEGRADOR 3 · ARQUITECTO 5 + ARQUITECTO 6

## Misión
**INTEGRAR · REPARAR · AVANZAR**

Pair:
- Arquitecto 5: `B-11 B-12 B-13 B-14 B-15`
- Arquitecto 6: `B-16 B-21 B-22 B-24`

## Responsabilidades
- intake continuo B5/B6;
- reparar schemas, provenance, tests, workflows y replay;
- ayudar a cerrar work IDs cuando exista evidencia suficiente;
- impedir que B6 cierre B22/B24 antes de terminalidad de B4/B5;
- reconciliar B ledger y provenance total;
- ejecutar B-only regression y master regression de cada slice;
- mantener B-14 blindspot honesto si no hay provider;
- no convertir commodity reference objects en futures por inferencia;
- no convertir architecture-only B11..B13 en empirical closure.

## Coordinación con Integrador 2
Integrator 3 consume los outputs terminales de B4 desde master; no reimplementa B-06..B-10.
Si B5/B6 depende de una interface B4, el bug se documenta y se entrega a Integrador 2.

## Finalización
Cuando B5+B6 estén terminales y B4 ya esté integrado:
1. B21 coverage_complete;
2. B-only zero-open audit;
3. B22 WORLD_PERCEPTION_FREEZE;
4. B24 final handoff;
5. entrega al Consejo de Integradores.

No final Shared holdout ni merge sin Owner.
