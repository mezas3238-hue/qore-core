# QORE Scalper — novena auditoría, 381 divergencias CISD (P0)

**Branch B metodologia:** `agent/scalper-architect-b-methodology-20261010`, [PR #759](https://github.com/mezas3238-hue/qore-core/pull/759), issue #757. A cognitivo [PR #758](https://github.com/mezas3238-hue/qore-core/pull/758), issue #756. **RESEARCH ONLY, no VPS, no merge, no LIVE.** Fecha 2026-10-10.

## Problema y evidencia congelada

- Nueve libros V49 de [run #38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695), SHA `e356e7a52541e99533b25ecfef0ab9c4e9ce03c0`; **2876 oportunidades**. 2020 MAX3, 1167 ganadoras, PF 0.66446, DD 236.134R.
- Sensor multicontexto M1, [run #38071138991](https://github.com/mezas3238-hue/qore-core/actions/runs/38071138991), SHA `74f4d9c89cdaaefd220a9a45ba98c2a0376be3d7`; **2495 matches, 381 discrepancias** del primer evento CISD fuente M1 respecto de V49.
- Fuente provider-native M1 nine markets [run #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334) SHA `18c338aedd5013ce65a6cb6408ffbc2e904a6217`. Horizonte desarrollo septiembre 2025–septiembre 2026. Nada se imputa.
- PAPER A/B [run #38071484777](https://github.com/mezas3238-hue/qore-core/actions/runs/38071484777): solo descartar discrepar produce PF 0.62131 vs control 0.66446, DD **252.10R** frente a 236.13R, menos R ganadora, **gate descartado**. No es evidencia de la cognitiva real.
- **Master Frame cognitivo A1** no conectado a autorización PAPER con 2876 decisiones reales y prueba de no-lookahead; sigue P0 bloqueante, no fingir su impacto económico.

## Autor original CISD — conclusión de fuentes primarias

- [TTrades — Understanding Change in State of Delivery (CISD)](https://ttrades.com/understanding-the-change-in-state-of-delivery-cisd/): cierre fuera de la **apertura de la primera vela de la secuencia opuesta**. Bullish: después de serie down-close, cerrar por encima de su primera apertura. Bearish: espejo con up-close.
- [TTrades — Market Structure Shifts vs CISD](https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/): CISD no equivale a MSS ni exige romper high/low swing; debe usar el inicio de la serie opuesta. 
- [TTrades — How CISD Confirms Swing Points, 2026-01-10](https://ttrades.com/how-change-in-the-state-of-delivery-confirms-swing-points/): cierre por las velas que formaron el extremo, vinculada obligatoriamente a una closure HTF Candle 2/3 y al protected swing. El autor advierte sobre CISD de mala calidad: mucho lateral frente a desplazamiento decisivo. Requiere **cierre**, no simple mecha.
- En código V49 `observe_first_m1_cisd` obtiene `boundary=series[0].open` y cierra más allá, no sobre el máximo del swing ni apertura de última vela. `_series_ending_at` reúne cierre opuesto al sesgo. Lo anterior es **MATCH en el nivel y cierre básicos**; fidelidad de *qué serie corresponde al swing relevante*, POI H1 y M15, y jerarquía temporal requieren test separado. **No declarar invertido el CISD por tasa retrospectiva 40%.**
- **Punto técnico pendiente**: `_earliest_m1_trigger` V49 recibe ventana M1 desde **M15 setup confirmado hasta siguiente M15 setup o límite H1 state** y selecciona min(first Sweep, first FVG). El panel de sensores vuelve a evaluar ambos primeros observers contra un prefijo que termina exactamente en la decisión fuente. Son universos de búsqueda distintos; una diferencia de primera ruta puede provenir de **deadline/ventana** y de search algorithm dependiente del prefijo. No presupone que uno sea el correcto o que exista trade autorizado antes del source V49.
- El sensor solo evalúa **la dirección H1 heredada de V49**: los 381 no permiten cuantificar "dirección contraria", ya que tal variante no se instrumentó; su contador de dirección opuesta es epistemológicamente NO OBSERVABLE y no se debe reportar como 0 casos reales.

## Test preregistrado antes de sus resultados

**Código** `src/qore/infrastructure/trader_lab/capitalizer_scalper_cisd_381_discrepancy_forensic_v1.py`, tests `tests/infrastructure/trader_lab/test_capitalizer_scalper_cisd_381_discrepancy_forensic_v1.py`, Actions `.github/workflows/qore-scalper-a2-ninth-cisd-381-forensic.yml`. Nueve mercados paralelos, exactas 2876 source_ids con 381 divergencias, resultados por ID, market, session, family y tipo. **No se descarta ninguna fila por rendimiento**.

Taxonomía mutuamente excluyente, definida sin retornos:
1. `SENSOR_EARLIER_THAN_V49`;
2. `SENSOR_LATER_THAN_V49` — *imposible de observar si se alimenta el panel solo con M1 hasta el instante de V49*, una discrepancia future-identified aquí causaría FAIL CLOSED, no un conteo engañoso;
3. `SAME_TIME_DIFFERENT_FAMILY` — empate Sweep/FVG clasificado distinta ruta;
4. `SENSOR_NOT_DETECTED`;
5. `MATCHED` para 2495 restantes.

En misma fila y **para ambos instantes fuente vs sensor**, retorno direccional final, MFE y MAE a +15/+30/+60 minutos, con M1 **nativa continua**, dentro de la sesión NY, exigencia de vela de evento cerrada (precio testigo, no high/low de vela en formación). Puntos de observación posteriores son *outcomes posthoc*, jamás usados en selección. Se computa MFE/MAE en unidades de PRECIO y R sobre **stop M15 fuente declarado** solo cuando el stop está al lado de riesgo del timestamp hipotético; si no, `INVALID_RISK_GEOMETRY` y R ausente, sin inventar SL. Cada reporte indica cobertura, ausentes, N pareado, tasa favorable de sensor vs V49, diferencia puntos porcentuales y excursiones medias. No es replay de *un fill* a tiempo sensor, ni su ejecución tiene POI/stop/TTrades confirmados.

**Determinación posterior:** si sensor temprano mejora 30m no sustituir CISD automáticamente. Antes reconstruir ventana M15 / H1, cierre de la serie opuesta, swing confirmado y secuencia del autor; preregistrar cambio **único** en implementación si existe bug literal, y validar multianual/OOS. Las métricas PAPER requieren cognitiva A1 real y costes QDLE, no son sustituidas por MFE/MAE.

## Certificación

**SCALPER NO CERTIFICADO**. Queda vigente 934 winners originales/415.75R masa original, n suficiente, PF neto tras broker físico, drawdown ≤6R conforme Owner, fuente TTrades y robustez OOS. Nunca promover un filtro binario o usar retrospección para autorizar entrada.

## RESULTADOS FINALIZADOS — nueve mercados, CI 11/11 GREEN

**GitHub Actions:** [#38076268436](https://github.com/mezas3238-hue/qore-core/actions/runs/38076268436) **SUCCESS 11/11**, SHA de código probado `1cc7b569682ec82b97fd355f5808bbc6202ef19d`. [Informe agregado descargable, Artifact #11679210450](https://github.com/mezas3238-hue/qore-core/actions/runs/38076268436/artifacts/11679210450). Nueve artifacts por symbol con 2.876 eventos source por ID y ambos vectores MFE/MAE a 15/30/60; todas las 381 divergencias conservadas, y 2495 coincidencias. Ruff, mypy y 5 pruebas de causalidad GREEN. Auditoría de metodología posterior [#38076353370](https://github.com/mezas3238-hue/qore-core/actions/runs/38076353370) GREEN.

### Qué ocurrió en las 381 discrepancias

| Tipo | n | % sobre discrepancias |
|---|---:|---:|
| **SENSOR_EARLIER_THAN_V49** | **247** | **64.83%** |
| **SAME_TIME_DIFFERENT_FAMILY** | **134** | **35.17%** |
| Sensor posterior | **0** | **0%** — imposible en panel as-of evaluado al timestamp V49 |
| Sensor sin detectar | **0** | **0%** |

**Discrepancias exactas de ruta, hallazgo P0:** 
- 171 originales `FVG_RETRACE_CISD` → sensor `LIQUIDITY_SWEEP_CISD` **anterior**;
- 76 originales `LIQUIDITY_SWEEP_CISD` → sensor `FVG_RETRACE_CISD` **anterior**;
- 134 originales `LIQUIDITY_SWEEP_CISD` → sensor `FVG_RETRACE_CISD` **al mismo cierre M1**.

Así, **381/381 cambian de familia**, y **247/381 cambian además de instante**. No hay un solo caso de CISD mismo tipo en diferente minuto. Los 134 de empate temporal son reclasificación de ruta sin diferencia de hora, precio de cierre ni desplazamiento posterior. Por tanto, atribuirles un «mejor timing» sería falso. El panel hereda la dirección del source H1, luego la *dirección contraria* NO está instrumentada y no puede concluirse ausente en el mercado: solo es imposible dentro del panel.

### MFE / MAE comparados sobre pares de fuente, velas M1 contiguas

**Dirección favorable del cierre a +30m**, en **349/381 fuentes con cobertura completa en ambas rutas y antes de cierre de sesión**:

| Grupo | n pareadas | Sensor favorable +30m | V49 favorable +30m | Diferencia SENSOR−V49 |
|---|---:|---:|---:|---:|
| **Todas las discrepancias** | **349** | **189/349 = 54.15%** | **176/349 = 50.43%** | **+3.725 pp** |
| **Solo sensor más temprano** | **224** | **126/224 = 56.25%** | **113/224 = 50.45%** | **+5.804 pp** |
| **Mismo cierre, familia distinta** | **125** | **63/125 = 50.40%** | **63/125 = 50.40%** | **0.0 pp** |

**La mejoría a +30min NO es monótona ni garantiza edge**. Para las **247 señales anteriores**, a +15min la comparación pareada disponible (239 casos) es sensor 107/239=44.77% frente V49 115/239=48.12% (**−3.347 pp**). A +60m, 204 pares observables obtienen 106 favorables por brazo, **0.0 pp**. En el conjunto de 381: +15m sensor 171/370=46.22%, original 179/370=48.38% (−2.16pp); +60m ambos 167/312=53.53%.

**Excursiones MFE/MAE en R orientativas, con STOP M15 original, SOLO donde geometría es válida:** para grupo sensor más temprano a +30m, MFE medio sensor ~**1.103R** vs V49 ~**0.793R**, pero también **MAE media sube** de ~**0.580R** en V49 a ~**0.724R** en instante anterior. Hay 219/224 geometrías de riesgo válidas para el sensor y 224/224 para V49 en esa ventana; las medias R usan denominadores distintos y NO son diferencias causales pareadas de mismo soporte válido. Las cifras en precio para activos distintos **no deben agregarse como si fueran dólares del mismo lote**, y no existe P&L monetizable del evento hipotético. No se simularon SL/TP/fees del sensor ni entradas adelantadas.

**Diagnóstico:** las discrepancias de la novena ronda son **conflictos de PRECEDENCIA entre familias y/o ventanas temporales fuente**, no evidencia de que el cierre CISD esté invertido. Los dos observadores utilizan la dirección H1 dada, y el Sweep usa el nivel `opening` de la primera vela de la serie de cierres opuestos, como TTrades. Los datos no permiten declarar que V49 sea incorrecto ni que el sensor sea una mejora operable. El aumento a +30m existe en el contraste retrospectivo temprano, pero se acompaña de excursión adversa mayor, cambia de signo a +15m y desaparece a +60m; reforzar el veto automático habría empeorado PF y DD, como ya probó el PAPER previo.

**Siguiente P0 de ingeniería causal**: para las mismas 247+134 discrepancias reconstruir *exactamente* la ventana V49 original de `_earliest_m1_trigger` (hasta siguiente setup M15 o H1 state as-of), confrontarla con el snapshot prefix-only, y enumerar condiciones exactas de precursor sweep/FVG y prioridad en empate. Fijar la precedencia de ruta solo por definición fuente del autor y cronología causal, no por cuál produce mayor R en este mismo desarrollo. A1 debe seguir conectando Master Frame real as-of al motor PAPER (no false cognitive metrics) e informar su DD bajo todos los controles de winner retention y costes.

**Certificación:** NO CERTIFICABLE. Datos septiembre 2025 a septiembre 2026; robustez 2023/2024 OOS no aportada, motor económico continúa negativo, full Master Frame decisor no verificado, broker físico no integrado. No hubo cambios de política LIVE, VPS ni fusión de PR.
