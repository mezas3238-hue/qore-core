# QORE CORE — HANDOFF MAESTRO P0: TRES ARQUITECTOS, UNA MESA COGNITIVA DE TRADING


## OVERRIDE P0 DE INTEGRACIÓN GENERAL (2026-10-08)

**Handoff CANÓNICO ACTUAL para el próximo arquitecto:** [CIBO_SOVEREIGN_QDLE_MASTER_HANDOFF_2026-10-08_GENERAL_INTEGRATION_P0.md](CIBO_SOVEREIGN_QDLE_MASTER_HANDOFF_2026-10-08_GENERAL_INTEGRATION_P0.md). Prioridad absoluta: arreglar el circuito CIBO cognitivo + cuatro motores + QDLE + capital Bank/Medium/Attack + gestión de posiciones, reconciliar ramas A1/A2/A3, reparar Legacy Stack Quarantine / Zero Open Work / CE2I / GEN-C5 / Phase20 OOS, y ejecutar replay causal completo sin fabricaciones. Este enlace **prevalece sobre planes antiguos que propongan cerrar QDLE aisladamente**; no borra genealogía ni convierte CI verde aislado en certificación financiera. **NO LIVE**.

**Fecha:** 2026-10-08  
**Repositorio:** mezas3238-hue/qore-core  
**Branch de integración / publicación:** agent/qdle-independent-engine-p0-20261008-001  
**PR físico actual:** [#735 QDLE P0, DRAFT / NO LIVE](https://github.com/mezas3238-hue/qore-core/pull/735)  
**Equipo distribuido:** [Arquitecto 1 — #737](https://github.com/mezas3238-hue/qore-core/issues/737) · [Arquitecto 2 — #738](https://github.com/mezas3238-hue/qore-core/issues/738) · [Arquitecto 3 — #739](https://github.com/mezas3238-hue/qore-core/issues/739)  
**Estado:** HANDOFF PUBLICADO; implementación integral y certificación financiera PENDIENTES. Crear issues y ramas NO inicia tres agentes autónomos.

---

## 0. DIRECTIVA SOBERANA DEL PROPIETARIO

Construir un grupo de trading profesional capaz de RAZONAR como un operador humano competente: entender el mercado, interpretar una entrada, calcular lotaje, stop, coste completo, margen, riesgo de pérdida, concentración, gestión activa, beneficios compuestos, defensa del capital y salida. La exigencia no es representar a una persona humana ni copiar cuatro veces una fórmula, sino demostrar criterio, competencia, decisiones autónomas por especialidad, coordinación, resultados auditables y mejora medible.

Se requieren **TRES ARQUITECTOS COORDINADOS**, cada uno en rama e issue independiente. Los componentes económicos tienen que SABER OPERAR (comprender órdenes MT5, precio Bid/Ask, spread, SL/TP, PnL, swaps, comisión, margin y apalancamiento), no ser simples topes pasivos.

**División de autoridad obligatoria:**
- El Trader produce dirección, señal, geometría de entrada, precio, stop, salida técnica, tipo de orden y es el único responsable de ejecutar a través del gateway autorizado. Los Traders NO inventan lotes ni asignan capital financiero.
- CIBO es director cognitivo y administrador de la entrada y la posición: evalúa condiciones, volatilidad, gestión y salidas, propone defensa y monetización, y coordina decisiones económicas con Shared y Traders. Shared conserva la cognitiva superior, sin facultad de anular gates financieros.
- Sizing, CIBO Compuesto, Adaptive Leverage y Portafolio Compuesto son **cuatro motores de decisión económica distintos** que comparten un presupuesto común. Cada uno emite propuesta con motivo y prueba de valor incremental.
- QDLE es la **única autoridad técnica de volumen físico**: consulta costos/valuación/margen MT5, interseca los límites y reserva fondos. No genera señales ni envía órdenes ni inventa ejecución.
- FundedNext/MT5 confirma información real, operaciones, posiciones, margen y resultados. Solo un fill/deal autenticado cuenta como ejecución real.

**CIBO no rechaza señales legítimas del Trader:** registrar 100% de oportunidades recibidas, incluidas no financiables. Pero señal recibida NO es igual a orden enviada, fill o resultado financiero. Si un lote mínimo real no cabe, marcar NO_FINANCIABLE con explicación y jamás inventar una operación.

---

## 1. DOS CAPITALES Y UNA ÚNICA REGLA DEL 5% DINÁMICO

| Libro | Saldo inicial | Uso correcto |
| --- | ---: | --- |
| Broker FundedNext MT5 | **USD 2.000** | equity, margen libre, lotes financiables, restricciones y límite del proveedor |
| Capital económico QORE propio | **USD 60** | calcular riesgo interno y reinversión compuesta exclusivamente sobre ganancias/pérdidas QORE reconciliadas |

**Política:** riesgo objetivo por nueva entrada = 0,05 × capital económico QORE causal. El 5% es CONSTANTE como fracción, DINÁMICO como USD: QORE 60 -> 3 USD; QORE 100 -> 5 USD; QORE 1.000 -> 50 USD; QORE 40 -> 2 USD. NUNCA 5% de USD 2.000 MT5, nunca fijar USD 3 para todo el recorrido, nunca sumar cuatro veces 5%. Si el broker o una capa económica solo permite menos, el riesgo ejecutable será inferior. No se fuerza el lote mínimo cuando excede SL, fees o margen.

**Riesgo efectivo de nueva operación:** mínimo en USD entre 5% del QORE NAV, tope Sizing, tope Compuesto, tolerancia de Portafolio, liquidez interna no reservada, riesgo agregado disponible y colchón frente al floor del proveedor. **Margin USD y lotes NO son riesgo al stop en USD**: Adaptive Leverage aporta límites de margen y lotes en unidades específicas, y el QDLE los transforma mediante una valoración de broker. La pérdida real puede superar el stop nominal por slippage, gaps o retrasos; nunca prometer garantía de pérdida exacta al 5%.

**Contabilidad:** NAV QORE inicia en 60 y cambia por PnL realmente atribuido y conciliado, comisiones, swaps, fees, gastos, pérdidas y ajustes explícitos del propio libro. Broker equity incluye flotante; se descuentan conservadoramente pérdidas flotantes antes de arriesgar más y no se promueven ganancias flotantes a NAV realizado sin conciliación. No generar capital por multiplicadores legacy, snapshots incongruentes o reservas sin fill.

---

## 2. ESCUELA OBLIGATORIA DE OPERACIÓN / COMPETENCIAS DE TODOS

Cada arquitecto debe entrenar y certificar su subsistema en estos temas. No basta con conocer la fórmula de lotes:

1. **Instrumentos y mercado:** FX AUDJPY, EURUSD, GBPJPY, GBPUSD, oro XAUUSD e índice Nasdaq NAS100/NDX100; divisa base/cotización, precio bid/ask, sesiones, spread flotante, volatilidad, noticias, gaps, swap y cambios de régimen.
2. **Órdenes MT5:** BUY/SELL, market, limit, stop, stop-limit, SL/TP, time in force, condiciones de fill, rechazo, recotización, llenado parcial, cancelación auténtica, cierre parcial, trailing y diferencias netting/hedging.
3. **Valor físico del lote:** contrato, tick size, tick value direccional y conversión a divisa USD de cuenta, 1 lote/0,1/0,01, min-max-step y volumen agregado por dirección. Un lote NO es una cantidad universal de dólares ganados/perdidos.
4. **Comisiones completas:** apertura Y cierre, por lote / nocional porcentual, spread, slippage, rollover/swap, moneda de cargo, duración y calendario de triples. Con tarifa incompleta se bloquea financiación LIVE.
5. **Sizing y matemática:** distancia entry->SL, valuación loss por lote con order_calc_profit u otra valoración broker causal verificable, riesgo all-in, redondeo SIEMPRE hacia abajo a rejilla legal; margin con order_calc_margin/order_check, reservas y posiciones abiertas.
6. **Riesgo avanzado:** equity/pérdida flotante, DD intratrade y al cierre, riesgo simultáneo, VaR/sensibilidades sin asumir normalidad, reglas daily/max loss FundedNext, floor y stop-out, correlación de pares JPY, concentraciones e impactos de apertura múltiple.
7. **Cognición de mesa humana:** tesis basada en datos disponibles, escenario adverso, confianza calibrada, condiciones de invalidación, razonamiento de gestión hasta salida, log de decisión y aprendizaje posoperación. No utilizar resultado futuro para la entrada.
8. **Portafolio y compuesto:** NAV económico, capital protegido, balance, equity, free margin, reinversión de beneficios REALIZADOS, asignación entre Traders y activos, capacidad simultánea y protección del banco soberano.
9. **Auditoría de trading:** cada decisión y fill tiene ID, fuente, reloj causal, broker cuenta/símbolo, bid/ask, lotaje, fees, margen, budget, SL, PnL realizado/flotante, DD, motivo y hash/firma; distinguir señales, lotes propuestos, órdenes, fills y operaciones cerradas.

**Prueba práctica:** para cada familia Forex/XAU/NDX examinar al menos BUY/SELL con SL, spread y fee, operación con lote mínimo no financiable, fills parciales, incremento/caída NAV QORE, riesgo en posiciones concurrentes, orden no ejecutada, fuente stale y riesgo de floor proveedor.

### Seis símbolos MT5 observados por capturas de octubre 2026 — NO contratos actualmente autenticados

| Símbolo | Contrato por lote | min / max / step | Margen BUY aprox. 1 lote USD | Tarifa mostrada |
| --- | ---: | --- | ---: | --- |
| AUDJPY | 100.000 | 0,01 / 40 / 0,01 | 2.318,93 | USD 7/lote **al abrir** |
| EURUSD | 100.000 | 0,01 / 40 / 0,01 | 3.735,03 | USD 7/lote **al abrir** |
| GBPJPY | 100.000 | 0,01 / 40 / 0,01 | 4.407,40 | USD 7/lote **al abrir** |
| GBPUSD | 100.000 | 0,01 / 40 / 0,01 | 4.407,63 | USD 7/lote **al abrir** |
| XAUUSD | 100 | 0,01 / 50 / 0,01 | 53.637,48 | 0,0016% (base por aclarar) |
| NDX100 (NAS100) | 10 | 0,01 / 40 / 0,01 | 61.481,98 | Comisión **no visible** |

Oro: tick size 0,01, valor USD 1 por tick y lote completo según captura. NDX100: tick size 0,01, valor USD 0,10 por tick y lote. Swap triple miércoles FX/XAU y viernes NDX100 según observación; no asumir horario de rollover histórico. Profit currency de AUDJPY/GBPJPY = JPY, exige conversión correcta a USD de cuenta. El histórico NAS100 usó USTEC, **no presumir equivalencia** de contratos/símbolos. Spread flotante y margen cambian con mercado. **El hecho de que 0,01 lotes de oro/NDX requieran ~USD536/~USD615 de margen no significa que QORE necesite esos importes como NAV; broker aporta margen de su cuenta USD2000, sujeto a reglas.** También debe caber el riesgo a SL dentro de USD3 inicialmente.

---

## 3. LOS TRES ARQUITECTOS — MISIONES Y ÁREAS DE CÓDIGO

### ARQUITECTO 1 — CIBO, DIRECTOR COGNITIVO DE OPERACIONES
**Issue:** [#737](https://github.com/mezas3238-hue/qore-core/issues/737)  
**Rama aislada:** agent/cibo-architect-1-cognitive-trade-ops-20261008  
**Rol:** comprender el mercado y las oportunidades del Trader; decidir cómo administrar una posición real como lo haría un operador profesional responsable, sin generar lotes ni inventar fills.

**Trabajo:** construir máquina causal completa desde SIGNAL_RECEIVED -> ECONOMICALLY_VALUED -> FUNDED/UNFUNDABLE -> SENT -> PARTIAL/FILLED -> MANAGED -> CLOSED; cada transición tiene fuente y motivo. Aplicar análisis de régimen, volatilidad, sesiones, distancia SL, estructura TP, invalidación, manejo de posiciones concurrentes, reduce/trailing/partial close, límites de DD, protección de floor, Shared y Traders. CIBO registra y argumenta cada propuesta de gestión económica/SL/TP/cierre y monitorea continuamente. Puede proponer defensa pero no eludir la autoridad broker/Trader sobre envío.

**Propiedad de archivos:** módulos cognitivos/gestión CIBO y tests respectivos. NO modificar QDLE o finanzas del Arquitecto 2 sin PR contractual.

**Entrega y aceptación:** decisiones por signal_id y lifecycle, documentar racional y observaciones no futuras, unit/integration tests en BUY/SELL, medición de reducción real de pérdidas/impacto en DD con mercados de prueba, informe de contribución CIBO vs baseline con ablation. Cero rechazos invisibles de señales.

### ARQUITECTO 2 — COMITÉ ECONÓMICO DE CUATRO MOTORES
**Issue:** [#738](https://github.com/mezas3238-hue/qore-core/issues/738)  
**Rama aislada:** agent/cibo-architect-2-four-economic-motors-20261008  
**Rol:** llevar a los cuatro motores de topes ficticios a DECISIONES ECONÓMICAS AUTÓNOMAS y verificables por entrada. **Todos han de saber trading y aportar criterio, no copiar el 5%.**

**Sizing:** riesgo monetario según stop, volatilidad, coste integral, capital QORE 5%, buffer, distancia/valoración real. Producir preferred risk y max stop-risk en USD con explicación; QDLE decide lote final.
**CIBO Compuesto:** reinversión causal con capital realizado y pérdidas; proteger banco, no contar flotante como realizado; producir cuánto riesgo compuesto/colchón puede asignarse sin romper solvencia.
**Adaptive Leverage:** servicio de capacidad financiera broker: free margin, exposición, leverage/margin real, max lot por precio/activo y límite provider, no multiplicadores que simulen dinero; producir márgenes USD y volúmenes broker unidades.
**Portafolio Compuesto:** decidir partición de reservas, exposición agregada y por Trader/activo, coincidencia de posiciones y correlaciones (FXJPY), fondos reales disponibles y límite de stop-risk agregado.

**Propiedad:** src/qore/infrastructure/cibo_account_sizing_authority.py, cibo_compound_capital.py, cibo_marginal_leverage_utility.py, cibo_core_compound_portfolio.py y tests propios. Propuestas de cambios del contrato QDLE a Arquitecto 3 sin pisar código.

**Entrega:** cuatro event receipts INDIVIDUALES (producer, timestamp UTC, account_sequence, signal_id, side/symbol, decision, monetary units, margin/lot limits, rationale, source event SHA256 + firma verificable), con prueba de autoría y frescura; pruebas de inversión/reducción capital/compounding; benchmark de aportación con 4 ablations independientes de motor (misma señal, costes y mercado). Prohibida atribución de rentabilidad por un cap empatado con otro.

### ARQUITECTO 3 — QDLE, FUNDEDNEXT MT5 Y CERTIFICACIÓN FINANCIERA
**Issue:** [#739](https://github.com/mezas3238-hue/qore-core/issues/739)  
**Rama aislada:** agent/cibo-architect-3-qdle-mt5-physical-20261008  
**Rol:** mantener motor de lotes único, bróker lectura causal, reservas transaccionales y reconciliación, más replay realista bajo condiciones actuales verificables.

**Propiedad:** src/qore/infrastructure/qore_dynamic_lot_engine.py, cibo_physical_lot_sizing.py, qdle_mt5_read_only.py, qdle_local_api.py, qdle_signed_treasury.py, qdle_cibo_bridge.py; scripts/qdle_*, tests/infrastructure/test_qdle_*, workflows QDLE. No modificar cognitivas/motores ajenos.

**P0 pendiente ya verificado:** en rama hay funciones/endpoints para ejecución parcial pero **NO hay test dedicado test_qdle_partial_fills.py**; crear y certificar multi-deal, cancelación de remanente, ticket auténtico, no doble contabilidad, restart, liquidaciones, netting/hedging. Conectar los eventos firmados de los motores al bridge y validación HMAC desde productores confiables; el hash solo no valida inteligencia/identidad. Probar cotizaciones/datos actuales por puente qore-vps-control read-only, comisiones all-in, provider floor real, slippage/stopout, DD intratrade y ledger de capital. Nunca usar order_send en investigación sin consentimiento explícito.

**Entrega:** dataset observable por signal_id (entrada prevista, SL, total-loss/lote, size, lot grid, fee open+close, swap, margin, risk, IDs deal y account, cost/PNL reconciliados), semáforo certificado y reporte de límites. 0 fills inventados; CI del motor + controles globales no falseados.

---

## 4. PROTOCOLO ÚNICO ENTRE LOS TRES — COMO MESA HUMANA COOPERANDO

**Contrato por trade:** trade_id/signal_fingerprint, trader_id, broker_account_id, symbol exacto, BUY/SELL, order type, entry/SL/TP, source_lane, event time UTC, account_sequence, QORE_NAV, broker equity/free_margin, provider_loss_floor, market regime; cada revisión tiene versión, fuente y timestamp.

**Flujo:** Trader emite oportunidad -> CIBO analiza y propone gestión -> cuatro motores entregan cuatro decisiones económico-cognitivas diferentes y firmadas -> QDLE calcula all-in pérdida por lote y margen en broker, interseca límites y reserva -> si no hay lote legal, guarda señal UNFUNDABLE con causa -> si hay, Trader gateway valida presend y envía sólo cuando autorizado -> MT5 confirma fills reales, parciales, cancelaciones -> QDLE concilia reservas y banco QORE -> CIBO administra/cierra posición con reevaluación de cuatro motores -> libro actualizado -> aprendizaje y análisis post-trade.

**Contratos de datos, no ediciones simultáneas:** el Arquitecto 1 propone esquema de gestión, 2 esquema de decisiones económicas, 3 custodia y verifica contrato físico; debates de APIs vía issues, pruebas contract-first, PR pequeños. Ningún arquitecto toca rama ajena, force-push, borra CI rojo, atribuye dinero sin deal ni reescribe un handoff histórico como éxito. Se comparan SHA exactos y los tres revisan cada cambio de interfaz.

**Cadencia en GitHub:** issue #737/#738/#739 por owner; comentario tras cada lote con: HALLAZGO -> CORRECCIÓN -> COMMIT -> TEST RUN -> EFECTO EN ESTADÍSTICAS -> LIMITACIONES -> SIGUIENTE PASO. CI exact-SHA para aceptar; rebase/fusión por integrador designado al final y con revisión cruzada. Un error blocking de otro módulo abre issue/contrato, no editarlo sin coordinación. Los tres branches se crean desde el mismo SHA del documento canónico.

**Evidencia por operación de extremo a extremo:** signal_id, evento inicial, cuatro límites autónomos, precio/stop, fee por cada lado, pérdida por lote, volumen solicitado y finalmente ejecutado, broker order/deal IDs, margin, position state, riesgo abierto, swaps, realized/float PnL, QORE NAV, MT5 balance/equity, DD y motivo. Si algo falta, NO CERTIFICADO.

**Agentes humanos coordinados ≠ humano real y autonomía no autorizada:** los tres issues permiten trabajar a tres agentes/sesiones; crearlos por sí solo no los ejecuta ni abre operaciones. Activación de trading real necesita aprobación expresa del propietario y control de riesgo.

---

## 5. SITUACIÓN REAL VERIFICADA Y DEUDAS; NO MAQUILLAR RESULTADOS

**SHA observado antes de crear este handoff:** ecfb980b2652b1a7751583ec02f159c0463132a3. QDLE PR #735 **DRAFT**, no fusionado ni desplegado en FundedNext.

| GitHub Actions exact-SHA base | Resultado | Interpretación |
| --- | --- | --- |
| [QDLE Atomic Engine #37849215628](https://github.com/mezas3238-hue/qore-core/actions/runs/37849215628) | SUCCESS | pruebas de código, NO certificación live |
| [QDLE 3368 Replay #37849221992](https://github.com/mezas3238-hue/qore-core/actions/runs/37849221992) | SUCCESS técnico | geometrías históricas, costes screenshot y truth gate que RECHAZA certificación |
| [CIBO Zero Open Work Gate #37849222233](https://github.com/mezas3238-hue/qore-core/actions/runs/37849222233) | FAILURE | deudas de cierre global |
| [Legacy Stack Quarantine #37849222050](https://github.com/mezas3238-hue/qore-core/actions/runs/37849222050) | FAILURE | imports cognitivos legacy sin aislar |

La investigación 3.368 señales 2019–2022 con fichas MT5 octubre 2026 **NO** demuestra 3.368 operaciones reales. H8 invalidó una parte de antiguas curvas de capital ~670.000 y DD ~35%; banco soberano negativo/falta de fondeo físico. Auditoría de research detectó 272 pérdidas proxy >5% del QORE NAV de apertura, 777 >reserva inicial y 306 propuestas NDX100 con fee desconocida reemplazada por $0. Estos son bloqueos de certeza en modelado, no prueba de operaciones broker. El informe anterior de motores mostró topes gemelos, sin atribución de PnL incremental a cada uno. Nunca ofrecer esos PnL/DD/PF como rentabilidad demostrada.

**Pendientes exactos:**
- Remediar rutas parciales sin test y conciliar tickets/deals con broker, no solo lotaje reservado.
- Obtener tarifa completa de salida Forex, base 0,0016% XAU, comisión NDX, spreads reales, swaps y rollover servidor.
- Confirmar cuenta/servidor, especificaciones seis símbolos y reglas actuales de FundedNext con lectura autenticada del VPS; qore-vps-control ya fue reportado como puente de lectura, pero NO se ha comprobado conexión viva en este handoff.
- Conectar los emisores cognitivos económicos REALES de los cuatro motores y probar firmas/identidad de origen, resultados contra baseline.
- Simular/medir fills, slippage, gaps, daily/provider floor, margin call, open exposure, QORE NAV y DD **intratrade** con series actuales de mercado versionadas; mantener el replay histórico separado como investigación de geometrías.
- Cerrar Zero Open Work y Legacy Stack Quarantine SIN desactivar controles. Ejecutar certificación científica holdout/OOS, perturbaciones, stress y pruebas de robustez.
- DD ideal 20% y tolerable 25% solo cuando el recorrido está físicamente financiado y sin degradar techo verificable; 8.000% era benchmark base, nunca garantía ni techo caprichoso.

---

## 6. EXÁMENES DE CERTIFICACIÓN Y GATES DE CIERRE

**A. Competencia:** cada uno de los 3 arquitectos certifica conocimiento operacional de los seis activos, BUY/SELL, gestión SL/TP, margin, fees, partials, netting, stop-out, riesgo y contabilidad, con casos adversos y explicación cognitiva.

**B. Propiedad financiera:** capital QORE USD60 inicialmente, MT5 broker USD2000, ratio 5% recalculado, 4 topes no aditivos, 0 lotajes fuera grid, 0 capital ficticio, 0 double-spend, 0 deal duplicado, 0 fill sin firma/recibo, 0 beneficios futuros leak, provider floor solvente al presend. Las pérdidas reales por gap pueden exceder 5%; medir sensibilidad y exigir buffers, no falsificar resultados limitando outcome R a -1.

**C. Contribución:** mismas oportunidades/quotes/fees, control y 4 ablations de motor, más CIBO razonando vs baseline. Se exige variación real/causal de decisiones y métricas (PnL, gross loss, PF, DD, exposición, capital, fills legales, supervivencia), no solo contadores de llamadas/caps empatados.

**D. Certificación:** conservar 3.368/3.368 señales en research, separado de paper actual y fills reales; DD al cierre + intratrade, costo completo, forward/fresh OOS, stress de pérdidas, spreads, datos cambiantes, sesiones, reglas FundedNext, fallos VPS, latencia, crash recovery y agresión. Objetivo DD ~20–25% es meta; no forzar curva simulada para cumplirlo.

**E. Gate de producción:** ningún arquitecto puede desplegar dinero real automáticamente. Un PR DRAFT y CI GREEN sintético son insuficientes. Se requiere certificación de datos actuales, broker rules, revisión cruzada, autorización específica del propietario y despliegue gradual con kill-switch/protecciones.

---

## 7. PUNTO EXACTO DE REANUDACIÓN; EN QUÉ TRABAJA CADA ARQUITECTO

**1 / Issue #737:** empezar por CIBO FSM y decisiones de gestión registradas por señal, analizar causas de DD y pérdidas sin tocar dirección/entrada del Trader. Implementar cognitivas de entrada/salida por régimen y conexión a comité económico, tests y ablation.

**2 / Issue #738:** empezar por lograr que Sizing/CIBO Compuesto/Adaptive Leverage/Portafolio emitan decisiones monetarias propias firmadas por productor, con unidades correctas y efectos medidos. No copiar topes 5% cuatro veces. Tests del NAV 60/100/40, exposición, reinversión y independencia.

**3 / Issue #739:** empezar por crear y ejecutar test_qdle_partial_fills.py que falta, fortalecer conciliación del libro, autenticar datos MT5 por puente de lectura, tarifas reales, provider floor y certificado paper; integrar contratos de 1 y 2 sin pisar sus ramas.

**Para concluir la ingeniería y poder afirmar "TRABAJO TERMINADO":** los tres PR revisados/CI, cuatro motores funcionando de forma independiente y útil, QDLE real físico, reconciliación broker, pérdida y comisión trazables, gestión cognitiva CIBO, replay realista y batería científica completos. **Ese estado NO se alcanza al publicar este documento.**

---

## 8. DOCUMENTACIÓN DE CONTINUIDAD CON EL RESTO DE QORE

- [QDLE handoff original](QDLE_P0_MASTER_CONTINUITY_HANDOFF_2026-10-08.md).
- [QDLE reparación y bloqueos](QDLE_P0_FINANCIAL_REPAIR_EXECUTION_STATUS_2026-10-08.md).
- [QDLE invalidación de cálculo](QDLE_P0_FINANCIAL_CALCULATION_INVALIDATION_AND_REPAIR_2026-10-08.md).
- [Informe de cuatro motores con tarifas foto MT5](QDLE_P0_CURRENT_MT5_4_ENGINE_COMMISSION_AND_LOTAGE_REPORT_2026-10-08.md) — SOLO RESEARCH.
- [CIBO 5% dinámico rama previa](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-p0-dynamic-equity-5pct-lotage-002/docs/research/CIBO_P0_MASTER_CONTINUITY_HANDOFF_2026-10-08_DYNAMIC_5PCT_MT5_LOTAGE_AND_SOLVENCY.md) — se subordina al libro dual USD2000/60.
- [CIBO techo y DD legado](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-causal-expectation-leakage-fix-001/docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md) — curvas no certificadas tras diagnóstico H8.

**Lema de continuidad:** TRES arquitectos; UN QDLE; CUATRO decisiones económicas independientes; UNA autoridad de riesgo de 5% QORE; Broker USD2000 para margen; cero ganancias ficticias; evidencia por operación; sin trading real no autorizado.
