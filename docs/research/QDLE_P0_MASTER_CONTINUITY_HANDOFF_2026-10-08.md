# QDLE P0 — HANDOFF MAESTRO DEL MOTOR INDEPENDIENTE (2026-10-08)

**Repositorio:** mezas3238-hue/qore-core
**Branch:** agent/qdle-independent-engine-p0-20261008-001
**Base original:** e0ea443b92cfb4773d05d932f20b1d1448be46b8
**Estado:** motor QDLE implementado con CI sintética positiva; integración observacional MT5, servicio de reservas SQLite y puente de cuatro motores; **NO LIVE**, **NO CERTIFICADO**, sin aprobación física real de los 3.368 intentos de Trader Lab.


## ACTUALIZACIÓN P0 — GATEWAY MT5 LIVE + FINANZAS CAUSALES DEL 5%

**PR DRAFT:** https://github.com/mezas3238-hue/qore-core/pull/735

**VPS:** vps-vrix sigue OFFLINE según Desktop Commander; última conexión ~67 h antes de este trabajo. No se inspeccionó la cuenta FundedNext, ni existe replay real de 3 años financiado, ni se enviaron órdenes.

### Extensiones implementadas

- Motor QDLE: riesgo objetivo = 5% de equity causal actual EN CADA ENTRADA, sujeto a QORE Risk, origen de efectivo soberano, margen libre, costes reales y restricciones MT5. USD60 -> riesgo techo USD3; USD100 -> techo USD5. No se fuerza riesgo si lote mínimo es imposible.
- Aprobación financiera independiente: publish_finance_approval persiste un hash de la oportunidad + límites del cuarteto aprobados por Treasury; el token Trader no puede aprobar economía ni sustituir presupuestos luego de la aprobación. Servicio HTTP se inicia en modo enforce_finance_approval=True.
- Broker pre-send arming: arm_for_live_send revisa broker-native stop/margin al precio ejecutable más reciente, snapshot de la cuenta, riesgo 5%, estado HELD y coincidencia exacta de lotes/símbolo/SL. Transición HELD -> SENDING atómica y única; el crash o resultado incierto retiene el dinero hasta broker reconciliation. Sólo provider autentificado accede a /v1/pre-send-check.
- src/qore/infrastructure/qdle_live_submission_guard.py: puerta HTTP localhost 127.0.0.1 obligatoria, no envía órdenes; error o timeout bloquea.
- src/qore/infrastructure/fundednext_live_mt5.py: integración ANTES del order_send real, y DESPUÉS de las barreras existentes de QORE Risk, reglas proveedor, tick fresco, profit-risk y order_check. La guardia no tiene autoridad de admisión de Trader.
- scripts/qore_fundednext_runtime.py: modo LIVE configura qdle_required_for_live=True y exige QDLE_PROVIDER_TOKEN; SHADOW no cambia. Sin el productor real de contabilidad soberana + cuarteto, ese LIVE bloqueará órdenes. NO fusionar ni activar en VPS hasta completar el emisor de aprobaciones, fuentes reales y replay.
- scripts/qdle_trader_lab_replay.py: cuenta total de intentos y signal IDs únicos; un request_id duplicado devuelve RESEARCH_FAIL_CLOSED en vez de fingir otra entrada/ejecución.
- Tests: test_qdle_live_presend.py, test_qdle_local_api.py, test_qdle_trader_lab_replay.py, casos de live gateway en test_fundednext_live_mt5.py. GitHub Actions QDLE ejecuta unittest + pytest y comprueba que un veto/no autorización no llega a order_send. Todos los valores de seis activos en CI siguen SYNTHETIC_TEST_ONLY.

### Bloqueos para GO-LIVE

