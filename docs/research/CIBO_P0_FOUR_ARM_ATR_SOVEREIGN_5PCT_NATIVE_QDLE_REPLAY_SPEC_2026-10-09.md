# QORE CORE — P0: especificación ejecutable de replay CIBO Native MAX + QDLE

**Versión 2026-10-09**, fuente: directiva del usuario. **GitHub Trader Lab PAPER / NO LIVE / no VPS.** PR de cuatro brazos: #748, PR libro dual: #746/#745. No afirmar PF ni DD nuevos hasta que artefactos `exact-SHA` sean verificables.

## 1. Universo fijo e invariantes de solvencia

- **Exactamente 3.368 oportunidades originales**, siete emisores: R42/AUDJPY, R43/GBPUSD, R38/GBPJPY, R38/EURUSD, R34/XAUUSD, VT31/NAS100, VT08/FOREX. No retirar señales por silenciamiento, ni suplantar una señal con posterior resultado.
- Cuenta QORE **USD60** inicial. `risk_ceiling_fraction = 0.05` **dinámico** del NAV conciliado al instante de decisión y de la actualización pre-fill. **El riesgo conjunto abierto es `<=5% * NAV`**; sobreexposiciones, gaps y PnL flotante se notifican y se contabilizan, nunca se ignoran.
- `entry_risk_budget = max(0,min(0.05*NAV, 0.05*NAV - held_open_stop_loss_risk, available_source, physical_margin_budget))`. El margen es una restricción independiente dimensionalmente en USD; se traduce a lotes con margen/lote, no se trata directamente como riesgo de stop. Restar previamente sólo aquello que no resta ya el libro único. **Reservas no duplicadas**.
- Lotes físicos sólo en grilla del instrumento (`0.01` min/step sujeto a snapshot real por símbolo); `floor(theoretical_lots / step) * step`. Si lotaje viable < mínimo → `UNFUNDABLE_MIN_LOT`; NUNCA elevar a 0.01 por debajo del riesgo. Para compra usar ASK y cierre/SL BID; venta usa BID y cierre/SL ASK. Incluir fees al OPEN, posibles costes de cierre, swap, spread, gaps y slippage con evidencia; no double-charge de spread.
- No controles estratégicos heredados (haircut de tres pérdidas, cuota fija de 15/7,5/10%, reducción 0.8 del margen) como puertas ocultas. Tampoco eliminar límites físicos, techo 5% o seguridad BROKER.
- **Un único libro PAPER SQLite** por corrida/cuenta, atomiza `RESERVE → PAPER_FILL → PAPER_SETTLE/CANCEL` y registra `UNASSESSABLE`, persistencia, idempotencia, reconciliación `cash+held_risk+margin`, 3.368 recibos. La divergencia #745 `PaperQDLE` vs #746 `QDLE(research_paper_mode=True)` está sin resolver. No ejecutar ni aceptar financiera comparativa mientras haya ambas rutas autoritativas.

## 2. Matriz obligatoria: MISMA lógica de señal, salida, datos y política salvo intervención

| Brazo | BANK cap solicitado | NDX100 comisión PAPER | Clasificación |
|---|---:|---:|---|
| **A-X** | 1.25% NAV | $0/lote | Control de política, régimen de índices publicado |
| **A-Y** | 1.25% NAV | $20/lote | Estrés sintético de costes — **NO comisión real** |
| **B-X** | Hasta 5% NAV dinámico | $0/lote | Candidato política corregida — régimen publicado |
| **B-Y** | Hasta 5% NAV dinámico | $20/lote | Política candidata bajo estrés sintético |

MEDIUM y ATTACK tienen ambos techo solicitado 5% NAV, siempre limitados por el 5% total del libro. La elección de modo la realiza Native MAX a T **sin usar desenlaces futuros**; salvo política BANK el modo calculado no se modifica entre brazos. Para causalidad financiera, reportar `matched_original_fingerprints`, `OPEN_A_ONLY/B_ONLY/BOTH/NEITHER`, nuevos fill prices, lotes, fees, compromiso y NAV por época. **No** atribuir diferencias a una señal sin un control pareado.

Las variantes Y jamás se publican como cuentas con comisiones broker reales. `B-X` no presume que riesgo solicitado sea idéntico al real; `actual_risk<=budget`, siempre.

## 3. Stop económico por modo, ATR14 verdadero y cuatro temporalidades

**Definición del ATR14:** Wilder True Range con 14 observaciones previas *completamente cerradas* antes de decidir; mantener timeframe nativo `ctx_timeframe` de la fuente original (VT31 M1; VT08 M15; Turtle H1/H4), símbolo, timestamp, provider/digits y fuente hash. Ninguna vela que termina después de decisión ni ATR de M5 sustituye sin evidencia a M1/H1/H4. Si faltan suficientes barras nativas → `UNASSESSABLE_MISSING_NATIVE_TF_ATR`.

