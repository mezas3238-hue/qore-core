# SHARED — INTEGRADOR 2 · ARQUITECTO 3 + ARQUITECTO 4

## Misión
**INTEGRAR · REPARAR · AVANZAR**

Pair:
- Arquitecto 3: A transversal / MC-28 + X seam.
- Arquitecto 4: B-06..B-10 World Foundation.

## Intake A3
`MC-28 X-01 X-02 X-03 X-05 X-06 X-07 X-08 X-09 X-10 X-12 X-14 X-15 X-16`

## Intake B4
`B-06 B-07 B-08 B-09 B-10`

## Responsabilidades
- revalidar master HEAD antes de cada slice;
- integrar sólo evidencia coherente;
- reparar incompatibilidades A3↔B4;
- avanzar seam work cuando el bloqueo sea de integración;
- ejecutar regression master;
- preservar UNKNOWN/ABSTAIN;
- exigir temporal comparability antes de relation claims;
- mantener timestamps <= decision time;
- impedir hidden trade filters y trader methodology leakage.

## No invasión
No tocar A1/A2 ni B5/B6 salvo bug de interfaz probado y documentado.

## Prohibido
No merge #635, no holdout final, no LIVE/VPS, no sizing/Risk/CIBO/Execution authority.
