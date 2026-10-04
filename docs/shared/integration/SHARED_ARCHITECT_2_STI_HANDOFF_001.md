# SHARED — ARQUITECTO 2 · META-LEARNING, CONTINUAL LEARNING & KNOWLEDGE GOVERNANCE

**Owner:** Sergio Meza  
**Repo:** `mezas3238-hue/qore-core`  
**Rama asignada:** `agent/shared-architect-2-sti-001`  
**Integrador:** Integrador 1  
**Fuente detallada:** `docs/shared/handoffs/QORE_SHARED_ARCHITECT_A_SPLIT_A1_A2_A3_MASTER_HANDOFF_001.md`

## Gobierno absoluto

- GitHub es la fuente de verdad.
- PR #635 permanece OPEN / DRAFT / UNMERGED.
- NO merge sin orden explícita del Owner.
- NO LIVE / producción / capital real / Funded / VPS.
- NO broker mutation ni creación/modificación/cierre de órdenes o posiciones.
- Shared no tiene sizing, Risk, CIBO ni Execution authority.
- NO abrir el holdout final protegido de Shared.
- NO outcome-aware tuning ni rescate de gates después de observar resultados.
- UNKNOWN / INSUFFICIENT / FALSIFIED son disposiciones válidas cuando la evidencia lo exige.
- CI GREEN no equivale automáticamente a cierre científico.
- Cada actor debe revalidar HEADs, runs, artifacts y blockers antes de trabajar.


## Misión

Cerrar el ciclo adaptation → regression → stress → governed knowledge. No invadir causal/trajectory de A1, cross-system de A3 ni B.

## Ownership exclusivo

1. **MC11 Neural-Symbolic completion**
   - Revalidar binding existente.
   - Cerrar sólo gaps reales de freshness / independent validation.
   - No usar población solapada como fresh.
   - Preservar symbolic constraints, causal traceability y uncertainty.

2. **MC23 validated real novel-regime adaptation**
   - Run `36782458472` prueba real novelty detection, no adaptación completa.
   - Seleccionar NOVEL/NEAR_KNOWN prospectivamente.
   - Hipótesis de adaptación sin fingir que el régimen ya es conocido.
   - Validación independiente.
   - No silent rewrite de conocimiento certificado.

3. **MC24 continual learning closure**
   - Run `36781874072` prueba regression infrastructure.
   - Bind de adaptación MC23 validada.
   - Medir empirical knowledge half-life.
   - Probar non-degradation del conocimiento retenido.

4. **MC25 same-lineage performance stress**
   - Lineage-integrity stress run `36783028642` ya GREEN.
   - Ejecutar exactamente un performance-stress gobernado.
   - Mantener 6 escenarios congelados y gate incremental de 100 bps.
   - Si PASS: formal STRESS → same-lineage SHADOW → CERTIFICATION → governed PROMOTION.
   - Cualquier FAIL terminaliza esa configuración; no rescatar gates.

5. **WP11 exact closure**
   - Reconciliar de forma monótona los blockers:
     `MC23_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION`,
     `MC24_BIND_REAL_MC23_ADAPTATION`,
     `MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE`,
     `MC25_SAME_LINEAGE_PERFORMANCE_STRESS`,
     `MC25_FORMAL_STRESS_STAGE`,
     `MC25_SAME_LINEAGE_SHADOW`,
     `MC25_CERTIFICATION`,
     `MC25_GOVERNED_PROMOTION`.
   - Refresh sólo desde sealed evidence.

## No tocar

- A1 scientific implementation.
- A3 MC27/MC28/global coverage.
- B producer surfaces.
- Integrator/master zero-open ledger.
- Owner directives.

## Definition of Done

MC11 y la cadena MC23→MC24→MC25→WP11 deben quedar sin paso local sin ejecutar. Lo restante sólo puede ser external/future evidence con dependencia explícita.

## Entrega a Integrador 1

Manifest exacto de commits/runs/artifacts/dispositions/blockers; cero “finished” prose-only.
