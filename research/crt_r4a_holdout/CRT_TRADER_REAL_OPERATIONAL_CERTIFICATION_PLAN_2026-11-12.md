# QORE CRT Trader — Programa REAL de certificación operativa
**Fecha:** 2026-11-12 UTC | **SSOT:** mezas3238-hue/qore-core PR #1007 | **estado:** NO CERTIFICADO / SIN ÓRDENES / NO LIVE / NO VPS / NO MERGE.

## Decisión arquitectónica
El Owner exige **un trader operable** y certificable, no un indicador con `strategy()` ni un
reporte visual que atribuya rentabilidad a eventos CRT. El indicador Pine es el contrato fuente
de detecciones; el trader cTrader DEMO debe tener motor autónomo causal, modelo de entradas
y salidas, dimensionamiento por riesgo, validación de costos, protección en broker, reconciliación
de posiciones, telemetría auditable y certificación externa al desarrollo.

**No reinterpretar 23.919 señales como 23.919 operaciones.** El resultado de 2024-2025 consta
de 23.919 eventos estructurales en 33/34 fuentes M5, con BTCUSD ausente y 12/33 archivos
Atlas sin paridad IC. Es retrospectiva **BURNED**, no validación económica nueva, no se conocen
PF/DD/PnL netos certificados.

## Componentes implementados ahora

| Componente | Ruta | Alcance |
|---|---|---|
| Detector Pine original congelado | `pine/QORE_CRT_TRADER_R1_V34_12X_ORIGINAL_ENGINE_QA.pine` | Misma `f_engine()`; estrategia visual, **no compilada ni validada en TradingView** |
| Siete eventos CRT en 33 orígenes históricos | `seven_family_event_tape.py` | 23.919 eventos estructurales, no trades |
| Propuesta de compra/venta por broker | `src/qore/infrastructure/traders/crt_r4a_protected_candidate.py` | Rechaza señal vieja, fuente distinta, spread, volumen, riesgo, SL/TP sin geometría |
| Plan relativo cTrader para MARKET | `src/qore/infrastructure/traders/crt_r4a_native_bracket.py` | Construye distancias `relativeStopLoss`/`relativeTakeProfit` en 1e-5 del precio, sin órdenes |
| Conexión DEMO preexistente | `src/qore/infrastructure/ctrader_demo_operational_runtime.py` | Ejecución autenticada de órdenes **ya autorizadas**; todavía NO conectada al CRT |
| Gate de activación | `crt_operational_release_preflight.py` | Informe automático **BLOCKED_NOT_CERTIFIABLE** a falta de verdad externa |

La propuesta mantiene `can_submit=False`: ni el detector, ni CIBO, ni el script de prueba
deben crear una `ExecutionSubmission` o elevar su propia autoridad. Solo un gate separado,
con firma/evidencia auditada, podrá solicitar a QORE Risk una autorización temporal; el
`ExecutionSafetySwitchSnapshot` y el gateway original conservan la autoridad de veto.

## Bloqueo concreto de protección en cTrader
El `CTraderOrderCreatePlan` ahora admite los campos **opt-in** `relative_stop_loss` y
`relative_take_profit`, y `CTraderOpenApiExecutionTransport.submit_order()` los puede
codificar como `relativeStopLoss`/`relativeTakeProfit` de MARKET. **Sin embargo, el
constructor canónico `build_ctrader_demo_order_create_plan()` y el gateway existente
siguen creando planes SIN ambos campos.** Por tanto el CRT no dispone aún de una ruta
segura y certificada para abrir una operación protegida.

El protocolo oficial cTrader **no permite SL/TP absolutos en MARKET**. Para MARKET dispone
de `relativeStopLoss` y `relativeTakeProfit`, enteros en unidades 1/100000 del precio.
Referencia: https://help.ctrader.com/open-api/messages/ (ProtoOANewOrderReq).

