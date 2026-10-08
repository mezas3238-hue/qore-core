# QORE Core — Contrato de integración V1 entre 3 arquitectos

**Propuesto por:** Coordinador técnico — 2026-10-08  
**Rama exclusiva de coordinación:** agent/cibo-three-architect-coordination-contract-20261008  
**Base congelada común:** df10bf9d3def78a69c02dfc1292de49a0027529f  
**Autoridades:** CIBO [#737](https://github.com/mezas3238-hue/qore-core/issues/737) · Cuatro motores [#738](https://github.com/mezas3238-hue/qore-core/issues/738) · QDLE/MT5 [#739](https://github.com/mezas3238-hue/qore-core/issues/739)  
**Handoff maestro:** [QORE_CIBO_THREE_ARCHITECT_MASTER_HANDOFF_2026-10-08.md](QORE_CIBO_THREE_ARCHITECT_MASTER_HANDOFF_2026-10-08.md)

**Estado:** interfaz acordable, no declarada implementada ni aceptada hasta tres revisiones. Este documento no activa trading LIVE.

## 1. Definición central — evitar que 3 arquitectos construyan 3 sistemas incompatibles

**Separar siempre cinco identidades que no son sinónimos:**
- \`signal_id\`: oportunidad recibida, incluso sin lotaje financiable. No se borra ninguna.
- \`proposal_revision\`: versión causal de gestión y economía. El evento firmado no se modifica.
- \`qdle_request_id\`: idempotencia para una sola propuesta física. Debe ser único por signal + revision; no reusar para señal distinta.
- \`broker_order_id\`: solicitud aceptada/recibida por servidor, puede no producir fill.
- \`broker_deal_id\` / \`broker_position_ticket\`: cada ejecución y posición deben tener identidad verificable; varias ejecuciones pueden corresponder a una orden o posición y hay netting que requiere desambiguación.

**Fechas/epoch:** \`decision_at_utc\`, \`producer_event_at_utc\`, \`quote_at_utc\`, \`account_sequence\`, \`broker_server_time\`. Prohibido usar \`exit_at\`/PnL futuro como feature de sizing o apertura. Timestamps con zona UTC; motor de QDLE exige frescura y cuenta actual.

**Dos libros monetarios:**
1. \`qore_trading_capital_usd\` (NAV económico propio; inicia USD 60; fracción 5% fija por nueva entrada).
2. \`broker_equity_usd\`, \`broker_balance_usd\`, \`free_margin_usd\` (FundedNext USD 2.000 inicial destinados a garantía; NO dinero de riesgo QORE).
3. \`provider_loss_floor_usd\` y límites diarios reales son **separados**, obtenidos de normas autenticadas del proveedor. Nunca asumir USD120 de trailing sin comprobar programa.
4. \`costs\` incluye comisiones **open + close**, spreads, swap/rollover, slippage buffer y tipo de conversión de moneda. Si falta dato crítico LIVE, bloquear.

La fórmula compartida, **máximo objetivo previo al trade, no límite garantizado al fill adverso**, es:
\`target_stop_risk_usd = Decimal("0.05") * causal_qore_nav_usd\`.
Por ejemplo: 60 -> 3; 100 -> 5; 40 -> 2. Cuatro motores no suman cuatro 5%; sólo el mínimo de sus límites de riesgo es el techo económico, intersecado con caps de lote/margen y restricciones de proveedor.

## 2. Contratos responsabilidad por módulo (contenido mínimo)

### CIBO / Arquitecto 1 — salida de razonamiento independiente

Evento sugerido \`cibo.management_decision.v1\`:
- \`signal_id\`, \`proposal_revision\`, \`trader_id\`, \`symbol\`, \`side\`, \`order_type\`, \`entry\`, \`stop\`, \`tp\`, \`session/regime\`, \`decision_at_utc\`.
- \`position_status\`: \`SIGNAL_RECEIVED | COSTED | UNFUNDABLE | RESERVED | SUBMISSION_ARMED | ORDER_ACKED | PARTIAL | FILLED | MANAGED | CLOSED | REJECTED_NO_FILL\`. No confundir SIGNAL con ORDER_ACKED o fill.
- \`causal_features_sha256\`, \`rationale\`, \`invalidates_if\`, \`management_action\` (hold/stop-change/trailing/take-profit/partial-close/exit), \`risk_before_usd\`, \`risk_after_usd\`, \`approved_by\`. Propuesta no envía orden.
- Un lifecycle event sin fill/deal real **no** tiene \`realized_pnl_usd\` como ingreso confirmado.
- CIBO administra después de oportunidad Trader, pero no borra señales no financiables ni sustituye a QDLE para lote.

### Cuatro motores / Arquitecto 2 — recibos por productor, no cuatro caps copiados

El código actual de QDLE \`_validate_motor_receipts()\` requiere exactamente estas claves de \`module_evidence\`:
- \`SIZING\`: \`approved_risk_usd\` debe coincidir con \`QDLEIntent.sizing_cap_usd\`.
- \`CIBO_COMPOUND\`: \`approved_risk_usd\` coincide con \`QDLEIntent.cibo_compound_cap_usd\`.
- \`ADAPTIVE_LEVERAGE\`: \`approved_max_lots\` y \`approved_margin_usd\` coinciden con \`QDLEIntent.leverage_cap_lots\` y \`margin_cap_usd\`.
- \`PORTFOLIO_COMPOUND\`: \`approved_source_funds_usd\` coincide con \`QDLEIntent.portfolio_cap_usd\`.

Campos obligatorios **por cada recibo** (se firma el contenido):
- \`producer\` exacto entre los cuatro nombres; \`request_id\` idéntico al QDLE intent; \`account_sequence\` entero igual al snapshot; \`observed_at\` aware (no futuro, máximo 10 s de edad respecto a \`approved_at\`).
- \`source_event_sha256\` con prefijo \`sha256:\` del cuerpo canónico; \`hmac_sha256\` HMAC SHA-256 con **clave distinta y de alta entropía por emisor**. Confiar sólo en emisores autenticados aguas arriba. QDLE comprueba el hash y la firma al aprobar; **SHA solo no demuestra productor auténtico**.
- Recomiendo \`causal_snapshot_sha256\`, \`decision_model_version\`, \`reason_codes\`, \`risk_budget_before_usd\` y \`risk_budget_after_usd\` dentro del contenido firmado para auditoría. Sin esos campos no se prueba cognición independiente.
- Formato canónico EXACTO compatible con QDLE: JSON UTF-8, \`sort_keys=True\`, \`separators=(",",":")\`, excluir **sólo** \`source_event_sha256\` y \`hmac_sha256\` del objeto canónico antes de calcular. Serializar Decimals como cadenas (no IEEE float) y fechas como ISO8601 con TZ. IDs son strings, \`account_sequence\` entero.
- Prohibido publicar secretos HMAC en repositorios, datasets, artifacts o logs; se provisionan por entorno de secretos autorizado, rotan por arquitectura y se prueba revocación. Ningún Trader crea recibos de cuatro motores.

El adaptador a \`QDLEIntent\` **NO** mete margen y lotes en la misma escala que USD de pérdida: leverage devuelve lotes y USD de margin, sizing/compuesto USD de loss, portafolio USD de fondos y risk separado. Intersectar con \`0.05×NAV_QORE\` y provider headroom y redondear hacia abajo al paso MT5.

**Ablation obligatorio:** \`baseline\`, \`minus_sizing\`, \`minus_compound\`, \`minus_leverage\`, \`minus_portfolio\`, mismos eventos/precios/tarifas y mismo costo operacional. Contar llamadas, cambios efectivos de lotes y riesgo, cambios por escenario en DD/PnL, supervivencia y volumen; un cap empatado no recibe beneficio exclusivo.

### QDLE / Arquitecto 3 — solicitud/reserva/fill/cierre

El contrato \`QDLEIntent\` tiene los campos reales:
\`request_id,trader_id,symbol,side,entry_price,stop_price,requested_risk_usd,sizing_cap_usd,cibo_compound_cap_usd,portfolio_cap_usd,leverage_cap_lots,margin_cap_usd,source_lane,slippage_usd_per_lot,expected_account_sequence,methodology_min_lots\`.

\`QDLEAccount\` aporta \`balance,equity,free_margin,qore_unreserved_risk_usd,sovereign_free_source_usd,cushion_free_source_usd,qore_trading_capital_usd,provider_loss_floor_usd,positions,covered_fill_tickets,sequence,as_of\`.

**Autoridad de los estados:** \`HELD\` reserva pero NO es fill; \`SENDING\` significa presend one-shot armado sin prueba de fill; \`FILL_UNRECONCILED\` bloquea liberación hasta prueba de broker+tesorería; \`ABSORBED\` significa posición de broker incorporada al libro fuente; \`SETTLED\` exige comprobante auténtico del deal de cierre. Señales UNFUNDABLE o broker REJECTED_NO_FILL no cuentan como ejecutadas.

**Fills parciales:** \`/v1/partial-fill\` recibe \`request_id,broker_ticket,broker_deal_id,filled_lots\` del proveedor autorizado; \`/v1/partial-remainder-cancelled\` recibe \`request_id,broker_cancel_receipt\`. Es necesario que \`sum(fill_lots) <= requested_lots\`; no confundir orden parcial con llenado completo. Si volumen final < reservado, requerir confirmación de cancelación, snapshot broker nuevo con posición y cobertura de source. Falla cerrada para tickets mezclados / netting no reconciliable y si el servidor no confirma cancelación. \`record_broker_settlement\` se computa con deal único; no fabricar un settlement para justificar release.

**Evidencia MT5 del presente:** instrumentar actual read-only \`symbol_info,account_info,positions_get,history_deals_get,order_calc_profit,order_calc_margin\` y \`order_check\` de manera controlada; \`order_check\` no prueba fill. Nunca enviar \`order_send\` sin autorización explícita de propietario, incluso para medir comisiones.

## 3. Gates comunes y decisión de aceptación

| Gate | Dueño | Aceptación común |
| --- | --- | --- |
| Causalidad de CIBO/gestión | 1 | 100% señales preservadas, no leakage, estado y razón específicos por posición |
| 4 motores realmente independientes | 2 | 4 productores + firmas distintas verificadas, aportaciones medibles vía 4 ablations |
| Lotaje físicamente viable | 3 | broker volumes/ticks, SL USD, fees complete, margen neto y provider floor |
| Broker ledger y partial fill | 3 | deals únicos, cancel confirmada, snapshot más nuevo, no liberar reserva anticipada |
| Replay | 1+2+3 | mismo mercado/costes, causal por evento, balance/equity/QORE NAV, DD cerrado e intratrade |
| Integración | coordinador | CI exact SHA + informe auditado y revisión de otros dos owners |
| Trading LIVE | propietario | autorización explícita adicional; NO se concede en este documento |

**Estado hoy:** la [rama del Arquitecto 3](https://github.com/mezas3238-hue/qore-core/tree/agent/cibo-architect-3-qdle-mt5-physical-20261008) publicó [test de fills parciales](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-architect-3-qdle-mt5-physical-20261008/tests/infrastructure/test_qdle_partial_fills.py), CI [#37851542935](https://github.com/mezas3238-hue/qore-core/actions/runs/37851542935) SUCCESS técnico. Arquitectos 1 y 2 todavía tienen branches en commit base del programa, según inspección de commits de GitHub. Los gates globales \`QORE CIBO Zero Open Work Gate\` y \`Legacy Stack Quarantine\` están fallando; el replay research no certifica PnL LIVE.

## 4. Protocolo de revisión y secuencia de integración

1. Los tres leen el handoff maestro, sus issues [#737](https://github.com/mezas3238-hue/qore-core/issues/737), [#738](https://github.com/mezas3238-hue/qore-core/issues/738), [#739](https://github.com/mezas3238-hue/qore-core/issues/739), y este contrato. Es una propuesta coordinada, deben validar cambios del esquema por comentarios y tests.
2. Arquitecto 1 entrega evento CIBO y FSM; Arquitecto 2 responde con 4 decisiones auténticas por \`qdle_request_id\`; Arquitecto 3 valida formato/firmas, costes y lotes. No fusionar tres ramas a ciegas.
3. Si un módulo necesita nuevos campos, abre comentario \`CONTRACT_CHANGE\` con nombre, tipo, unidad, fuente/temporización, migración, test. No editar archivos propiedad ajena.
4. Publicar para cada cambio \`owner,head_sha,test_run,tests_passed,blockers,changed_contracts\` en su issue y enlazar al coordinador. Al tratar con decisiones humanas-like, reportar el razonamiento/beneficio medible, no antropomorfizar la certeza.
5. Coordinator revisa compatibilidad y aprueba contrato solo cuando existan firmas, tests de contrato y casos de integración adversos. Los tres owners hacen code review cruzado.
6. **No convertir ninguno de estos issues en tareas autónomas activas por sí solos**: GitHub registra trabajo; solo agentes/sesiones realmente conectados/ejecutados producen código. PR #735 continúa DRAFT/NO LIVE.
