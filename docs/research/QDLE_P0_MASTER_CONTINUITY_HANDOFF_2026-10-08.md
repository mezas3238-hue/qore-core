# QDLE P0 — HANDOFF MAESTRO DEL MOTOR INDEPENDIENTE (2026-10-08)

**Repositorio:** mezas3238-hue/qore-core
**Branch:** agent/qdle-independent-engine-p0-20261008-001
**Base original:** e0ea443b92cfb4773d05d932f20b1d1448be46b8
**Estado:** motor QDLE implementado con CI sintética positiva; integración observacional MT5, servicio de reservas SQLite y puente de cuatro motores; **NO LIVE**, **NO CERTIFICADO**, sin aprobación física real de los 3.368 intentos de Trader Lab.


## INFORME 4 MOTORES + COSTES ACTUALES MT5 — 2026-10-08

**Enlace:** [Informe completo de comisiones, lotaje y Sizing/CIBO Compuesto/Leverage/Portafolio](QDLE_P0_CURRENT_MT5_4_ENGINE_COMMISSION_AND_LOTAGE_REPORT_2026-10-08.md). Replay GitHub Actions [37831818976](https://github.com/mezas3238-hue/qore-core/actions/runs/37831818976), exact-SHA `3e86cbe563ad64c1ab85757a6f6b1cb9cc039e17`, SUCCESS. Se incluyen topes de cuatro motores y comisión por señal en 3 informes JSON reproducibles, con 3.368 señales por caso.

**Diagnóstico P0:** Broker 0,01 sin inventar regla de trailing desconocida -> 2.113 propuestas QDLE, **USD60 a USD9,84 NAV QORE proxy**, DD cerrado 97,53%, comisión de apertura ~USD479,16, swap proxy -USD154,67. No es trading ni PnL MT5 real. Si hipotéticamente aplicamos trailing $120 -> 1.628 propuestas y stop simulado 2021-05-05, resultado no superviviente. El informe separa métrica observable de cada módulo: Sizing/CIBO Compuesto duplican techo 5%, Portafolio Compuesto no es tope final, Leverage limita margen; **no hay cuatro ganancias independientes atribuibles**. Prueba de código no implica certificación ni producción.

---

## ACTUALIZACIÓN REPLAY QDLE 3.368 / 36 MESES — 2026-10-08

**Evidencia más reciente:** [Informe replay con QDLE acoplado, comisiones, swaps y corte por provider DD](QDLE_P0_3368_DUAL_CAPITAL_PHYSICAL_LOTAGE_REPLAY_REPORT_2026-10-08.md). Run [37830200266](https://github.com/mezas3238-hue/qore-core/actions/runs/37830200266), SHA de código probado `5481bfd22cb9ec23f7953fc97f39a652ab03b313`, SUCCESS.

**Resultados**: 3.368/3.368 señales; propuesta financiable 697 (mínimo original Trader) o 1.628 (mínimo broker 0.01). Capital QORE USD60 → USD5.50 / USD125.05 modelados, DD de equity cerrado 92.86% / 87.75%. **La variante 0.01 sufre stop de proveedor hipotético el 2021-05-05 y 1.276 señales siguientes son bloqueadas; USD125.05 NO es saldo superviviente.** Resto de P&L es proxy de outcomes R investigación sin deals reales MT5. No certificar ni desplegar; continuar con ticks, account terms y reconciliación física.

---

## DIRECTIVA SOBERANA P0 — CUENTA FUNDEDNEXT USD 2000, CAPITAL QORE USD 60

**Override del propietario (2026-10-08) — prevalece sobre toda interpretación anterior que use el equity MT5 como base del 5%.**

- **Cuenta de ejecución/margen:** FundedNext MT5 tiene **USD 2.000 nominales inicialmente**, sujetos a sus propias reglas, margen libre, posiciones, trailing DD y límites de capital del proveedor. **No se asignan estos USD 2.000 como capital económico de QORE**.
- **Capital económico QORE:** cuenta virtual/ledger segregado, **USD 60 al inicio**, que registra únicamente resultados económicos reales atribuibles a QORE. Base autónoma de cálculo: \`qore_trading_capital_usd\`. No confundir con \`balance\`/\`equity\` del bróker.
- **5% único y CONSTANTE como porcentaje, DINÁMICO como monto:** \`risk_target_usd = 0.05 * qore_trading_capital_usd\` para **cada nueva señal**. Ejemplos: capital QORE $60 → stop risk objetivo $3; $100 → $5; $1.000 → $50; si cae a $40 → $2. No sumar USD 2.000 en la base ni usar 5% del broker MT5. La fracción no debe configurarse por otros módulos.
- **Evolución causal del capital:** un emisor QORE firmado y reconciliado calcula la cartera económica neta de resultados realizados, fees, swaps y pérdidas; floating losses reducen prudencialmente la capacidad, mientras ganancias flotantes no pueden inflar el capital antes de realizarse/conciliarse. Nunca añadir depósitos ficticios ni aplicar a la cuenta interna 5% de equity externo.
- **Cuarteto:** Sizing, CIBO Compuesto, Adaptive Leverage y Portafolio Compuesto reciben el **mismo objetivo** del 5% QORE y responden con sus topes monetarios, reservas de capital, utilización de margen y lotes. **No hay cuatro presupuestos de 5% que se acumulen**. QDLE convierte la intersección de todos los límites y la distancia real al SL en lotaje legal; QORE Risk y reglas proveedor pueden imponer topes **inferiores** y nunca se fuerza un mínimo inviable.
- **Financiación del margen:** broker \`free_margin\` MT5, cotización actual, \`order_calc_margin\` y \`order_check\`, tras deducir reservas, órdenes y posiciones abiertas. El respaldo de USD 2.000 **no autoriza** pérdidas superiores a la capacidad neta y a los límites QORE/broker.
- **Escenario de las capturas:** con MT5 de USD 2.000 de equity y margen libre suficiente, los mínimos de 0.01 lote para **XAUUSD (~$536 margen)** y **NDX100 (~$615 margen)** podrían superar la restricción de margen que surgiría de **USD 60 de broker**, PERO aún deben superar el stop-risk máximo de **$3**, las fuentes internas, el riesgo agregado y todos los controles del proveedor. El anterior diagnóstico «XAUUSD/NDX100 no financiables con USD 60 de margen broker» **NO aplica automáticamente** a esta arquitectura de dos capas.
- **VPS/sandbox:** las pruebas y especificaciones MT5 aportadas por capturas son observacionales; no permiten proclamar fills ni resultados certificados. No activar trading real ni fusionar PR por esta actualización.

**Corrección implementada en la rama QDLE:** se incorporó \`qore_trading_capital_usd\` al snapshot QDLE (requerido), evento firmado de tesorería, publisher MT5, API local y replay. \`QDLE.reserve_for_trader\` y \`arm_for_live_send\` usan la base QORE, y la fracción está fijada en 5%. Migrar los emisores de snapshots anteriores: si falta el campo, **FAIL CLOSED**; no usar silenciosamente \`equity\` MT5 como sustituto. El código debe superar CI exact-SHA antes de considerarse probado.

**Pendiente explícito:** implementar/verificar atribución real y causal de PnL al libro QORE, reconciliar posiciones/fees/MTM y validar los límites agregados y proveedor; el campo firmado por sí solo no certifica que los USD 60 o su evolución sean verdaderos.

---

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

## ANEXO 2026-10-08 — SEIS SÍMBOLOS OBSERVADOS EN MT5 MÓVIL (OPERADOR, NO CERTIFICADO VPS)

**Proveniencia y validez:** El operador aportó capturas de propiedades/commissions/margins MT5 de los seis activos. Son **observaciones de la interfaz MT5 móvil** en una sesión puntual, no resultados de \`scripts/qdle_mt5_read_only_inventory.py\` en VPS, no evidencia de la identidad de cuenta/servidor, ni contrato histórico 2019–2022. Los USD de margen por lote en la pantalla son **aproximados**, sujetos a la cotización/condiciones de cuenta. Úsense únicamente para diseñar y contrastar el motor, nunca como fuente automática de autorización.

| Propiedad observada | AUDJPY | EURUSD | GBPJPY | GBPUSD | XAUUSD | NAS100 (bróker: NDX100) |
| --- | --- | --- | --- | --- | --- | --- |
| Símbolo visible MT5 | AUDJPY | EURUSD | GBPJPY | GBPUSD | XAUUSD | NDX100 (descripción NAS100) |
| digits | 3 | 5 | 3 | 5 | 2 | 2 |
| contract_size | 100000 | 100000 | 100000 | 100000 | 100 | 10 |
| volume_min | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 |
| volume_max | 40 | 40 | 40 | 40 | 50 | 40 |
| volume_step | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 |
| tick_size | no visible | no visible | no visible | no visible | 0.01 | 0.01 |
| tick_value (pantalla, por 1 lote) | no visible | no visible | no visible | no visible | USD 1 | USD 0.10 |
| currency_margin | AUD | EUR | GBP | GBP | USD | USD |
| currency_profit | JPY | USD | JPY | USD | USD | USD |
| Comisión observada al abrir | USD 7/lote | USD 7/lote | USD 7/lote | USD 7/lote | 0.0016% en USD por lote (base no explicitada) | no visible |
| margen BUY aprox USD/1 lote | 2318.93 | 3735.03 | 4407.40 | 4407.63 | 53637.48 | 61481.98 |
| margen SELL aprox USD/1 lote | 2318.67 | 3734.77 | 4407.40 | 4407.63 | 53629.68 | 61478.78 |
| swap long (puntos) | -11.27 | -13.472 | -25.806 | -17.13 | -107.151 | -372.912 |
| swap short (puntos) | -19.841 | +0.107 | -44.278 | -2.977 | -46.917 | -57.6 |
| día de coeficiente triple | miércoles | miércoles | miércoles | miércoles | miércoles | **viernes** |

Todas las capturas indicaron spread **flotante**, stops_level 0, permiso trading «Acceso completo» y ejecución de mercado; **ello NO equivale a permiso/autorización de órdenes de QORE ni garantiza fills**. En XAUUSD y NDX100 el modo de beneficio es «Contratos»; para los cuatro FX «Forex». En EURUSD, la captura muestra trading 00:15–23:55 de lunes a viernes; en XAUUSD y NDX100 muestra 01:15–24:00 en días hábiles, con intervalos 00:00–00:00 para NDX100 mar-jue que requieren interpretación del servidor. Husos horarios aún NO corroborados: no usar como calendario histórico absoluto.

### Impacto imprescindible en la simulación causal de USD 60 iniciales

Los márgenes mínimos *linealizados como aproximación inicial del screenshot* (margen por 1 lote × 0.01 lotes), suponiendo no haber posiciones abiertas, cotización idéntica y sin efecto de offsets por cobertura, son:

| Símbolo | Margen BUY aprox USD / 0.01 lote | Margen SELL aprox USD / 0.01 lote |
| --- | ---: | ---: |
| AUDJPY | 23.19 | 23.19 |
| EURUSD | 37.35 | 37.35 |
| GBPJPY | 44.07 | 44.07 |
| GBPUSD | 44.08 | 44.08 |
| XAUUSD | 536.37 | 536.30 |
| NDX100 | 614.82 | 614.79 |

**Corrección P0 de capital bifurcado:** para **USD 60 de capital QORE** el riesgo objetivo es **USD 3**, pero la cuenta de **margen del broker parte de USD 2.000**. La comparación con USD 60 de *margen libre MT5* del párrafo original es únicamente un contrafactual y **no corresponde al plan operativo del propietario**. Bajo las condiciones de margen de la captura, XAUUSD 0.01 requiere ~$536 y NDX100 0.01 ~$615: podrían caber en una cuenta broker de $2.000 sin exposición previa, **sujeto a la cantidad real de margen libre**. Para cada señal, QDLE debe verificar simultáneamente que el SL más costes del lote legal no exceda $3 (o el 5% actualizado de QORE), que el margen libre broker alcanza y que todos los límites QORE/provider se cumplen. Si falta capacidad por cualquier motivo, registrar \`UNFUNDABLE\` sin inventar fill ni omitir la señal de la población de 3.368.

En XAUUSD, \`tick_size=0.01, tick_value=$1/1 lote\` implica, si la tarifa de valoración permanece, **$1 de PnL por movimiento de $1 del oro con 0.01 lote**, antes de costes. En NDX100, \`tick_size=0.01, tick_value=$0.10/1 lote\` implica **$0.10 por movimiento de 1 punto del índice con 0.01 lote**, antes de costes. **No confundir PnL, riesgo al SL y margen**. El stop real y los costes deben determinar el lotaje y el recálculo secuencial del 5%; el margen puede vetar incluso la mínima cantidad.

**Pendientes para pasar de evidencia manual a inventario broker-real:** identidad correcta FundedNext/VPS, símbolo exacto NAS100→NDX100 en el servidor, tick values direccionales y su divisa, comisiones efectivas (especialmente la base exacta del 0.0016% XAUUSD y si NDX100 cobra comisión), valores \`order_calc_profit/order_calc_margin\`, coste de rollover, spread, slippage, free margin, posiciones abiertas y las reglas de cuenta. Verificar en terminal con un probe **solo lectura, jamás order_send**. Cuando se conozca la tarifa histórica se recalculará el replay con eventos del broker y marks intraoperación.

**Estado de este anexo:** 6/6 símbolos CON DATOS MANUALES observados; **0/6 certificados desde VPS/servidor** a través de este documento. Cero replay QDLE de 3.368 entradas certificado. PR continúa DRAFT / NO LIVE.
