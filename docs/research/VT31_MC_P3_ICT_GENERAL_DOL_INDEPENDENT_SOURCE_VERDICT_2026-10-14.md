# VT31 MC-P3 — Dictamen del origen DOL, perfil ICT GENERAL (14 octubre 2026)

## Resumen de certificación

**`MC_P3_INDEPENDENT_QORE_DOL_LINEAGE_ENGINEERING_PASS`** en el universo de pruebas diseñado; **`ICT_GENERAL_FULL_SOURCE_FIDELITY_NOT_CERTIFIED`**, **`VT31_COGNITION_NOT_CERTIFIED`**, **`VT31_TRADER_NOT_CERTIFIED`**, **`G3_PENDING_DUAL_SIGNATURE`**, **`NO_LIVE`**.

La intención científica de MC-P3 es cerrar el `UNKNOWN:ICT_EXTERNAL_DOL_PROVENANCE_UNVERIFIED` de [PR #928](https://github.com/mezas3238-hue/qore-core/pull/928), **únicamente** cuando existe fuente M1 original corroborable, completa y sin consumo. La elección QORE del DOL más próximo, MSS 1,25× y mínimo de 10 puntos son formalizaciones QORE, **NO** atribuciones universales a ICT.

## Procedencia y ejecución

- Prerregistro **anterior al código** `docs/research/VT31_MC_P3_ICT_GENERAL_INDEPENDENT_DOL_PREREG_2026-10-14.md` commit **`68f5dbd17e0da59c305c1a0b7a0a633eb0ca1f97`**.
- Implementación `scripts/vt31_mc_p3_ict_independent_dol_20261014.py`; pruebas `tests/infrastructure/test_vt31_mc_p3_ict_independent_dol_20261014.py`; CI `.github/workflows/vt31-mc-p3-ict-dol-source-v1.yml`. Rama de investigación propia sobre #928; NO toque código G3.
- **[GitHub Actions #38608745246 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38608745246)** ejecutó código commit **`b6f77c2b19311c7f3732279c6ecb2f9bdfd894ba`**, **103/103 tests PASS**, Ruff y py_compile PASS, límites blob frozen G3 PASS, comprobación ancestor prereg PASS. Incluye regresiones M0–M3, V2, COG/OPS/M1/G3.
- Artifact de CI [#11917440311](https://github.com/mezas3238-hue/qore-core/actions/runs/38608745246/artifacts/11917440311), ZIP sha256 **`dc91e7064d89a4663f08e9db0e8cab7f035ed63c10a1f512d4f2df830e3d61dc`**, con JUnit, fuente sha y scope; caduca 2027-01-12. **103 son tests, no 103 operaciones.**

## Qué se logró

Se construyó **`verify_ict_dol_from_m1`**, un atestador independiente que recibe un `CognitiveDecision` existente del COG, `as_of` externo, sesión y M1 cerradas propias. Reconstruye:
- Prior NY cash último día con 390 M1 completas de 09:30–16:00 (límite 5d).
- Asia de la fecha actual 00:00–03:00 NY (180 M1).
- Londres 03:00–05:00 NY (120 M1) sólo para sesiones NY.
- Compara el high/low real, sufijo HIGH/LOW, lado del DTO, instante de confirmación y si hubo touch posterior al cierre de la fuente. Si falta un minuto **entre confirmación y decisión**, `UNKNOWN:POST_CONFIRMATION_M1_MONITORING_GAP`, nunca presupone un pool no consumido durante cierres de mercado/fin de semana; un touch observado produce `REJECTED` incluso con otros gaps.
- Un target equivocado, fecha de fuente adulterada, lado contradictorio, input posterior a `as_of` o datos no ordenados: `REJECTED` con causa.
- **`compare_general_cog_v2_with_dol`** compone **SIN MODIFICAR** el atestador original de MSS/pivote `COG_EVIDENCE_V2` con evidencia DOL independiente. Sólo cambia el `UNKNOWN` DOL específico por un resultado `QORE_MSS_AND_DOL_SOURCE_SUPPORTED_NOT_ICT_CERTIFIED` cuando MSS/pivote/impulso pasan y DOL externo se corrobora; cualquier otro UNKNOWN permanece.

**Caso real del motor, mercado sintético:** se alimentó el propio `VT31CleanroomCognition(framework_policy=G3_MSS_FRAMEWORK_POLICY)` desde medianoche NY, con Asia high=120/low=80 causal y 6 M1 de shift final; decisiones verdaderas del código COG en **03:06 London, 10:06 NYAM, 14:06 NYPM**, para LONG/SHORT y días verano EDT/invierno EST. El atestador independiente encontró la fuente high/low, fecha de confirmación y ausencia de touch con **testigo continuo**. V2 seguía `UNKNOWN` por su diseño de no revisar DOL externo, mientras la **composición** certificó sólo coherencia de MSS+precio del pool QORE, **no** fidelidad autoral ni economía.

## Matriz adversarial SUPERADA

- Cobertura completa ventana Asia high/low y monitor posterior, 3 sesiones, dos direcciones y ambas estaciones.
- Falsificación del precio target, confirmación temporal, fuente desconocida, lado opuesto, sesión falsa.
- Toque posterior a la formación: pool no puede resucitar, `REJECTED`.
- Falta M1 dentro de 00–03: `UNKNOWN`; falta M1 tras 03: `UNKNOWN` por vigilancia incompleta, nunca relleno.
- Historial duplicado, información futura, `as_of` stale, cash anterior no disponible, Londres como DOL durante propia London: fail-closed.
- Composición V2 con cierre MSS falseado rechaza y nunca oculta un fallo por un DOL positivo.
- Flags de todo módulo `method_certified=false`, `cognition_certified=false`, `execution_authorized=false`.

## Limitaciones y prioridad siguiente

1. Estas pruebas se ejecutaron con **M1 sintéticas**, aunque `CognitiveDecision` salió de la clase verdadera del trader. No son una muestra histórica del Nasdaq ni una tasa de falsos positivos sobre mercados reales. PR #929 cubre separadamente TTrades NY AM. Hace falta aplicar atestadores a corpus real completo, medir `UNKNOWN`, `REJECTED` y coherencia por sesiones sin usar PnL para seleccionar.
2. `KNOWN_WINDOWS` comprueba los pools que QORE usa; **no prueba que sean la totalidad de pools o que el autor ICT ordene escoger el más cercano**. La selección y causalidad global de DOL deberá revisarse metodológicamente con la fuente ICT original, no ajustar cifras históricas para pasar.
3. Por diseño conservador, fines de semana/pausas con M1 ausentes devuelven `UNKNOWN`; no etiquetar falsamente como pérdida de edge. Fuente de horarios negociables necesitaría demostración aparte.
4. M4 familias FVG/OB/Breaker todavía por certificar; M5 stops y objetivo según perfil faltan. M6 dual signoffs #897 pendientes; M7 edge neto independiente no demostrado. Ninguna regla metodológica revisada se ha inyectado en G3 bajo doble firma pendiente.

**G3 SHA intactos**: DOC `a446afa17ed6e411b8f0b6fc182b103a78959a97`, CODE `78d4cdac0e09d1a6eef37b99c505ffc5098031fc`. Sin merge, producción, LIVE, VPS, sizing, órdenes, QDLE, holdout o backtest económico. **El próximo trabajo debe ser fuente real M1 y M4, no retocar la rentabilidad.**
