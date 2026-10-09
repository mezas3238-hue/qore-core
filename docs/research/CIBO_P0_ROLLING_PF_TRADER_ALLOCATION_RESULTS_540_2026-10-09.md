# P0 — CIBO rolling PF causal y pausa por Trader: política y resultados PAPER

**Fecha:** 2026-10-09 · **PR:** #748 (DRAFT) · **CI PASS:** [#37984529092](https://github.com/mezas3238-hue/qore-core/actions/runs/37984529092) · **SHA ensayado:** `c92b93a81822544a5e92027c7b288e00454cefc2` · **Artifact:** `11642765366`

## Misión y límites

Medir cuánto puede mejorar un asignador CIBO **sin modificar dirección ni timing de los Traders**, usando PF rolling de SOLO operaciones ya liquidadas, y pausas temporales causales. No utilizar PF final de cada Trader de 2019–2022 como si fuese conocido antes de la entrada. No abrir más de las 540 oportunidades de la cohorte ni aumentar el volumen en 0,01 pasos. **Este experimento no sustituye replay completo de las 3368 decisiones ni datos reales de broker.**

Fuentes de investigación:
- Entrada original: artifact `11451743578` (`walk-forward-manifest.json`; `fresh_oos_claimed: false`), SHA256 ZIP `d439957f21e2f79148b5a2fb75a53db6fa448698f17aeb6978f379ed3547f7ea`.
- Baseline anterior exacto: artifact `11639429464`, ZIP SHA256 `ef269745e321cf0a847fc20f98872a87bef6bb3f7d7e6e122f2850904140323a`; contiene las 540 entradas físicas, 538 cierres, dos abiertos sin final y costos sintéticos del escenario.
- Código: `scripts/cibo_trader_lab_p0_rolling_pf_allocation_540.py`.
- Tests: `tests/infrastructure/test_cibo_trader_lab_p0_rolling_pf_allocation.py`, cinco tests: historial mínimo, causalidad, liquidaciones concurrentes, salida de pausa sin bloquear indefinidamente y lote mínimo.
- Workflow independiente, rápido y reproducible: `.github/workflows/cibo-p0-rolling-pf-allocation-540.yml`.

## Contrato matemático congelado antes del ensayo

Para Trader t y tiempo de nueva decisión T, historial `H_t(T)` = **últimos 30 PnL netos de operaciones admitidas por el brazo actual y liquidadas a más tardar en T**. Las operaciones ignoradas **no** producen resultados de entrenamiento más adelante. No leer el cierre de ninguna posición activa, ni el eventual resultado adjunto de la nueva entrada.

`PF_suavizado(t,T) = (3 USD + suma PnL positivos en H_t(T)) / (3 USD + suma de magnitudes negativas en H_t(T))`, con presupuesto neutral 1 antes de 12 cierres. Los dos pseudo-acumuladores de USD 3 sirven solamente como estabilización explícita de muestra corta; deben validarse OOS antes de usarse operativamente.

Cuatro brazos congelados:

1. **BASELINE**: volumen y resultados originales, auditados contra el replay anterior con tolerancia menor a 1e-8 USD.
2. **ROLLING_PF**: después de 12 cierres propios, peso `min(1, max(0,25, PF_suavizado))`; antes peso 1. Lotes = `floor(original_lots * peso / 0,01)*0,01`. Nunca aumentar volumen original. Rechazar lote menor que 0,01.
3. **COOLDOWN**: detiene temporalmente nuevas oportunidades durante **10 candidatos propios** si `PF_suavizado < 0,60` con mínimo de 12 cierres o si hay 10 pérdidas consecutivas propias; después admite **una operación de prueba** sin leer outcomes de trades suprimidos, evitando pausa infinita por PF congelado.
4. **ROLLING_PF_AND_COOLDOWN**: aplicar ambas intervenciones al mismo Trader para comprobar si sus efectos son realmente aditivos.

Para brazos alternativos, chequeos extra conservadores de caja QORE actual, riesgo de stop aún abierto, **5% de caja** y margen disponible `2000 + cash - 60 - held_margin`, además del volumen original como techo. Los costos OPEN se descuentan en tiempo de apertura y los PnL brutos restantes se acreditan solamente en la fecha de cierre; dos trades sin salida permanecen abiertos. Son **valores proxy de escenario**, no estados certificados de broker.

## Resultado GitHub Actions #37984529092 — VERIFIED SUCCESS

