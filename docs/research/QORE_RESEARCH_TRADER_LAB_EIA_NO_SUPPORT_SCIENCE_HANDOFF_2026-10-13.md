# QORE Research ⇄ Trader Lab — Handoff científico EIA WTI / NG (13-OCT-2026)

**Estado:** integración **read-only** de evidencia completada; NO estructura de un nuevo Trader; no LIVE/DEMO, no operación, no sizing, no PnL. Budget datos **US$0**. Research ≠ execution.

## Mandato del propietario y alcance estricto

Conectar el resultado ya sellado de **dos pruebas de asociación** WTI/NG EIA a los contratos de QORE Research y Trader Lab, manteniendo el **dictamen NO_SUPPORT**, sin abrir el holdout 2022–2024 ni intentar "rescatar" los p-values cambiando dirección/horizonte. Mandato científico independiente de otras metodologías QORE y del cierre de FX Native.

- Fuente/handoff original: [PR #913](https://github.com/mezas3238-hue/qore-core/pull/913) y [preregistro SHA 00065e6](https://github.com/mezas3238-hue/qore-core/commit/00065e6df7450cac707f983858ca39eed7b30c47).
- Resultado autoritativo: [Actions #38448311219 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38448311219), `HEAD 25b8d2fc18c02992ff1115bbb117cc42438de891`; [artefacto JSON original id 11839586948](https://github.com/mezas3238-hue/qore-core/actions/runs/38448311219/artifacts/11839586948), SHA256 ZIP `48cc8c7e8b3816fb7adf23658303bd90c3ed9e270c6e0e015fbd82a9904bf9eb`.
- [Resultados completos fuente](QORE_FUTURES_A_EIA_WTI_NG_F1F2_PREDICTIVE_SCREEN_EXECUTED_NO_SUPPORT_2026-10-13.md): WTI DEV delta −0.03726, p 0.70771; DIAG delta +0.22078 p 0.14442. NG DEV delta −0.40890 p 0.99921; DIAG delta +0.36000 p 0.05796. Ambos FAIL al criterio previo p<=0.025 y delta>=+0.10 en DEV y DIAG.
- Fuente económica **NO válida para ejecución**: EIA publica un precio por día para *rank* F1/F2 rotante; no identifica contrato de entrega ni `first_published_at`, no es vela OHLCV y no hay spread/costes/roll. No inventar retorno, Sharpe, NAV ni evidencia de fills.

## Implementación concreta

| Recurso | Función |
|---|---|
| `src/qore/infrastructure/trader_lab/qore_eia_research_science_handoff_v1.py` | Adaptador fail-closed: comprueba cuatro SHAs EIA, variables/horizontes congelados, conteos exactos, independiente Fisher unilateral, multiplicidad, clases y signos, original holdout sellado; crea receipt con SHA256 de JSON de ciencia |
| `tests/infrastructure/trader_lab/test_qore_eia_research_science_handoff_v1.py` | 14 testigos y ataques: p/delta falsificados, muestras/SHAs cambiados, promover Trader/DEMO, abrir holdout, root sustituida, alpha modificado, etc |
| `.github/scripts/qore_eia_research_science_receipt_v1.py` | Verifica vía API GitHub el run original SUCCESS, SHA del commit, id/digest del artifact, ancestro prereg antes del runner; emite una **única evidencia estructural no económica** |
| `.github/workflows/qore-eia-research-traderlab-science-bridge.yml` | Descarga JSON de fuente original con `actions:read`; valida Ruff/Mypy/tests; publica `qore-eia-research-traderlab-science-only-receipt` solo con resumen científico |

### Contratos QORE existentes respetados

- `src/qore/infrastructure/cibo/research_director.py`: el enum `CiboResearchStage.EXPERIMENT` es un **rótulo válido** de esta evidencia. El adaptador NO ha creado un `CiboResearchPlan` autenticado ni llamado a un Director autónomo, porque haría falta `CiboFunctionalEvidence` válida de las autoridades pertinentes.
- `src/qore/infrastructure/trader_lab/lifecycle.py`: `TraderLabState.DRAFT`; todavía faltan todos los Gates obligatorios. No se simula una entrada de `RESEARCH_READY`.
- `src/qore/infrastructure/trader_lab/stage_evidence.py`: **NO** se produce `TraderLabStageEvidenceRecord`; la etapa RESEARCH requiere `RESEARCH_STRATEGY_BINDING` genuino con candidato/version/control; estos datos EIA no constituyen tal trader ni una transacción.
- `src/qore/infrastructure/research_sampling_frame.py`: **NO** se crean `ResearchReturnObservation`, porque necesitarían `ResearchGrossEconomicResult` con fills reales; las subidas de F1 son simples precios de referencia.
- `src/qore/infrastructure/research_hypothesis_family.py`: NO usar familia de bootstrap económico `ResearchPeriodicEquityReturnSeries` para esta asociación binaria; sería blanquear el tipo de evidencia.

### Verificaciones de confianza

**La procedencia del archivo** no se afirma porque lo diga el caller: GitHub autentica descarga del artifact exacto con sha ZIP conocido, metadata de `SOURCE_RUN_ID=38448311219`, conclusion `success`, `head_sha`, orden ancestro Git del prereg, y el código **recalcula** Fisher en vez de confiar en los p-values declarados. Rechaza JSON de salida con `trader_certified!=0`, `trading_orders!=0`, más raíces, estado OOS abierto, cambio de SHAs, thresholds, ventanas o conteos.

**Limitaciones honestas:** la ascendencia Git prueba orden del prereg *en el repositorio*, no ceguera histórica universal de toda persona; fechas de publicación de precios EIA permanecen no certificadas; reporte firmado con SHA no es prueba de origen de broker, ni authority root. El artefacto GitHub tiene retención limitada; si caduca, el workflow **falla** (no falsifica un re-run con reserva), hasta nuevo protocolo que revalide origen sin reinterpretar los resultados.

## Output, interpretación y límite de promoción

```text
QORE_RESEARCH_SCIENCE_STAGE         experiment
EIA_PREREG_SCIENTIFIC_DECISION     NO_SUPPORT_UNDER_PREREG
WTI                                  NO_POSITIVE_DIRECTION (DEV)
NG                                   NO_POSITIVE_DIRECTION (DEV)
TRADER_LAB_STATE                     draft
TRADER_LAB_EVIDENCE_PRODUCED         false
DEMO_ELIGIBLE                        false
EXECUTION_AUTHORITY                  false
ECONOMIC_RETURNS_OR_FILLS            false
FRESH_HOLDOUT_CONSUMED               false
```

**NO_SUPPORT** = ninguna prueba respaldó de modo suficiente la hipótesis fija. No significa que el mercado no tenga edge ni que una hipótesis futura nueva esté prohibida. La investigación original Futures A 6 futuros sigue **BLOCKED_DATA_OR_LICENSE** por necesidad de históricos por vencimiento 2012–2024; no mezclar dictámenes.

## Pendientes exactos para próximo arquitecto

1. **No rerun oportunista** de esta hipótesis con reversión, días distintos o reserva 2022–24 tras los resultados; escribir hipótesis económica *genuinamente nueva*, fundada externamente, en un PR diferente y con fuentes suficientes.
2. La conexión con el **runtime real** de QORE Research/CF-11 requiere evidencia acreditada que el Director pueda aceptar sin blanquear `ResearchRun`. La presente integración solo **clasifica y verifica** evidencia existente, no controla el orquestador que ejecuta nuevos experimentos.
3. Para Trader Lab auténtico se precisan contratos nativos, calendario/fees/bid-ask, candidate binding/version, replay determinista causal, OOS, Monte Carlo, Risk, CIBO e independencia. Sin ello, mantener DRAFT.
4. Sin financiación disponible, mantener presupuesto 0 y explorar científicamente solo fuentes lícitas disponibles; no compras, no API keys/tokens en repo, ni tarjetas, VPS/LIVE/MT5/producción.

**NO MERGE** de PR #914, #913 o #895 salvo orden del propietario.
