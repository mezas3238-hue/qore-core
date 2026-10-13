# QORE Research CF-11 — integración REAL del experimento EIA cerrado (13 OCT 2026)

**Autoridad:** propietario QORE Core, presupuesto de market data US$0. **Estado:** contrato funcional CF-11 enlazado (valor tipado de investigación), **NO un agente autónomo en producción**. No merge, no LIVE, no DEMO, no VPS, no órdenes ni capital real.

## Resultado verificable y punto exacto de continuación

- Rama: `research/qore-eia-cf11-closed-plan-20261013`. PR [#915](https://github.com/mezas3238-hue/qore-core/pull/915) **DRAFT** child of PR [#914](https://github.com/mezas3238-hue/qore-core/pull/914). Parent prior science experiment PR [#913](https://github.com/mezas3238-hue/qore-core/pull/913); source acquisition parent PR [#895](https://github.com/mezas3238-hue/qore-core/pull/895).
- [GitHub Actions #38454993701](https://github.com/mezas3238-hue/qore-core/actions/runs/38454993701) `SUCCESS`, head **`ba316d0044f624cb5da485d1090d187b65d8ad33`**: Ruff PASS, Mypy PASS, **13/13 pruebas PASS**, descarga del **artefacto EIA original** y verificación GitHub run SHA, artifact digest y prereg ancestor PASS.
- [Artefacto nuevo #11841967856](https://github.com/mezas3238-hue/qore-core/actions/runs/38454993701/artifacts/11841967856) `qore-eia-cf11-real-plan-science-closure-no-promotion`, ZIP SHA256 **`f37d2cc7f5a437c3288cb73f81dd90a7a35d5878e600296ab82c159dcee2cb96`**, retención GitHub Actions **90 días**. El JSON es metadato y refs SHA, **no contiene precios ni retornos**.
- Origen: [Actions EIA original #38448311219](https://github.com/mezas3238-hue/qore-core/actions/runs/38448311219), prereg commit `00065e6df7450cac707f983858ca39eed7b30c47`, resultado original `NO_SUPPORT` para los dos mercados WTI/NG en la hipótesis fija F1>F2 -> futura subida F1. Periodos DEV 2012–18 y DIAG 2019–21; diagnóstico 2019–21 no reprodujo la dirección DEV. EIA holdout **2022-01–2024-04** no abierto.

## Qué se implementó, concretamente

| Recurso | Función | Resultado |
|---|---|---|
| `src/qore/infrastructure/trader_lab/qore_eia_cf11_closed_experiment_binding_v1.py` | Adaptador de `ScientificHandoffReceipt` revalidado a **instancia verdadera** de `qore.infrastructure.cibo.research_director.CiboResearchPlan` con `CiboFunctionalEvidence`; 4 refs de SHA256 XLS | Plan en `CiboResearchStage.EXPERIMENT`, `CiboEvidenceStatus.INSUFFICIENT` |
| `tests/infrastructure/trader_lab/test_qore_eia_cf11_closed_experiment_binding_v1.py` | 13 testigos sintéticos/adversariales, intento de falsificar SHAs/p-values/receipt/holdout, chequeo `CiboResearchDirector.advance` con evidencia insuficiente a LAB y DEMO | 13/13 PASS |
| `.github/scripts/qore_eia_cf11_closed_plan_assembly_v1.py` | Verifica coincidencia semántica de recibo SHA previo y JSON EIA original autenticado en el **mismo job** | Construye y serializa un único plan CF11, ningún replay |
| `.github/workflows/qore-eia-cf11-closed-plan-binding.yml` | pipeline de provenance+Ruff+Mypy+tests con `permissions: contents:read; actions:read` | Actions SUCCESS, artifact solo ciencia |

Campos de salida fundamentales:
```text
CF11_REAL_RESEARCH_PLAN = research.eia.futures-a-f1f2-closure
CF11_STAGE             = experiment
CF11_EVIDENCE          = insufficient
SCIENTIFIC_DECISION    = NO_SUPPORT_UNDER_PREREG
TRADER_LAB_STATUS      = draft
DEMO_ELIGIBLE          = false
TRADER_LAB_STAGE_EVIDENCE_PRODUCED = false
ECONOMIC_BACKTEST_PERFORMED = false
FRESH_HOLDOUT_CONSUMED = false
```

- El `CiboResearchPlan` **no falsifica** el paso por `OBSERVATION/HYPOTHESIS/FORMALIZATION/DATA`; es un **registro retrospectivo tipado** de un experimento ya cerrado cuya autenticidad se verifica por GitHub. No se llama a `CiboResearchDirector.advance` para inventar las etapas anteriores.
- `CiboEvidenceStatus.INSUFFICIENT` se exige a pesar de que las tablas científicas sean verificadas: la plataforma no posee **market authority** ni capacidad de calcular resultados económicos contratables con una serie EIA F1/F2 continua de precios únicos, sin identificadores de vencimiento, as-of y costes.
- El plan tiene refs de hashes de los **4 archivos EIA** y `scientific_receipt_sha256`. Estos son **identificadores de contenido y trazabilidad**; no pretenden ser certificados externos de proveedor, Risk o Mercado.
- Contrato `CiboResearchDirector.advance` efectivamente ensayado: avanzar desde ese plan a `TRADER_LAB` o `DEMO` con evidencia insuficiente regresa `Failure`, como corresponde. El contrato general de CF-11 puede representar etapas intermedias con evidencia dependiente; **NO** debe interpretarse que el CF-11 global bloquea automáticamente toda transición a `REPLAY_BACKTEST`. La vía especializada no realiza esas transiciones; cualquier integrador ulterior debe exigir pruebas económicas y autoridad extra en frontera.
- `TraderLabState.DRAFT` + `TraderLabStageEvidenceRecord` ausente + 0 fills reales: no trader creado, ningún OOS abierto, no entrada DEMO.

## Hallazgos y límites abiertos

1. **La conexión aquí es funcional/tipada y probada en CI, no deployment autónomo.** En el repositorio hay un `CiboResearchDirector` determinista sin bucle de vigilancia ni autoridad de emitir gobernanza `SUFFICIENT`. El trabajo pendiente es diseñar **un orquestador externo con autenticación real** para consumir nuevos experimentos al producirse, con colas/reintentos/idempotencia y permiso explícito del Owner para desplegarlo (sin confundir código con servicio en ejecución).
2. La herramienta `verified_source=True` **no es credencial**: solo se usa dentro del workflow que revalida GitHub API, original artifact digest, SHA de commit y prereg ancestry. Su valor pasado por un caller aislado **no se convierte en authority root**, y el plan queda `INSUFFICIENT` incluso tras comprobar el workflow. No reutilizar este bool fuera del workflow para afirmar autenticidad.
3. Investigación financiera de los **6 futuros de CME**: `SOURCE_M0=BLOCKED_DATA_OR_LICENSE` con presupuesto 0; EIA solo tiene 2 series rank1/rank2 para WTI/NG 2012–abr2024 y no OHLCV CME natives. No hacer test de profits/Sharpe y no reabrir misma hipótesis con cambios ex post.
4. Para certificación completa falta un **TraderCandidate binding** legítimo, datos de contrato negociable, reclamo de coste con bid/ask, Replay+Fast Forward+OOS+Stress+Monte Carlo+Risk+CIBO+Independent Validation externos. La plataforma no posee eso en este experimento. No permitir `DEMO_ELIGIBLE` por registrarlo en Research.
5. El artifact EIA original caduca tras el período de retención; una revalidación del mismo resultado NO autoriza abrir el holdout ni entrenar sobre las mismas tablas. Política de archivo de metadatos/actas firmadas en GitHub disponible, no precios raw.

## Próxima misión propuesta (sin ejecutarla automáticamente)

Construir un **registro/cola de hipótesis nuevas** que asigne identities y familias estadísticamente separadas antes de obtener resultados, controle presupuesto de datos 0, requisitos causales, disponibilidad de fuentes, timestamps as-of y propiedad de acceso, y canalice SOLO RESULTADOS AUTENTICADOS a `CF-11` en etapa adecuada. Si no hay market data contractual, cerrar como `SOURCE_BLOCKED` antes de cualquier cálculo económico. Independientemente, priorizar traders Forex con edge neto validado en otros proyectos; no comprometer capital ni ejecución real para financiar estas hipótesis.

**Dictamen:** integración CF-11 en código **PASS**; runtime autónomo **NOT VERIFIED/NOT RUNNING HERE**; resultado científico EIA `NO_SUPPORT_UNDER_PREREG`; Trader Lab `DRAFT`; source M0 `BLOCKED_DATA_OR_LICENSE`; **US$0, no MERGE, no LIVE**.
