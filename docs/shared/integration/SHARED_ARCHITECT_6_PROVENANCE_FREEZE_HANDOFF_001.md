# SHARED — ARQUITECTO 6 · ACTIVE PERCEPTION, PROVENANCE & FREEZE

**Ownership exclusivo:** `B-16 B-21 B-22 B-24`  
**Integrador asignado:** Integrador 3

## B-16 Active Perception
Estado inicial:
- 177 sensores frozen;
- 0 admissions;
- 90 con identity evidence para siguiente paso;
- 2 con full real BID/ASK history;
- 1 partial;
- 174 sin bound real causal history.

Objetivo: qualification científica read-only. No admisión por cobertura aparente ni por nombre.

## B-21 Total Provenance
Mantener manifest exacto run↔artifact↔branch↔SHA↔digest para todos los workstreams obligatorios.
Debe consumir evidencia de B4/B5 sin reescribirla.

## B-22 WORLD_PERCEPTION_FREEZE
Downstream gate.
No emitir freeze mientras cualquier B obligatorio esté OPEN/PARTIAL/BLOCKED sin terminal disposition válida.

## B-24 Final B Handoff
Preparar paquete final para integración:
- exact B ledger;
- provenance complete;
- deterministic replay;
- explicit UNKNOWN/blindspots;
- authority-free outputs;
- no holdout final abierto.

## Uso de B-23
B-23 está COMPLETE_AND_PROVEN y sólo se usa como auditor final. No reabrir.

## No tocar
B-06..B-15 internals. Si encuentra inconsistencia, abrir disposition para Integrador 2/3 según ownership.