| Modo | Multiplicador ATR14 |
|---|---|
| BANK | 0.50 |
| MEDIUM | 1.00 |
| ATTACK | siguiente tabla |

| Instrumento | M1 | M15 | H1 | H4 |
|---|---:|---:|---:|---:|
| AUDJPY | — | 1.50 | 1.75 | 2.00 |
| EURUSD | — | — | 1.50 | 1.75 |
| GBPJPY | — | 1.75 | 2.00 | 2.00 |
| GBPUSD | — | 1.50 | 1.75 | 2.00 |
| NDX100 | 2.00 | — | — | — |
| XAUUSD | — | — | 2.00 | 2.00 |

Cruces `(instrument, timeframe)` sin regla explícita ATTACK → `UNASSESSABLE_UNDEFINED_ATR_MULTIPLIER`, nunca interpolar. Guardar geometría de SL estructural del Trader en expediente; comparar SL económico propuesto con el estructural, broker stop-level y riesgo del contrato. Si la política permite SL económico *más ancho* que SL estructural, registrar `ATR_STOP_WIDENS_TRADER_STRUCTURAL_RISK` y abortar o pedir aceptación **específica** en investigación; no cambiar silenciosamente la definición económica de la señal.

**CRÍTICO:** en PAPER se puede usar una política de SL alternativo al SL estructural solo como **brazo explícito de investigación** y recalcular lote y riesgos, no atribuirlo al Trader original. El `R` y MFE/MAE se conservan por stop original y stop candidato para comparabilidad.

## 4. Tarifas verificadas como PROGRAMAS publicados vs tarifas históricas efectivas