**Próximo desarrollo bloqueante:** evolución retrocompatible y tipada del contrato de orden
y del plan/transport cTrader para transmitir AMBAS protecciones, comprobar rangos de símbolo,
límites del broker y **verificar SL/TP realmente asociados a la posición tras el fill**.
Un texto enviado no equivale a protección confirmada. Nunca abrir CRT sin protección
server-side; un SL no garantizado NO limita pérdidas extremas si hay gap o fallo del broker.
No ejecutar siquiera canary CRT DEMO hasta pasar ese gate; tampoco ejecutar MARKET y
enviar SLTP luego como solución provisional que deje la posición desnuda.

## Doce requisitos de certificación (todos deben tener evidencia)

1. **Motor del indicador real:** compilar Pine original y trader R1; comparar por
   símbolo/familia/vela/C1/SL sweep/MSS, 100% exactitud causal contra el motor autónomo;
   reconocer todas las familias superpuestas, sin falsos MSS15 o lookahead.
2. **34 mercados:** recibir fuente broker identificada, Digits, TickSize, volumeMin/Max/Step,
   unidad económica, horarios, DST, hash por proveedor; homologar 12 Atlas y recuperar BTCUSD.
3. **Cinta M5 y ticks/bid-ask reales** con cobertura suficiente y pruebas de continuidad,
   spread, horarios, slippage de noticias y sesión.
4. **Siete libros independientes** de oportunidades con evento ID estable y sin doble PnL,
   mismo instante / señales opuestas resueltas por política congelada.
5. **Entradas y salidas** congeladas antes de analizar validación; órdenes MARKET/LIMIT,
   cancelación/expiración, fill parcial, SLTP, cambio de condición, lifecycle y reconciliación.
6. **Costos verificables** y conversión PnL a moneda de cuenta, swaps, comisiones,
   spread, slippage, especificación contractual y garantías de stop.
7. **Ventana económica independiente de 24 meses sin exposición previa:** 2024-2025
   ya fue usado para investigar y ajustar. Cualquier nuevo set debe certificar origen,
   SHA, bloqueo de acceso y fecha de congelación.
8. **Estabilidad y edge OOS:** expectativa después de costos positiva, PF neto objetivo
   al menos 1.50, PF OOS combinado objetivo 1.70, sample suficiente por familia/
   régimen/símbolo, no selección oportunista por ver ganadoras.
9. **DD y robustez:** DD en R explícito, MC p95 DD objetivo <=15R y
   preservación de ventaja ante spread/slippage mayor, gaps, DST y períodos de crisis.
   Objetivos son *criterios de laboratorio propuestos*, no resultados logrados.
10. **Protocolo Risk/CIBO:** equity real DEMO de cuenta elegible, riesgo por evento
    y cartera, correlaciones, DD diario, max posiciones, idempotencia, kill switch;
    ningún módulo de señal se autoaprueba.
11. **Pruebas de ejecución real DEMO:** órdenes protegidas en broker,
    posiciones reconciliadas, pérdida máxima, desconexión/timeout, replay del mismo
    evento, resultado desconocido, parcial, cancelación, recotización, reinicio.
    Cero posiciones sin SL/TP nativo confirmado y cero duplicados atribuibles a bot.
12. **Forward DEMO con reglas congeladas y auditoría independiente:** período y mínimo
    de operaciones definidos antes del ensayo, resultados netos consistentes
    con backtest, revisión final humana y aprobación expresa del Owner.

La certificación **técnica** (correcta operación segura) y la **económica** (edge neto
robusto) son dos PASS distintos. NO LIVE o capital real hasta la orden soberana
del Owner, independientemente de que un reporte diga PASS.

## Próxima acción sin fragmentar proyectos
1. Completar transporte con SL/TP nativos cTrader y pruebas adversariales;
2. Validar fuente 34 y paridad exacta Pine;
3. Obtener datos bid/ask y cerrar evaluación neta por familia;
4. Conectar a Risk/CIBO y ejecutar DEMO forward protegido;
5. Emitir certificado reproducible sobre un commit congelado, no sobre la
   cantidad de PASS unitarios.

**Status actual: BLOCKED_NOT_CERTIFIABLE. La existencia del código no habilita órdenes.**
