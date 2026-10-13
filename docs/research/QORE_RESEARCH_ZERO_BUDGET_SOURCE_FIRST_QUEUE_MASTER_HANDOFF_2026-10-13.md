# QORE Research — Handoff maestro: cola científica con presupuesto cero

**13 de octubre de 2026. Estado: implementación y GitHub Actions SUCCESS. Presupuesto autorizado de datos: USD 0. Sin merge ni LIVE.**

## Identidad y ejecución autoritativa

- PR: https://github.com/mezas3238-hue/qore-core/pull/916 (DRAFT, hija de PR #915 → #914 → #913 → #895).
- Rama: research/qore-cf11-source-first-mission-queue-20261013.
- GitHub Actions: https://github.com/mezas3238-hue/qore-core/actions/runs/38459093369 — SUCCESS en commit df6111bca5e03f4cecd19aa172c7f42513bd5487. **Ruff PASS, Mypy PASS, 19/19 tests PASS**. Descargó evidencia EIA de run original #38448311219, volvió a validar commit, checksum, ascendencia del preregistro, reconstruyó el plan auténtico CF-11 en el mismo runner y construyó el ledger.
- Ledger resultante: https://github.com/mezas3238-hue/qore-core/actions/runs/38459093369/artifacts/11844264129 — artifact ZIP SHA256 ceae5132364ecbb486bb1ef9899357213cd9f7da26c06294e7694322d5653e63 (retención 90 días). Huella JSON canónica 4652885158b3cc6febe04f42009b754199506702f5c0eceedbd3fce0fd01dcae.

## Estados realmente emitidos

| Misión | Estado | Siguiente acción permitida |
|---|---|---|
| research.eia.futures-a-f1f2-closure | CLOSED_NO_SUPPORT | STOP_AND_ARCHIVE |
| research.futures-a.native-6roots-d1 | SOURCE_BLOCKED | ACQUIRE_VALID_SOURCE_WITHIN_ZERO_BUDGET |
| Propuestas genuinamente nuevas | PROPOSAL_ONLY, cero entradas actuales | WRITE_NEW_PREREG, **nunca ejecución automática** |

Estos son **estados de investigación**; ninguno prueba ausencia general de edge ni genera órdenes, retornos operables o un trader certificado. El experimento EIA específico WTI/NG (backwardation → aumento posterior de referencia F1) falló DEV y DIAG preregistrados. La reserva 2022–abril 2024 no fue evaluada y el holdout independiente FX también quedó intacto.

Futures A con seis raíces CME CL NG GC HG ZC ZS, dos vencimientos nativos simultáneos y OHLCV D1 2012–septiembre 2024, todavía necesita fuente legal completa. Los 12.352 precios de referencia EIA WTI/NG diarios ya adquiridos **no son** velas negociables ni históricos por contrato de entrega. Budget USD0.

## Código y límites

- src/qore/infrastructure/trader_lab/qore_research_zero_budget_intake_v1.py: estructura inmutable, tres estados, huella SHA de JSON canónico, controles contra falsa disponibilidad, presupuesto distinto de cero, traders certificados, apertura de holdout y reapertura de hipótesis descartadas.
- tests/infrastructure/trader_lab/test_qore_research_zero_budget_intake_v1.py: 19 tests sintéticos y adversariales; rechazo de source data ficticia, promociones falsas, duplicaciones, presupuestos, cambio de decisiones y parentesco de evidencias.
- .github/scripts/qore_research_zero_budget_queue_v1.py: genera el ledger solo después de consumir un plan CF11 ya autenticado en el mismo job. Propuestas restringidas a identificador, pregunta, requisito de datos y número de raíces (sin resultados ni supuestos retornos).
- docs/research/QORE_RESEARCH_ZERO_BUDGET_PROPOSALS_2026-10-13.json: vacío deliberadamente; no hay nuevas hipótesis preregistradas por arte de magia. Permite propuestas nuevas como intenciones **no congeladas**, hasta 20 por llamada.
- .github/workflows/qore-cf11-source-first-research-intake.yml: GitHub Actions por push / invocación manual, permisos contents:read y actions:read, no triggers de trading; autentica original, reconstruye CF-11, impone tests, genera artifact de metadatos.

