# QORE CORE — HANDOFF MAESTRO INTEGRAL
## Futures A, mercado de futuros, EIA, QORE Research CF-11 y Trader Lab

**Checkpoint:** 13-OCT-2026. **Repositorio soberano:** mezas3238-hue/qore-core. **Presupuesto de market data:** USD 0.
**Rama de continuidad:** research/qore-cf11-source-first-mission-queue-20261013.
**PR de continuidad:** [#916](https://github.com/mezas3238-hue/qore-core/pull/916), OPEN/DRAFT, NO MERGE.
**HEAD previo a este documento verificado en el turno:** 243ba9e8325abc9c59578e380da7e04bb15d6982. La publicación de este handoff agregará un commit nuevo; verificar HEAD en el relevo.

> **Resumen autoritativo:** se entregó infraestructura de investigación por GitHub Actions, descarga gratuita limitada de precios EIA, dos hipótesis de asociación preregistradas y ensayadas con resultado NO_SUPPORT, un puente de evidencia QORE Research/Trader Lab, conexión a una instancia real de CF-11 y una cola source-first gobernada. **NO** existe un trader rentable certificado derivado de este trabajo, **NO** se evaluó rentabilidad neta de futuros, **NO** se desplegó director autónomo Research siempre activo y la compra de datos no está autorizada. La misión de obtener seis futuros contract-native sigue BLOCKED_DATA_OR_LICENSE.

## 1. Reglas de gobernanza para el próximo arquitecto

- GitHub es la fuente soberana de verdad. NO MERGE sin orden expresa. Las cinco PR están abiertas en DRAFT y se encadenan jerárquicamente; no rebasar contra main a ciegas.
- NO LIVE, NO capital real, NO VPS/MT5/cTrader/servicio broker sin orden; no ejecutar órdenes. CIBO y Risk conservan autoridad soberana. Traders sin sizing propio.
- **US$0** para adquisición de datos; no tarjeta, no compra, no consumo de servicio con cargo, no fingir que los USD125 promocionales de Databento equivalen a cobertura completa gratuita.
- Preservar reserva EIA **2022-01 a 2024-04** sin puntuar outcomes; separar del holdout QORE Native FX desde 2024-09-17, tampoco tocado.
- Importante matiz: el XLS EIA completo se descarga para validar hash, pero el algoritmo de evaluación solo usa observaciones anteriores a enero de 2022. No afirmar que esos bytes no se descargaron; lo sellado es la **evaluación** de la reserva.
- Ningún PnL sin fuentes, cost model y contratos identificados. Ninguna “evidencia suficiente” de CF-11 sin authority root. El conteo cero de nuevos traders se refiere a Futures A / QORE Native, no es un juicio sobre todos los Traders existentes.

## 2. Orden de PR soberanas — todas OPEN/DRAFT

| PR | Rama | Qué contiene y resultado | Base |
|---|---|---|---|
| [#895](https://github.com/mezas3238-hue/qore-core/pull/895) | research/qore-commodity-futures-mission-a-data-contract-20261013 | M0 contratos nativos seis futuros, fuentes gratuitas y gate sintético 18/18 | main |
| [#913](https://github.com/mezas3238-hue/qore-core/pull/913) | research/qore-futures-a-eia-front2-predictive-screen-20261013 | dos hipótesis WTI/NG, prereg y NO_SUPPORT, 8/8 | rama #895 |
| [#914](https://github.com/mezas3238-hue/qore-core/pull/914) | research/qore-eia-research-traderlab-evidence-bridge-20261013 | science receipt solo lectura, revalidación de resultados y 14/14 | rama #913 |
| [#915](https://github.com/mezas3238-hue/qore-core/pull/915) | research/qore-eia-cf11-closed-plan-20261013 | CiboResearchPlan REAL con evidencia INSUFFICIENT, 13/13 | rama #914 |
| [#916](https://github.com/mezas3238-hue/qore-core/pull/916) | research/qore-cf11-source-first-mission-queue-20261013 | cola source-first, hipótesis archivadas y propuesta-only, 19/19 | rama #915 |

**Issue fuente:** [#894](https://github.com/mezas3238-hue/qore-core/issues/894). Prórrogas o pruebas en otra rama no suponen autorización de merge.

### Commits HEAD verificados antes del handoff

- #895: c8aececffee1e393849eb585740fe919cae01098
- #913: e9f86d3249be28f0494d9aaed039bf454183460c
- #914: 6b919a2a76adde706898b93c0e248e09388a6634
- #915: 20a1da90b1b7c56387494c33e8e5e44eb5b9fa66
- #916: 243ba9e8325abc9c59578e380da7e04bb15d6982, sujeto a avance del propio handoff.

## 3. Trabajo I — M0 Futures A: contrato de datos y descubrimiento

**Objetivo de datos:** seis raíces CME/CBOT/COMEX/NYMEX CL WTI, NG gas Henry Hub, GC oro, HG cobre, ZC maíz, ZS soja; al menos dos vencimientos individuales simultáneos por raíz, D1 OHLCV, precio de settlement separado, OI, multiplicador, tick, calendarios de first notice/last trade y roll, bid/ask y costes. Ventana planeada 2012-01-01 a 2024-09-16. Continuos ajustados y CFD no equivalen a contrato real.

**Código y documentos creados:**
- docs/missions/QORE_FUTURES_A_M0_NATIVE_COMMODITY_CONTRACT_DATA_MISSION_2026-10-13.md
- docs/research/QORE_FUTURES_A_M0_EXCHANGE_NATIVE_SETTLEMENT_DATA_PROVIDER_RFI_DRAFT_2026-10-13.md — borrador RFI **NO ENVIADO**.
- src/qore/infrastructure/trader_lab/qore_futures_a_m0_native_contract_source_gate_v1.py
- tests/infrastructure/trader_lab/test_qore_futures_a_m0_native_contract_source_gate_v1.py
- .github/workflows/qore-futures-a-m0-native-contract-source-gate.yml
- [Actions #38341020091](https://github.com/mezas3238-hue/qore-core/actions/runs/38341020091) SUCCESS **18/18 tests SINTÉTICOS**; protege fechas de aviso/cutoff, WTI negativo, source identity. No acredita datos contratables.

**Fuentes realmente investigadas:**

| Fuente | Qué ocurrió | Limitación real |
|---|---|---|
| Databento GLBX.MDP3 | documentación y selección publicadas; ofrece schemas ohlcv-1d, statistics y definition; posible crédito promocional | Sin entitlement/card/costos totales confirmados a USD0. Ninguna descarga con cobro |
| TurtleTrader | [Actions #38342603409](https://github.com/mezas3238-hue/qore-core/actions/runs/38342603409), cinco ZIP CL GC HG ZC ZS descargados e inventariados por SHA | últimas fechas parseables diciembre-1999/enero-2000, cero filas 2012–24; NG ausente |
| SSEconomics | mismo preflight; ZIP de **17 XLSX** incluyendo seis commodities | curvas académicas mensuales/mixtas hasta dic-2022; no velas contract-native D1, licencia de origen necesita verificación |
| TopstepX público via repositorio axb0306/cme-futures-ohlc | [Actions #38370156044](https://github.com/mezas3238-hue/qore-core/actions/runs/38370156044), metadatos de seis carpetas | archivos declarados 2025–26, no 2012–24 y no dos contratos nativos por fila certificados |
| CME DataMine | auditoría documentación oficial y una llamada metadata-only a endpoint EOD sin credenciales: HTTP 401 | Settlements File postmedianoche puede no llevar fee, pero EOD comercial y API exigen derecho/acceso. No prueba 12 años gratis ni OHLCV |
| Portara/CQG | catálogo de seis raíces y formato individual-contract D1 revisado, muestras/Free Tier examinadas | histórico completo comercial, precio y entitlement; no importado, no compra |
| US EIA | cuatro XLS oficiales descargados: CL primer/segundo, NG primer/segundo; [export Actions #38343102029](https://github.com/mezas3238-hue/qore-core/actions/runs/38343102029) | un precio por día/contract-rank, NO velas ni contract delivery ID, as-of desconocido, cobertura se corta abril-2024 |

**Dato EIA efectivamente recuperado:** 3.086 fechas WTI F1, 3.086 WTI F2, 3.090 NG F1, 3.090 NG F2; **12.352 observaciones diarias**, 2012-01-03 a **2024-04-05**, con precio WTI negativo de 2020 preservado. Artefacto público [#11786984830](https://github.com/mezas3238-hue/qore-core/actions/runs/38343102029/artifacts/11786984830), ZIP digest 50ea702cebad87c67ec1eaf1026cd949598672613d1112d6084eb8ed3cfaed04.

**Conclusión M0:** BLOCKED_DATA_OR_LICENSE para los seis futuros. Existen precios gratuitos útiles para ciencia preliminar, **no** fuente ejecutable seis raíces/dos expiries. No se ha encontrado todavía vía completa legal de USD0.

Informes M0:
- docs/research/QORE_FUTURES_A_M0_NATIVE_CME_OHLCV_VENDOR_SELECTION_DATABENTO_2026-10-13.md
- docs/research/QORE_FUTURES_A_M0_FREE_ARCHIVE_6_SOURCE_EXECUTED_BLOCKED_2026-10-13.md
- docs/research/QORE_FUTURES_A_M0_CME_FREE_SETTLEMENT_TOPSTEP_PUBLIC_REPO_SOURCE_GATE_2026-10-13.md
- docs/research/QORE_FUTURES_A_M0_PORTARA_CQG_CONTRACT_D1_ZERO_BUDGET_ENTITLEMENT_AUDIT_2026-10-13.md

## 4. Trabajo II — evaluación científica preregistrada EIA WTI/NG (#913)

**Preregistro temporalmente anterior a resultados:** commit [00065e6df7450cac707f983858ca39eed7b30c47](https://github.com/mezas3238-hue/qore-core/commit/00065e6df7450cac707f983858ca39eed7b30c47).

**Hipótesis fija por raíz:** backwardation F1(t)>F2(t) en primer día común del mes aumenta Pr[F1(t+7)−F1(t+2)>0] respecto de contango F1(t)<F2(t). t+2/t+7 son observaciones comunes del mismo mes, no días corridos, un evento mensual por root. Precios referenciales, sin rendimiento de contrato comprable.

**Ventanas:** DEV 2012–2018; DIAG 2019–2021; reserva 2022 a abril-2024 NO puntuada. Prueba Fisher exacta unilateral por raíz, Bonferroni (p <=0,025), efecto >= +10 pp, al menos 8 meses por régimen **en ambas ventanas**. Sin ajuste posterior de orientación, años o plazo.

| Root | DEV meses / efecto / p | DIAG meses / efecto / p | Dictamen |
|---|---|---|---|
| WTI | 83; **−3,7258 pp**; p 0,7077117 | 36; +22,0779 pp; p 0,1444197 | NO_SUPPORT |
| NG | 83; **−40,8903 pp**; p 0,9992108 | 35; +36,0000 pp; p 0,0579600 | NO_SUPPORT |

N de meses válidos WTI 119, NG 118. Signo cambia entre DEV y DIAG, ningún test cumple p 0,025 en ambas ventanas. **NO_SUPPORT_UNDER_PREREG para estas dos hipótesis únicamente.** No implica que el mercado carezca de todos los edges; p 0,058 NG DIAG no puede promocionarse.

**Evidencia:** [Actions #38448311219](https://github.com/mezas3238-hue/qore-core/actions/runs/38448311219) SUCCESS 8/8 tests, artifact [#11839586948](https://github.com/mezas3238-hue/qore-core/actions/runs/38448311219/artifacts/11839586948) SHA ZIP 48cc8c7e8b3816fb7adf23658303bd90c3ed9e270c6e0e015fbd82a9904bf9eb.

**Código:** src/qore/infrastructure/trader_lab/qore_futures_a_eia_f1f2_predictive_screen_v1.py y tests/infrastructure/trader_lab/test_qore_futures_a_eia_f1f2_predictive_screen_v1.py. Documentos de prereg y acta detallada bajo docs/research/QORE_FUTURES_A_EIA_WTI_NG_F1F2_PREDICTIVE_SCREEN_*_2026-10-13.md.

**Limitaciones:** el ranking F1/F2 rota de vencimiento, sin identidad de delivery ni as-of first publication; retardar dos observaciones reduce contaminación pero no garantiza causalidad verdadera. Sin bid/ask, vol, OI individual, comisiones, slippage, margin, lot, rollover real. **No se calculó PnL, PF, DD ni Sharpe negociable.**

## 5. Trabajo III — QORE Research a Trader Lab, ciencia de solo lectura (#914)

Se hizo receipt de resultados a prueba de cambios: verifica fuente EIA congelada, reevalúa Fisher y probabilidades desde conteos, requiere GitHub Actions SUCCESS del original, mismo commit/hash de archivo y antecedencia del preregistro. Clasifica evidencia en CF-11 EXPERIMENT, Trader Lab DRAFT; **NO** fabrica ResearchRun económico, fills, Risk approval, CIBO authority ni StageEvidenceRecord.

- Código: src/qore/infrastructure/trader_lab/qore_eia_research_science_handoff_v1.py
- Script: .github/scripts/qore_eia_research_science_receipt_v1.py
- Test: tests/infrastructure/trader_lab/test_qore_eia_research_science_handoff_v1.py
- Workflow: .github/workflows/qore-eia-research-traderlab-science-bridge.yml
- [Actions #38452295022](https://github.com/mezas3238-hue/qore-core/actions/runs/38452295022) SUCCESS **14/14, Ruff PASS, Mypy PASS**; [artifact #11841351490](https://github.com/mezas3238-hue/qore-core/actions/runs/38452295022/artifacts/11841351490), SHA ZIP a34f13db3c75a3a6c86be43bef795b0118e4864d927afde2cc855ce9e42c7fbf.
- Informe: docs/research/QORE_RESEARCH_TRADER_LAB_EIA_NO_SUPPORT_SCIENCE_HANDOFF_2026-10-13.md

**Problema estructural:** SHA autentica contenido y Actions origen, no que un proveedor/licenciante o Risk emita autoridad. No confundir ciencia con approval de Trader Lab.

## 6. Trabajo IV — contrato REAL de CF-11 Research Director (#915)

Se creó verdadera instancia de qore.infrastructure.cibo.research_director.CiboResearchPlan, como **acta retrospectiva tipada**, no falsa progresión de etapas previas. Stage EXPERIMENT; status CiboFunctionalEvidence.INSUFFICIENT, 4 refs EIA más hash receipt. Se ensayó CiboResearchDirector.advance real: rechaza TRADER_LAB y DEMO con INSUFFICIENT.

- Código: src/qore/infrastructure/trader_lab/qore_eia_cf11_closed_experiment_binding_v1.py
- Script: .github/scripts/qore_eia_cf11_closed_plan_assembly_v1.py
- Test: tests/infrastructure/trader_lab/test_qore_eia_cf11_closed_experiment_binding_v1.py
- Workflow: .github/workflows/qore-eia-cf11-closed-plan-binding.yml
- [Actions #38454993701](https://github.com/mezas3238-hue/qore-core/actions/runs/38454993701) SUCCESS **13/13 tests, Ruff PASS, Mypy PASS**; [artifact #11841967856](https://github.com/mezas3238-hue/qore-core/actions/runs/38454993701/artifacts/11841967856) SHA ZIP f37d2cc7f5a437c3288cb73f81dd90a7a35d5878e600296ab82c159dcee2cb96.
- Documento: docs/research/QORE_CF11_EIA_REAL_PLAN_RESEARCH_TRADERLAB_CONTINUITY_2026-10-13.md

**Problema pendiente:** CF-11 aquí es un contrato funcional dentro de GitHub Actions, no un director siempre ejecutándose. La variable verified_source=True aislada puede ser enviada por un caller; **no es autoridad** por sí misma. Se acepta solo en flujo CI cuyo proveedor GitHub verificó artifact/commit/digest/ascendencia. Incluso allí la evidencia financiera permanece INSUFFICIENT.

## 7. Trabajo V — cola source-first QORE Research (#916)

Entregados ResearchIntakeLedger y ResearchIntakeRecord inmutables, con identidad de misión y SHA de contenido, tres estados: CLOSED_NO_SUPPORT (solo EIA original), SOURCE_BLOCKED (futuros 6×2) y PROPOSAL_ONLY (ideas nuevas aún no preregistradas). La cola se construye con CF-11 verdadero regenerado en mismo job después de comprobar origen Actions; el manifiesto actual de nuevas propuestas está VACÍO.

| Misión | Estado | Próximo paso permitido | Ejecutable |
|---|---|---|---|
| research.eia.futures-a-f1f2-closure | closed_no_support | stop_and_archive | NO |
| research.futures-a.native-6roots-d1 | source_blocked | acquire_valid_source_within_zero_budget | NO |
| Ideas nuevas (0 registradas) | proposal_only | write_new_prereg | NO |

**Código:** src/qore/infrastructure/trader_lab/qore_research_zero_budget_intake_v1.py; tests/infrastructure/trader_lab/test_qore_research_zero_budget_intake_v1.py (19 tests); script .github/scripts/qore_research_zero_budget_queue_v1.py; workflow .github/workflows/qore-cf11-source-first-research-intake.yml; manifiesto docs/research/QORE_RESEARCH_ZERO_BUDGET_PROPOSALS_2026-10-13.json; handoff previo docs/research/QORE_RESEARCH_ZERO_BUDGET_SOURCE_FIRST_QUEUE_MASTER_HANDOFF_2026-10-13.md.

[Actions #38459093369](https://github.com/mezas3238-hue/qore-core/actions/runs/38459093369) primer SUCCESS (19/19). **Bug descubierto y corregido:** la aserción inicial del workflow exigía 0 propuestas para siempre, contradiciendo la admisión de nuevas proposals-only. Commit ca3a69845ded438a980d9473e9b40af86345391f corrigió el gate para permitir hasta 20 propuestas no ejecutables sin alterar los dos estados básicos. [Actions #38459547103](https://github.com/mezas3238-hue/qore-core/actions/runs/38459547103) **SUCCESS posterior, 19/19 tests + Ruff/Mypy PASS**, artefacto [#11844922650](https://github.com/mezas3238-hue/qore-core/actions/runs/38459547103/artifacts/11844922650), SHA ZIP 796f8bcde2c596687c3921e368ccc60a3a27106f2335f61d99cf005da7cc02b4.

**Limitación:** PR #916 todavía no ha probado experimentalmente una propuesta real nueva con datos y prereg (manifest vacío), solo estructura y tests sintéticos. Es intake y policy gate, NO scheduler/daemon ni investigación automática de mercados.

## 8. Matriz de evidencia: qué fue aprobado

| Componente | Acciones verdes verificadas | Alcance aprobado |
|---|---|---|
| Fuente M0 | #38341020091 — 18/18 | validadores estructurales SINTÉTICOS |
| Datos gratuitos | #38342603409, #38343102029, #38370156044 | fuentes auditadas; 4 series diarias EIA son close-only |
| Test predictivo EIA | #38448311219 — 8/8 | NO_SUPPORT de H1_WTI/H1_NG |
| Bridge Research ⇄ Trader Lab | #38452295022 — 14/14 | recibo científico auténtico, NO elegibilidad |
| Plan real CF-11 | #38454993701 — 13/13 | EXPERIMENT/INSUFFICIENT, no LAB/DEMO |
| Cola Research | #38459547103 — 19/19 | SOURCE_BLOCKED/CLOSED_NO_SUPPORT, intake no ejecutable |

**Todo ello suma varios éxitos de ingeniería**, NO un trader de futuros rentable. No reivindicar edge económico, fills, Sharpe, PF, DD o certificación a partir de pruebas de integridad.

## 9. PROBLEMAS abiertos por prioridad y remedio preciso

### P0 — Datos CME contract-native 6×2 no disponibles a coste cero
**Síntoma:** no hay OHLCV D1 por expiry, contract ID, tick/multiplier, last trade/first notice, as-of, derechos de uso, coberturas seis instrumentos 2012–2024.
**Raíz:** las fuentes gratuitas halladas son demasiado antiguas, mensuales, recientes o solo close/rank. Los proveedores completos exigen contrato y potencial pago.
**Aceptación:** evidencia de una fuente legal realmente US$0 con dos vencimientos simultáneos + derechos, checksums, timestamps, costes, sin modificar mercado/horizonte silenciosamente. En ausencia de ello NO-GO.

### P0 — Sin edge negociable certificado
**Síntoma:** los 12.352 precios EIA no contienen OHLC ni expiración, spreads, bid/ask, fees y roll; la probabilidad de subidas F1 no es rendimiento de trading.
**Aceptación:** fuente negociable + replay causal verificable + modelo de ejecución/costes, solo entonces medir net PnL/PF/DD y pasar Gates.

### P0 — Hipótesis EIA gastada; riesgo alto de outcome-aware tuning
**Síntoma:** resultados DEV negativos y DIAG positivos no significativos tientan a invertir predicción, variar t+2/t+7, filtrar años o abrir holdout.
**Aceptación:** mantener CLOSED_NO_SUPPORT, no consumir reserva EIA 2022–2024, escribir una hipótesis GENUINAMENTE distinta, prereg BEFORE outcomes con familia estadística independiente y datos aptos. No convertir p 0,058 en “edge cercano”.

### P0 — Autoridad externa inexistente
**Síntoma:** datos y sha dentro de GH no equivalen a atestación de Market/Risk/Economic/TraderLab. CF-11 no puede fabricar CiboEvidenceStatus.SUFFICIENT.
**Aceptación:** contrato de emisor de autoridad de origen conocido, recibos y revocación auditables; nunca promover etapas económicas desde el bridge solo científico.

### P0 — Runtime autónomo QORE Research no construido
**Síntoma:** GitHub workflows por push/dispatch; NO hay servicio investigador 24/7 con orquestador de colas persistentes, idempotencia, alertas, permisos, límites y contrato de lectura de fuentes.
**Aceptación:** diseño y tests de flujo source→prereg→run→receipt→decision, sin despliegue/credenciales/live salvo orden expresa. Etiquetar correctamente CI vs daemon.

### P1 — Proposal-only no es preregistro científico
**Síntoma:** el manifiesto de máximo 20 ideas futuras solo fija code, question, data_requirement y roots; NO congela outcome, time split, test, family, alpha, thresholds, fuente.
**Aceptación:** prereg versionado con commit antes del outcome, fuente permitida, tiempo de disponibilidad, reglas de múltiples tests y seal de holdout. Nuevas entradas mantienen runnable=False hasta validar fuentes y política.

### P1 — Evidencia GitHub Actions caduca y originales pueden revisarse
**Síntoma:** artefactos #11786984830, #11839586948, #11841351490, #11841967856 y #11844922650 tienen retención finita; XLS fuente podría cambiar SHA por revisiones posteriores.
**Aceptación:** custodia inmutable de ACTAS, metadatos y checksums en GitHub sin redistribuir precios de terceros; si falla SHA o artifact expiró, declarar BLOCKED_PROVENANCE y no reabrir holdout para recrear pruebas retrospectivamente.

### P1 — CI y jerarquía de ramas
**Síntoma:** PR anidadas; fallas anteriores Ruff E501, Mypy incompatibilidad de kwargs, gate falso de cero propuestas. Ya corregidas en commits y CI verde; los tests mayormente sintéticos no garantizan economía real.
**Aceptación:** verificar HEAD actual, conservar source commit/digest, correr workflows de cada estadio si se modifican contratos y no usar una ejecución verde previa como prueba automática de nuevo HEAD o de merge.

### P1 — Limitaciones de potencia y causalidad del EIA
**Síntoma:** ~35–36 eventos DIAG/root, regímenes desbalanceados, contratos rank rotantes y as-of histórico no demostrado; rango cambia de vencimiento y puede contaminar diferencias.
**Aceptación:** registrar como limitación, no usar tests diferentes ex post sobre el mismo outcome. Nueva ciencia necesita un mecanismo nuevo y datos mejores.

### P2 — Gates futuros de trader
Faltan candidate binding/identidad y versiones, contrato real, replay determinista, Bid/Ask y costos, prueba OOS independiente, stress, Monte Carlo, Risk, CIBO y certificación independiente. No usar sizing de Traders; CIBO sigue soberano. Cero promoción DEMO por contrato CF-11.

## 10. Lista de acciones concreta para siguiente arquitecto

1. **Verificar estado en GitHub:** abrir [PR #916](https://github.com/mezas3238-hue/qore-core/pull/916), HEAD actual y base #915→#914→#913→#895. No merge.
2. **Reproducir evidencia:** [Actions #38459547103](https://github.com/mezas3238-hue/qore-core/actions/runs/38459547103) con artifact #11844922650; en #913 consultar original EIA [Actions #38448311219](https://github.com/mezas3238-hue/qore-core/actions/runs/38448311219). Confirmar firmas/digests, 19 tests, Ruff, Mypy, stage EIA NO_SUPPORT y fuente seis CME SOURCE_BLOCKED.
3. **Leer documentos base:** este handoff, QORE_RESEARCH_ZERO_BUDGET_SOURCE_FIRST_QUEUE_MASTER_HANDOFF_2026-10-13.md, QORE_CF11_EIA_REAL_PLAN_RESEARCH_TRADERLAB_CONTINUITY_2026-10-13.md, QORE_FUTURES_A_EIA_WTI_NG_F1F2_PREDICTIVE_SCREEN_EXECUTED_NO_SUPPORT_2026-10-13.md y QORE_FUTURES_A_M0_FREE_ARCHIVE_6_SOURCE_EXECUTED_BLOCKED_2026-10-13.md.
4. **NO repetir EIA backwardation→F1-up:** conservar dos hipótesis cerradas, no tocar outcomes 2022+ y no convertir referenciales EIA en PnL neto.
5. **Trabajar lo desbloqueable sin US$:** endurecer intake/prereg idempotente, validación de identidad de fuente, orden prereg/outcome y custodia de receipts; probar propuestas sintéticas (no económicamente) sin desbloquear 6 futuros.
6. **Buscar fuente solo con evidencia MATERIAL nueva:** licencia legítima sin costo, dos expiries 2012–2024, OHLCV D1, settlement/OI y as-of; si no existe, dejar SOURCE_BLOCKED y no seguir proveedores sin sustento.
7. **Para iniciar una hipótesis nueva:** separar familia, formalizar mecanismo falsable y prereg previo, confirmar capacidad de fuente y test, aplicar potencia/alpha/corrección sin tocar holdout. Con datos ejecutables y Gate de costes, conectar Trader Lab, Risk, CIBO e independencia reales.
8. **Cerrar cada trabajo:** PR DRAFT, commit SHA, Actions run/conclusion, artifact SHA y nota de bloqueantes; jamás autopromocionar a GREEN económico ni LIVE.

## 11. Enlaces de recuperación inmediatos

- [QORE Core](https://github.com/mezas3238-hue/qore-core) · [Issue #894](https://github.com/mezas3238-hue/qore-core/issues/894).
- [PR #895 fuentes](https://github.com/mezas3238-hue/qore-core/pull/895) · [PR #913 EIA](https://github.com/mezas3238-hue/qore-core/pull/913) · [PR #914 puente](https://github.com/mezas3238-hue/qore-core/pull/914) · [PR #915 CF-11](https://github.com/mezas3238-hue/qore-core/pull/915) · [PR #916 cola](https://github.com/mezas3238-hue/qore-core/pull/916).
- [Acciones fuente M0 18 tests](https://github.com/mezas3238-hue/qore-core/actions/runs/38341020091) · [Fuente gratuita EIA 12.352](https://github.com/mezas3238-hue/qore-core/actions/runs/38343102029) · [Prueba ciencia 8 tests](https://github.com/mezas3238-hue/qore-core/actions/runs/38448311219) · [Bridge 14 tests](https://github.com/mezas3238-hue/qore-core/actions/runs/38452295022) · [CF-11 13 tests](https://github.com/mezas3238-hue/qore-core/actions/runs/38454993701) · [Cola 19 tests, última](https://github.com/mezas3238-hue/qore-core/actions/runs/38459547103).

**CIERRE DE RELEVO:** entregables investigativos conservados, pruebas verdes dentro de sus alcances, presupuesto USD0. El cuello de botella económico sigue siendo contratos históricos legales y coste/ejecución, no el número de runners. No afirmar edge ni rentabilidad con precios referenciales. No afirmar QORE Research autónomo donde solo hay GitHub Actions. Mantener #916 DRAFT / no merge.

---

## 12. CONTINUACIÓN — HARDENING P1 DE IDENTIDAD/ANTI-LAUNDERING (13-OCT-2026)

**Arquitecto de continuidad:** primera modificación técnica después del handoff maestro. **Estado:** implementado y certificado solo en su alcance de tests sintéticos de integridad; no hay nuevo test de señal económica.

**Causa descubierta al inspeccionar el código real #916:**
1. `ResearchIntakeRecord` permitía crear directamente una misión base con el ID conocido pero sustituyendo `question_code`, `data_requirement_code` y/o el número de raíces (2/6); el estado de cierre/bloqueo se preservaba, pero se perdía identidad científica.
2. `register_unfrozen_proposal` permitía copiar el `question_code` de las misiones ya cerradas o bloqueadas usando otro `code`; una propuesta podía además etiquetar `eia.f1f2.reference-close-only` como dependencia de una nueva idea.
3. El límite de 20 `proposals` existía en el parser de manifiesto pero no en la API pura `ResearchIntakeLedger`.
4. Dos `code` distintos podían apuntar a una misma `question_code`, duplicando familias de pregunta bajo identidades superficiales.

**Corrección en** `src/qore/infrastructure/trader_lab/qore_research_zero_budget_intake_v1.py`: exige la identidad cerrada EIA exacta (pregunta + dato EIA + 2 raíces), identidad bloqueada Futures A exacta (pregunta + dato CME + 6 raíces), rechaza reuso literal de preguntas base o fuente referencial EIA en propuestas y rechaza preguntas duplicadas y más de 20 propuestas, incluso al construir la cola directamente en Python.

**Pruebas nuevas en** `tests/infrastructure/trader_lab/test_qore_research_zero_budget_intake_v1.py`: 5 casos adversariales, con subcasos de suplantación de identidades y reutilización de fuentes. Commits:
- `a41a168e55358532ece72d5dec3d650fd8006f5a` — lógica de barrera de identidad.
- `e87a3cd875fbe1b219da256d5dfa6e3c8053c8a3` — regresiones.

**CI probada [Actions #38476568635](https://github.com/mezas3238-hue/qore-core/actions/runs/38476568635):** SUCCESS en commit `e87a3cd875fbe1b219da256d5dfa6e3c8053c8a3`; **24/24** tests Python, Ruff PASS, Mypy PASS; ledger sigue conteniendo exactamente las dos misiones cerrada/bloqueada, sin abrir holdout, sin costos y sin trading. El checksum del ledger generado por ese job fue `e94a52d943c8f1d4e2d57dc9ccf7265f5137dcf5ac29e55e92aec9dcf52244c7`.

**Limitaciones que el siguiente arquitecto NO debe confundir con cierre:**
- Esta barrera compara `question_code` y `data_requirement_code`, **no puede descubrir paráfrasis semánticamente equivalentes** sin revisión científica; nuevas hipótesis siguen requiriendo prereg explícito previo a outcomes.
- El ledger no crea autoridad externa criptográfica por sí solo: la procedencia auténtica depende del pipeline GH Actions y la verificación de artefacto y ancestry previos al ensamblaje CF-11.
- No existen nuevos contratos CME licenciados a USD0, fills/costes netos ni trader certificado. `SOURCE_BLOCKED` y `NO_SUPPORT` permanecen intactos.
- El código no configura daemon/autoscheduler. Próximo trabajo priorizado: contrato prereg/versionado/causal independiente con fuente verificable y workflow idempotente de solo lectura. No habilitar RUN ni abrir reservas mientras la fuente siga bloqueada.

**Gobernanza:** PR #916 DRAFT/NO MERGE; sin LIVE/DEMO/órdenes, sin sizing y sin presupuesto adicional.
