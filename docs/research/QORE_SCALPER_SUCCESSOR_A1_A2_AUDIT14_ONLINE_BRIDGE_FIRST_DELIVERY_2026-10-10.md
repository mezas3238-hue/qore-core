# SCALPER sucesor — entrega 1: frontera causal Audit14 (B) -> A1

**Estado:** RESEARCH/PAPER only; no merge, no VPS, no MT5, no LIVE, no certificación.
**Ramas:** A1 `agent/scalper-architect-a-cognition-20261010` HEAD `a84391a9ff27113fb85688f6e8d5c3b1d384e28c`; B `agent/scalper-architect-b-methodology-20261010` HEAD observado `17a92ded3f52f474009ad9d4e5fda6676b28317a`.
**Por qué nueva rama:** la rama A1 original queda sin escritura concurrente; este PR de sucesor apunta a ella para revisión, sin mezclar B silenciosamente.

## Problema concreto confirmado por revisión de código

El puente A1 `capitalizer_a1_sensorized_paper_runtime_v1.py` compara `EntrySensorInput.decision_at` con `barrier.observed_at` y `m1_bars[-1].close` con el `V49EconomicTrade.entry_price`. El PAPER A1 `capitalizer_a1_master_frame_paper_trader_integration_v1.py` además verifica `binding.confirmed_at == trade.entry_at` y simula solo fills V49 congelados. Es correcto para fixtures V49, **pero NO permite atribuir al Master Frame el resultado económico first-online de B**, que mueve reloj, familia, precio, SL/TP, sesión potencial y cartera MAX3. **No eliminar esas barreras mediante un bypass**: antes hace falta una vía causal independiente del baseline económico.

El Audit14 de B (`capitalizer_scalper_a2_fourteenth_causal_first_economics_v1.py`) contiene por ID original campos **as-of** (primera entrada, familia, precio close, stop M15, target H1) mezclados en una misma fila JSON con `original_gross_r`, `candidate_gross_r` y `candidate_exit_reason` FUTUROS. No es admisible entregar la fila entera al cerebro.

## Cambio implementado en este PR

- `capitalizer_a1_audit14_online_predecision_bridge_v1.py`: lee el esquema **exacto** de Audit14, concilia source hash V49 y campos de H1/M15, valida que el primer evento de investigación no fue anterior a H1/M15 ni posterior al V49 original, confirma reglas de status diagnósticas y geometría básica de stop/target antes de crear `A1FirstOnlinePredecisionWitness`.
- La proyección no transporta `h1_state_until` (fin conocido retrospectivamente), realized R, exit reason, MFE/MAE, la condición de ganador o decisiones de Risk/CIBO. Variar resultados ex-post deja el witness idéntico. Cambios de schema sin revisión independiente fallan cerrado.
- `reconcile_audit14_online_witnesses` exige igual conjunto de IDs sin duplicados; modo full exige **2876 y nueve mercados**. Las `36 INVALID_M15_STOP` y `24 NO_H1_TARGET` son estados informativos de la reconstrucción source-anchored; **no** se convierten automáticamente en veto de metodología cognitiva.
- Se registra explícitamente `source_universe_regenerated=False`, `master_frame_invoked=False`, `physical_bid_ask_present=False`, `paper_trades_executed=0`. Este contrato NO proporciona todavía PF/DD ni entrada nueva.

## Resultados base previos (verificados en handoff y evidencias B, NO re-medidos por este PR)

| Métrica | V49 | Audit14 first-online bruto source-anchored |
|---|---:|---:|
| Source IDs | 2876 | 2876 |
| Candidatos válidos pre-MAX3 | 2876 | 2816 |
| Ejecutados MAX3 | 2020 | 1997 |
| PF bruto | 0.664463 | 0.842524 |
| DD máximo en R | 236.134 | 114.799 |
| Resultado neto bruto R | -233.269 | -109.055 |

No se han ejecutado estos 2876 source IDs con el nuevo bridge todavía. Las pruebas añadidas son **fixtures negativos** del contrato, no 9/9 histórico.

## P0 siguiente — responsabilidad conjunta A1/B, antes de ejecutar full cognition

1. Ejecutar contrato contra Audit14 real 2876/9/9 con Actions, source manifest/hashes pin y output sin ex-post. Registrar cuántos estados por mercado y 1090 diferencias first-online / 381 subset. Si no reconcilia, **detener promoción**, investigar esquema o temporalidad; no modificar baseline para forzar verde.
2. B reconstruye universo **H1 -> M15 -> M1 bar-by-bar** no anclado a las 2876 fuentes; causalidad de POI autor, protected swing, C2/C3 y primera CISD. 2638 C2 + 238 C3 source, 2372 con doble H1 full 60/60, 504 PARTIAL, 152 offclock sin M15/M1 prematuro son testigos QORE, NO certificación autor.
3. B publica cada oportunidad con cierre observable, native bar hash, nueva economía por orden de portfolio MAX3 y costos físicos BID/ASK/comisiones. El primer evento debe congelarse al primer cierre confirmatorio, con desempate multi-ruta explícitamente `QORE_ENGINEERING_RULE` cuando el autor no lo define.
4. A1 adapta el consumidor al **nuevo** evento/ejecución realmente recalculado, sin fingir equivalencia con el trade económico congelado V49. Construye nueve snapshots sincronizados, regímenes respaldados, grafo/pressure físico y memoria de posiciones **chosen + settled only**. No derivar entradas de resultados futuros.
5. A/B cognitivo preregistrado: denominadores de fuente **y** nuevo universo, barreras 2822 históricas de fuentes originales como control, PASS/WAIT/ABSTAIN, selección y fills netos, PF, expectancy, DD, retención de IDs/ganancias R originales y densidad, bootstrap por día/mercado, OOS independiente. Congelación de capas World Model nuevas sigue vigente hasta causalidad y fidelidad.
6. En caso de ambigüedad, consultar DeepSeek para *hipótesis falsables*; verificar texto original de TTrades y probarlo con GH Actions. DeepSeek no promueve ninguna regla ni tiene acceso automático a secrets.

## Riesgo de coordinación detectado

PR #758 y #759 aparecen abiertos como DRAFT, pero sus descripciones dicen que fueron sustituidos por #760/#761. Al consultar #760/#761 estos aparecen **cerrados**, con SHAs antiguos. Por eso este PR apunta a **A1 #758 abierta** (y se notifica a B #759), sin fusionar ni interpretar la descripción como autoridad suficiente. Aclarar qué PR representa a cada arquitecto antes de cualquier merge.

**Dictamen:** mejora de trazabilidad e aislamiento cognitivo, no mejora económica demostrada. Scalper sigue NO CERTIFICADO.
