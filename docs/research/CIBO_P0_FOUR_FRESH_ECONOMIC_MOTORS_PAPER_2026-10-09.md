# CIBO P0 — cuatro motores nuevos por evento PAPER — checkpoint 2026-10-09

**Rama:** `agent/cibo-p0-fresh-paper-economic-votes-20261009`  
**PR draft:** https://github.com/mezas3238-hue/qore-core/pull/748  
**Integrador base:** `agent/cibo-sovereign-integration-p0-20261008` / PR #745  
**Último replay científicamente limitado aprobado en este cambio:** GitHub Actions #37955814331, SHA `3ed7396e9d284323b888539a8aeb6c56f02af2b9`. **SUCCESS.** Este run precede a la compactación de la telemetría y pruebas de seguridad posteriores: verificar CI de HEAD antes de utilizar código final.

## Reparación incorporada

**El código del replay dejó de consumir cuatro caps antiguos multiplicados por NAV/60.** Ahora `src/qore/infrastructure/cibo_trader_lab_fresh_four_motor_votes.py` llama por separado, en cada oportunidad con geometría físicamente cotizable, a las funciones reales:

1. `propose_p0_sizing_vote` — coste al stop y costes de escenario / presupuesto de riesgo.
2. `propose_p0_compound_vote` — capital QORE de PAPER procedente de comisión OPEN debitada y liquidación bruta CLOSE contabilizada antes del instante de decisión.
3. `propose_p0_adaptive_leverage_vote` — margen libre de escenario y lotes de posiciones PAPER activas.
4. `propose_p0_portfolio_vote` — fuente de dinero QORE, riesgo concurrente por trader/símbolo y reserva de stops abiertos.

La observación conserva fingerprint del signal, secuencia de cuenta, precio, símbolo, dirección, hora y evidencia sha256 de escenario; el motor QDLE sigue siendo único y persistente desde el checkpoint anterior. Los recibos PAPER marcan `producer_signature_authenticated = false`, `broker_evidence_authenticated = false` y nunca pueden firmarse como voto LIVE mediante `sign_producer_receipt`. `FourMotorObservation.research_scenario_only` permite valorar escenarios imperfectos sin afirmar que comisión/cotización/margen históricos del bróker estén completos. El comportamiento normal de producción sigue exigiendo la evidencia de broker completa.

Solo para modo PAPER se omiten límites estratégicos arbitrarios heredados: `THREE_SETTLED_LOSSES_HAIR_CUT`, margen retenido 20%, y 15% global/7.5% correlación/10% Trader como presets. QDLE sigue verificando lotaje mínimo/paso, fuente disponible, margen, stops y 5% máximo dinámico por señal sobre caja QORE de este **escenario**.

En cada fila físicamente cotizable se guardan los cuatro votos, su razón, cap actual, observación temporal, huella resumida de eventos de caja, dictamen QDLE, pérdida y margen necesarios para el lote mínimo, y límites vinculantes de no-financiación. Las oportunidades sin geometría válida mantienen un expediente explícito NO COTIZABLE: no se inventa su ejecución.

## Ensayo base verificado #37955814331

| Métrica | Resultado |
|---|---:|
| Señales originales preservadas | 3368/3368 |
| Geometrías originales no cotizables | 20 |
| Señales con 4 votos nuevos y evaluación QDLE | 3348 |
| Votos económicos nuevos | 13.392 = 3348 × 4 |
| Solicitudes QDLE sin lote broker ejecutable | 2808 |
| Aperturas PAPER simuladas | 540 |
| Cierres PAPER simulados | 538 |
| PAPER sin cierre terminal | 2 |
| P&L cerrado PAPER | -$51,17463426574761 |
| PF cerrado PAPER | 0,716603334534 |
| Drawdown caja PAPER | 85,8411937331% |
| Caja PAPER tras cashflows conocidos | $8,6853657343 |
| MTM drawdown / NAV auténticos | NO MEDIDOS |
| Ejecuciones broker reales | 0 |

**Comparación honesta:** último run antiguo #37954318995: 539 aperturas, 537 cierres, PnL net -$50.7796, PF 0.716659, DD caja 85.197246%; recalcular votos añade 1 fill PAPEL y empeora ligeramente el resultado. No es una mejora de estrategia, pero cierra parcialmente el déficit de autoría económica.

## Rendimiento y auditoría

La primera salida almacenaba en cada uno de 13.392 recibos la lista acumulada de TODOS los cashflows históricos; producía un artefacto innecesariamente grande. La revisión de telemetría la sustituye por `realized_event_count` y `realized_event_ids_sha256`, manteniendo un commitment determinista sin repetir millones de identificadores. El código nuevo resume `qdle_binding_limits`, coste all-in del mínimo lote y margen mínimo para explicar cada solicitud sin lote; los motivos de rechazo múltiples son **no excluyentes**. Verificar la última CI antes de citar tamaño del artefacto compactado.

## P0 aún abiertos — no confundir con éxito final

1. **CIBO Native MAX continúa utilizando una instrucción de riesgo y política de salida precomputadas** (`cibo_max_native_requested_risk_fraction_of_nav` y `cibo_max_native_proposed_exit_management`). Se requiere 3368/3368 nuevos episodios cognitivos causales emitidos en tiempo de decisión y gestión intratrade por nueva observación. Responsable A1 #737.
2. **20 oportunidades siguen sin precio físico utilizable** porque su geometría original es inválida. Solo CIBO puede elegir un replanteamiento válido con fundamentos PREdecisión o abstenerse con recibo; no inventar un 0,01 lote. A1 + A3.
3. **El libro PAPER no es cuenta MT5 real**. Las fotos de spread/comisión observadas en octubre de 2026 son proxy del histórico 2019–22; conversiones JPY ancladas a 2026 y salida OHLC sintética. Margen, fills, comisiones cierre y swaps reales no certificados. A3 #739.
4. **No existe gestor de NAV MTM global de seis símbolos y acciones cognitivas por barra**, por lo que el 85,84% aquí es DD *sobre caja*, NO drawdown económico intratrade verdadero. Arquitecto integrador.
5. Se requieren recibos productor firmados de verdad y aprobación QDLE de fuente/broker para cualquier capacidad LIVE. Este PR permanece DRAFT/NO LIVE.
6. PR #746 gate de evidencia universal **debe rechazar** este replay por falta de nueva autoría cognitiva Native MAX y ausencia de cotización física para 20 señales. No falsear un PASS cambiando solo campos JSON.

## Próximo lote de ingeniería

- A1: fabricar entradas `TraderOpportunityEnvelope` y `CiboEconomicConsultationReceipt` desde observaciones causales auténticas, ejecutar `build_native_max_cognitive_episode` por señal, no copiar del `stellar-instant-3368.json`. Incorporar decisiones de gestión por barra sin mirar el futuro.
- A2: contrastar nueva votación por símbolo, razón vinculante y trayectoria NAV/cash; comparar contra baseline con exactamente mismos costes y cierres; demostrar causalidad en tests.
- A3: contabilizar explícitamente físico `UNFUNDABLE` en el precio mínimo real con comisión completa; sistema de posiciones persistentes y reconciliación por evento.
- Integrador: scheduler UTC unificado y serie de equity MTM; documentar y etiquetar experimentos por datos reales vs sintéticos; asegurar gate PR #746.

**No tocar VPS ni enviar órdenes reales. Todo el trabajo está hecho en GitHub y Trader Lab PAPER.**