1. Reconectar VPS y obtener symbol_info + order_calc_profit + order_calc_margin + volume grid + fees auténticas de seis activos (NAS100 vs NDX100 por resolución explícita).
2. Construir e integrar el emisor real y autenticado de bank/cushion/equity/risk limits/MLL + las cuatro decisiones del cuarteto. Sin esos eventos FINANCE_APPROVAL la API LIVE falla cerrada, y así debe quedarse.
3. Consistencia de RiskAuthorization y QDLE en TODOS los Traders: nunca autorizar una cantidad mayor que el QORE Risk ni alterar el Trader. Si los lotajes no coinciden se pide una nueva autorización soberana y se BLOQUEA.
4. Desarrollar conciliación MT5 de fills parciales, órdenes pending, fees, slippage, swaps, hedging/netting, stop-out, y unknown results, sin liberar SENDING arbitrariamente.
5. Alimentar Trader Lab con 3 años reales, 3.368 intenciones causales originales y condiciones broker equivalentes; reconstruir gross loss, portfolio PnL, equity y DD intratrade, registrar cada UNFUNDABLE y conservar densidad sin fingir ejecución. No elevar USD670k del antiguo carrier a capital certificado.
6. Sólo entonces batería científica, OOS, control de DD ideal <=20%, tolerable <=25% sin degradar el nuevo techo realmente financiado.

**Nota:** las pruebas unitarias prueban código y bloqueos, NO rentabilidad certificada ni autoridad para entrar en real. El PR #735 debe seguir DRAFT.

---

## DIRECTIVA SOBERANA

Traders poseen decisión estratégica de entrada y ejecución, nunca el cálculo de volumen. QDLE es la única autoridad técnica para convertir límites coordinados de Sizing, CIBO Compuesto, Adaptive Leverage y Portafolio Compuesto en lotaje físico del broker. CIBO gestiona el dinero y las posiciones conforme al contrato de autoridad; QORE Risk y el bróker mantienen bloqueo físico obligatorio. No rechazar señales no significa poder inventar fills: si el broker no financia el mínimo, FAIL con recibo; no marcar como ejecutado.

El H8 de CIBO tiene prioridad máxima: los resultados antiguos de USD~670k y DD de ~35% no tienen supervivencia financieramente comprobada. Ver docs/research/CIBO_H8_REAL_CAPITAL_SOLVENCY_BLOCKER_2026-10-08.md de la rama canónica. No hacer promoción del techo ni del drawdown mientras no exista un libro contable, margen, SL y financiación físicamente reconciliados.

## IMPLEMENTACIÓN EN ESTA RAMA

1. src/qore/infrastructure/cibo_physical_lot_sizing.py
   - Calculador puro Decimal, ROUND_FLOOR, pasos/mínimos/máximos MT5.
   - Composición de límites independientes en USD y lotes; pérdidas al SL más fee y slippage.
   - Respaldo de adaptación de TraderOpportunityEnvelope; un solo núcleo para traders actuales y futuros.

2. src/qore/infrastructure/qore_dynamic_lot_engine.py
   - QDLE independiente, contrato broker-agnóstico; account/symbol events y cálculo delegado a motor físico.
   - SQLite BEGIN IMMEDIATE con libro durable, idempotencia por request_id+SHA, sumas de reservas atómicas intertrader/interproceso.
   - Bloqueo de quotes stale, cuenta distinta, instrumento no operable, source sin dinero, riesgo y margen cero, minimo no financiable, paso ilegal, alias ambiguo, preflight del broker fallido.
   - Reserva HELD -> FILL_UNRECONCILED -> ABSORBED tras snapshot posterior mostrando posición y cobertura firmada en contabilidad QORE; rechazo confirmado -> REJECTED_NO_FILL; sin liberación ante resultado desconocido.
   - Auditoría: lotaje propuesto, stop USD, costos, all-in stop, margen, límites vinculantes, identidad de broker, numero de cuentas, lotes ejecutados tras posición cubierta y pérdida/ganancia realizada declarada por recibo de broker.
   - No implementa order_send ni gestión arbitraria de órdenes.
   - Stop no garantiza que slippage/gap real no exceda el presupuesto; es coste conservador planificado, debe medirse OOS.

3. src/qore/infrastructure/qdle_mt5_read_only.py
   - Consulta symbol_info, account_info, positions_get, orders_get.
   - Usa order_calc_profit y order_calc_margin a volumen válido, convertido a USD de la cuenta real.
   - Exige validación de volumen con order_check antes de reservar; no asegura ejecución futura.
   - No autoriza inventar estructura de comisión. Requiere VerifiedFee con evidencia y firma de contrato del plan real.
   - NAS100/NDX100 resuelto sólo con alias explícito de símbolo existente en esa instalación MT5.

