# CIBO P0 — cuatro motores nuevos por evento PAPER — checkpoint 2026-10-09

## Override final verificado: replay compactado + diagnóstico 2.808 sin lote

**GitHub Actions definitivo:** [#37956379198](https://github.com/mezas3238-hue/qore-core/actions/runs/37956379198), SHA `7e65c3e5be7d5ccabbba4b165e21b6fb926cf601`, **SUCCESS**. Todos los pasos de compilación, 4 tests nuevos + 3 tests del libro PAPER, replay 3368 y auditoría de cardinalidad PASS. El posterior commit de este documento no altera código ni workflow.

**Mismas métricas comprobadas:** 3368 señales originales, 3348 cotizables físicamente, 20 geometrías inválidas, 13.392 votos nuevos, 2808 sin lote, 540 PAPER abiertas, 538 cerradas, 2 unresolved, PnL cerrado -$51.17463426574761, PF 0.71660333453, DD SOBRE CAJA 85.8411937331%. Sin NAV/DD MTM certificado y 0 MT5 real deals. No se ha declarado certificación financiera.

**Artefacto nuevo:** [artifact #11628042022](https://github.com/mezas3238-hue/qore-core/actions/runs/37956379198/artifacts/11628042022). ZIP anterior con listas redundantes ~230.615.283 bytes frente a ZIP compactado **1.675.649 bytes** (reducción >99%). Las huellas sha256 mantienen el compromiso de los eventos y no implican autenticación.

### Causa física específica en el JSON (2860 posibilidades no deben confundirse con ejecución)

Todos los **2.808 NO_LOT** tienen el límite vinculante `REQUESTED_USD`: el coste all-in calculado para 0,01 lotes excede el riesgo elegido en el modo antiguo BANK/MEDIUM/ATTACK. De los 2808:
- **1712** exceden incluso el 5% absoluto del NAV de CAJA PAPER en ese momento; sería deshonesto fabricar lotes legales a ese tamaño sin replan físico.
- **1096** cuestan <=5% de la caja PAPER en stop+fee de escenario y pasan la comprobación básica de margen mínimo, pero el antiguo modo de CIBO solicitó por debajo del coste mínimo. Requieren nueva decisión CIBO genuina de riesgo, si lo justifican mercado y capital, nunca incremento externo forzado.

| Activo | NO_LOT | mínimo <=5% caja PAPER | mínimo >5% caja PAPER |
|---|---:|---:|---:|
| AUDJPY | 462 | 182 | 280 |
| EURUSD | 402 | 245 | 157 |
| GBPJPY | 522 | 194 | 328 |
| GBPUSD | 548 | 255 | 293 |
| NDX100 | 395 | 138 | 257 |
| XAUUSD | 479 | 82 | 397 |
| **TOTAL** | **2808** | **1096** | **1712** |

Las 1096 se concentran en los modos con riesgo PREFIJADO: **BANK 980** y **MEDIUM 116**; **ATTACK 0**. No se puede concluir que todas las 1096 lleguen a ser nuevas aperturas reales porque falta autorización cognitiva auténtica, posibles correlaciones, SL estructural, validación histórica de costes, origen de fondos y fill confirmado. Son oportunidades de *revisión cognitiva*, no ejecuciones garantizadas. El cálculo usa el **fee/open-only y los spreads 2026 del escenario**; no comisión roundtrip histórica comprobada.

**Dirección siguiente para A1:** eliminar la equivalencia fija `BANK=1.25%, MEDIUM=2.5%, ATTACK=5%` como sustituto del razonamiento. CIBO debe elegir su `desired_risk_fraction` individual entre 0-5% atendiendo a riesgo actual, mercado y cartera; QDLE vuelve a cotizar. No elevar automáticamente a 5% las 1096. Para las 1712 físicamente inviables, CIBO solo podrá proponer otra entrada, SL físicamente defendible o abstenerse explícitamente, nunca reducir stops arbitrariamente ni falsificar tamaños.

---


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
