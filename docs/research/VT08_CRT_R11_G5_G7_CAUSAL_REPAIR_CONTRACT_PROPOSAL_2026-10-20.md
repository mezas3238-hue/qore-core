# VT08 CRT — R11: contrato de reparación causal G5/G7 (propuesta no aprobada)

Fecha: 2026-10-20. PR #626 DRAFT. Este documento NO es una certificación ni una firma independiente.

## Evidencia inspeccionada
- `crt_pure_gm1_g2_g7_causal_audit.py`: `audit_g7_rearm` requiere que **cada** historia anterior tenga `terminal_observed_at` anterior al nuevo `observed_at`. Aunque cambia el parent, el UNKNOWN anterior mantiene WAIT.
- `crt_pure_methodological_certification.py`: `evaluate_methodological_gm5` bloquea PASS auto-declarado; conservar.
- Handoff R1–R10 y forense R5/R6: 139 eventos, 108 WAIT, 31 PROVISIONAL, cinco UNKNOWN; 2 open ya más allá de invalidación, 2 huecos de viernes, 1 M5 miércoles.

## Decisión de ingeniería PROPUESTA, no implantada
1. Separar **registro global inmutable de eventos** de **alcance de dependencia causal**: `market`, `parent_id`, `source_event_id`, `hypothesis_id`, `event_generation`, `observed_at`, `decision_at`, `terminal_observed_at`, y un `lineage_id` autenticado por derivación de fuente, NO provisto arbitrariamente por el trader.
2. No habilitar nuevo source del MISMO lineage mientras el anterior esté UNKNOWN; ABSTAIN ante reutilización de parent/source/hypothesis, clocks no causales, IDs falsificados, generación no monotónica.
3. Una fuente realmente independiente de otro parent podrá recibir **solo PROVISIONAL** cuando exista prueba positiva de independencia y de inventario completo PIT. Sin evidencia: WAIT. Ningún PROVISIONAL autoriza rearm/ejecución/capital.
4. G5: cuando el open M5 ya está fuera de la barrera al reloj de decisión, propuesta de `ABSTAIN_NONVIABLE_AT_DECISION` antes de construir hipótesis ejecutable. No reescribir el outcome histórico UNKNOWN. Fin de semana: WAIT hasta calendario histórico autenticado; hueco M5 aislado: censurar o recuperar del mismo proveedor con SHA.
5. Mantener la versión GLOBAL_ALL_PRIOR_TERMINAL como control congelado; comparar exclusivamente decisiones metodológicas, **sin PnL ni selección retrospectiva**.

## Pruebas adversariales requeridas ANTES de implementar o promover
- Dos hipótesis del mismo lineage, primera UNKNOWN => WAIT.
- Parent distinto sin evidencia de independencia => WAIT.
- Parent distinto con evidencia PIT autenticada => PROVISIONAL, nunca EXECUTE.
- Misma source/hypothesis rehasheada => ABSTAIN.
- Terminal observada después del nuevo source => WAIT, sin leakage.
- Referencias con timestamp futuro, market equivocado o source sin SHA => rechazo.
- Open M5 más allá de invalidación => abstención sin fill ni cambio del ledger congelado.
- Calendario viernes NY/DST no autenticado => censura; M5 2025-02-12 22:30Z no reconstruida => censura.
- Toda evidencia con `independent_adjudicator` libre o `owner_approval_id` string => G-M5 NO EMITIDO.

## Evidencia humana y custodia pendiente
- 36 G2 reviewer-only: 16 AUDUSD, 20 USDJPY; 0 dictámenes auténticos. No exponer sealed engine labels.
- 48 G-M2 first-look sin dictamen externo. Separar ACL reales.
- Atlas original #35166210458, issue #837: backup privado con SHA y prueba restore antes de expiración 2026-12-16.
- Siete contratos G1–G7 requieren aprobación de Owner y revisión independiente autenticada; propuesta R11 no sustituye ninguna.
- Gates económicos E0–E11 permanecen abiertos. V1–V3 no son OOS virgen ni fills BID/ASK.

## Estado
G-M1…G-M4 PARTIAL; G-M5 NOT ISSUED; GLOBAL NOT CERTIFIED. NO sizing (ni ficticio/1R), NO merge, NO broker, NO demo/live/VPS. CIBO/Risk único dueño del capital y DD patrimonial.

## Siguiente implementación segura
Crear un evaluador de comparación **research-only** aislado del router productivo; pruebas unitarias de identidad/lineage, inmutabilidad, PIT y rechazo de autorización; correr CI; someter artículo G7 y G5 a revisión auténtica. No alterar V1/V2/V3 ni los 139 outcomes congelados.
