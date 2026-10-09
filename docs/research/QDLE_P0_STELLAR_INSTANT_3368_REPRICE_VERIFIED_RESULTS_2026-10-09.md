# QDLE P0 — Replay 3.368 con tarifario público FundedNext Stellar Instant; resultado verificado

**09-10-2026** · **CI [#37943757745](https://github.com/mezas3238-hue/qore-core/actions/runs/37943757745) SUCCESS** · **SHA ensayado:** `51a29de341e1d223c9ccdd8c79449bd9650c82fc` · **Artefacto:** [#11622282725](https://github.com/mezas3238-hue/qore-core/actions/runs/37943757745/artifacts/11622282725) (`qdle-stellar-instant-3368-fee-reprice-37943757745`) · **PR #745** · **RESEARCH/NO LIVE/NO DD de gestor**.

## Tarifa utilizada y proveniencia
Artículo oficial [«What are the commission charges for the Stellar Instant Account?»](https://help.fundednext.com/en/articles/11641300-what-are-the-commission-charges-for-the-stellar-instant-account): Forex USD7/lot apertura, sin segunda comisión de cierre; XAUUSD 0.0016 % del nocional al abrir; indices USD0. Se mantiene el escenario alternativo de [reglas generales por lado](https://fundednext.com/general-rules/cfds/symbols-and-conditions). **La tarifa pública no equivale a recibo efectivo de comisión de la cuenta del usuario ni a condiciones históricas 2019-2022**. Aún hace falta reconciliar `history_deals_get` y precio/cambio histórico.

- Código: `src/qore/infrastructure/qdle_stellar_instant_costs.py` define tarifas per-lot con OPEN y CLOSE separadas, y `jpy_quote_pip_value_usd_per_lot` (precio USDJPY causal explícito, no usar captura actual en historia).
- `scripts/qdle_3368_dual_ledger_replay.py` ahora acepta `--fee-model legacy_proxy|stellar_instant_open_only|stellar_general_per_side` y usa `opening_fee + closing_fee` para el denominador QDLE y propuesta de stop económico; no imputa comisiones **pagadas** a cotizaciones no ejecutadas.
- `tests/infrastructure/test_qdle_stellar_instant_costs.py` valida FX, índice sin tarifa, oro nocional, modelo anterior, divisor JPY y rechazos; pruebas y recotizaciones CI PASS.
- `scripts/qdle_3368_fee_model_comparison.py` concilia 3 x 3368 IDs, los 3 modos, 4 motores y QDLE, calcula cambios por señal y modo y conserva DD/PF/NAV `null`.
- `.github/workflows/qdle-stellar-instant-3368-fee-reprice.yml` reutiliza artefacto FRESH Native MAX [#37937821428](https://github.com/mezas3238-hue/qore-core/actions/runs/37937821428), hash de ZIP histórico y source CIBO original; corre los 3 brazos **sin repetir innecesariamente 20 minutos de inferencia cognitiva**, con 0 broker order_send.

## Resultado comparativo global
| Métrica de CIBO/QDLE | Legacy (FX14 RT, XAU2 tramos, NDX20) | FundedNext Stellar FAQ (FX7 OPEN, XAU apertura, NDX0) | General rules *por lado* (FX14 RT, XAU2 tramos, NDX0) |
|---|---:|---:|---:|
| Señales Native MAX consumidas por QDLE | 3.368 | 3.368 | 3.368 |
| Lotes financiables >0 | **1.961** | **2.102** | **2.015** |
| No financiables | 1.407 | 1.266 | 1.353 |
| Lotes positivos sumados por señales | 31,63 | **37,74** | 32,78 |
| BANK cotizaciones positivas / 2.031 | 870 | **996** | 918 |
| MEDIUM cotizaciones positivas / 520 | 274 | **289** | 280 |
| ATTACK cotizaciones positivas / 817 | 817 | **817** | 817 |
| Fills MT5 verificados | 0 | 0 | 0 |
| Capital inicial económico QORE | 60 USD | 60 USD | 60 USD |
| CIBO NAV final, drawdown y PF auténticos | **NO CALCULABLE** | **NO CALCULABLE** | **NO CALCULABLE** |
| Certificación de tarifas de la cuenta | No | No | No |

**Diferencia Legacy → FAQ: +141 propuestas con lote y +6,11 lotes agregados.** La comparación línea por línea del artefacto incluye 580 señales cuyo *lote* cambió en al menos uno de los 2 escenarios alternativos: frente al legacy, 141 pasan de 0 a positivo y 439 cambian el volumen, sin perder financiabilidad en el escenario FAQ.

## Distribución por instrumento (solicitudes → propuestas con lote físico)
| Símbolo | Señales originales | Legacy | Stellar FAQ | Por lado | Cambio legacy→FAQ |
|---|---:|---:|---:|---:|---:|
| AUDJPY | 673 | 508 | **521** | 508 | **+13** |
| EURUSD | 495 | 331 | **354** | 331 | **+23** |
| GBPJPY | 618 | 394 | **410** | 394 | **+16** |
| GBPUSD | 606 | 285 | **315** | 285 | **+30** |
| NDX100 | 484 | 239 | **293** | 293 | **+54** |
| XAUUSD | 492 | 204 | **209** | 204 | **+5** |
| **TOTAL** | **3.368** | **1.961** | **2.102** | **2.015** | **+141** |

**No equiparar volumen agregado con simultaneidad ni rentabilidad**. El presupuesto CIBO por modo en este estudio sigue BANK 1,25% NAV, MEDIUM 2,50% y ATTACK 5,00%, QORE inicial $60, QDLE min grid y margen, cuatro motores y snapshot/manifest research.

## Comisiones estimadas en las cotizaciones, NO pagadas
Tarifas $ por lote según fuentes/escenario; suma de `lots_quoted × fee_open/close_per_lot` sobre TODAS las propuestas de un brazo, sin ejecutar ni debitarlas. Para el escenario FAQ, las comisiones **estimadas de apertura** acumuladas de 2.102 cotizaciones son aproximadamente **USD224,7582**; comisión de cierre según FAQ **USD0**. En el legacy, sobre 1.961 cotizaciones diferentes, se estiman USD221,4190 en apertura y USD221,4190 en cierre, **USD442,8381** roundtrip total **teórico**. No comparar como ahorro realizado: difieren la cantidad de cotizaciones, su volumen y la trayectoria sin liquidaciones. En ambos brazos, comisiones **efectivamente pagadas = 0**, pues fills = 0.

## Imagen MT5 aportada por el CEO y su uso correcto
Dos capturas recientes de cotización MT5 muestran, en un mismo instante **sin fecha ni zona de servidor probada**: AUDJPY aproximadamente bid 110,405 / ask 110,419; GBPJPY 209,403/209,426; XAUUSD 4188,47/4188,85; NDX100 30797,17/30798,77; USDJPY 158,337/158,349. El valor orientativo de un pip JPY (contrato 100K y `pip_size=0.01`) es `1000 / 158.337 ~ 6.316 USD/pip/lote`; los metadatos MT5 reales deben prevalecer. **No aplicar esta cotización 2026 a precios, tipos USDJPY ni spreads de 2019-2022.** Esta captura es observación de mercado *actual*, no historia.

## Veredicto de salida, NAV y drawdown solicitado
`cibo-exit-path-coverage.json` del nuevo CI: 3.368 señales reconciliadas; **2.102** cotizaciones con volumen, **1.266** sin volumen; **0 trayectorias históricas consecutivas de salida por señal aportadas en el origen 2019–2022**; resultado `MISSING_BID_ASK_PRICE_PATH=2102`, `NOT_PHYSICALLY_QUOTED=1266`, `real_mt5_fills=0`, `global_manager_nav_usd=null`, `global_manager_dd_and_pf=null`. El NAV técnico de quote-only permanece $60, no es capital final de operaciones cerradas. **No inventar** DD, PF, comisiones pagadas, win rate, salidas ni P&L de gestión usando `gross_structural_outcome_r` del Trader CONTROL. Las capturas de mercado puntual no sustituyen precio durante toda una operación.

### Abiertos para siguiente fase
1. Verificar con documentación contractual/tickets MT5 la tarifa de la cuenta Stellar Instant y resolver diferencia FAQ vs reglas generales por lado, XAU bases, fees adicionales.
2. Incorporar eventos continuos read-only de símbolo, tick value/margen, FX USDJPY **con tiempo causal y fuente**, no una cotización fijada del 9/10/2026.
3. Acoplar `cibo_managed_exit_replay.py` al ledger de todas las posiciones para un **segundo replay** con operaciones reales o trayectorias de mercado suficientes; solo así publicar capital final, DD intratrade, PF, win rate y comisiones pagadas. El motor de cierres unitario existe; datos/cartera conjunta pendientes.
4. Mantener `PAPER/NO LIVE` y desactivar cualquier conclusión de certificación financiera sobre el arm histórico quote-only.

**Archivos publicados dentro del artefacto:** `legacy-3368.json`, `stellar-instant-3368.json`, `general-per-side-3368.json`, `summary-comparison.json`, `cibo-exit-path-coverage.json`. Están disponibles en el [run exitoso](https://github.com/mezas3238-hue/qore-core/actions/runs/37943757745).
