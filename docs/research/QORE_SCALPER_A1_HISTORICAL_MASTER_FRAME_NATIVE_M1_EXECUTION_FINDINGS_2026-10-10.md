# QORE Scalper — Auditoría histórica nativa M1 para integración real Master Frame

**Fecha:** 2026-10-10 | A1 cognitiva PR #758 (DRAFT) | Peer A2 metodología PR #759 | Maestro PR #623. Trabajo exclusivo GitHub Actions; sin VPS, MT5, operaciones live ni merge.

## Mandato explícito y veredicto verificable

El Owner ordenó ejecutar el replay económico histórico **de la cognitiva potente completa**, después de la integración demostrada de `build_master_cognitive_frame` en el selector real de Trader y el runner PAPER A1. Se inició directamente un chequeo causal sobre los artefactos históricos nativos publicados y se lanzó un segundo proceso de **observación real de nueve mercados M1 sincronizados**.

**No se puede certificar ni calcular legítimamente PF/DD de la cognitiva completa todavía**: en las evidencias históricas ya almacenadas faltan inputs obligatorios de mundo/regímenes/estructura. Atestar un estado `WELL_SUPPORTED`, ausencia de posiciones o percepción `GOOD` sin evidencia sería reconstruir el mismo error diagnosticado en V50-G. El código falla/declara bloqueo de manera auditable, preserva todas las oportunidades y NO elige una submuestra favorecedora por hindsight.

### Ensayo 1: nueve libros fuente V49 vs nueve libros de sensores provider-native M1

