# VT08 CRT — R10: validación fail-closed de 36 respuestas humanas G2 sobre datos reales

**18 OCT 2026.** CI y pruebas reales verificadas, NO metodología aprobada, NO trader certificado, NO autorización económica. Tri-fuente Owner RomeoTPT + SpeculatorFL + TraderFlameseN; umbrales QORE propuestos son hipótesis, no instrucciones textuales atribuibles a autores. V1/V2/V3, G-M4, 139 eventos, 5 UNKNOWN, 108 G7 WAIT congelados. Está prohibido sizing de VT08 de toda clase; CIBO/QORE Risk soberano para capital y drawdown. Ningún merge/demo/live/orden/VPS.

## Reproducción verificada

[**GitHub Actions #39096884947**](https://github.com/mezas3238-hue/qore-core/actions/runs/39096884947), código exacto `506e1be614e94aa83343dafe5c9a85b523edbc91`, **3/3 jobs SUCCESS**: Ruff PASS, mypy PASS 6 módulos, **77 tests PASS**, AUDUSD/USDJPY original Atlas de 296.372 M5 con checksum original y 36 G2 R9 review packs comparados. [Pre-registro R10](VT08_CRT_R10_G2_36_INDEPENDENT_RESPONSE_GM1_ATTESTATION_PREREG_2026-10-18.md), commit anterior `de7bb5cc0808c0d0ce76561167f93f564db542e2`; no se estudiaron outputs antes de fijar contrato.

Nuevo módulo `src/qore/infrastructure/trader_lab/vt08_crt_g2_human_response_guard.py`; pruebas `tests/infrastructure/trader_lab/test_vt08_crt_g2_human_response_guard.py`. Integrado en `vt08_crt_g2_g7_real_atlas_pit_bridge.py`, workflow dedicado `.github/workflows/vt08-crt-g2-g7-real-atlas-pit-audit.yml`; emite separado en el artifact REVIEWER ONLY `g2-independent-human-response-readiness-R10.json`, firmado por SHA/commit GitHub. No consulta `g2-sealed-engine-labels.jsonl` ni C3 outcomes.

### Resultado real, sin simulación de firma

| Mercado | G2 ciego original R9 | Respuestas reales con justificación | **Sin responder** | Dictámenes independientes GitHub |
|---|---:|---:|---:|---:|
| AUDUSD | 16 | 0 | **16** | 0 |
| USDJPY | 20 | 0 | **20** | 0 |
| **TOTAL** | **36** | **0** | **36** | **0** |

En ambos mercados `blocker_counts={"UNANSWERED_BLIND_CASE":n}`, `structurally_complete_NOT_APPROVED=false`, `independent_GitHub_identity_authenticated=false`, `owner_approval_authenticated=false`, `G_M1_PASS=false`, `G_M2_PASS=false`, `G_M5_ISSUED=false`, `GLOBAL_CERTIFIED=false`. El output no convierte estas 36 anotaciones en entradas de trading.

## Seguridad y adversariales

R10 rechaza: alteración SHA del payload R9, duplicación de case IDs, permutación o sustitución de respuestas, respuestas para otro mercado, modificación de velas, campos de aprobación falsa (`methodology_gate_passed=true` o identidades GitHub false→true), inyección de resultado económico como campo extra, elección fuera de C0/C1/BOTH_AMBIGUOUS/NEITHER_VALID/INSUFFICIENT_SOURCE. Exige fuente/etiqueta explícita (RomeoTPT, SpeculatorFL, TraderFlameseN, `QORE_ENGINEERING:` o `SOURCE_GAP:`), explicación causal y contraejemplo para que **un envío** pueda considerarse **estructuralmente completo**, no verdadero ni fuente-validado.

Se probaron también respuestas sintéticas 16/16 completas: el validador marca `structurally_complete_NOT_APPROVED=true` solo para esas fixtures, pero devuelve **G-M1 PASS=false, G-M2 PASS=false, G-M5=false, GLOBAL=false** y cero autoridad GitHub incluso entonces. Una respuesta QORE_ENGINEERING es una propuesta, no un texto de autor. `SOURCE_GAP:` con `INSUFFICIENT_SOURCE` deja la insuficiencia registrada, no cuenta como evidencia válida de prioridad.

**Reutilizar y NO sustituir:** `src/qore/infrastructure/traders/crt_pure_gm1_external_review.py`, validador R1 ya existente, obtiene PR, reviews nativas, comentarios Owner, historia de commits, sha dossier y trusted identities DESDE ambiente protegido; PR #626 todavía **0 reviews** en la inspección de esta ronda. El test R10 solo comprueba estructura y SHA de caso, **NO autentica personas**; sí verifica que campos editables no puedan fingir autenticación. Cualquier futura integración con aprobación real exige entorno protegido aislado, reviewer genuinamente independiente, 7 artículos adjudicados individualmente y mismo HEAD SHA sin cambio posterior. Un GitHub `APPROVED` solo puede ser un testigo externo, no una certificación autoemitida.

## Artefactos SHA y continuidad

[Run #39096884947](https://github.com/mezas3238-hue/qore-core/actions/runs/39096884947); caducidad 2027-01-16T04:22:50Z:

- **REVIEWER ONLY AUDUSD** artifact [#12125231326](https://github.com/mezas3238-hue/qore-core/actions/runs/39096884947/artifacts/12125231326), ZIP SHA256 `c3bef18cc39479ec87f18fc03facd3aa317b013d7078c23f6500c5b627ccdc31`.
- **REVIEWER ONLY USDJPY** [#12124797767](https://github.com/mezas3238-hue/qore-core/actions/runs/39096884947/artifacts/12124797767), ZIP SHA256 `583bdd6c11e94cd167535421ca5c537bd7c64b550c591c094d12ab249e5f4948`.
- **ENGINE SEALED — NO MOSTRAR AL REVISOR** AUDUSD artifact #12125385879 SHA256 `2eff128154e9e4032849fb0397acb63028d18021120dbbfef57b8a0c9c0071cb`; USDJPY #12125101905 SHA256 `e409e97688f33f8617e129dd19ceda8cbcd019ec901ee6883c8aff5d0b8caa83`.
- Full G2/G7+GM4 original audit AUDUSD #12125261288 SHA256 `26dd08b088e4d5b0e8df2c2aebcff4cb18a35af0c431950824b82afdace59a32`; USDJPY #12124972228 SHA256 `b861a08fd3462d94053f5cfd7456154cb59952984eeadf6aa25a07328fa2c799`. Full audit expone ENGINE labels y **NO es reviewer-only**.

**Atención seguridad:** los ZIP SEALED y reviewer-only comparten ACL del repositorio GitHub. La separación de artifacts NO garantiza cegamiento humano si el evaluador tiene acceso a ambos. Registrar control de custodia y prueba de no exposición; no reclamar "blind independent" solo por los nombres del ZIP.

## Qué falta para avanzar realmente a G-M1 y G-M5

1. **G2:** un auditor externo genuinamente independiente debe completar los 36 R9 casos con decisiones, explicación causal y fuentes; el Owner debe firmar los artículos G1–G7 con versión/hash. G2 sigue WAIT en los 139 V3 por inventario old-CRTH/CRTL incompleto, los 36 son solo conflictos observables C0/C1.
2. **G7:** Owner y auditor deben decidir política `GLOBAL_ALL_PRIOR_TERMINAL` vs `LINEAGE_SCOPED_CAUSAL_REARM` propuesta (NO AUTORIZADA) por validez causal tri-fuente, nunca elegir por PnL/densidad. Hasta entonces, 5 UNKNOWN de GM4 bloquean 108 G7 WAIT.
3. **G-M2:** 48 casos first-look necesitan adjudicación independiente sin filtración del futuro; G-M3 verdad externa y GM4 integración con CIBO Risk. Ni más unit tests ni un sistema de labels pueden sustituir estas pruebas.
4. **Global:** OOS verdaderamente virgen, costes reales BID/ASK, edge neto, PF/Sharpe/Sortino, WFO/MC y DD patrimonial (CIBO Risk exclusivo). V3 desarrollo tuvo trayectoria adversa y no hay prueba de rentabilidad. No inventar capital, sizing, ni 1R ficticio.
5. **Custodia:** Atlas original AUDUSD/USDJPY SHA-backed expira 2026-12-16, issue #837. No confundir artifacts temporales R10 con custodia permanente.

**Dictamen final:** G-M1..G-M4 PARTIAL, G-M5 NOT ISSUED, GLOBAL NOT CERTIFIED. PR #626 DRAFT, 0 reviews aprobatorios reales, no merge ni órdenes/DEMO/LIVE/VPS; VT08 sigue estrictamente sin sizing.
