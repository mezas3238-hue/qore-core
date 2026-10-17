# VT08 B R16 — Exclusión categórica QORE-alpha por decisión del Owner y auditoría source-only

**Corte:** 15-oct-2026. **Owner:** «Qore alpha quedó excluido del programa por ende no puede mezclarse con el vt08 actual». **Interpretación vinculante:** cero vías VT08-alpha, cero trasvase de reglas/cognitiva/señales/estadísticas desde QORE-alpha, cero «experimentos de salvamento» alfa. **Única familia:** VT08 metodología TTrades+cognitiva VT08; completar gates económicos cuando haya auténtica fuente A/B y BID/ASK ejecutable, siempre sin sizing.

**[Contrato Owner de exclusión](VT08_OWNER_SCOPE_CURRENT_ONLY_NO_QORE_ALPHA_2026-10-15.md)** existe en **AMBAS ramas** PR A #765 y PR B #764. El [informe previo R15](VT08_B_R15_DEEPSEEK_V2_FIDELIDAD_AUTOR_EQ_POI_CORRECCIONES_SOURCE_2026-10-15.md) fue corregido en commit `f95abf3086ffb4b5508ea605a015a88aaa2a6da0` para eliminar explícitamente la propuesta errónea de dos tracks. Esta decisión supera recomendaciones anteriores de otros auditores, incluida DeepSeek V2.

## Gate R16 verificable

[**GitHub Actions #38805194446**](https://github.com/mezas3238-hue/qore-core/actions/runs/38805194446): **5/5 SUCCESS, Ruff y 34 pruebas adversariales por mercado = 170 pruebas**, originales A R3 fijados por run #38715560333, **2.657/2.657** casos fuente del único universo VT08, sin lectura de futuro, sin sizing, sin 7Y, sin órdenes/merge.

- Validador nuevo: `src/qore/infrastructure/trader_lab/vt08_b_r16_owner_scope_no_alpha_v1.py`.
- Tests adversariales: `tests/infrastructure/trader_lab/test_vt08_b_r16_owner_scope_no_alpha_v1.py`.
- Workflow: `.github/workflows/vt08-b-r16-owner-scope-no-alpha.yml`.
- Dos funciones: `assert_single_vt08_current_manifest()` rechaza identidades alternativas, `fallback_strategy`, `parallel_track`, `foreign_signal_origin`, `QORE-alpha` con variantes case/underscore/guion, importación cognitiva/estratégica externa, falsa certificación, órdenes y sizing; `audit_frozen_source_program_scope()` audita todas las identidades originales del censo R3, autor falsamente verificado y denominador alterado. **Es un firewall de gobernanza de source-only**, no una garantía de que todas las rutas de producción ajenas ya invoquen el validador: integración futura en entradas de manifest/candidate en la cadena correspondiente debe permanecer P0 antes de certificar.

| Mercado | Casos VT08-only confirmados | Alfa/otra vía autorizada | Fills |
|---|---:|---:|---:|
| EURJPY | 538 | 0 | 0 |
| USDCHF | 518 | 0 | 0 |
| NZDUSD | 550 | 0 | 0 |
| CADJPY | 516 | 0 | 0 |
| USDCAD | 535 | 0 | 0 |
| **TOTAL** | **2.657** | **0** | **0** |

**Ruta A, metodología:** solo reglas genuinas TTrades confirmadas con source URL/fragmento, contexto swing/protected swing/POI/EQ/breaker/stop/target. Si falta autoridad o desempate, `D_PENDING_SOURCE_AUTHORITY` y WAIT; **no crear un método QORE-alpha ni un track derivado en VT08**.

**Ruta B, cognitiva:** revisar 27 `CAUSAL_FIELDS`, causa/tiempo/receipts originales y signoff genuino. Rechazar cualquier procedencia de estrategia QORE-alpha, aunque herramientas genéricas Trader Lab/QORE Research puedan ser usadas para ejecutar pruebas de VT08 sin alterar método.

**Gates económicos:** PF/DD/Sharpe/Sortino = NO_EVALUABLE mientras no existan operaciones fuente completas y broker BID/ASK auténtico, sin sizing. Holdout 7Y sellado. No órdenes VPS/LIVE/DEMO ni merge.

**Vinculación de handoff:** este informe y el contrato Owner deben anexarse al handoff de arquitecto A y B y comunicarse en #762/#763; no permitir que recomendaciones archivadas rehabiliten QORE-alpha.

**Estado:** `VT08_OWNER_SCOPE_EXCLUSION_ENFORCED_IN_R16_SOURCE_GATE` / `VT08_NO_CERTIFICADO`.
