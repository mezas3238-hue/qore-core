# QORE Research — Continuidad: prerregistro Git y control SOURCE_FIRST a presupuesto cero

**Checkpoint:** 13-OCT-2026. Repositorio soberano: mezas3238-hue/qore-core. NO MERGE sin orden. NO LIVE, no nuevos trades, no coste de mercado. 

## Dónde continuar

- PR #917 (DRAFT): https://github.com/mezas3238-hue/qore-core/pull/917 ; rama research/qore-cf11-prereg-source-gate-20261013. Es hija de #916 (cola CF11, también DRAFT), que a su vez desciende de #915, #914, #913 y #895.
- GitHub Actions #38469794973 SUCCESS (HEAD cdfe340d3b035a0713b409eb6c13f5348d65eaa3): https://github.com/mezas3238-hue/qore-core/actions/runs/38469794973 . **19/19 pruebas sintéticas/adversariales PASS**, Ruff PASS, Mypy PASS, snapshot de manifests idénticos a HEAD Git.
- Artifact #11851476889: https://github.com/mezas3238-hue/qore-core/actions/runs/38469794973/artifacts/11851476889 ; digest SHA256 ZIP bc101f9d3285f81f23c6bb2d6e8e14e4c5a73b6887fa56065b7816b34e84a5a5 (retención 90 días). Recibo SHA del contenido: d0c8baf15425a35af6da28f7d90662d7747007052b34f24e2c767f9c7f605a03.

## Trabajo nuevo realmente construido

- src/qore/infrastructure/trader_lab/qore_research_prereg_source_gate_v1.py: contrato puro para que un nuevo identificador PROPUESTA registrada en #916 tenga un prereg científico completo. Cierra campos exactos de hipótesis, familia, definición textual de señal y outcome, lag, horizonte, muestra, roll, publicación as-of, costes, precios negativos, derechos de fuente, método, corrección familiar, efecto mínimo y DEV/DIAG/HOLDOUT no solapados.
- tests/infrastructure/trader_lab/test_qore_research_prereg_source_gate_v1.py: 19 tests con inputs totalmente sintéticos, incluso hipótesis histórica EIA quemada omitida fraudulentamente de previous_tests. Rechaza campos Sharpe ajenos, estados false source-ready, coste >US$0, préstamos de permisos, ventanas superpuestas, claves duplicadas y prereg ausente para una idea existente.
- .github/scripts/qore_research_prereg_snapshot_v1.py: valida las DOS fuentes declarativas contra los **bytes reales de git show HEAD:path**, rechaza worktree sucio y registra commit SHA exacto. Los hash de specs, manifests y receipt son SHA-256 de JSON canónico. Una modificación cambia huella y exige nuevo commit.
- docs/research/QORE_RESEARCH_ZERO_BUDGET_PROPOSALS_2026-10-13.json: **0** propuestas nuevas. Mantener como fuente canónica de propuestas sólo si se ha formulado una pregunta genuinamente diferente de la EIA descartada.
- docs/research/QORE_RESEARCH_FUTURE_HYPOTHESES_PREREG_2026-10-13.json: **0** prerregistros nuevos. No inventar respuestas para rellenar el laboratorio.
- .github/workflows/qore-research-prereg-git-freeze.yml: se ejecuta por push en rama de investigación o manual, `contents:read`, valida código con Ruff/Mypy, tests, Git manifest y sube únicamente recibo meta (sin datos de mercado).

## Dictamen de seguridad y autoridad

**Infraestructura PREREG GIT = PASS. No existe un nuevo experimento válido, rentable o aprobado.** El pipeline produjo `PREREG_COUNT 0`, `DATA_SPEND_USD 0`, `economic_backtest_executed=false`, `source_market_authority_obtained=false`, `holdout_read=false`, `trader_qualified=false`. Esto no es una evidencia de que haya edge: exclusivamente un contrato para registrar metodologías ANTES de observar sus resultados. El origen fuente y derechos siguen bloqueados para la misión de seis futuros CME.

El prereg SHA **NO prueba por sí solo** que el autor nunca vio resultados por otros medios; un futuro executor deberá verificar de manera independiente que el commit del prereg es ANCESTRO del run de resultados, su data-as-of, fecha de primera publicación, separación real de holdout y que no existe selección post-hoc de especificaciones. Los testigos sintéticos no constituyen certificación del mercado ni de metodología.

Se introdujo una lista concreta de hipótesis usadas: `research.hypothesis.backwardation-predicts-f1-up`, ya investigada y NO_SUPPORT en #913. Ni ocultar previous_tests ni reetiquetar esa misma hipótesis justifica reabrir el holdout; rechazar también cualquier alias semánticamente equivalente mediante revisión independiente. No usar el bloqueador mecánico como único criterio científico.

## Relación con otros estados existentes

- #916: EIA WTI/NG F1/F2 `CLOSED_NO_SUPPORT`, CME seis futuros `SOURCE_BLOCKED`, nuevas propuestas `PROPOSAL_ONLY`.
- #915: plan verdadero CF-11 en etapa EXPERIMENT con evidencia INSUFFICIENT y TraderLab DRAFT. Los tipos CIBO no otorgan autenticidad de Market/Risk/Lab ni DEMO.
- #913: 2 hipótesis EIA probadas 2012–2018 DEV + 2019–2021 DIAG, ambas sin apoyo reproducible. EIA holdout 2022–abril 2024 intacto.
- #895: fuente CME contratos nativos OHLCV 2012–septiembre 2024 aún incompleta / sin licencia a US$0. EIA (12.352 registros close-only WTI/NG) no prueba retornos negociables.

## Pendientes prioritarios del arquitecto siguiente

1. Formular una nueva hipótesis de mecanismo diferente, ANTES de examinar su outcome. Añadir idea y ficha detallada a los dos manifests versionados, con permisos/ventanas/criterios precisos; no inventar una señal tras mirar resultados.
2. Conseguir fuente US$0 con identidad, fecha de primera publicación, campos requeridos y permisos de reutilización. Mientras falte, la salida es `SOURCE_AUTHORITY_REQUIRED` y NUNCA `experiment_runnable=true`.
3. Crear un futuro runner de ejecución distinto del prereg con evidencia authenticada que verifique DAG causal (prereg commit ancestor del result), embargo temporal, datos que realmente existían antes de decisión, costos y holdout. No combinar prueba de registro con prueba económica.
4. Si algún día aparece una hipótesis con soporte estadístico, pasar por Trader Lab contractual real y todos los gates: Replay, Fast Forward, OOS, Stress, Monte Carlo, Risk, CIBO, independiente. Prohibido self-certification.
5. Un director de investigación siempre activo requeriría servicio/orquestador autorizado, almacenamiento/colas/idempotencia y auditoría de credenciales. Este código es CI por disparador, NO servicio autónomo.

**Regla final:** Sin gastar, sin merge, sin producción, sin falsificar rentabilidad. PR #917 está lista para auditar por otro arquitecto con testigos verdes, y las limitaciones documentadas.