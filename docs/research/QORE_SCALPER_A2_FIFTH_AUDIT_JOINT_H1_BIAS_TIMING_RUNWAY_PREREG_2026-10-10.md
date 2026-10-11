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

## Control adicional descubierto en USDCAD: huecos nativos M1, sin alterar outcomes

Durante la primera ejecución 9/9 [#38063578064](https://github.com/mezas3238-hue/qore-core/actions/runs/38063578064), el mercado **USDCAD** abortó la nueva auditoría antes de la matriz final porque la nueva medición de «primera observación del target» exigía barras M1 **continuas** hasta el toque, mientras el V49 original ya admitía huecos en la fuente nativa. El libro económico y el MFE/MAE original **sí** conciliaban las barras realmente vistas y el final TARGET; rechazar un toque posterior únicamente por una M1 faltante era una condición adicional de ingeniería del **auditor nuevo**, no una invalidación del V49 anterior. **No se descartó ni se modificó ninguna operación del control**, y no se publicó agregado incompleto.

**Corrección de test de datos**, sin ninguna alteración de trade: `fixed_forward_15/30/60m` mantiene el requisito de M1 totalmente consecutivas y reporta `None` si hay huecos, porque un cierre de dirección exacto en un horizonte con gaps no es evaluable con la misma precisión. Para `TARGET`, la auditoría puede comprobar que la barra OHLC **observada** llegó al precio antes o en la salida V49, sin afirmar conocer el recorrido de precios dentro del hueco. El delay de target pasa a `target_first_observed_touch_delay_minutes_hypothetical`, minutos reales de reloj; indicador `target_observed_touch_follows_native_m1_gap` identifica incertidumbre de la primera vez real. No se infieren precios faltantes, spreads, stops ni beneficios anteriores. Test de regresión simula un M1 ausente, conserva target OHLC observado y exige `None` en forward15/30/60, manteniendo outcome original.

Esta mejora se documentó **antes** de ver resultados agregados por tercio horario/runway, no toca grupos, umbrales ni selección. Nuevo run [#38063930894](https://github.com/mezas3238-hue/qore-core/actions/runs/38063930894), rama B PR #759, conserva la misma matriz de 9 mercados y los 2.876 IDs congelados.

## RESULTADOS 9/9 CONFIRMADOS — H1 BIAS × TIMING M1 × NY SESSION RUNWAY

**GitHub Actions**: [#38063930894](https://github.com/mezas3238-hue/qore-core/actions/runs/38063930894), fuente SHA `ca9e143f8d056c9141c2da4ed439acfd40af7d4e`: **11/11 SUCCESS** (1 contract, 9 markets, 1 aggregate), [matriz reproducible artifact #11674655664](https://github.com/mezas3238-hue/qore-core/actions/runs/38063930894/artifacts/11674655664). Los nueve archivos source-ID JSONL están retenidos en la misma corrida; los 2876 registros V49 se conciliaron exactos a los 2876 registros MFE/MAE, mismo P&L original, sin ningún cambio de señal ni regla ni re-ranking MAX3. Control seleccionadas **2020, 1167 winners, 852 losers, 1 flat**, net `-233.269327R`, MFE previo 0.34364R, MAE previo 0.46553R.

### 1. Sesgo H1: prueba direccional independiente de win rate

| Horizonte fijo H1-direction-aligned (POST-TRADE, todos 9 mercados) | Cobertura M1 completa (N) | Avance precio a favor del sesgo H1 (N) | Proporción favorable |
|---|---:|---:|---:|
| +15 minutos | 1975 | 874 | **44.253%** |
| +30 minutos | 1924 | 839 | **43.607%** |
| +60 minutos | 1824 | 837 | **45.888%** |

Los 15/30/60 son ventanas **independientes de la salida V49**: si la operación ya cerró en STOP, se observa retrospectivamente el precio a ese horizonte SOLO PARA MEDIR DIRECCIÓN, no como beneficio capturable. El diagnóstico **NO demuestra** que la entrada sea un predictor direccional >50%; de hecho, con esta métrica descriptiva `<50%` las tres ventanas. Faltan confianza por día, costos, ajuste de sesión/volatilidad, autocorrelación de trades y validación OOS. Diferentes horizontes no son tests independientes; no declarar «H1 sesgo se equivoca siempre», ni «V49 57.8% win rate = acierto H1».  

**Diferencia entre familias:** a +30m FVG+CISD **477/1023 = 46.63%** favorables vs Sweep+CISD **362/901 = 40.18%**. A +60m FVG **476/973 = 48.92%**, Sweep **361/851 = 42.42%**; ambos por debajo del 50% descriptivo, y la ruta Sweep tiene más MAE previo. La confirmación CISD de cierre sobre serie opuesta pasó los unit tests, pero su timing/sweep/POI aún merece auditoría causal; no eliminar autor-legítimas familias ex-post.

### 2. Tiempo dentro de H1: temporal ≠ precio en rango observado

| Tercio del **RELOJ** H1, medido as-of | Operaciones | Ganadoras | P&L bruto | Favorable direccional +30m |
|---|---:|---:|---:|---:|
| Primeros 20m | **684** | 424 | -82.946R | 284/657 = 43.23% |
| Minutos 20–40 | **662** | 367 | -89.488R | 261/628 = 41.56% |
| Últimos 20m | **674** | 376 | -60.835R | 294/639 = 46.01% |

**Descartada la predicción de que la mayoría de entradas ocurre en el último tercio horario**: aproximadamente uno de cada tres trades se sitúa en cada tercio. Ningún tercio agregado consigue profit R >0; la banda LAST no explica por sí sola la pérdida.

| Tercio de posición de **PRECIO en el rango H1 parcial YA OBSERVADO**, dirección-ajustada | Operaciones | TARGET reales | P&L bruto | Precio H1 favorable +30m |
|---|---:|---:|---:|---:|
| Primer tercio favorable | 158 | 23 | -49.938R | 45/151 = 29.80% |
| Tercio intermedio | 468 | 158 | -108.553R | 170/439 = 38.72% |
| Último tercio favorable | **1337** | 810 | -66.864R | 603/1277 = 47.22% |
| Sin rango definible | 57 | 39 | -7.914R | 21/57 = 36.84% |

**OBSERVACIÓN** 1337/2020 = **66.19%** sí están en el tercio favorable alto del **rango disponible hasta el instante**, pero **no** en el último tercio temporal. No se puede llamar «agotamiento H1» sin el rango FINAL futuro y estructura/delivery; la correlación descriptiva +30m es más positiva en LAST precio (47.2%) que en FIRST (29.8%), aunque ambos son sub-50% y potencialmente confudidos por sesión, tendencia, cierre NY y oportunidades repetidas.

### 3. Horizonte de sesión: H12 supported SOLO COMO MECANISMO PARCIAL

| Runway al cerrar la M1 de confirmación | N | TARGET reales | SESSION_EXIT | R bruto |
|---|---:|---:|---:|---:|
| Menos de 30 minutos | 92 | **10 (10.9%)** | **70 (76.1%)** | -7.406R |
| 30–60 minutos | 98 | **36 (36.7%)** | **41 (41.8%)** | -17.707R |
| 60–120 minutos | 254 | **105 (41.3%)** | **72 (28.3%)** | -44.762R |
| 120 minutos o más | 1576 | **879 (55.8%)** | **198 (12.6%)** | -163.394R |

La mediana original de runway era **215 minutos** y 1576/2020 trades (**78.0%**) tenían al menos dos horas disponibles; el horizonte próximo a cierre parece restringir **~190 trades bajo una hora, 9.4%** y explica SESSION_EXIT alto en ese subgrupo, no el PF global <1. Ninguna banda es netamente rentable; **NO** promover gate ≥120m, ni reetiquetar el horizonte como causa única.

### 4. Madurez tesis H1: indicio nuevo, NO filtro autorizado

| Edad desde `h1_state_from` as-of | N | Favorable a +30m | R bruto |
|---|---:|---:|---:|
| Menos de 60 minutos | 69 | 38/68 = 55.88% | -2.807R |
| 60–180 minutos | 1305 | 575/1273 = 45.17% | -128.209R |
| 180 minutos o más | **646** | 226/583 = **38.77%** | -102.254R |

Parece haber deterioro del horizonte fijo +30m a medida que envejece el contexto H1; **observación y nueva hipótesis**, no regla. La edad viene de **`h1_state_from` confirmado pasado**, no `h1_state_until` futuro. Sin controlar sesgo por mercado, volumen, hora de sesión y solapamiento de señales, no se puede atribuir causalidad ni imponer un TTL artificial H1 nuevo.

### 5. MFE/MAE, stops y observabilidad posterior

- 609 operaciones terminaron en STOP. De ellas, **82** muestran un primer toque **observado** del target original *después* de que el trade ya había salido, antes del fin formal de sesión: **13.5% de los STOP**. Son **contrafactuales NO ejecutables**, nunca acreditación de beneficio, ni prueba de stop óptimo. Un toque posterior en una barra con datos nativos discontinuos se etiqueta como incierto en el momento exacto de primer touch.
- En los 1030 TARGET, el MAE preterminal medio fue **0.21844R**, MFE previo medio 0.31945R (el toque del target suele ocurrir en última barra excluida de PRE). En 609 STOP, MAE previo fue **0.83865R** (sin vela de salida) y MFE previo 0.32865R. No inferir el orden real intrabar ni afirmar que MAE medio comparado con MFE medio demuestra una secuencia temporal causal.
- El primer ensayo USDCAD abortó por un supuesto adicional de datos continuos al buscar testigo target, incompatible con huecos M1 de su fuente original. Fix **antes de estos resultados** validó el testigo OHLC observado sin imputar gap, mantuvo forward 15/30/60 solo en ventanas **completamente contiguas**, y agregó campo de observación posterior a gap. Ninguna fila original modificada, original runs V49 y MFE ya eran GREEN.

### 6. Adjudicación científica quinta auditoría

- **SESGO DIRECCIONAL / H12**: aun sin aislar “bias skill” puro, el precio va a favor de dirección señalada en **menos de 50%** a +15/+30/+60 en muestras con cobertura. Problema sistémico de sincronización/sesgo/estructura sigue abierto; no atribuir pérdidas solo a targets.
- **ENTRADA TARDÍA (tercio RELOJ H1)**: no confirmada; la distribución 684/662/674 es casi uniforme.
- **ENTRADA en extremo de rango YA observado H1**: 66.2% LAST favorable price rank, pero no equivale a «cerca del high final H1». La progresión posterior en esta banda sigue sub-50% a 30m.
- **HORIZONTE vinculante**: confirmado como correlación clara en operaciones con runway <60m; insuficiente para explicar toda la pérdida.
- **H1 edad/frescura**: nueva hipótesis prioritaria para el arquitecto A1: decay descriptivo +30m 55.9% muy fresco N68 →45.2% 60-180 N1273 →38.8% ≥180 N583; evita TTL y rechazo cognitivo en desarrollo sin prereg/OOS.
- **Sweep vs FVG**: 40.18% vs 46.63% favorables +30m, 42.42% vs 48.92% +60m; ambas negativas en P&L, diagnóstico sobre calidad POI/delivery sin prohibir ruta Sweep autor.
- **CERTIFICACIÓN**: ningún cambio ni trader autorizado. Requiere análisis multivariado con intervención única prereg y validación OOS independiente, coste real BID/ASK/comisión, Master Frame cognitivo A1 completo, original winner retention 934/415.75R, PF OOS ≥1.5 y DD≤6R. El suelo propuesto N≥500 no es suficiente para potencia estadística, especialmente con solapamiento y autocorrelación.

**Veredicto quinta ronda:** mecanismo múltiple parcialmente localizado, SIN corrección aprobada aún. **SCALPER NO CERTIFICADO.** Ningún modelo, H1 TTL, target, stop, filtro temporal o gates nuevos fue adoptado en producción.