4. src/qore/infrastructure/qdle_cibo_bridge.py
   - Entrada universal TraderOpportunityEnvelope + CiboFourEngineLimits -> reserve_for_trader.
   - Mantiene limites de geometría del Trader, su minimum_execution_steps y obligaciones del cuarteto económico.

5. src/qore/infrastructure/qdle_local_api.py
   - Servicio HTTP sólo 127.0.0.1 con tokens independientes Trader/Treasury/Provider.
   - /health, /v1/reserve, /v1/account-event, /v1/symbol-event, /v1/fill, /v1/reject, /v1/reconcile, /v1/settlement.
   - Ningún endpoint envía/modifica órdenes. No exponer el puerto al exterior ni reutilizar tokens.

6. scripts/qdle_local_service.py
   - Proceso worker persistente de la API. No arranca si falta la cuenta MT5 correcta o secretos.
   - Por seguridad inicia NO READY hasta obtener snapshot de tesorería QORE y especificaciones MT5.
   - En producción requiere supervisión del servicio Windows y control de autenticidad de publisher.

7. scripts/qdle_mt5_metadata_publisher.py
   - Observador sin órdenes que genera eventos por cambio/poll desde la cuenta MT5 conectada.
   - --aliases especifica AUDJPY/EURUSD/GBPJPY/GBPUSD/NAS100/XAUUSD y la traducción real NDX100 si aplica.
   - --verified-fees es política del plan FundedNext exacto, no supuestos globales; revalorar tarifas por precio/contrato donde sean variables.

8. src/qore/infrastructure/qdle_signed_treasury.py
   - Verificador de eventos de tesorería firmados HMAC SHA-256 con timestamp, cuenta, época y sumber no reservado. El HMAC autentica origen, no demuestra integridad económica subyacente.

9. scripts/qdle_qore_account_event_publisher.py
   - Fusiona balance/equity/margen/posiciones del broker con banco/colchón/risk headroom firmados por QORE.
   - Rechaza cash positivo inventado por encima del equity y risk-headroom que supere equity - MLL real.
   - Sin productor soberano HMAC que mande snapshots genuinos, la publicación falla cerrada.

10. scripts/qdle_trader_lab_replay.py
    - Harness causal de eventos ACCOUNT/SYMBOL/VALUATION/INTENT/FILL/RECONCILE/REJECTED con SQLite real.
    - Registro por entrada del lote y riesgo; devuelve RESEARCH_FAIL_CLOSED al primer caso faltante/no financiable y si faltan entradas del count esperado.
    - Fuente SEALED_REPLAY_NOT_LIVE_MT5: una simulación no es demostración de fills, margen ejecutado o ganancias.
    - RESEARCH_PHYSICAL_GATE_PASS solo prueba que el dataset de eventos respetó el gate; broker_execution_proven=False y certified=False siempre.

11. Suites test_*.py y .github/workflows/qdle-p0-atomic-engine.yml
    - Cálculo de USD3 según SL, 6 activos sintéticos, NAS100/NDX100, reserva concurrente multiinstancia, idempotencia, reinicio, fees, margen, MLL, HMAC, autenticación API, bridge, y no falsa contabilización de entradas.
    - En GitHub Actions deben verificarse los SUCCESS completos tras cada commit. En caso FAIL no promover.

## ORIGEN EXACTO DE DATOS Y LÍMITES

- FundedNext/MT5 es la única fuente de broker_symbol, broker lot grid, contract_size, current tick sizes/values, margin y preflight ejecutable.
- QORE soberano es la única fuente de cuenta/subcuentas, banco, colchón, capital realmente disponible, reservas anteriores, riesgo abierto, pérdidas máximas, provider trailing MLL y garantías.
- Trader trae entry/SL/TP, lado y señal, sin lotaje.
- Sizing y Compuesto aportan límites monetarios; Portfolio Compuesto aporta fondos disponibles reales por lane y prioridades; Adaptive Leverage aporta máxima cantidad autorizada en lotes/margen. QDLE es el único cuantizador.
- El coste de comisiones en FundedNext depende del plan y símbolo; XAUUSD puede requerir tarifa porcentual del nocional. No usar tarifa Forex universal ni USD/pip universal.
- Se prohíbe duplicar el capital disponible entre banco y portafolio, y retornar mínimo de broker cuando stop-risk supera límite.
- order_calc_margin estima margen sin incluir exposición abierta en ciertos cálculos; order_check real y reservas de portfolio/cuenta son obligatorias. Revalidar cotización/fill antes de ejecutar.
- Cuenta Stellar Instant tiene en documentación pública MLL trailing de 6%, pero no se puede asumir el tipo/programa de la cuenta VPS hasta inspección.