## Aclaración de autoridad esencial

Esta funcionalidad **NO** convierte QORE Research en un agente siempre activo. Se ejecuta al dispararse el workflow. No ejecuta experimentos, monitoriza mercados ni compra datos. Es un **intake** gobernado por GitHub y un ledger auditado.

El CF-11 consumido es una instancia real de CiboResearchPlan con estado EXPERIMENT y evidencia INSUFFICIENT, no una fabricación de aprobación Risk, Market Intelligence, OOS, Trader Lab o DEMO. Trader Lab permanece DRAFT, sin certificados.

### Problemas pendientes y orden sugerido

1. **P0 — prerregistro y autoridad externa:** un futuro servicio de orquestación necesitará aprobación legítima, fuente autenticada/licenciada, as-of, familias de hipótesis y calendario inmutable. La idea PROPOSAL_ONLY no puede ejecutar estudio hasta preregistro Git previo y autorización científica. No pasar de código a servicio permanente sin orden.
2. **P0 — datos negociables a cero dólares:** falta cobertura completa nativa CME 6×2 para 2012–2024, costes, vencimientos y registros as-of. Sin ellos la misión económica continúa SOURCE_BLOCKED. No simular gastos ni fills.
3. **P1 — custodia:** GitHub artifacts caducan. Preservar actas y referencias criptográficas legales en GitHub, sin distribuir precios de terceros, ni reabrir holdout por vencimiento de evidencia.
4. **P1 — nuevas propuestas:** mecanismo realmente independiente y preregistrado antes de mirar resultados; no ajustar dirección, horizontes o filtros del resultado EIA ya refutado bajo sus condiciones. Continuar solo con ideas científicas nuevas justificadas.
5. **P1 — certificación:** ningún estado de esta cola sustituye los Gates de Replay, Fast Forward, OOS, Stress, Monte Carlo, Risk, CIBO e independiente. La certificación sigue 0.

**Restricciones:** no merge, no cTrader/MT5/VPS, no LIVE ni capital real, nada de sizing/leverage en Traders. Datos US$0 y EIA holdout sellado.

**Conclusión:** cola SOURCE-FIRST real y verificada; utilidad actual es saber qué detener, qué está bloqueado por fuente y cómo ingresar una propuesta sin contaminarse con resultados. No inventar ejecución económica.


---

## Addendum de CI final: propuestas futuras sin romper el gate (13-OCT-2026)

Se corrigió una restricción excesiva del workflow: la aserción previa exigía 0 propuestas siempre, lo que impedía aceptar propuestas nuevas aunque fueran legítimamente `PROPOSAL_ONLY`. Ahora el workflow permite **hasta 20 propuestas**, siempre que todas sean no ejecutables, los dos registros autoritativos mantengan `CLOSED_NO_SUPPORT` y `SOURCE_BLOCKED`, ningún resultado científico/económico se fabrique, el budget permanezca USD0 y ningún holdout se abra. El manifiesto actual sigue **vacío**.

**Verificación posterior a la corrección:** [GitHub Actions #38459547103 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38459547103) con HEAD de código `ca3a69845ded438a980d9473e9b40af86345391f`. **Ruff PASS, Mypy PASS, 19/19 tests PASS**, ciencia CF-11 y procedencia EIA autenticadas. Artifact nuevo [#11844922650](https://github.com/mezas3238-hue/qore-core/actions/runs/38459547103/artifacts/11844922650), SHA256 ZIP `796f8bcde2c596687c3921e368ccc60a3a27106f2335f61d99cf005da7cc02b4`. Mantener ambos runs documentados para auditar evolución (el previo #38459093369 también fue SUCCESS).
