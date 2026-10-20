# VT08 A — DICTAMEN M30→M3: AUTORIDAD STOP EQ+BREAKER PASA D→A (REGLA), EJECUCIÓN SIGUE D

**Fecha:** 2026-10-11, arquitecto metodológico A, PR #765, issue #762, B #763, parent #634. Solo GitHub, no VPS, 7Y sellado intacto. **VEREDICTO: NO CERTIFICABLE.**

## 1. Hallazgo primario que corrige al auditor

TTrades [Timeframe Alignment, 30-jul-2025](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/), sección EXACTA **Example 1 – 30M to 3M Intraday Reversal**, contiene **en la página escrita accesible** la oración con: *"stop below the EQ of the 30 minute candle as well as below the breaker low"*. **A FUENTE para ejemplo alcista M30→M3**. No hace falta especular sobre vídeos no indexados. No significa que se aplique a todo bearish, H4 ni a todos los setups.

**TTrades [Trading Breaker Blocks for Continuations, 03-ago-2025](https://ttrades.com/trading-breaker-blocks-for-continuations/)** define bullish breaker low→high→lower low→higher high, y elegir *up-close candle series* anterior a lower low; el low exacto del breaker del ejemplo M30→M3 **NO** ha sido identificado inequívocamente mediante la secuencia QORE (cuatro M3 de una sola barra cada uno es PROXY C, sin evidencia de esa serie de velas up-close).

**TTrades [Stop Loss Mastery, 07-ago-2025](https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/)** establece PS low/high como stop general, pero no revoca el ejemplo específico EQ+breaker M30→M3. El antiguo stopped-at-PS de QORE no es implementación demostrada de este ejemplo.

**TTrades [POI priority, 18-jul-2026](https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/)** fuente A: desde PS hacia actual range, FVG primero, luego swing high/low y último CISD retest. La jerarquía es A escrita. La relevancia exacta de un POI y desempate multi-FVG/varios swing/canonical PS siguen D. **[Using EQ in Continuations, 02-ago-2025](https://ttrades.com/using-equilibrium-in-continuations/)** menciona además order blocks y protected highs/lows como supporting POIs. No eliminar OB con jerarquía de solo tres tipos.

**TTrades [EQ intra-C2, 10-oct-2026](https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/)**: fuente A para dos fórmulas alternativas, pero swing point autor válido y su relación con C2 sigue D. Un external pivot conocido antes de C2.open NO representa por sí mismo un swing validado a propósito de EQ.

**TTrades [Internal & External Liquidity, 22-ago-2026](https://ttrades.com/internal-external-liquidity-using-the-ttrades-fractal-model/)**: geometría external pivot de tres velas, con right.closed_at como primera fecha disponible, es A pero no prueba POI o validez de EQ. La reacción/familia C2-C3+CISD sigue siendo obligatoria.

## 2. Correcciones de implementación PUBLICADAS

- **Contrato nuevo** `src/qore/infrastructure/trader_lab/vt08_5m_a_ttrades_m30m3_stop_authority_contract_v1.py`: separa `stop_condition_written_a=True` de `source_eq_reference_swing_valid=False`, `source_breaker_low_adjudicated=False`, `source_poi_significant=False`. Regla matemática del ejemplo alcista estricta `stop<eq_m30 AND stop<breaker_low` solo si fuente de ambos niveles *ya verificada*; el módulo no acepta ni retorna permiso de orden. Expone candidato EQ full/candidate EQ close-to-low como **alternativas sin selector A** y estado `BOTH_EQ_AND_BREAKER_UNADJUDICATED`. Un pivote conocido antes de C2 no cambia ese estado.
- `observed_bullish_breaker_shapes`: **PROXY C** de cuatro M3 cerradas consecutivas con low→high→lower low→higher high; todas confirmadas antes de la decisión; no elegir "breaker low" ni aceptar como stop.
- **Productor anterior corregido** `src/qore/infrastructure/trader_lab/vt08_5m_a_native_m30_m3_favorable_entry_v1.py`: cada registro ahora incluye `stop_basis=QORE_PS_ONLY_PROXY_C_NOT_AUTHOR_M30_EQ_BREAKER`, `author_m30_eq_breaker_stop_proven=False`, `author_eq_reference_swing_asof_proven=False`, `author_breaker_low_asof_proven=False`. Los 42–45% de riesgo bruto anterior siguen siendo estudio de PS-only y NO comparativa certificada del stop original del autor.
- **Auditor independiente de mercado** `src/qore/infrastructure/trader_lab/vt08_5m_a_author_stop_gate_market_audit_v1.py`: vuelve a consumir la matriz M30/M3 independiente de datos nativos, no confía en bool fuente completo ni reescribe history as-of; distingue rule A vs breaker proxy C y POI D, reserva bearish para autoridad específica. 
- **Prerregistro antes de resultados** [VT08_A_AUDITOR_STOP_AUTHORITY_AND_POI_PREREG_2026-10-11.md](VT08_A_AUDITOR_STOP_AUTHORITY_AND_POI_PREREG_2026-10-11.md), commit `68d7e6fc82d631a42f81af6bedb04f645a1d0717`.

## 3. CI real 1095d M3+M15 — cinco FX, cero fills

[GitHub Actions **#38148776547**](https://github.com/mezas3238-hue/qore-core/actions/runs/38148776547) **SUCCESS 5/5**, exact SHA ensayado `3eea172e02f9b2c9607ddc86829c186f1553c778`. Ruff verde, **12 pruebas adversariales por par ×5 = 60 PASS** y M3/M15 históricos consumidos previamente en run #35941643396 y #35934924907; no toca sealed 7Y ni VPS.

| Mercado | Geometrías M30/M3 previas | CisD/PS fuente M3 nuevamente reconstruido con H1 | Long, regla escrita A pero EQ+breaker D | Pivote low pre-C2 geográfico (subconjunto) | 4-M3 breaker shape QORE proxy (subconjunto) |
|---|---:|---:|---:|---:|---:|
| EURJPY | 1895 | 1893 | 924 | 209 | 755 |
| USDCHF | 1751 | 1751 | 817 | 179 | 660 |
| NZDUSD | 1794 | 1794 | 919 | 178 | 742 |
| CADJPY | 1790 | 1789 | 869 | 167 | 709 |
| USDCAD | 1752 | 1752 | 877 | 188 | 702 |
| **TOTAL** | **8982** | **8979** | **4406** | **921** | **3568** |

- 3 H1 SOURCE INCOMPLETE permanecen NO ADMITTED; 4.573 geometrías short requieren fuente específica y no se "invierte" el stop del ejemplo long sin verificación. 
- **921** tienen geometría pivote bajo previo; **3568** tienen al menos una secuencia de 4 M3 compatible con el proxy reducido. Estos subconjuntos NO son independientes, no se suman y NO representan "swing EQ valid" ni breaker author. No concluir que se pueden calcular stops según autor.
- **0** `candidate_events_source_complete`, **0** cognitive approved, **0** orders, **0** fills, sin PnL, PF/DD, sin retest broker BID/ASK. Las 8982 siguen siendo geometrías.
- 105 H4 C2 dual sweep antiguos permanecen D y **excluidos de source complete**, no confundir con doble sweep M30. 36 body-engulf y 129 CISD proxies anteriores mantienen C, no source A.

**GitHub ZIP, 30 días:**
- EURJPY `11706405755` SHA256 `99c88624fae84ae535992e78f1396eb8a5a6ffe59ff1dd6b2e89e0b7e1a74c65`
- USDCHF `11705766662` SHA256 `a41c6c3f5dddadc36c14533dc29305ed9ad1d76db0fae6e5cc95fc2cc0d46dd7`
- NZDUSD `11706091283` SHA256 `09de6ffaa127fa8f24e7d5a7717d808e01b07463ac7524bab5a7ffe795bd61f1`
- CADJPY `11706141175` SHA256 `f31473710fa0ffe24301d622cba007871fc27b191d3bef995734414ec5380ca6`
- USDCAD `11706365878` SHA256 `65aa57144ed2c468729e77a4bf3e42748f87f26181e7595ce5ddd221c032951a`

## 4. Decisión formal dual sweep y lógica futura

**Adjudicación policy A del arquitecto QORE, NO regla TTrades:** `DUAL_SWEEP_UNADJUDICATED` permanece INEXEQUIBLE y excluido de certificación para H4/M30. Si se desea test "último CISD gana", deberá ser nueva hipótesis QORE C preregistrada para investigación, sin mezclarse con método TTrades.

La cadena producer→verifier→cognitive continúa fail-closed hasta probar:
1. Identidad estructural del swing reference **known BEFORE C2.open**, validado como swing del modelo y no simple external pivot; de lo contrario EQ intra-C2 y stop EQ tienen D.
2. Breaker block autentificado desde estructura del autor y up-close series M3, low real registrado antes M3 entry; el four-bar proxy no alcanza.
3. POI válido significativo por familia basado en prioridad source, reacción y CISD/PS con timestamps de cierre M3; no FVG touch o H1 pivot aislado como candidato.
4. BID/ASK y spread fees tick/as-of y situación cognitiva completa 27+ campos, A→B manifest aprobado y firmado. Nunca prometer densidad operativa a partir de shapes.

**Próximo paso priorizado:** no ampliar más proxies M3; establecer muestras fuente del autor para definir el vínculo reference swing→C2 y validar broker STOP/POI; solo entonces medir candidates→signals→trades→PF/DD. 
