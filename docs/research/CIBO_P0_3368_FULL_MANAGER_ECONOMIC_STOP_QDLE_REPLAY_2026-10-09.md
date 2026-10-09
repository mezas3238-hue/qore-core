# CIBO P0 — Replay CEO de LAS 3.368 entradas: acciones administrativas y QDLE con SL económico dinámico

**Estado: EJECUTADO / CI SUCCESS / PROXY RESEARCH NO LIVE** · [GitHub Actions #37907644177](https://github.com/mezas3238-hue/qore-core/actions/runs/37907644177) · [Artefacto completo #11605550958](https://github.com/mezas3238-hue/qore-core/actions/runs/37907644177/artifacts/11605550958) · Rama `agent/cibo-sovereign-integration-p0-20261008` · commit ensayado `f100df1e01458fb8c5723f67c4c15b40e676a0be`.

**Comandos reproducibles**: workflow `.github/workflows/cibo-p0-manager-qdle-replay.yml`, invoca `scripts/qdle_3368_dual_ledger_replay.py --motor-policy independent_four_motors --min-policy broker_grid --provider-trailing-usd disabled --swap-proxy off --ndx-roundtrip-fee-proxy-usd-per-lot 20 --experimental-cibo-administrator` con manifest original sellado `11451743578`, SHA256 verificado. **0 autorizaciones cognitivas Native**, cada Trader signal pasa por CIBO y se solicita QDLE cuando la geometría es presupuestable.

## Resultado accionable de 3.368 señales, sin excluir ni borrar ninguna

| Acción | Conteo |
| --- | ---: |
| Trader señales recibidas por CIBO y revisadas en ledger | **3.368** |
| CIBO preservó el SL estructural por caber en NAV dinámico disponible | **813** |
| CIBO propuso SL protector económico más estrecho | **2.555** |
| QDLE propone lote con SL estructural original | **359** |
| QDLE devuelve lote para SL económico propuesto (QUOTE ONLY) | **209** |
| No financiables bajo todos los motores y presupuesto vigente | **2.800** |
| QDLE propuestas con volumen mayor que 0 (originales + nuevas, subconjuntos disjuntos) | **568** |
| Broker real fills | **0** |

**Descomposición de las 209 cotizaciones de SL económico**: exactamente **0,01 lote cada una**, total volumétrico `2,09` lots *sumados entre operaciones individuales*, **NO una posición simultánea**. Riesgo al SL propuesto + roundtrip costs sumado por cotización `USD158.47855266`, incluye USD27.90375232 de comisiones teóricas; **0 / 209** sobrepasaron el 5% de NAV del camino de control empleado al momento de la señal. La suma NO representa capital depositado ni margen simultáneo real.

| Símbolo | Recibidas | QDLE con SL original | QDLE quote SL económico nuevo | No financiables |
| --- | ---: | ---: | ---: | ---: |
| AUDJPY | 673 | 70 | 31 | 572 |
| EURUSD | 495 | 90 | 18 | 387 |
| GBPJPY | 618 | 58 | 42 | 518 |
| GBPUSD | 606 | 61 | 37 | 508 |
| NDX100 (origen NAS100) | 484 | 56 | 38 | 390 |
| XAUUSD | 492 | 24 | 43 | 425 |
| **TOTAL** | **3.368** | **359** | **209** | **2.800** |

### Restricciones de las 2.800 sin lote

- `CIBO_COMPOUND`: **2.782**: el presupuesto soberano asignado por ese motor no permite reservar un lote mínimo con los costes proxy. Es el verdadero mayor cuello de botella tras proponer SL más estrechos; **NO ES RECHAZO COGNITIVO** de la entrada.
- `SOVEREIGN_BANK`: **17**: el capital de fuente disponible es insuficiente.
- `ZERO_FINANCE_CAPACITY`: **1**.
- `REQUESTED_USD` no aparece como primary blocker en este brazo: el stop CIBO se ajusta hasta el presupuesto del intento. Esto NO elimina restricciones de otros motores ni garantiza la geometría del broker.

**Hallazgo crítico:** el motor Compuesto necesita revisión económica: ¿limita por un cálculo de protección legítimo (tres pérdidas recientes, NAV y capacidad) o mantiene un gate de la vieja selección? No deshabilitarlo ciegamente ni declarar que todas las 2.782 debían abrirse.

## Finanzas: separación explícita entre CONTROL y CIBO administrador

**Control SL original, 359 salidas Trader estructurales:** NAV USD60→USD9.51746750, DD sobre NAV cerrado 87.40357309%, PF neto proxy 0.7814715961, commissions OPEN USD54.07647168 y CLOSE USD54.07647168. **Es exactamente el resultado viejo del brazo control**, incluido para comparabilidad, **NO** rendimiento de la estrategia con nuevos SL. Los 209 nuevos trades NO se incorporan a este PnL ni a DD: son propuestas físicas aisladas con reserva nunca convertida en fill ni salida.

**P&L / PF / DD de la nueva estrategia de 568 propuestas:** **NO MEDIBLES con el manifest sellado**, porque no contiene path bid/ask para decidir exit por SL económico / parcial / trailing / breakeven / salida defensiva, ni reevaluación secuencial del NAV después de esas nuevas ejecuciones. No inventar capital final ni utilizar `gross_structural_outcome_r` de las salidas anteriores.

### Modelo de datos del run: LIMITACIONES NO NEGOCIABLES

1. **NAV para SL dinámico:** utiliza NAV del **escenario de control original** tras liquidar su Trader-R histórico. Esto no es NAV de una cartera real con los 209 quotes añadidos. El número de SL económicos crece de 300 a 2.555 precisamente porque el NAV del control cae fuertemente. No interpretar 2.555 como cifra validada para el futuro manager autónomo.
2. **Broker:** USD2000 para margen proxy, QORE USD60 inicial para 5% risk, contratos/margin tomados de captura FundedNext 2026, NDX fee USD20/lot RT sensibilidad, FX USD14/lot RT, XAU proxy nocional; conversión JPY desde el manifest. No hay `MT5 order_calc_profit`, `order_check`, `order_send`, fill tickets ni coste/stop histórico auténtico.
3. **Min stop distance histórico desconocido se modela como CERO**; slippage buffer CERO, spread/gaps no probados. Los 209 pueden reducirse en una preflight real y no son autorizaciones LIVE.
4. **A1 CIBO managed exits** sí tiene el motor causal testado, pero no hay trayectoria de velas bid/ask en las 3.368 señales. El motor preserva prueba fail closed: `NEEDS_PRICE_PATH`, no fake winners.
5. **Fuentes Bank/Cushion:** este ensayo usa fuente Bank modelada; requiere ledger fuente real, no mezclar atribución/transferencias históricas sintéticas.
6. **Los cuatro motores** reciben observación simulada de precio/margen y cashflow del control; QDLE calcula el lote físico válido **dentro de ese proxy**. CIBO no filtra Trader entries y QDLE no ejecuta operaciones.

## Próxima prioridad P0 para conseguir resultados verdaderos de gestión

1. Recuperar trayectoria histórica completa y verificable `bid/ask OHLC` o ticks, con reloj causal y precio ejecutable por instrumento (AUDJPY, EURUSD, GBPJPY, GBPUSD, XAUUSD, NAS100/NDX100). Exigir velas cerradas para ATR14, fills originales plausibles, gaps y spread.
2. Conectar stops CIBO reales y estrategias Bank/Medium/Attack, parcial, break-even, trailing y cierre adverso; decidir orden intrabar stop-first conservador y fees/reprice.
3. En el mismo timeline causal, modificar NAV y tesorería Bank/Cushion tras cada cierre y correr QDLE secuencialmente con 5% dinámico **recalculado en el brazo manager, no heredado del control**.
4. Inspeccionar **2.782** limitaciones `CIBO_COMPOUND` con desglose de razones/proveniencia por señal; corregir incoherencia si demostrable, nunca forzar lotaje mínimo que incumpla presupuesto.
5. Solo entonces calcular capital final, PF/DD MTM y cumplimiento FundedNext; revalidar OOS fresco antes de certificar.

**El presente trabajo responde la solicitud de «poner a correr el replay de las 3.368 y saber qué acciones tiene QDLE con CIBO».** Es el experimento de cotización financiera P0, no una demostración de rentabilidad.
