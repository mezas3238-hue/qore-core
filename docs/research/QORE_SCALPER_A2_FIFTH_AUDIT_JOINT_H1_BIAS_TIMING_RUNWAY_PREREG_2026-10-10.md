# QORE Scalper — quinta auditoría independiente: diagnóstico conjunto sesgo H1, timing M1 y horizonte de sesión

**Fecha**: 2026-10-10. Arquitecto B metodología, PR #759 / issue #757; colaboración arquitecto A cognitiva PR #758 / issue #756, matriz padre PR #623.  
**Misión**: diagnosticar causas de resultados V49 sin cambiar una sola entrada, salida, target, stop, sesgo, MAX3 ni construir filtros del futuro. **Solo GitHub Actions, NO VPS, NO LIVE, NO CERTIFICACIÓN ni merge.**

## Contexto congelado

- Control V49 9 mercados, fuente nativa provider M1 [Actions #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), SHA `18c338aedd5013ce65a6cb6408ffbc2e904a6217`; matriz económica [#38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695), SHA `e356e7a52541e99533b25ecfef0ab9c4e9ce03c0`: 2876 source oportunidades; 2020 MAX3 seleccionadas, 1167 wins, PF bruto 0.66446, net -233.269R, DD 236.134R.
- MFE/MAE nativo M1 V49 ya reconstruido 9/9 en [#38057290884](https://github.com/mezas3238-hue/qore-core/actions/runs/38057290884) SHA `6ca33be13e23cdcb5288f40a5326955ab1274215`. La última vela de salida tiene secuencia intrabar desconocida: se separan MFE/MAE PREterminal del máximo/mínimo OHLC final observacional.
- Reemplazar target reciente por primer swing H1 externo confirmado [#38061448754](https://github.com/mezas3238-hue/qore-core/actions/runs/38061448754) duplicó target planned mediano 0.443→1.025R, pero empeoró net (-233.27→-277.61R), DD(236.13→279.56R) y retención del R original ganador (83.9%). Nueva jerarquía **NO PROMOVIDA**.
- Sweep+CISD M1 existente exige close a través de serie de velas opuestas, probado LONG y SHORT con mecha NO suficiente; no se toca esa ruta.

## Cinco preguntas ex ante, diagnóstico, no selección

**H12 sesgo:** ¿La dirección H1 en el momento de entrada es coherente con el **cierre** de precio 15/30/60 minutos después, en ventanas completas M1 que no rebasen la sesión? Se mide por signo del cambio de precio en dirección del sesgo, nunca `WIN_RATE = H1_DIRECTION_ACCURACY`. Los cierres que suceden después del STOP/TARGET original son **etiquetas retrospectivas contrafactuales de dirección**, NO ganancias alcanzables, ni parte de la entrada.

**H13 timing horario H1:** Fracción `(entry_at - floor_h1_hour)/60m` (FIRST, MIDDLE, LAST tercio de reloj); exacta, observable en el cierre M1. No inferir que el tercio horario sea el tercio del **rango FINAL** de H1. La vela H1 continúa abierta durante el trade.

**H14 ubicación de precio H1 observable:** calcular `(entry-low_observed_so_far)/(high_observed_so_far-low_observed_so_far)` LONG, inverso SHORT sobre **SOLO M1 cerradas** entre el inicio de la H1 vigente y `entry_at`. Porcentaje de rango parcial observado `FIRST/MIDDLE/LAST`, no rango final que sería future leak. Sin barras antes del instante o rango plano → `UNDEFINED_RANGE`, nunca inventar percentil.

**H15 runway sesión:** minuto de salida de bucket NY del reloj DST-aware: Asia 20:00–02:00 NY; Londres 02:00–08:30 NY; Nueva York 08:30–16:00 NY. Medir minutos **conocidos a la entrada** hasta esa frontera; bandas predefinidas <30, 30–60, 60–120, ≥120 min. Separar `SESSION_EXIT` observada de la hora estimada de toque del target sin stop (resultado contrafactual posthoc; cualquier toque posterior a STOP/TARGET no ejecutable).

**H16 M15/H1 madurez:** antigüedad H1 y M15 en minutos desde `confirmed_at`, direccional H1 original, target planned y distancia de stop inicial, MFE/MAE anteriores a vela de salida; bandas H1 age predefinidas <60, 60–180, ≥180m. **PROHIBIDO** leer `h1_state_until` offline derivado del siguiente estado futuro para decidir/estratificar “stale” ex ante.

## Reglas de integridad del experimento

1. Unirse por identidad exacta V49 `source_opportunity_id` con las 2876 operaciones completas y registros MFE; símbolo, sesión, precio, fecha, identidad de tesis y salida deben coincidir. Fallo de join o fila faltante **invalida todo el informe**; ningún denominador se reduce por conveniencia.
2. Aplicar el mismo primer MAX3 **cronológico por sesión+fecha sobre nueve mercados**, sin usar R, excursiones, sesgo ex post ni etiquetas forward. Expectativa de identidad: 2020 seleccionadas, 856 contrafactuales, 1167 ganadoras y resultado bruto -233.269327R inalterado.
3. M1 hacia adelante 15/30/60 minutos requiere **secuencia de barras completa, exacta y dentro de misma ventana de sesión**; si faltan M1 o la ventana cruza el cierre NY: `None` y cobertura explícita, nunca imputar ni reemplazar por rendimiento hasta el stop.
4. Entregar mediana runway, distribución de clock thirds y partial H1 price thirds, por sesión, mercado, ruta, exit reason, edad tesis H1; para cada banda comparar `wins`, `gross_R`, porcentaje dirección positiva a horizontes fijos y MFE/MAE preterminal. Sin declarar falsa causalidad por correlación.
5. No construir gate de “entrar primer tercio” / “runway ≥60m” a partir del mismo replay. El hecho de que los resultados históricos muestren asociación no certifica una regla; próximo paso, si corresponde, es preregistrar un ensayo único y probarlo OOS independiente. No convertir MFE/MAE de futuro ni resultados direccionales posteriores en features de la cognitiva A1.

**Implementación GitHub**: `src/qore/infrastructure/trader_lab/capitalizer_scalper_h1_timing_session_diagnostic_v1.py`, `tests/infrastructure/trader_lab/test_capitalizer_scalper_h1_timing_session_diagnostic_v1.py`, workflow [joint test #38063578064](https://github.com/mezas3238-hue/qore-core/actions/runs/38063578064). GitHub almacena 9 JSONL de evidencias inmutables y 1 matriz agregada solo tras 9/9 contratos y cardinalidades exitosos.

**Potencia**: anotar n ≥500 como un suelo de investigación solicitado por auditor, no garantía de significación. El Owner mantiene barreras independientes: original winning IDs ≥934 (80%), original winning R ≥415.75R (90%), PF OOS ≥1.5, DD ≤6R según mandato vigente, costes BID/ASK comisión y slippage reales, pruebas de estabilidad, Master Frame completo y fidelidad autor. Ningún brazo con n bajo 500 puede presentarse como evidencia sólida; tampoco uno con n≥500 se certifica automáticamente. 

**Veredicto al preregistro**: CAUSA SIN RESOLVER; diagnóstico posthoc autorizado como investigación; ningún cambio ejecutable; no datos de MFE futuro accesibles a Trader/Shared/CIBO.