[Run #38080396264 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38080396264), con 3 tests + Ruff/Mypy correctos. Pinned:
- V49 9-market economic control [#38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695), commit `e356e7a52541e99533b25ecfef0ab9c4e9ce03c0`.
- Sensores M1 as-of [#38071138991](https://github.com/mezas3238-hue/qore-core/actions/runs/38071138991), commit `74f4d9c89cdaaefd220a9a45ba98c2a0376be3d7`.

**Fuente:** 9/9; **2.876/2.876** `source_opportunity_id` conciliadas, sin desajustes temporales de vela; **381/2.876** divergencias CISD preservadas. Observables críticos:
- `ACTUAL_M15_STRUCTURE_REVALIDATION`: **2.876 NOT_AVAILABLE**.
- `M1_PROTECTED_SWING_ATTESTATION`: **2.876 NOT_AVAILABLE**.
- `H1_TARGET_ROOM_R`: **2.876 NOT_AVAILABLE**.
- `FULL_COGNITIVE_MASTER_FRAME`: **2.876 NOT_AVAILABLE**.

Estas ausencias describen el alcance del panel A2: **no demuestran que el source V49 M15 o H1 fuera inválido** ni que 2.876 señales deban bloquearse. Sólo demuestran que el panel no atestó esos datos de forma independiente. Prohibido hacer veto automático ante el mismatch CISD porque el ensayo previo 1.910 trades/DD 252.10R empeoró frente a V49 DD 236.13R.

`capitalizer_a1_historical_full_frame_preflight_v1.py` + workflow `qore-scalper-a1-nine-market-full-frame-preflight.yml`: reconcilia hash fuente, H1/M15/M1 cronología y todos los sensores, rechaza entradas duplicadas/ajenas/futuras y devuelve formalmente `BLOCKED_MISSING_NINE_MARKET_CAUSAL_WORLD`, NO un falso resultado de trading.

### Ensayo 2: nueve datos provider-native M1 sincronizados exactamente en las decisiones V49

[Run #38080367716 — **11/11 SUCCESS**](https://github.com/mezas3238-hue/qore-core/actions/runs/38080367716), SHA `435e2369f1ed94d7130d328115d2402dcd4e5b84`; artefacto [summary #11680232462](https://github.com/mezas3238-hue/qore-core/actions/runs/38080367716/artifacts/11680232462). Las nueve fuentes raw-M1 provienen del archivo nativo oficial [#35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), SHA `18c338aedd5013ce65a6cb6408ffbc2e904a6217`, con manifest leído: `provider_native_m1=true`, no `synthetic_m1` ni `interpolated_m1`, solo lectura.

`capitalizer_a1_native_nine_market_bar_witness_v1.py` construye el censo de **todos los instantes originales**, no solo trades seleccionados. Para cada timestamp cierra únicamente velas M1 que `closed_at <= decision_at`, con join determinista y sin backfill ni fabricar BID/ASK. Distribución observada:
- **2.876** oportunidades fuente V49 → **2.822** instantes únicos de decisión.
- **2.791** instantes tienen exactamente **9 de 9** velas M1 nativas cerradas contemporáneamente.
- **24** instantes tienen 8/9 mercados con vela M1 del mismo instante.
- **7** instantes tienen 7/9.
- Total **31** instantes sin dato exacto para al menos un mercado, conservados como `has_exact_predecision_m1=false`, nunca suplantados por una vela del futuro o quote simulada.
- Ausencia **de verificación BID/ASK**, **regime attestation**, cross-market causal graph y ledger económico de posiciones as-of. Ninguna M1 OHLC basta para inferirlos.

Las nueve salidas JSONL por mercado y los 2.822 timestamps están archivados como GitHub Actions artifacts en ese run. La evaluación de `M1` es **evidencia auténtica**, pero NO sustituye régimen, causalidad H1/M15 ni telemetría de cartera.

### Estado de pruebas de la rama

[QORE Scalper Cognition Audit #38080396277](https://github.com/mezas3238-hue/qore-core/actions/runs/38080396277) **SUCCESS**, Ruff repo, Mypy **1.640 archivos**, **57/57** pruebas cognitiva. Además los nuevos workflows prueban sus propias verificaciones, incluidas 3 pruebas fail-closed para libros históricos y 2 pruebas de sincronizador M1. El **Master Frame→Trader sí afecta intentos de PAPER en tests de integración** previos, pero en el dataset nativo real falta todavía completar los contratos fuente y mundo.

## Mandato P0 restante y asignación A1 / A2

**A1 (cognitiva):** enlazar cada una de las 2.822 barreras M1 reales con `CapitalizerGlobalWorldModel`, percepciones honestas, régimen derivado de hechos y no de etiquetas, cross-market edges as-of, `CapitalizerCognitivePressureFacts`, session ledger y posiciones elegidas realmente abiertas/cerradas; nunca fabricar `quote_fresh=True` a partir de OHLC ni `KNOWLEDGE.KNOWN` sin evidencia. Consumir los nueve artifacts nativos del run nuevo. Cuando un input no pueda corroborarse, resultado por candidato debe ser UNKNOWN/WAIT con WHY, no silenciosamente caer del denominador.

**A2 (metodología):** producir un ledger **atestado sin hindsight y uno-a-uno por source ID** para origen/confirma H1, protected M15 pivot y stop, target room H1 con timestamp causal, primera ruta M1 CISD y criterio de simultáneos; adjudicar 381 divergencias sin imponer rechazo global. Clarificar ingeniería QORE vs TTrades/ICT. No adivinar ni rellenar fuente H1 expiración futura.

**Integración/paper:** solamente una vez que ambos ledgers causales coexistan, ejecutar `run_sensorized_master_frame_paper` / Trader selecciones bajo los mismos 2.876 IDs, memoria *chosen-and-settled-only*, risk QORE y los nueve mercados nativos, frente a las 2.020 ejecuciones del control. Preregistrar A/B y ablations, contar `PASS`/WAIT/ABSTAIN y selección MAX3 por fuente; computar verdadero PF/DD/Sharpe/Sortino y retención (>=934 ganadores originales y >=415.748485649R de masa de ganadoras originales). Separar gross de BID/ASK+commission physical net.

### Prohibiciones y certificación

No afirmar que los PF/DD históricos V49 (PF 0.664/DD 236.13R) o V50-G (94 trades) midan el efecto del nuevo Master Frame. No fingir PF o DD cuando el resultado nativo es una **auditoría de insumos bloqueada**; `measured_cognitive_pf=null`, `measured_cognitive_drawdown_r=null`. No abandonar 31 instantes con falta parcial de vela ni las 381 discrepancias CISD. Ninguna acción VPS/MT5/LIVE, ningún merge de PRs draft y **Scalper NO CERTIFICADO**.

**Resultado real entregado:** nueva sincronización física 9 mercados/2.822 instantes, cuatro bloqueos específicos cuantificados 2.876/2.876, fuente conservada y Actions verdes. **Replay PF/DD del Master Frame real completo NO ejecutado** porque faltan input de cognitiva causal exigidos; el output publicado identifica exactamente por qué.