| Brazo | Abiertas | Cerradas | Winrate | PF net | PnL cerrado USD | DD cash-only | Cash residual |
|---|---:|---:|---:|---:|---:|---:|---:|
| BASELINE | 540 | 538 | 37,175% | 0,71660 | -51,17463 | 85,841% | 8,68537 |
| ROLLING_PF | 228 | 227 | 38,326% | 0,75181 | -17,45440 | 30,757% | 42,47560 |
| COOLDOWN | 397 | 395 | 39,241% | **0,81279** | -23,51290 | 43,696% | 36,34710 |
| ROLLING_PF_AND_COOLDOWN | 159 | 159 | 32,075% | 0,63800 | -17,83929 | 31,270% | 42,16071 |

El peso PF reduce la pérdida monetaria ≈65,89%, pero admite 228/540 candidatas y mejora PF apenas de 0,717 a 0,752; **no ha demostrado selección rentable**, en parte disminuye simplemente exposición. El cooldown reduce pérdidas ≈54,05% con PF 0,813. La combinación reduce el volumen hasta 159 fills y **empeora PF a 0,638**. No hay evidencia de que sumar dos reglas aporte resultados combinados positivos.

**NO hay PF > 1.** No se declara recuperación del edge del Trader, no se recomiendan pesos LIVE ni suspensión de Trader en producción.

## Críticas/limitaciones: qué NO ha demostrado todavía

- Es **contrafactual de 540 fills congelados**. Ni el QDLE original ni los cuatro motores fueron re-ejecutados para los **2.808 originalmente sin lote** usando el capital alternativo. Al cambiar la caja/capital, algunos nuevos fills serían distintos. Por eso las cifras no equivalen a replay físico financiero completo, aunque todos los volúmenes sean subconjuntos válidos de los originales y sus lotes se redondeen al mínimo.
- Los **ratios de PF comparan conjuntos diferentes de operaciones** (538 vs 227 vs 395 vs 159). Tampoco se ha cuantificado la incertidumbre OOS; la población de tres eras es **burned/reused**.
- Los precios provienen de Atlas M5 2019–2022 con spreads fijos de octubre 2026 y USDJPY 2026, sin bid/ask históricos ni comisiones/slippage/correlaciones auténticas. DD mostrado es **sobre caja**, no equity MTM multiactivo.
- Al congelar lotes/entradas, la situación real de margen y la ejecución original pueden cambiar; los controles usan escenario de riesgo conservador pero NO sustituyen `QDLE.reserve_for_trader` nuevamente.
- El valor `0,6`, los 10 turnos, la ventana de 30 y los priors en USD son **hipótesis exploratorias**. No han sido elegidos ni aprobados en una validación fuera de muestra; nunca calibrarlos retroactivamente sobre las mismas 540 entradas para reportar «mejor política».
- Pausas por pérdidas consecutivas **no son** restaurar el antiguo `THREE_SETTLED_LOSSES_HAIR_CUT`. Este último era un recorte arbitrario aplicado al capital compuesto; los nuevos brazos son intervenciones explícitas y trazadas por Trader, solo investigación.
- La tercera propuesta, **reformar stop protector**, sigue **NO PROBADA por ablación aislada**. La Prueba A apagaba a la vez trailing, defensiva y parciales; el beneficio retrospectivo de $16,43 en subgrupo no puede sumarse a los resultados de asignación. La siguiente prueba debe cambiar SOLO protección de stop, sobre cohorte idéntica y con mismas comisiones y marcas; nunca extrapolar.
- CIBO Native MAX aún no ha emitido 3.368 episodios nuevos en el replay; por tanto, atribuir esta **política de investigación** a «toda la cognitiva CIBO» sería falso.

## Condiciones de aceptación de prioridad P0

A. **Reejecución causal end-to-end:** inyectar propuesta de capital/pausa en cada evento de la cronología de 3.368 señales, recalculando QDLE y los cuatro votos con libro PAPER único. No reemplazarlo por multiplicación a posteriori y no ampliar el riesgo 5% por PF.
B. **Ablación stop protector separada** vs baseline, fijando mismo conjunto de oportunidades y decomposición stop/partial/defense, marcando censurados; después probar composición.
C. **Controles negativos y OOS:** comparación contra asignación uniforme más conservadora con misma actividad o capital acumulado, PF rolling de etiqueta permutada temporal y volumen minimizado. Sin estos controles, mejora PnL por menos operaciones no significa ventaja cognitiva.
D. **Métrica objetivo:** PF > 1 *neto* y esperanza neta > 0 con intervalo temporal de incertidumbre sobre data independiente; DD MTM multiactivo medido. No aceptar 0,8 PF aunque reduzca pérdidas.
E. **P0 seguridad:** NO LIVE, NO VPS/MT5; todo hallazgo es etiqueta PAPER sin autenticidad de feed histórico o ejecución.

**Estado final actual:** `ALLOCATION_LOSS_REDUCED_BUT_EDGE_UNPROVEN_RESEARCH_ONLY`. Mantener PR #748 **DRAFT**.
