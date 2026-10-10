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