## EJECUCIÓN / DESPLIEGUE BLOQUEADOS POR VPS Y EVIDENCIA

Durante este handoff Remote Desktop Commander informó vps-vrix **OFFLINE**. NO se obtuvo tick size real ni volumen real de FundedNext VPS; NO se puso un bot operando. Las cifras de seis activos de tests son SYNTHETIC_TEST_ONLY, nunca reales.

Para el siguiente arquitecto:
1. Verificar dispositivo conectado, cuenta y programa FundedNext, MT5 build, símbolos existentes y broker lot grid en modo SOLO LECTURA.
2. Confirmar fee schedule / swaps / conversion a USD / slippage y fuente HMAC de QORE Risk; no insertar una tarifa genérica sin evidencia.
3. Implementar en el QORE capital ledger un productor firmado por cuenta y secuencia monotónica, sin usar resultados futuros; conectar al account event publisher.
4. Instalar QDLE worker en VPS de prueba, localhost y supervisor con reinicio; demostrar fresh account/symbol, account ID, fail-closed al desconectar MT5, health, order_check.
5. Enlazar bridge con el punto de ejecución REAL de todos los Traders (antes de order_send), no sólo con el replay experimental. Mantener compare-and-swap de cuenta/cotización.
6. Revalidar fill real frente a request (precio, lotes, slippage, fees, stop y liquidación intratrade), reconciliar parcial fills y órdenes pendientes sin liberar reservas prematuramente.
7. Conectar feed signed de MARK-TO-MARKET, stop-out y real PnL. Verificar vida completa de cada posición y release sólo autorizado.
8. Alimentar 3.368 intentos con snapshots económicos broker-realistas de cada decisión en los tres años; si los datos históricos reales del broker no existen, reportar esa ausencia. Hacer comparador old multiplier vs QDLE físico pero NO promover USD670k.
9. Sólo tras full replay físicamente financiado, redescubrir nuevo techo CIBO y reducir DD <=25% (ideal <=20%), seguido de la batería científica, OOS y certificación.

**LIMITACIÓN DECLARADA**: QDLE central y su bridge están construidos; todavía hay deuda de integración end-to-end con Trader Lab original, recálculo dinámico intratrade y conectores LIVE de QORE Treasury/MT5. QDLE no demuestra hoy 3.368 fills fundables ni el capital terminal histórico. No difundir etiqueta CERTIFIED ni DEPLOYED.


## INVENTARIO REAL FUNDEDNEXT PREPARADO (PENDIENTE DE VPS ONLINE)

Se agregó scripts/qdle_mt5_read_only_inventory.py y su prueba test_qdle_mt5_inventory.py. Cuando vuelva a conectarse el agente vps-vrix, ejecutar la captura en la instancia Windows donde MT5 está asociado a la cuenta correcta, SIN operar ni alterar posiciones:

    set QDLE_MT5_ACCOUNT_ID=<login de la cuenta, solo como variable local>
    python scripts/qdle_mt5_read_only_inventory.py --output qdle_mt5_observed_specs.json

El inventario registra de modo observacional para AUDJPY, EURUSD, GBPJPY, GBPUSD, NAS100/NDX100 y XAUUSD: MT5 exact symbol, lot min/max/step/limit, contract_size, tick size/value, profit currency y trade mode; no guarda login ni inventa comisiones. Ambigüedad NAS100/NDX100 y cualquier otro alias requieren identificación humana respaldada por contrato real. El código publica todas las coincidencias observadas y retorna error si faltan o sobran. Un resultado unit-test sintético no constituye observación de FundedNext.

Luego verificar fees/commission y símbolo específico, publicar el mapa autorizado para el provider event pump y obtener aprobaciones reales de QORE Risk/Treasury. El presente PR NO está desplegado ni aprobado para trading; preservar toda evidencia y el veto H8 hasta 3-year financed replay.

