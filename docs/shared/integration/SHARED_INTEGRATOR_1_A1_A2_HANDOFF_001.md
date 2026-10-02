# SHARED — INTEGRADOR 1 HANDOFF (ARQUITECTOS 1 + 2)

## Rol
**INTEGRAR · REPARAR · AVANZAR**

Integrador 1 no espera pasivamente. Absorbe continuamente A1/A2, corrige incompatibilidades y puede ejecutar trabajo de soporte para cerrar sus carriles.

## Inputs permitidos
- Architect 1 — WP/MC Cognitive Core.
- Architect 2 — STI.

## Inputs prohibidos
- Architect 3.
- Architect 4/5/6.
- B lane interno.

## Responsabilidades
1. Revalidar master HEAD antes de cada intake.
2. Comparar source HEAD vs master actual.
3. No admitir partial work como terminal.
4. Integrar slices pequeños y aislables.
5. Resolver conflictos de schemas, imports, tests y workflows.
6. Ejecutar regresión master y authority-isolation.
7. Reconciliar master zero-open ledger con evidencia exacta.
8. Cerrar audits donde el engine/evidencia ya existe.
9. Avanzar trabajo A1/A2 cuando haya deuda cross-cutting.
10. Mantener PR #635 DRAFT y UNMERGED.

## Handoff hacia el resto
Integrador 1 NO integra Architect 3. Debe dejar master estable para que Integrador 2 pueda rebasar su costura A3+B4 sin conflictos.

## Prohibiciones
- no final holdout;
- no certification claim;
- no production/live/VPS;
- no Risk/CIBO/sizing/execution;
- no merge final.
