# GATE A — LON-A: prueba de vínculo causal H4↔M15 sin certificar swing ni trades

**Fecha:** 2026-10-11. **Issue:** [#785](https://github.com/mezas3238-hue/qore-core/issues/785). **PR:** [#788](https://github.com/mezas3238-hue/qore-core/pull/788). `GATE_A_PARTIAL / NO_TRADER / NO_ECONOMIC_REPLAY / NO_LIVE`.

## 1. Prioridad original y reglas distinguibles

**LON-A artículo autoral de Londres, 12-sep-2026**: https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/ — apartados «Use The 4 Hour Candle», «Confirm The Swing On The 15 Minute» y «How To Trade The Model». Describe Daily→H4 wick/swing→M15 CISD y protected swing→continuación. **No** autoriza escoger a posteriori cualquiera de las rachas de velas que cruzó primer-open.

**CISD original, 29-jun-2025**: https://ttrades.com/understanding-the-change-in-state-of-delivery-cisd/ — sección «What Is The Change In State Of Delivery»: en secuencias alcistas/bajistas, el cierre cruza el **open de la primera vela**. El hecho aritmético `close > first_open` o `close < first_open` no selecciona automáticamente la **serie que hizo el swing**.

**Confirmación del swing, 10-ene-2026**: https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/ — «How I Use CISD With Swing Points», «CISD Without A Higher Time Frame Closure Means Nothing» y «The Fractal Nature». Requiere cierre C2/C3 HTF + CISD LTF dentro de la vela, no CISD aislado.

**Ambigüedad que no se puede resolver por programación:** 
- Revisión retrospectiva: HTF cierra a `tH4`; CISD dentro de HTF cerró a `tM15 < tH4`; la primera decisión capaz de exigir ambos es `max(available_at(H4), available_at(M15))`. El precio en `tM15` no es ejecutable desde el instante `tH4`.
- Provisionalidad: operar con H4 todavía abierta es hipótesis separada; sin prueba autoral específica, no se llama `TTrades fiel`.
- El texto no permite fijar de forma única pivot right bars, wick completion, entry inmediato o retest, stop buffer, ejecución BID/ASK, DOL target ni expiración.
- La afirmación `C2` o `C3` de un productor de datos **no prueba** por sí sola un cierre válido. Se requiere oracle independiente y ejemplos negativos de fuente.

## 2. Nuevo contrato de ingeniería de investigación — no estrategia

[Auditor H4/M15 first-online](https://github.com/mezas3238-hue/qore-core/blob/research/london-lona-gate-a-primary-evidence-20261011/src/qore/infrastructure/trader_lab/qore_london_lona_swing_h4_m15_link_audit_v1.py) consume sólo evento **M15 observacional** + referencia **H4 cerrada**. No usa PnL, backtest ni ejecuta trades. Todos los certificados finales permanecen `false`.

Comprueba:
1. Timestamp ISO/UTC explícito, H4 con duración exacta de 4h, `first_known_utc >= bar_close_utc`, decisión posterior al cierre conocido.
2. Serie M15 y confirmación enteramente **dentro** de H4 referenciada, `first_known_M15 >= close_M15`, orden temporal correcto de serie/cierre.
3. Símbolo EURUSD/GBPUSD, mismo `provider_id`, y extremo de serie dentro del rango high–low H4 suministrado.
4. Marca `MULTIPLE_SERIES_NOT_ADJUDICATED` y `EXTREME_EXTENDED_BEFORE_CROSS_NEEDS_AUTHOR_REVIEW` sin elegir por beneficio.
5. Emite `decision_not_before_utc`, nunca `entry_price`/fill. Una etiqueta upstream `C2`/ `C3` queda `h4_c2_c3_label_unverified=true`.

**Limitaciones fundamentales:** el `provider_id` es autodeclarado y no una firma; no se demuestra feed completo con este guard. La geometría del indicador se recibe de otro módulo (que sólo enumera secuencias candidatas). Los campos `closure_claim` y rango H4 tampoco certifican que la vela sea la C2/C3 válida del autor. La comprobación «serie íntegramente dentro H4» es **política conservadora QORE**, potencialmente más estricta que el autor, y debe contrastarse con ejemplos reales.

**Verificación GitHub:** [workflow #38173569548](https://github.com/mezas3238-hue/qore-core/actions/runs/38173569548) `SUCCESS`, **25** pruebas guard temporal + **21** pruebas observador CISD + **20** pruebas vinculación H4/M15 = **66 tests sintéticos**. Solo demuestra que estos invariantes pasaron los fixtures.

## 3. Dictamen formal de fidelidad

`CANONICAL_LONDON_TEXT_IDENTIFIED` — Sí.

`M15_FIRST_OPEN_FORMULA_AUTHORIAL` — Sí, en su ámbito de secuencias identificadas.

`UNIQUE_SWING_FORMING_SERIES_SELECTOR_AUTHORIAL` — NO, no adjudicada.

`HTF_C2_C3_CLOSURE_DETECTOR_AUTHORIAL` — NO; etiqueta externa no autentica geometría ni condición.

`FIRST_ONLINE_CHRONOLOGY_INVARIANTS_SYNTHETIC_VERIFIED` — SÍ, solo módulo de infraestructura.

`PROTECTED_SWING_AUTHOR_EXACT_CERTIFIED` — NO.

`ENTRY_STOP_TARGET_AUTHOR_EXACT_CERTIFIED` — NO.

`ECONOMIC_REPLAY_AUTHORIZED` — NO.

**Siguiente paso permitido:** obtener escenas de vídeo/capturas fechadas (incluso ejemplo sin operación); adjudicar dojis, rachas solapadas, fallo y extensión del extremo, H4 con mecha parcial, y C2/C3 con cierres reales *first-known*. Si falta fuente unívoca, reportar `AUTHOR_UNDERDETERMINED` y, solo con preregistro propio posterior, `QORE_VARIANT`. Nunca seleccionar el detector por PF.
