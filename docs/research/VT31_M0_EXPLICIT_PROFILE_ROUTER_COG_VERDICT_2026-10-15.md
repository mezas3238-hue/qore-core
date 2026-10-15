# VT31 — M0 Dictamen fuente/perfil REAL G3, congelado antes de sesión
**15-OCT-2026**. Owner: metodología+cognitiva, SIN PF/DD/Sharpe/Sortino/densidad/lotaje. PR #963 hijo de PR #956 source-first. No merges ni operaciones.

## CI verificable
- [GitHub Actions #38715456385 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38715456385), código ejecutado commit `ee4683b653dc3bf999e5d5a748a644c5cef373a3`, **51/51 tests PASS**, Ruff PASS.
- [Artifact #11962776871](https://github.com/mezas3238-hue/qore-core/actions/runs/38715456385/artifacts/11962776871), ZIP SHA256 `5567a46bc3a466129435282f637bfdbf6fa1e4d92a17f768f5ba0ce7ae2d0b2e`.
- [Prerregistro anterior al código](https://github.com/mezas3238-hue/qore-core/blob/e5aa05d533a46a6ecf88f3a20bbbd8b0a746fb98/docs/research/VT31_M0_EXPLICIT_SOURCE_PROFILE_ROUTER_PREREG_2026-10-15.md). G3 COG blob `d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9`, OPS `0ce9707314aecb71155de8b57044b6ec028847b2`, acta r1.3 `e99c70b4e018d626fb620d9a21b9314a51abc36d`, source-first research #956 code blob `9e3a143cfb27db61b3eec99d84a804e6cec55fcc`: **CI protege hashes**, código original no reescrito.
 
## Problema M0 resuelto EN CONTRATO DE INVESTIGACIÓN (no producción)
Nuevo componente `PreSessionMethodRouter` exige un perfil seleccionado ANTES del inicio de su ventana horaria New York con DST, no permite cambiar al observar el mercado, distingue:
- `ICT_GENERAL_2023`: 03–04 London / 10–11 NYAM / 14–15 NYPM, usa COG G3 genuino y NO afirma fidelidad plena al video ICT; DOL cash QORE no se identifica como DOL TTrades.
- `TTRADES_NY_AM_2025`: **NYAM 10–11 exclusivamente**, adapter source-first #956 reusa el MSS del COG ORIGINAL pero exige fuente H1 09 y DOL opuesto testigo #929/V2, rechaza otras sesiones.
- `QORE_G3_PROPUESTA`: mismo G3 genuino, fuente/requisitos QORE propios, NO etiqueta fuente ICT/TTrades.
- Tiempo `as_of` coincide con CIERRE última M1, entrada no futura; selector fijado antes ventana/sesión y día. Contrafactual por preferencia/pnl no admitido. No se entrega DTO research a OPS ni se emiten órdenes, fills, stops/lotaje.

**Ocho contextos sintéticos LONG/SHORT EST/EDT con COG original REAL (NO trade, no OOS):**
- 4 con target TTrades H1 09 opuesto y distancia compatible QORE G3 `>=10 pts`: `TTRADES_SOURCE_FIRST_CONTEXT_RESEARCH_ONLY` (DTO de versión research que nunca pasa a OPS).
- 4 con target autoral válido pero distancia QORE G3 `4/5 puntos`: `WAIT_TTRADES_AUTHOR_DOL_QORE_MIN10_CONFLICT`; jamás mover el target del autor o reducir G3MIN10 por rentabilidad.
- `ICT_GENERAL` y `QORE_G3` no se contaminan con claim de DOL H1 TTrades. TTrades NYPM/London, selector tardío y barras fuera asof rechazan.

**Calificación:** `M0_PROFILE_ROUTER_RESEARCH_ENGINEERING_PASS`, una mejora material del contrato cognitivo de un solo VT31. `M0_TRADER_RUNTIME_INTEGRATION_CERTIFIED=FALSE`: falta integrar con el runtime canónico ya firmado, probar sin producir trades bajo fuente, resolver M3/4/5 y M6.

## Bloqueos que impiden CERTIFICADO_METODOLOGÍA y CERTIFICADO_COGNITIVA hoy
- Fuente TTrades AM no obliga `body>=1.25×median5` del QORE G3, ni siempre 10 pts mínimo. Estas reglas deben estar rotuladas QORE o ratificadas como propia metodología, no autoría falsa.
- M4 OB/CISD/Breaker: [PR #960](https://github.com/mezas3238-hue/qore-core/pull/960) contiene nuevas fuentes primarias TTrades que sí describen pivote3 swing corto, CISD, OB 50% body, breaker 4-leg; code QA 80/80 sobre M1, pero falta serie/zona/retest/desplazamiento fully source-attested e integración.
- M5 stop detrás swing que CAUSÓ displacement, no escoger cualquier pivot. [PR #959](https://github.com/mezas3238-hue/qore-core/pull/959) evidencia ambigüedades en 483 casos. Sigue sin witness causal autoral válido/stop.
- M6 [issue #897](https://github.com/mezas3238-hue/qore-core/issues/897) exige dos revisores técnicos humanos independientes COG+OPS sobre código/acta exactos. Se verificó 0 reviews del [PR #896](https://github.com/mezas3238-hue/qore-core/pull/896). **No firmar por el Owner+agentes mismos login.**

**Conclusión factual:** identidad metodológica del módulo research resuelta técnicamente con pruebas, **NO CERTIFICADOS GLOBALES**, NO MERGE/DEMO/LIVE/VPS/FundedNext/sizing VT31.
