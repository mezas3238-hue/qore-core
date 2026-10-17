# VT08 — Arquitecto B: R1 vinculación causal A→B y continuidad de certificación
**Fecha:** 2026-10-15 · **Fuente de verdad:** `mezas3238-hue/qore-core` · **Frente B:** PR #764 / issue #763, sin merge.

## 0. Resultado y significado
- **Código de seguridad A→B mejorado**, ver commit `4f574fea3062acc20daf475dce592f8ca95fdc5f`.
- **Pruebas adversariales añadidas** y workflow actualizado; HEAD de evidencia validada en GitHub Actions `ccc92edeed47229dcc73ed8d52acc5a6611f6e7c`.
- **CI verificada:** [run #38706444959](https://github.com/mezas3238-hue/qore-core/actions/runs/38706444959) = SUCCESS; **205 passed / 3 skipped** en suite general; **3 passed** en integración A congelada; Ruff PASS; Mypy PASS (14 fuentes). Los tres SKIP de la suite general son el módulo A opcional; su trabajo de integración se ejecuta aparte.
- **NO representa señales de mercado certificadas:** 0 señales REAL-SOURCE habilitadas por contrato A/B, 0 fills nuevos bajo cognitiva auténtica y 0 PF/DD/Sharpe/Sortino NET nuevos; `APPROVED_A_B_MANIFEST_SHA256=None`. El test positivo inyecta un manifiesto ficticio **SOLO** con `monkeypatch` en un fixture, jamás se graba en configuración de ejecución.
- **No sizing:** las métricas futuras se medirán a 1R de riesgo inicial por trade, sin ponderación, lotaje adaptativo, leverage ni compounding del Trader. CIBO/QDLE autoridad separada.

## 1. Hallazgo técnico P0 reparado
Antes de R1, `evaluate_provenanced()` revisaba source_event_id, market y UTC decision_at, pero NO comparaba todos los campos repetidos entre envelope A y Situation B. Un evento con manifiesto futuro aprobado podría emparejar un `side`, ancla NY, LTF, día NY, vencimiento, última vela o cortes individuales **diferentes**, engañando a la cognitiva aunque cada objeto pareciera internamente válido.

Ahora `_require_source_situation_binding()` fuerza antes del reasoning:
1. Igualdad exacta de **side / anchor_ny_hour / ltf_profile / ny_date** entre evento y Situation.
2. Coincidencia por **instante UTC** de `pending_expiry_at == situation.cycle_expires_at` y `latest_available_bar_close == situation.latest_available_bar_close`, protegiendo DST/fold.
3. Comparación **de todos los campos** de `cognitive_feature_cutoffs` del envelope contra `situation.feature_cutoffs`; una diferencia pasada, no solo una fecha futura, es **error**.
4. Ningún error anterior modifica el estado, crea decisión, fill, orden o terminal. `evaluate_provenanced()` sigue bloqueado si no existe manifiesto revisado; `evaluate()` permanece simulador de fixtures y debe ser cerrado para toda futura ruta real.

Evidencias:
- Código: `src/qore/infrastructure/trader_lab/vt08_cognitive_5m_consumed_gate_v1.py`.
- Tests nuevos: `tests/infrastructure/trader_lab/test_vt08_5m_a_to_b_provenance_binding_v1.py`.
- Workflow: `.github/workflows/vt08-cognitive-5m-research-bridge.yml`.
- CI negativa intermedia #38706343190: solo **orden de imports Ruff**; reparada con commit `ccc92ede...`, CI #38706444959 completamente verde. No ocultar el fallo reparado.

**Límite de R1:** coincidencia de fechas/valores y un SHA de 64 caracteres son verificaciones **de contrato**, NO autentican semántica TTrades ni la barra raw, quotes del bróker o procedencia empírica. El módulo A de la CI **está PINNED** al antiguo SHA `6e537cd8a8a01d9817802383c736baf5688f2a0f` del contrato B01 M15; los 3 PASS NO verifican la rama A actual ni el modelo M30→M3 nuevo. Este límite debe corregirse con un nuevo freeze de A revisado, nunca haciendo checkout dinámico del HEAD.

## 2. Reconciliación de identidades y economía: NO mezclar
- VT08 #763/#764: cognitiva 5 pares EURJPY, USDCHF, NZDUSD, CADJPY, USDCAD; 01/05/09 NY; max 1 fill/mercado/día NY. Proyecto metodológico TTrades propio.
- A #762/#765: autor/fuente y CandidateEvent; HEAD visto 15-Oct `1994e7a18ec04d316dd5ea1709becb8bb496090e` (mutable: volver a verificar antes de review).
- #787: trial FINAL1 histórico cerrado/superado, NO reabrir ese mismo OOS.
- #798 y #797: QORE-alpha, **identidad distinta**, no importar parámetros, outcomes, thresholds.
- QORE proxy M30→M3 NO-GO: PF bruto posicional ~0,964; no concluye sobre TTrades original y no autoriza retuning posterior.
- Gates históricos VT08: PF >=1,80; DD <=6R; MC p95 DD <=15R; probabilidad positiva MC >=0,90; mean R >=0. Gate de un trial previo: 100 fills y PF NET >1,15. Los nuevos umbrales de **Sharpe, Sortino, densidad y eventualmente DD%** requieren acta **por versión**, firmada antes de abrir OOS. No usar umbrales de Alpha por conveniencia.

## 3. Entregables concretos solicitados al Arquitecto A (#762)
**Primero texto fuente congelado y adjudicación independiente; no código A como oráculo de B**:
1. **Identidad de familia** elegida para la nueva versión autor-fiel, no derivada de PF: escenario, direcciones, C1/C2/C3, LTF, ancla, source-day, entry, cancel/expiry, stop, target, manejo; clasificar A fuente explícita / B inferencia / C contención QORE / D ambiguo, con URL, cita y fecha/timestamp.
2. **Swing relevant que clasifica EQ de C2:** identificar y comprobar antes de abrir C2 el swing que decide WITH/AGAINST; `source_bar_id`, fuente y SHA del raw, `closed_at`, `available_at`; una pivote confirmada después no sustituye la precondición.
3. **POI significativa:** selector causal y empate cuando hay múltiples FVG/swing high/low/OB, sin inventar ATR o distancia; **breaker-low exacto** y stop LONG **menor que ambos** EQ M30 y breaker low, con buffer broker no supuesto; **target HTF untouched** seleccionado antes del movimiento.
4. **CISD/PS M3** auténticos: secuencia opuesta, OPEN de referencia, close confirmatorio, PS y timestamps; demostrar reloj M30 C2→M3 C3 y LTF M3 causal, sin volver a usar el perfil estrecho M15 como equivalencia universal.
5. **Situations verdaderas 27+ campos:** cada campo con valor semántico, fuente primaria/derivación, `source_bar_id`, `source_sha256` verificable contra raw, `closed_at`, `available_at`, `decision_at`, `semantic_authority` A/B/C/D, market y versiones; también atributos UNKNOWN y contrarios. No basta el mapa de timestamps ni SHA inventado.
6. **Un candidate stream completo, incluidas las negativas**, sin filtrar ganadoras: stable source_event_id, snapshot IDs, no duplicate per market NY day, no múltiples familias elegidas ex post. Separar SHAPE, order, bid/ask fill, exit y costs, ninguno derivado desde `EXECUTE`.

A debe entregar ejemplos positivos y negativos de fuente **ANTES** del código/pnl, evidencia de la partición realmente no consumida y propuesta exacta de candidato versionado y hash. Donde haya D que afecte la entrada, **NO_ESPECIFICABLE / NO_EVALUABLE**; B no emite firma A/B por escribir código verde.

## 4. Próxima cola B — sin cambiar el método
**B-P0.2:** revisión independiente del texto A y casos contradicción/ambigüedad, reconstrucción raw de ejemplos M3/M15, sin código A como oráculo. Verificador de `field_source_sha256` frente a datos canónicos, modelo de dependencias por campo, igualdad semántica, fault injection y false negatives.

**B-P0.3:** aislar definitivamente `evaluate()` sintético en ruta fixture-only y dejar ingreso de datos reales exclusivamente por `evaluate_provenanced()`; añadir cobertura negativa. No promocionar la API fixture porque resulte EXECUTE.

**B-P0.4:** WAL/SQLite ledger durable / recuperación completa de hipótesis y fill/terminal, reinicio, dedupe por event_id/fill_id, race de mercados y orden por timestamp UTC; no declarar solucionado por test en RAM.

**B-P0.5:** comprobar cobertura cognitiva 100% en candidates reales (incluidos WAIT/ABSTAIN), WAIT→EXECUTE, KILLED sin resurrección, candle por candle en trayectoria post-fill, no exits inventados, first SL/TP con fuente externa.

**B-P1.1:** realizar contraste apareado mismo evento metodología A vs A+Cognitiva B **con BID/ASK y comisiones auténticas**, retornos netos en R igual exposición, PF/DD/Sharpe/Sortino según acta congelada; Gate OOS/STRESS/MC/WFO y validación independiente de C. Certificación solo si TODOS PASS.

## 5. Separación de autoridades
B no cambia reglas TTrades/entradas ni toma autoridad de riesgo; A no reescribe cognitiva; autoridad matemática PF/DD/Sortino independiente de programar el razonador. No merge, no VPS, no DEMO/LIVE, no 7Y sellado, no exposición de credenciales, no SIZING. Este reporte es **R1 avance de ingeniería** y continuidad; **NO es una certificación ni autoriza operaciones**.
