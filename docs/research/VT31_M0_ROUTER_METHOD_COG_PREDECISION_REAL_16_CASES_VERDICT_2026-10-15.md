# VT31 — Dictamen M0: identidad de método antes de M1, original G3 sin modificar

**15-OCT-2026.** Continuidad R4: se atacó bloqueo M0 real de certificación METODOLOGÍA+COGNITIVA, no PF/DD/Sharpe. Fuente TTrades primaria [AM Silver Bullet on NQ](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/) prescribe 10–11 NY, primera barrida H1 09, vuelta y objetivo lado opuesto H1. La política QORE MIN10 es distinta de la fuente del autor. ICT GENERAL London/NYPM permanece sin homologación autoral completa.

## Ronda verificada
- [PR #971 DRAFT](https://github.com/mezas3238-hue/qore-core/pull/971), rama `agent/vt31-m0-predecision-profile-router-20261015`, prereg ANTES del código `05e55b7528636ea60168d69a97b03559fae2f0dd`.
- [CI #38762670233 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38762670233), **78/78 pytest PASS**, Ruff PASS, `pytest-xdist -n4`; commit exacto de código/test `52133f4b82bbc22119d82e05cea99dfe64a47bb3`, hashes G3 original COG/OPS/acta inmutables PASS.
- [Artifact #11987016022](https://github.com/mezas3238-hue/qore-core/actions/runs/38762670233/artifacts/11987016022), ZIP SHA256 `692798ab1efcef5dbb67feacbeeb42a1f622a272fec98708837ddd6dca11fdba`, evidencia `VT31_M0_PREDECISION_METHOD_PROFILE_COG_16_CASES.json`, tests JUnit, SHA256SUMS, resumen.
- Intento anterior falló solo Ruff I001/F401 test import, corregido sin modificar ninguna premisa de método.

## Decisiones causales de 16 casos
| Perfil declarado ANTES del primer M1 | Long/Short EST+EDT | Estado real read-only |
|---|---:|---|
| NY AM TTrades 09h H1, método fuente compatible con G3 MIN10 | 4 | `RESEARCH_TTRADES_CONTEXT_CONFORMANT_NOT_CERTIFIED` (DTO research independiente, no productor G3 integrado) |
| NY AM TTrades 09h H1, DOL autoral validado pero infringe el contrato QORE MIN10 | 4 | `G3_MIN10_AND_TTRADES_SOURCE_TARGET_CONFLICT_WAIT` (sin DTO) |
| London + NY PM bajo ICT_GENERAL, COG original observado LONG/SHORT | 8 | `ICT_CONTEXT_WITNESS_UNDERDETERMINED`, no declarar autor ICT verificado |

**La fuente está seleccionada antes de ingresar M1**, en `FrozenMethodProfilePolicy` inmutable, hora efectiva 2025-12-01; el módulo comprueba su matriz de sesión/perfil, perfil reconocido, timestamps causalmente previos, as-of igual a último M1 cerrado, no data de futuro ni sesión mal asignada. El mismo original G3 COG sigue inalterado. La elección `NY AM=TTrades` es **propuesta de investigación preseleccionada, NO decisión firmada por el Owner ni integración del trader productivo**.

## Estado que NO se puede falsear
**M0 parcialmente demostrado en investigación**, no `M0_NATIVE_GOVERNED_CERTIFIED`. Falta política firmada del perfil de producción y nueva versión COG/OPS realmente conectada + revisores humanos separados. Continúan M3 MSS fuente, M4 OB/Breaker/familias, M5 swing que causó desplazamiento, Issue #897 dos firmas humanas. No se usaron 3Y NAS100, BID/ASK, PnL, PF/DD, fills, OMS, sizing ni LIVE. Una CI verde **no** es certificado metodológico o cognitivo completo.

Referencias continuidad: [PR #969 tribunal 10 artifacts](https://github.com/mezas3238-hue/qore-core/pull/969), [Issue #957](https://github.com/mezas3238-hue/qore-core/issues/957), [Handoff R4](https://github.com/mezas3238-hue/qore-core/blob/73d170337ff6cc0a30c85f9f58979e7b307650df/docs/research/VT31_HANDOFF_R4_TRADERLAB_32X_10_EVIDENCIAS_CERT_METODO_COG_2026-10-15.md). Próximo arquitecto debe usar 16 casos y evitar volver a evaluar perfil en función del resultado.