La documentación oficial Stellar Instant ([reglas detalladas](https://help.fundednext.com/en/articles/11641300-what-are-the-commission-charges-for-the-stellar-instant-account)) explica tarifa **charged only at trade opening**, no doble cargo de cierre:
- `EURUSD, GBPUSD, GBPJPY, AUDJPY`: **USD7/lote al OPEN**, USD0/lote por comisión al CLOSE, según tarifa pública; cuenta específica/historial `not_deal_verified` hasta evidencia.
- `XAUUSD`: `lots * contract_size * PAPER_OPEN_PRICE * Decimal('0.000016')` USD al OPEN, no multiplicar por 2 para Stellar Instant sin prueba de otro modelo. `contract_size=100 oz` solo si coincide con snapshot de contrato fechado. La fórmula pública también está en [ejemplos FundedNext](https://help.fundednext.com/en/articles/10701368-what-are-the-commission-charges-for-stellar-challenges-and-fundednext-accounts).
- `NDX100/NAS100`: USD0/lote al OPEN como tarifa pública, `Y=USD20/lote` **sensibilidad** hipotética, bien identificada en informe, no broker autenticado.
- **Reproducibilidad 2019–2022:** una tarifa pública de 2026 no prueba ejecuciones históricas. Se requieren contratos/snapshot históricos fechados, bid/ask, slippage, MTM y USDJPY con cronología. **Cuando no existen, solo publicar `RESEARCH_TARIFF_SCENARIO`; `REAL_HISTORICAL_BROKER_CERTIFIED=false`.** La exigencia del usuario «no proxies» hace que el gate **real histórico** permanezca bloqueado con el corpus actualmente conocido; no falsear evidencia para forzar cuatro PF.

`value_per_pip_USD(GBPJPY/AUDJPY, T) = (contract_size * pip_size_JPY) / USDJPY_observed_at_or_before_T`, normalmente `1000 / USDJPY(T)` para 100k unidades y 0.01 JPY pip; si falta `USDJPY(T)` predecision real → `UNASSESSABLE_NO_HISTORICAL_USDJPY`. EURUSD/GBPUSD 10 USD/pip/lote para pip 0.0001 y contrato 100k; XAUUSD 1 USD/tick de 0.01/lote para 100 oz; NDX100 10 USD/punto/lote solo sujeto a especificación física broker. Valores dependientes del instrumento, símbolo y broker; no hardcodear si `SYMBOL_TRADE_TICK_VALUE_PROFIT/LOSS` real difiere.

## 5. Causalidad de entrada e instrumentación VT31 M1

El runner previo usa `bisect_left(M5.opened_at, market_decision_at)` y alimenta `next_M5.open` con timestamp de cotización `decision_at`: posible **look-ahead de precio predecisión**, además de retraso fill M1→M5 hasta ~5 min. Auditor previo: [protocolo exacto de 540/246](CIBO_P0_VT31_M1_TO_M5_CAUSAL_TIMING_AND_540_VS_246_SELECTION_2026-10-09.md).

Por cada señal:
1. Extraer `decision_at` de código y manifiesto Trader original de época, `first_eligible_execution_at`, `M1/M15/H1/H4` de origen, ATR14 nativo, `next_broker_tick_at`, `execution_price_at`, `last_quote_asof<=decision_at`.
2. QDLE delibera solo con precio/ticks observados `<= decision_at`; fill posterior puede cambiar precio; **volver a validar lote, stop y total all-in** justo al fill, abortar NO_FILL si supera techo 5%, log reason por fingerprint. No usar resultado de la vela M5 que todavía no cerró.
3. Si falta M1 bid/ask/tick con cobertura adecuada, VT31 etiquetar `NATIVE_M1_FILL_NOT_VERIFIED` y no atribuirle el PF del desplazamiento a su estrategia nativa. No atribuir disminución de PF a señal rota sin resolver este defecto.
4. En el análisis de 4 brazos, si no se puede preservar fuente, tamaño/coste y bar path con causalidad no publicar PF como resultado válido: `INCONCLUSIVE_INSUFFICIENT_NATIVE_DATA`.

## 6. Gestión de posiciones PAPER, causal y física

Solo aplicar acciones **después de observar cierre de vela** y ejecutarlas **en siguiente apertura/tick**, nunca en la misma vela que disparó criterio. Una sola agenda UTC global multiinstrumento y mark-to-market flotante.

| Intervención | Condición del usuario | Restricción |
|---|---|---|
| Parcial | 50% al +1×ATR favorable | ambos lotes resultantes deben respetar min_lot y step (para 0.01, 50% no es físico); registrar `PARTIAL_UNFUNDABLE_LOT_GRID`, no inventar 0.005 |
| Break-even | +0.5 ATR → SL a entrada + coste de comisión | ajustar por BUY/SELL y fee USD→precio por volumen/tick; aplicar siguiente barra, no crear stop fuera de mercado |
| Trailing | desde +1.5 ATR, distancia 0.5 ATR | sólo apretar stop, never widen |
| Stop protector | después +1 ATR, stop a 0.25 ATR del precio favorable actual | sólo apretar, no colisión/broker minimum stop |
| Defensivo | retroceso 0.75 ATR desde mayor excursión favorable observada | state high-water favorable causal, no extremos de vela futura; salida posterior observable |
| Fin sesión | cerrar al fin de sesión nativo del Trader, con TZ/DST IANA | fecha/hora exacta deben derivar de fuente Trader y sesión; nunca inventar M1 final ni rellenar gaps |

Conflictos de gestión en la misma vela (TP/SL, trailing, parcial y defensiva): orden causal conservador, SL antes de TP si OHLC no permite reconstrucción intrabar, no reconocer segundo evento cuando posición ya cerró. Actualizar fees, lotes restantes, riesgo físico, cashflow, margen y MTM junto con el libro persistente. En sesiones sin precio de salida registrar `OPEN_INCOMPLETE`, no settle retrospectivo al fin conocido.

## 7. Cuatro brazos: gates, métricas y decisión

**Pre-flight obligatorio (no ejecutar full replay si FAIL):**
`3368_unique_source + 7_traders + one_canonical_SQLite_PAPER_ledger + zero_LIVE + native_TF_ATR14 + causal_VT31_M1_price + timestamped_USDJPY + authentic_instrument_cost_provenance + four_engine_fresh_votes + no_legacy_haircut + 5pct_open_risk`. Cada item debe tener booleano, fuente y SHA; ninguna flag self-reported cuenta como prueba sin test/artifact externo.

Métricas por A-X/A-Y/B-X/B-Y: 3.368 decision receipts, aperturas/settlements/no-financiables por causa, BANK/MEDIUM/ATTACK, winrate/PF global y siete Traders, por años 2019–2022, cash final, DD sobre caja y **DD MTM portfolio** (null si faltan marks completos), lotes, comisión OPEN/CLOSE por símbolo, costo/SL y riesgo real, distribución R/MFE/MAE y ambigüedad intrabar, miembros de cohortes pareadas, 0 errores de conciliación. Comparar rentabilidad **neta**, nunca ganancias solo realizadas de conjunto diferente sin estado de flotantes.

**Objetivos de investigación del usuario:** PF `>=1.0` (valor 1.0 significa break-even, **no rentabilidad positiva**), cash DD `<30%`, financiabilidad `>=40%` (= **1.348 aperturas de 3.368 como mínimo** con redondeo entero hacia arriba), PF año `>0.9` en >=3/4 años, cero errores reconciliación. Estos son **objetivos para evaluar**, no permiso para modificar riesgo, ni garantía/expectativa basada en cohortes quemadas. Para edge verificable exigir `PF>1`, `net_expectancy>0`, DD MTM con márgenes de error y OOS real independiente. Si todos PF <1, aún no se puede atribuir exclusivamente a calidad de señales mientras timing/costos/libro sean inválidos.

**Estado de implementación a 2026-10-09:** `SPEC_VERSIONED_ONLY`, autoridad dual #745/#746 pendiente, QDLE PAPER test incremental sí, nuevo runner de los cuatro brazos **no** ejecutado ni CI/artefacto confirmado. No sustituir spec por replays pasados.
