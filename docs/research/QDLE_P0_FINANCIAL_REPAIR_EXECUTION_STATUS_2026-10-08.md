# QDLE — EJECUCIÓN DE REPARACIONES P0 Y GATES DE CERTIFICACIÓN

**Estado a 2026-10-08:** remediaciones concretas implementadas y probadas en GitHub; **NO hay certificación financiera ni autorización LIVE**.
**Repositorio:** `mezas3238-hue/qore-core`.
**Rama de trabajo:** `agent/qdle-independent-engine-p0-20261008-001`.
**PR:** [#735 QDLE P0 (DRAFT)](https://github.com/mezas3238-hue/qore-core/pull/735).
**CI de motor:** [QDLE P0 Atomic Physical Lot Engine #37847261427](https://github.com/mezas3238-hue/qore-core/actions/runs/37847261427) — **SUCCESS**. 67 pruebas unitarias + 3 pytest de integración gateway aprobadas en SHA `fea2b85e8ccbf1de172ffeb698f815123eb76b9f`.

## Directiva económica sin confusiones

- QORE cuenta con **USD60 de capital económico interno inicial**: riesgo objetivo `0.05 * QORE_NAV_CAUSAL`, dinámico en USD por cada señal. Ejemplo: $60->$3, $100->$5, $40->$2.
- FundedNext **USD2000 broker** proporciona financiación de margen, **no es el denominador del 5%**. Debe cumplir free margin, posiciones, pérdidas y reglas reales del proveedor.
- Las decisiones de Sizing/CIBO Compuesto/Adaptive Leverage/Portafolio Compuesto son **topes diferentes que QDLE interseca**; NO suman cuatro presupuestos del 5%.

## Reparaciones de código efectuadas

### P0.1 — Comisiones de ida y vuelta para LIVE

`VerifiedFee` ya no acepta la mera comisión de apertura como coste total de ejecución. Requiere `covers_open_and_close=True` y evidencia específica de tarifa completa; la función MT5 de inventario marca solamente tarifas completas con `BROKER_ROUND_TRIP_VERIFIED:`. El **LIVE pre-send** bloquea símbolos con comisiones desconocidas o provenance research/screenshot. Las capturas aportadas muestran $7/lote para **apertura Forex**, pero **no confirman** tarifa de cierre. NDX100 no tiene comisión confirmada y XAUUSD tiene 0,0016% sin base acreditada. No inferir cierre igual a apertura sin prueba.

### P0.2 — Cadena de órdenes y liquidaciones sin duplicidad

Cuando `enforce_finance_approval=True`, `acknowledge_fill` rechaza confirmación de un fill antes de `arm_for_live_send` (estado `HELD` no es broker enviado). Base de datos dispone de `broker_settlements` con `deal_receipt` y `request_id` únicos, evitando doble atribución de PnL. Migración automática al reinicio reconstruye el registro desde `BROKER_REALIZED_SETTLEMENT` en audit; conflictos en el histórico fallan cerrados. El modelo de fills parciales/netting completo sigue **PENDIENTE**; no inventar ticket ni reconciliar un lote parcial como completo.

### P0.3 — Trazabilidad de los cuatro motores

Una aprobación productiva QDLE exige cuatro **recibos de evento distintos**, uno por Sizing, CIBO Compuesto, Adaptive Leverage y Portafolio Compuesto, ligados a la misma señal y secuencia de cuenta, ≤10 segundos, con topes económicos numéricamente iguales al intent aprobado. Se conserva `module_evidence_json` con el registro de la aprobación; no se permite sustituir pruebas o presupuesto después de aprobar. `/v1/finance-approval` transmite los recibos. **Muy importante:** un hash único acredita identificación, pero **NO verifica por sí mismo firma ni razonamiento del productor**. Faltan conectores originales y autenticación/validación de sus fuentes económicas antes de certificar los cuatro motores.

### P0.4 — Gate financiero explícito

`scripts/qdle_3368_financial_truth_gate.py` impide que el workflow califique el replay de CIBO como rentabilidad/broker real. El 5% presupuestado se respeta en las propuestas, pero bajo resultado R estructural 2019–2022 con tarifas y margen foto 2026 se observaron **272 pérdidas simuladas >5% NAV** y **777 pérdidas > reserva inicial al stop** en la variante 0.01/sin límite proveedor supuesto. Son pérdidas del outcome proxy; **no equivalen a 272 incumplimientos reales de orden MT5**. Sin Bid/Ask, gaps, slippage, comisiones totales, MTM y deals no puede certificarse la protección del 5%.

## Batería demostrada en GitHub

- QDLE Core: cálculo físico, reserva SQLite, source-lanes, concurrencia, idempotencia, reinicios, 5% capital QORE vs equity broker.
- LIVE pre-send: aprobación coordinada, precio/cuenta cambiantes, one-shot, sin mutación de broker.
- Broker fees: all-in verificado vs entrada-only USD7, bloqueo presend con contrato synthetic.
- Cuatro motores: rechaza falta de evidencias, duplicadas, caducadas, límites alterados.
- PnL: prohíbe duplicar un deal del bróker, recupera registro al reiniciar SQLite.

**Interpretación de SUCCESS:** confirma únicamente los contratos automatizados de software ensayados. No confirma operación con FundedNext ni los cuatro algoritmos cognitivos funcionando económicamente.

## Trabajo que NO se puede declarar reparado sin más información o desarrollo

1. **Datos actuales autenticados MT5:** bridge `qore-vps-control` está disponible para lectura, pero aún no hay snapshots terminal `order_calc_profit/order_calc_margin`, cotizaciones Bid/Ask ni estado completo del libro y especificaciones bajo identidad FundedNext. No lanzar `order_send` para investigar.
2. **Tarifas verificadas:** comisión total entrada+cierre/índice/oro, spreads, swap/rollover, slippage y conversión FX JPY en USD de cuenta; solo entonces habilitar `VerifiedFee`.
3. **Motores reales:** conectar emisores genuinos de las cuatro cognitivas económicas al bridge/treasury, verificar firmas y provenance y emitir decisiones con impacto incremental evaluable por `trade_id`; hacer ablaciones con iguales entradas.
4. **Vida de orden:** llenado parcial, diferencias netting/hedging, deal IDs, recuperaciones crash, cancellations con confirmaciones verificadas y conciliación de saldos de QORE/MT5.
5. **Reglas FundedNext y DD:** verificar programa, pérdida máxima, daily loss, trailing/static, equity flotante, liquidación/stopout y estrés de gaps; nunca presentar pérdida real garantizada exactamente al 5% ante slippage.
6. **Replay auténticamente actual:** capturar y versionar ticks, spreads y operaciones paper actuales; el archivo 2019–2022 solo permite un ensayo contrafactual de geometrías. No hay rentabilidad actual comprobada.
7. **Gates CI globales:** `QORE CIBO Zero Open Work Gate` y `Legacy Stack Quarantine` permanecen rojos por asuntos fuera del calculador físico; no suprimir esas reglas ni marcar PR aprobado.

## Reglas de trabajo siguientes

**No usar el éxito de GitHub Actions como certificado financiero**. Mientras los seis puntos anteriores no sean completados/validados: `QDLE_CERTIFICATION=REJECTED`, `PR_DRAFT=TRUE`, `LIVE_ORDERS_ALLOWED=FALSE`. Probar cada corrección en la batería QDLE y después en un replay causal con evidencia por orden; mantener intacta la población de 3.368 señales pero diferenciar señales, propuestas, fills paper y fills bróker.

**Objetivo:** descubrir techo económicamente financiable de CIBO con 5% dinámico del QORE NAV y DD deseado 20%, máximo tolerable 25% **solo cuando haya datos para medirlo**.
