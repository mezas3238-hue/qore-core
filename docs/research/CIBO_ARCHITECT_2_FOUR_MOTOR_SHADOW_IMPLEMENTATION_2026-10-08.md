# CIBO — Arquitecto 2 / P0 — Comité económico independiente (2026-10-08)

**Rama:** `agent/cibo-architect-2-four-economic-motors-20261008`  
**Issue:** [#738](https://github.com/mezas3238-hue/qore-core/issues/738)  
**Base compartida inicial:** `df10bf9d3def78a69c02dfc1292de49a0027529f`  
**Estado:** SHADOW / RESEARCH — **NO LIVE, NO CERTIFICADO, no envía órdenes**. La existencia de estos productores no implica que estén desplegados en VPS.

## 1. Qué cambió realmente

Se añadieron las cuatro funciones nuevas sin eliminar las rutas legacy:

| Productor | Función en su módulo nativo | Unidad / razonamiento independiente |
|---|---|---|
| SIZING | `propose_p0_sizing_vote` en `cibo_account_sizing_authority.py` | USD riesgo al SL con coste roundtrip, spread/slippage documentado, y reducción por estrés adicional |
| CIBO_COMPOUND | `propose_p0_compound_vote` en `cibo_compound_capital.py` | USD: NAV QORE realizado/conciliado, protección, reservas, pérdidas flotantes adversas, defensa tras 3 pérdidas liquidadas consecutivas |
| ADAPTIVE_LEVERAGE | `propose_p0_adaptive_leverage_vote` en `cibo_marginal_leverage_utility.py` | USD margen y lotes físicos de broker por unidad, menos margen retenido y volumen agregado en la dirección |
| PORTFOLIO_COMPOUND | `propose_p0_portfolio_vote` en `cibo_core_compound_portfolio.py` | USD de fuente bancaria real no reservada, límite de pérdida conjunta, cluster correlacionado y Trader |

**Comisión de apertura y cierre:** bajo el supuesto explícito indicado por el propietario para Forex, USD7 por lote al abrir + USD7 por lote al cerrar = **USD14 por lote roundtrip**; para 0,03 lotes => **USD0,42**. El test antes empleaba USD7 como coste completo, *incorrectamente*; corregido para el test de EURUSD y documentado en `roundtrip_commission_usd_per_lot`. Este valor es supuesto de prueba para EURUSD, **no** tarifa autenticada de los seis símbolos; QDLE Arquitecto 3 debe comprobar fee completa, momento de cobro, spreads y rechazar cualquier inconsistencia. Con QORE NAV USD60 y riesgo máximo USD3, un stop de USD100 por lote y costos USD16 adicionales por lote hacen que 0,03 lotes excedan USD3 en la prueba sintética; 0,02 lotes equivalen a USD2,32 todo incluido.

**No se suman cuatro presupuestos de 5%.** `QORE_NAV_CAUSAL × 0,05` se usa como máximo por oportunidad, no como promesa de lote mínimo. NAV QORE no se obtiene del equity USD2.000 del broker. 60→3, 100→5, 40→2. Ganancias flotantes no aparecen en eventos realizados; se descuentan pérdidas flotantes y reservas al valorar solvencia.

Las políticas nuevas tienen *umbrales de investigación*, sujetos a calibración OOS: margen utilizable 80% de disponible post-reservas; presupuesto agregado de stops 15% del NAV; correlación 7,5%; Trader 10%; reducción compuesta 50% tras tres cashflows negativos conciliados. Ninguno es una regla oficial FundedNext, ni está certificado como óptimo. En cualquier momento la fuente disponible, riesgo soberano, broker y QDLE pueden reducir más. No justificar riesgo agregado 15% en producción sin ratificación.

## 2. Contrato causal común, evidencias y firmas

- `cibo_four_motor_policy.py`: `ReconciledQoreCashflow`, `FourMotorObservation`, `FourMotorProposal`, `sign_producer_receipt`.
- Un `request_id`, `trader_id`, `symbol`, BUY/SELL, `source_lane`, `account_sequence`, reloj UTC, hash de upstream y cashflows conciliados con IDs no duplicados.
- Importes `Decimal` finitos no negativos; profit realizado exige `reconciled=True` y timestamp no posterior a la decisión. Floats positivos jamás acreditados como capital.
- Fail-closed de evidencia broker: quote UTC a menos de 10 segundos, nunca futuro; los tres flags explícitos `broker_fees_complete`, `broker_profit_valuation_complete`, `broker_margin_valuation_complete` deben ser verdaderos. Un flag en un test sintético **no prueba** autenticidad MT5; ésta sigue pendiente del Arquitecto 3.
- Cada función emite límites, evidencia de la decisión y `reason_codes`, en su propia unidad física.
- Firma HMAC SHA256 con **clave individual del productor**, inyectada por el servicio de ese productor, no por un harness con las cuatro claves. `source_event_sha256` firma el contenido canónico del recibo y `upstream_event_sha256` vincula el dato recibido.
- El receptor QDLE existente exige identidad de productor, cuatro hashes diferentes, HMAC distintas, match exacto de límites, epoch y frescura <= 10 segundos. La comprobación real de autoría del feed broker y la gestión aislada de secretos, en despliegue, están **pendientes**: un hash válido por sí solo NO certifica un deal auténtico.
- `cibo_four_motor_qdle_proposal.py` convierte las cuatro propuestas nativas en `QDLEIntent`. NO publica Treasury approval, NO llama `order_send`, NO abre posiciones. Arquitecto 3 valida `order_calc_profit`, `order_calc_margin`, `order_check`, lot grid, fees reales, slippage, account sequence, fuente y reservas atómicas antes de todo LIVE.

**Contrato cruzado que Arquitecto 3 debe revisar:** QDLEAccount.qore_trading_capital_usd y QORE_NAV_CAUSAL del recibo requieren igualdad por ID+epoch con libro autenticado; fee `QDLESymbol.fee_usd_per_lot` debe coincidir con roundtrip de observación; `slippage_usd_per_lot` debe ser sólo buffer incremental sin doble cobrar spread que ya está en entry Bid/Ask. Si hay discrepancia, bloquear propuesta/no enviar. Conectar cuatro secretos distintos en servicios realmente aislados, no generar recibos de muestra en Treasury.

## 3. Cinco brazos de ablación (todavía capacidad, NO profit)

`cibo_four_motor_ablation.py` evalúa **las mismas observaciones y costes** bajo:
1. Control — cuatro propuestas.
2. Sin reducción discrecional Sizing.
3. Sin reducción discrecional Compuesto.
4. Sin reducción discrecional Leverage.
5. Sin reducción discrecional Portafolio.

Se conserva siempre NAV 5%, capital no protegido, fuente sin reserva, margen libre físico, límites direccionales broker, min lot y step. El módulo expone `potential_lots`, `potential_risk_usd`, constraints vinculantes y diferencia por motor al retirarlo. Si retirar uno no cambia el volumen legal, delta=0: no atribuirle rendimiento sólo porque empató el límite. **No hay PnL/DD causal hasta ejecutar replay cronológico con precios, stop, fills y gastos verificados.** Es deliberadamente `pnl_attributed=False` / `drawdown_attributed=False`.

Pruebas incluyen cuatro escenarios artificiales de restricción exclusiva, coherencia de QDLE firmado en un FakeBroker, protección contra doble conteo, pérdidas y margen comprometido, y 3.368 IDs sintéticos distintos *sin* afirmar que son las 3.368 entradas históricas financiadas. El reporte histórico de ~USD670k/DD35% fue invalidado por solvencia H8 y no debe reutilizarse como equity verificado.

## 4. Estado de pruebas y criterios faltantes

CI específica: `.github/workflows/cibo-architect-2-four-motors-p0.yml`. Usa Python 3.12, `unittest` para las nuevas pruebas y `pytest` para suites anteriores. Exigir éxito en HEAD final exacto.

Pendientes de certificación en coordinación con Arquitectos 1 y 3:
- Leer y autenticar cuenta FundedNext MT5 y las seis especificaciones físicas actuales, comisiones COMPLETAS, spread, swap, margin, provider floor; bloquear si datos stale o desconocidos.
- Consumir eventos genuinos de broker: fills/parciales, cierres, liquidaciones, fees/swap, PnL realizado y trazabilidad de dinero; productor por proceso y clave auténtica rotada.
- Blindar cambio de epoch/cotización entre voto y reserva; cruce QORE NAV con libro y reserves bajo lock; evitar cualquier doble reserva intertrader/interproceso (la única reserva real la realiza QDLE).
- Al menos control + cuatro ablations sobre las **mismas 3.368 oportunidades históricas auténticas** con costes, lotes y clocks honestos; además paper forward actual y OOS/stress. Calcular PnL, gross loss, PF, DD intratrade/cierre, rate UNFUNDABLE, oportunidad perdida y contribución no superpuesta.
- Validar instrumentos BUY/SELL de AUDJPY, EURUSD, GBPJPY, GBPUSD, XAUUSD, NAS100/NDX100 con fee y conversión actuales, adversarial slippage/gap, swap, mercado abierto/cerrado y fills parciales.
- Auditoría cruzada y GO LIVE sólo con aprobación específica del dueño, sin omitir los gates globales rojos.

## 5. Punto de reanudación

Arquitecto 2 puede continuar añadiendo backend de snapshots causales y feeds genuinos para cada productor **sin pisar QDLE ni Cognitiva CIBO**; publicar aportación monetaria sólo después de replay broker-causal y gobernanza. Arquitecto 3 debe consumir/validar estas propuestas en el boundary financiero y confirmar physical quote equality. Arquitecto 1 consume razones y decisiones del comité para gestionar posiciones, jamás para alterar su autoridad técnica de volumen.
