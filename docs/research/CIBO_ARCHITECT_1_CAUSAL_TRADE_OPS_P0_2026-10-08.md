# CIBO ARQUITECTO 1 — CORTE P0: DIRECTOR CAUSAL DE OPERACIONES (2026-10-08)

**Issue propietario:** [#737](https://github.com/mezas3238-hue/qore-core/issues/737)
**Branch:** `agent/cibo-architect-1-cognitive-trade-ops-20261008`
**Base común:** `df10bf9d3def78a69c02dfc1292de49a0027529f`
**Referencia:** `QORE_CIBO_THREE_ARCHITECT_MASTER_HANDOFF_2026-10-08.md`

## Alcance ejecutado (incremento de código)

- `src/qore/infrastructure/cibo_trade_ops_director.py`: máquina de estados inmutable por `signal_id`, operador Trader y símbolo/dirección. `apply_trade_event` exige recepción de señal, valoración económica, financiación externa o `UNFUNDABLE`, envío confirmado, parcial/completo, gestión y cierre. Conserva IDs de evento, orden, deal y posición. Hash encadenado auditable. No asigna lotes ni capital.
- `decide_position_management`: propuestas de gestión **no ejecutables** basadas en evidencia con reloj causal, precio relevante de salida (Bid para BUY; Ask para SELL), ATR, spread, stop estructural, noticias, correlación y presión de piso proveedor. Propone protección a breakeven solo bajo ventaja marcada al menos 1R con precio de salida realista; nunca mueve stops ni contabiliza beneficio.
- Cobertura de errores: estado ilegal, fill sin orden financiada, origen broker no marcado verificado, volumen ejecutado superior al aprobado, reuso de deal/evento, reversión de tiempo, features futuros, ATR/cotización stale, stop ampliado, negativa de financiación trazable.
- `tests/infrastructure/test_cibo_trade_ops_director.py`: 17 tests locales unittest; incluye matriz de seis activos BUY/SELL y prueba de **3.368 IDs ficticios sintéticos**, que NO constituye reproducción del dataset histórico ni prueba de 3.368 fills.
- `.github/workflows/cibo-architect-1-trade-ops.yml`: pipeline aislado por branch/PR, Python 3.12, suite indicada.

## DIRECTIVA P0 — ADMINISTRACIÓN TOTAL DE LA MECÁNICA MT5 EN QDLE

El propietario confirmó expresamente el **2026-10-08** que **todo** lo recabado de las fichas MT5 corresponde a **QDLE**, no a CIBO. [Observaciones visuales e inventario transferido a QDLE](CIBO_ARCH1_MT5_SCREENSHOT_OBSERVATIONS_2026-10-08.md). Las capturas son referencia histórica de pantalla, **no** contratos activos ni coste total verificado.

- **QDLE / Arquitecto 3:** única autoridad técnica de la interfaz económica/física de MT5. Custodia especificaciones por instrumento y hora, precios Bid/Ask y sesiones de servidor autenticadas, contratos/ticks/min/max/steps, divisas, conversiones de ganancia JPY→USD, comisiones de ambas patas, swaps/rollover, margen, apalancamiento/capacidad, valoración de riesgos SL/TP antes y después, tope volumen e idempotencia/reservas y conciliación real de órdenes y deals. Verifica reglas broker/provider y presupuesto emitido por el comité económico; falla cerrado si hay datos incompletos o obsoletos. `order_calc_profit`, `order_calc_margin` y `order_check` son comprobaciones del adaptador MT5 según corresponda; el valor de una captura nunca reemplaza a estos cálculos.
- **CIBO / Arquitecto 1:** director cognitivo: comprende régimen, entorno, tesis, invalidación, defensa de pérdidas y protección de beneficios, seguimiento de toda señal, propuestas de stop/TP/trailing/partial close con justificación causal. **No gestiona ni calcula** lotes, fees, márgenes, swaps, conversiones, balance, pérdidas nominales ni posiciones MT5 mediante su propio libro físico. Recibe de QDLE *receipts* verificables para razonamiento. Ninguna propuesta equivale a modificación/ejecución.
- **Sizing / CIBO Compuesto / Adaptive Leverage / Portafolio — Arquitecto 2:** dictaminan cuatro decisiones independientes sobre presupuestos, NAV QORE, leverage permitido y exposición/correlación; **QDLE** transforma esos límites en lotaje físico ejecutable y aplica el 5% dinámico QORE (USD60 → USD3 al inicio), no 5% sobre USD2000 FundedNext ni cuatro veces 5%.
- **Trader / gateway autorizado:** responsable de enviar/actualizar/cerrar órdenes luego de todos los gates. QDLE no dispara órdenes arbitrariamente y CIBO tampoco; MT5 es la fuente de la confirmación real de cada fill.

**Contrato de ida y vuelta:** CIBO solicita revisión de gestión `signal_id + position_id + proposed_stop/tp/partial`; QDLE responde con valuación broker-native autenticada `risk_before_usd/risk_after_usd + commission+spread+swap+margin_delta + provider/QORE gate + as_of + evidence_hash` o denegación motivada; el gateway Trader decide/envía bajo autoridad permitida, QDLE reconcilia ticket/deal y CIBO actualiza la gestión únicamente desde recibos. Las unidades y procedimientos exactos requieren acuerdo de interfaz con #738/#739; no fingir que ya están conectados.

**Nuevo requisito P0 de comisión de APERTURA (propietario, 2026-10-08):** QDLE debe estimar tarifa de entrada antes de reservar y conciliar el **débito real por deal/fill** cobrado por MT5 después de la apertura, separado del fee total reservado y de la comisión del cierre. El receipt de QDLE debe incluir `actual_open_fee_usd`, `deal_id`, `filled_lots`, procedencia y ajuste de NAV QORE sin doble contabilización. CIBO consume esos recibos solo para gestión cognitiva; no reproduce tarifa ni acredita cargos. Documento de aceptación y gaps de código: [QDLE_P0_OPENING_COMMISSION_BROKER_DEBIT_CONTRACT_2026-10-08.md](QDLE_P0_OPENING_COMMISSION_BROKER_DEBIT_CONTRACT_2026-10-08.md). Su implementación corresponde a Arquitecto 3 (#739); no está certificada actualmente.

## Contrato entre los tres arquitectos

El Trader genera la oportunidad y ejecuta exclusivamente mediante gateway autorizado. Arquitecto 2 debe entregar `ECONOMICALLY_VALUED` y `ECONOMICALLY_FUNDED` o `UNFUNDABLE`, con su propio `request_id`, cuatro decisiones independientes, fuente, hash, times y cantidades aprobadas. El volumen `requested_lots` del evento financiado representa la salida **ya calculada por QDLE Arquitecto 3**; CIBO no calcula lotaje.

Arquitecto 3 debe proveer adaptador autenticado MT5/QDLE que reconstruya `ORDER_SUBMITTED`, `PARTIAL`, `FILLED`, `ORDER_REJECTED`, cancelación de restante y `CLOSED` desde órdenes, deals y cambios de posición firmados/contrastados. `broker_verified=True` en este módulo es **solo una aserción del productor**, NO verifica HMAC ni autenticidad por sí misma. No es seguro enchufar un emisor externo sin la comprobación de identidad/procedencia del Arquitecto 3. El hash encadenado prueba integridad lógica de inputs suministrados; sin firma y almacenamiento durable no prueba veracidad externa.

La valoración económica `current_stop_risk_usd` y `breakeven_stop_risk_usd` es opcional y solo puede introducirse junto con `valuation_as_of` y `valuation_sha256` de un proveedor confiable. Si no existe, los campos de riesgo quedan `None` y no se fabrican pérdidas/beneficios. `execution_authorized` siempre es `False`; cualquier propuesta requiere autorización de Risk / comité económico, verificación QDLE de pérdidas, costes/margen y ejecución por Trader Gateway.

## Decisión de mesa y límites científicos

**Regla demostrativa**, NO calibrada: tras 1R favorable calculado en precio actual de salida, se puede proponer mover stop a entrada siempre que no empeore stop actual; reglas de noticias/piso/correlación/propagación de spread producen aviso defensivo. `ESCALATE_STOP_BREACH` no es evidencia de fill de stop; verificar broker. `REQUEST_STOP_TO_BREAKEVEN` no implica breakeven económico: spreads, fees, swaps y slippage pueden causar pérdida neta.

El módulo actual es un **contrato aislado de primer corte**, sin conexión a los productores reales de Shared, Trader Manager, QDLE o MT5 y sin IO/durabilidad propia. Las 17 pruebas son sintéticas. No existe comparación incremental de PnL/DD frente a baseline, paper live ni holdout OOS aprobado. Las curvas research históricas de $670k, DD~35% y replays financieros anteriores siguen INVALIDADAS/no certificadas por H8 y la auditoría financiera de PR #735. No publicar ganancia, PF o DD nuevos con este corte.

## Próximo lote P0 para Arquitecto 1

1. Añadir `CIBO_MANAGEMENT_DECISION` como evento de auditoría persistente por señal/versiones/posición, incluyendo autoridad y callback broker de aceptación/rechazo de cambio SL/TP, y traducción de señal Trader al contrato sin descartar ninguna oportunidad.
2. Integrar observaciones predecisión causalmente correctas desde `cibo_cognitive_*`, Shared y sensores de régimen, noticias, correlación, sesiones y DD; comparar alternativas vs control sin leakage.
3. Ejecutar replay realista con el Arquitecto 3 sobre señales versionadas y ticks Bid/Ask/costes reales y ablation por política en holdout 3 años. Reportar pérdidas brutas, MTM DD, net PnL, PF, señales procesadas, fills verificados y diferencias; no inventar ejecución.
4. Contrato económico firmado y de riesgo antes/después con Arquitecto 2; vetos legítimos de presupuesto quedan como `UNFUNDABLE`, nunca desaparición de señal.
5. Mantener PR **DRAFT / NO LIVE** hasta revisión cruzada #738/#739, firmas verificables, pruebas CI exact-SHA y autorización explícita de despliegue.

**No modificar código de los otros arquitectos ni desactivar gates globales rojos.**
