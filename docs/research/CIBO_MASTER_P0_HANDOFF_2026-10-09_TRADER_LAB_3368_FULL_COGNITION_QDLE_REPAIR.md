# QORE CORE — HANDOFF MAESTRO CANÓNICO P0 — REPARACIÓN URGENTE CIBO + QDLE EN TRADER LAB

## OVERRIDE 2026-10-09 — CORTE P0 POSTERIOR AL HANDOFF: QDLE PAPER PERSISTENTE (NO CIBO CERTIFICADO)

**Prevalece sobre la descripción anterior de “SQLite NUEVO por señal” únicamente para el runner de la rama integradora actualizada.** Commit de código verificado `016a69feae21b209772c27bd16cc28d86832ac33`. GitHub Actions [#37954318995](https://github.com/mezas3238-hue/qore-core/actions/runs/37954318995) terminó **SUCCESS**, incluyendo compilación, 3 pruebas unitarias PAPER y replay completo.

Cambios implementados:
- `src/qore/infrastructure/qdle_paper_book.py`: adaptador aislado que reutiliza UNA QDLE y UNA SQLite durante toda la corrida, sin contaminar las rutas de tickets, fills, settlements o presend LIVE. Estados PAPER explícitos y auditable `PAPER_UNASSESSABLE_NO_PHYSICAL_QUOTE`; un método auxiliar para digest determinista de auditoría, **no firma autenticada**.
- `scripts/cibo_trader_lab_native_qdle_market_atlas_3368.py`: comparte esa instancia, actualiza el snapshot con posiciones PAPER abiertas, libera reservas al cerrar, registra explícitamente las oportunidades no cotizables y concilia contadores del libro físico.
- `tests/infrastructure/test_qdle_paper_book.py` + workflow M5: 3 pruebas PASS; la CI exige `physical_quotes + unassessable == 3368` y `paper_filled == paper_open`, `paper_settled == settled`.

Reconciliación confirmada **3368 recibidas = 3348 con evaluación QDLE física + 20 NO EVALUABLES POR GEOMETRÍA (registradas en el libro, sin falso lote)**. De 3348 cotizaciones, **2809 sin lote** y **539 con lote PAPER**. De 539 aperturas, **537 cerradas** y **2 sin salida terminal**. Resultados de este escenario **sin mejora por cambiar persistencia**: net cerrado `-$50.77962071869291`, PF `0.716659000917`, cash-DD `85.19724614858%`, caja final `$9.0803792813`, **NAV MTM/DD intratrade certificados NULL**. Ningún fill MT5, ninguna ejecución LIVE.

**NO levantar los gates P0 por este éxito de CI:** faltan episodios Native MAX genuinos 3368/3368; votos de los cuatro motores calculados de nuevo desde NAV y observación causal (actualmente son límites NAV60 reescalados); 20 geometrías originales aún deben recibir replanteamiento cognitivo válido antes de una posible cotización física; no existe scheduler causal de acciones intratrade ni DD MTM global; comisiones/cotizaciones 2026 no son históricos broker 2019–2022. El gate independiente de evidencia universal en [PR #746](https://github.com/mezas3238-hue/qore-core/pull/746) **debe continuar rechazando el replay baseline** hasta que A1/A2/A3 reparen realmente estas causas.

**Siguiente paso técnico prioritario:** A1 producir episodio/plan nuevo por señal y gestión por barra; A2 emisión de cuatro votos nuevos por cada snapshot sin reutilización de CAPs; A3 incorporar razones vinculantes de UNFUNDABLE y trazabilidad física exacta por ID; integrador construir scheduler temporal único con NAV MTM y pruebas de perturbación futura/causalidad. Conservar límites físicos 5% NAV, lot min/max/step y precio/comisión sin fabricar fills. Mantener DRAFT/NO LIVE.

---


**Fecha:** 2026-10-09 (corte tras Trader Lab #37949977967).  
**Repositorio:** mezas3238-hue/qore-core.  
**Rama integradora:** agent/cibo-sovereign-integration-p0-20261008.  
**PR coordinador:** https://github.com/mezas3238-hue/qore-core/pull/745 (**DRAFT / NO LIVE**).  
**HEAD comprobado antes de esta nueva publicación:** 7d5c5a267bfccde11fd79d5a0b79e3f803c53891. El commit del propio handoff será posterior; releer HEAD al comenzar.  
**Responsable del siguiente ciclo:** arquitecto integrador P0, coordinando A1 cerebro CIBO (#737), A2 cuatro motores (#738), A3 QDLE/física MT5 (#739), sin pisar sus ramas ni reabrir el antiguo motor de costes.  
**Estado:** ERROR DE DISEÑO SEVERO CONFIRMADO. Replay de ingeniería PAPER ejecutado, pero integración cognitiva-económica auténtica NO certificada. No permitir LIVE por este experimento.

> **DIRECTIVA DEL PROPIETARIO:** CIBO Native MAX debe ADMINISTRAR —no descartar por etiquetas externas— las **3.368 señales originales**, razonando cada entrada, el SL, las salidas, las posiciones existentes y la evolución económica. Los cuatro motores han de producir sus decisiones sobre el estado causal real de CIBO; QDLE es la ÚNICA autoridad de lotaje físico por intento. Retirar las restricciones ESTRATÉGICAS arbitrarias que estén mutilando la cognitiva y la gestión. El próximo arquitecto debe CORREGIR LA ARQUITECTURA, no entregar otro reporte de lotes estáticos o un replay con 3.368 simples recibos. Las 3.368 señales deben figurar individualmente como administradas y evaluadas por QDLE; el número final de FILLS físicamente financiables puede ser inferior, y debe explicarse sin omisión.

## 0. LEER ESTO ANTES DE PROGRAMAR — qué demostró el último Trader Lab

**Workflow REAL de Trader Lab:** https://github.com/mezas3238-hue/qore-core/actions/runs/37949977967, **SUCCESS**, SHA ensayado ae84d4566d385aa24c56e595d3dbf2e586d87b63.  
**Artefacto fuente de verdad del ensayo:** https://github.com/mezas3238-hue/qore-core/actions/runs/37949977967/artifacts/11626195451, miembro trader-lab-cibo-qdle-spread-3368.json; ZIP digest sha256:ecb417ab6041f03cbf7bf5b20759cfec31f047ffea6f4bdcc1d972be38bfaf07.  
**Informe desglosado:** docs/research/CIBO_TRADER_LAB_NATIVE_QDLE_M5_SNAPSHOT_SPREAD_3368_RESULTS_2026-10-09.md.  
**Runner actual del problema:** scripts/cibo_trader_lab_native_qdle_market_atlas_3368.py.  
**Workflow:** .github/workflows/cibo-trader-lab-native-qdle-market-atlas-3368.yml.  
**Resultado VERIFICADO directamente desde JSON + logs, sin mezclar QDLE antiguo:**

| Concepto | Resultado |
| --- | ---: |
| Fuente original de señales / IDs únicos | 3.368 / 3.368 |
| Señales que NO llegaron al QDLE físico por geometría descartada previamente | **20** |
| QDLE sin lote bajo la simulación secuencial | **2.809** |
| QDLE con lote positivo, PAPER aperturas | **539** |
| PAPER cierres con resultado | **537** |
| PAPER abiertas sin cierre terminal reconstruido | **2** |
| Saldo de caja simulado tras eventos conocidos | **$9,08037928** (capital inicial $60) |
| P&L neto sólo de 537 cierres PAPER | **−$50,77962072** |
| PF neto de 537 cierres PAPER | **0,716659** |
| DD máximo sobre CAJA simulada, NO equity intratrade | **85,197246%** |
| Win rate PAPER de 537 cierres | **37,243948%** |
| Comisiones OPEN debitadas en 539 aperturas PAPER | **$41,78370064** |
| Capital final NAV real de la política, DD MTM y PF certificado | **NO MEDIDOS / null** |
| Deals LIVE/Mt5 de CIBO de este replay | **0** |

**Conciliación correcta:** $60 + (−$50,77962072 NET de 537 cierres) − $0,14 de comisión OPEN de las dos posiciones sin cierre = $9,08037928 caja PAPER. Este no es NAV final con marks, swaps y posiciones abiertas.

**Desglose paper:** BANK 2031 señales, 259 PAPER cierres, −$26,7762 PF≈0,5357; MEDIUM 520 señales, 50 cierres, −$6,5742 PF≈0,5342; ATTACK 817 señales, 228 cierres y 2 abiertas, −$17,4293 PF≈0,8378. Entre activos, NDX100 89 cierres y **−$24,1025** aun con comisión $0; GBPJPY 87 y −$12,8749; GBPUSD 58 y −$5,7400; EURUSD 95 y −$4,375; AUDJPY 203 y −$2,8935; XAUUSD 5 y −$0,7937.

**MANDATO:** el 85,197% no es una «verdad del mercado» ni un DD auténtico de QORE Core; es una alarma en un escenario PAPER muy simplificado. Tampoco sustituirlo por el 35,24% del antiguo carrier con esquema económico diferente: no son comparables.

### Limitaciones exactas de los insumos que no pueden encubrirse

- Se empleó el corpus **Market Atlas M5 2019–2022**, OHLC sin BID/ASK históricos de FundedNext; el replay convirtió cada vela a bid/ask artificial mediante MITAD de un spread **constante observado en MT5 octubre de 2026**. AUDJPY 0,014; EURUSD 0,00000 capturado en un instante; GBPJPY 0,023; GBPUSD 0,00000 puntual; XAUUSD 0,38; NDX100 1,60. EURUSD/GBPUSD spread 0 NO es hipótesis realista para toda la época. Conservar este caso sólo como BASE DEL CEO y agregar sensibilidades, NUNCA llamarlo histórico certificado.
- Cambio GBPJPY/AUDJPY → USD basado en **USDJPY=158,337 de 2026**, aplicado a 2019–2022; el valor por pip real varía. No fingir cotización de USDJPY de época.
- Apertura PAPER se efectúa en primera vela M5 elegible y no modela el precio/límites efectivos de órdenes LIMIT del Trader; no hubo confirmación real de fill.
- El runner limita recorrido a 3200 barras y corta al primer gap temporal, lo que dejó **2 PAPER abiertas en 2020**: GBPJPY 2020-01-03 20:00 UTC (24 barras) y AUDJPY 2020-11-06 18:00 UTC (48 barras). Una interrupción de fin de sesión no se debe cerrar inventando el precio ni mantenerla para siempre sin investigación de continuidad de mercado.
- Broker FundedNext base aproximada $2.000 margen y capital dueño QORE $60 son magnitudes distintas; costes/margin contract de 2026 no validan históricos.
- Pese a usar el módulo real QDLE, el runner **crea un SQLite NUEVO por señal**, no mantiene un único libro persistente de reservas/fills/settlements del portfolio; las reservas concurrentes se simulan manualmente sumando posiciones activas. No equivale a persistencia/reconciliación atómica de toda la cuenta.
- El resultado de salida del gestor se calcula desde barras futuras del camino, pero se difiere su liquidación según timestamp; hay que auditar ausencia de leakage y que CIBO sólo observa barras cerradas al tomar cada nueva acción.
- No hay una serie de equity MTM, exposición temporal de cartera ni DD intratrade global certificado. El saldo paper en caja no es ese equity.

## 1. ERROR RAÍZ #1 — CIBO Native MAX no está llevando el volante cognitivo

**Hallazgo en código actual:** el runner consume «decisions» preelaboradas de la ejecución de cotizaciones de QDLE (stellar-instant-3368.json) mediante el campo cibo_max_native_management_mode; también copia una política de salida prefijada cibo_max_native_proposed_exit_management. No reejecuta CiboNativeMaxCognitiveEpisode ni razona sobre NAV actualizado, abierta/correlación, pérdidas recientes, nueva información, modificaciones de stops, parciales, BE, trailing o reversión en cada barra. Por tanto CIBO es UNA FUENTE DE RECIBOS, no el administrador completo que exige el propietario.

**Subproblema:** en src/qore/infrastructure/cibo_native_mode_authority.py existen bandas de confianza para derivar BANK/MEDIUM/ATTACK y plantillas estáticas EXIT_POLICIES. Es válido como control unitario o baseline SHADOW, pero no prueba la capacidad cognitiva individual de CIBO; una etiqueta y un preset no sustituyen una decisión basada en estado del mercado y cuenta. En este experimento BANK 1,25% NAV, MEDIUM 2,5%, ATTACK 5% son fracciones PREFIJADAS; la estrategia del propietario requiere que CIBO determine cuánto riesgo conviene asignar por señal dinámicamente, hasta el techo soberano 5% all-in autorizado por QDLE, sin segunda censura rígida por etiqueta.

**Obligación del siguiente arquitecto A1 + integrador:**
1. Evaluar el **motor Native MAX genuino** por cada señal una sola vez causal en su momento, tomando señales de Trader, contexto completo (estructura, régimen, sesión, correlaciones y posiciones), saldo NAV QORE, flotante, mercado predecisión, recientes cierres AUTÉNTICOS de la propia simulación, y límites físicos observados. No utilizar gross_structural_outcome_r, TP futuro ni path después del tiempo de observación.
2. Exportar para **cada una de las 3368** un recibo tipado: fingerprint, trader, símbolo, original side/entry/SL/TP/time, native_episode_digest, decisión_at, razonamiento mercado y alternativas, preferencia BANK/MEDIUM/ATTACK, proposed_entry_order_type, desired_risk_fraction 0–5% dinámico, SL protector y TP defendibles, policy_rev y firma/semantics SHA.
3. Reprocesar acciones cognitivas progresivas por cada posición: observación cerrada → CIBO evaluate → propuesta accionable (mantener, cerrar, parcial broker-grid, BE, trailing, defensa) → ejecución PAPER a la siguiente oportunidad disponible; almacenar acción/rechazo y causa. NO decidir el stop retrospectivamente tras ver una vela completa.
4. Construir una prueba de influencia **causal**: alterar de forma lícita una observación anterior cambia la decisión/plan de CIBO y puede cambiar la transacción paper; conservar el resto determinista. Otra prueba: perturbar velas futuras NO cambia la decisión en t.
5. La instrucción Native MAX no debe funcionar como veto externo del Trader: CIBO recibe 3368/3368. Cuando CIBO opte voluntariamente por no aumentar exposición, emitir MANAGEMENT_INTENT explícita (0 riesgo con tesis/riesgo) y no descartarla; QDLE registra intento/solicitud de volumen cero con causa, no hay fill inventado.
6. Separar modo BANK «tesorería/custodia» de BANK «operación» si diferentes escuelas del código colisionan. No permitir que una etiqueta sea simultáneamente preset rígido y restricción de admisión: definir semántica canónica bajo CIBO.

**Gate cognitivo innegociable:** 3368/3368 receipt genuinos NATIVE + 3368/3368 análisis contextual + 3368/3368 decisiones de administración causal y autoría verificable; contadores no pueden cumplirse copiando un campo antiguo en un JSON.

## 2. ERROR RAÍZ #2 — cuatro motores son CAPs reciclados, no cuatro razonamientos nuevos

**Hallazgo:** scripts/cibo_trader_lab_native_qdle_market_atlas_3368.py::_mode_quote hace scale = nav / INITIAL y toma four_engine_caps_usd de la antigua cotización con NAV60, multiplicando por scale. Eso NO es re-ejecutar los cuatro motores en el contexto actual. La prueba anterior de lotaje había consumido cuatro votos, pero el Trader Lab nuevo no los recalcula.

**Obligación A2 + integrador:** en cada intención y evento de NAV/fuente relevante, ejecutar genuinamente desde el estado *actual*:
- SIZING: stop/volatilidad/costes y riesgo deseado por CIBO; retorno de presupuesto USD con evidencia.
- CIBO COMPUESTO: capital **realizado** y disponible, fuente BANK y reinversión, fees realizados y pérdidas; no «THREE_SETTLED_LOSSES_HAIR_CUT» basado en ganancias/perdidas del Trader CONTROL.
- ADAPTIVE LEVERAGE: margen libre, contrato, notional, precio/quote, provider caps y volumen máximo expresado en lotes REALES, no 10000x abstractos.
- PORTAFOLIO COMPUESTO: riesgo concurrente por símbolo/Trader, correlaciones, buffer, fuentes de riesgo del owner y capital protegido, liberación de reservas al cierre.

**Se elimina en brazo PAPER** toda REGLA ESTRATÉGICA ARBITRARIA heredada que «vetaba Core»: bloques Cognitivo/CAPITAL usados para admisión; haircuts derivados de CONTROL; clip de multiplicadores y banda histórica sin evidencia; presets que sustituyan la preferencia razonada; cuotas automáticas que eliminan señales antes del cerebro o QDLE. Si una protección estratégica genuina es razonada por CIBO y tiene evidencia PREDECISIÓN, registrar decisión y no confundirla con un filtro anterior. Mantener rama control etiquetada para ablation; **no activar cambios de seguridad en producción por un estudio PAPER**.

**Gate económico:** 4 × 3368 votos nuevos, causalmente firmados/asociados a fingerprint y snapshot NAV, o negativa legítima con causa y estado; prohibido reciclar/reescalar cuatro números antiguos. Un motor no decide LOTE final.

## 3. ERROR RAÍZ #3 — QDLE no opera como autoridad PERSISTENTE de cartera

**Hallazgo:** se instancia QDLE en bases SQLite temporales por oportunidad con index.sqlite. El snapshot de cuenta, broker free margin, fuente y reserved risk se preparan externamente desde un balance de caja y sumatoria de posiciones paper; la secuencia de QDLE no evoluciona como un libro único auténtico con fills, posiciones y reconciliación idempotente.

**Acción P0 A3 + integrador:**
- Un único QDLEAccountState/FundAccount con secuencias monótonas, snapshots broker-paper, gestión de fuente QORE (NAV inicial $60) independiente del broker margin nominal ($2000 escenario), posiciones, fee paid, pending order risk, reserved margin, riesgo all-in y P&L realizado/flotante.
- CIBO decide ENTRY_SIDE / order type/SL/TP/deseado en USD y modo dinámico. Cuatro motores responden con fondos y capacidad. Sólo QDLE evalúa realmente volume_min/max/step, pérdida al SL, OPEN fee+estimación CLOSE fee, spread sin doble cargo, spread/slippage buffer, JPY cross USD por época, margen y exposición simultánea; redondea hacia abajo en min lot. Reserva atómica idempotente, no reset por señal.
- Si movimiento al SL+fee+buffer de mínimo 0,01 lote excede el máximo de riesgo **5% del NAV dinámico** o las fuentes/margen reales, QDLE devuelve **UNFUNDABLE_PHYSICAL** con el coste mínimo, causa, cuota y alternativa dentro del mandato CIBO. CIBO puede replanear una alternativa conforme a su tesis (p.ej., mejor entry/timing, SL protector real compatible), pero NUNCA falsificar 0,01 lot cuando exceda budget.
- Agregar ledger de eventos PAPER: signal_received, cibo_decision, four_motor_voted, qdle_attempted, order_submitted, filled/rejected/expired, open_fee_debited, stop/partial/trailing amendments, settled, MTM, NAV snapshot, release reserves, broker only as simulated. Exactamente-once por event ID, con hash/procedencia.
- No confundir QDLE.reserve_for_trader (HELD) con paper fill; simular evento posterior e integrarlo en QDLEAccountState. Un fill parcial se refleja con lots residual en paso legal de broker; un sin fill libera reserva sólo con evidencia de expiración/rechazo de la simulación.
- No introducir commission LIVE no verificadas: schedule OPEN Forex $7/lot, NDX $0, XAU 0,0016% del nocional OPEN **según la FAQ Stellar Instant**; la cuenta MT5 aportada muestra $0,07 por 0,01 lotes en EURUSD/GBPJPY/AUDJPY/XAU y $0 NDX, de modo que el modelo es coherente con muestra real; GBPUSD se trata como EURUSD en contrato/pip/tarifa, pero SIN operación GBPUSD en esa captura.

**Gate físico:** cada uno de 3368 recibe expediente QDLE con lotes 0/positivos y binding reason, sin silent drop. Para cada PAPER fill, 0,01+ broker step, all-in stop liability ≤ riesgo autorizado por CIBO y techo QORE 5%; ocupación de margen ≤ disponible y con liberación al cierre. Costes deben entrar en denominador, no suponer fills con comisión 0. Ningún código LIVE order_send.

## 4. ERROR RAÍZ #4 — trayectorias, ejecución, capital y DD no están conciliados

**Hallazgo de código y JSON:**
- Antes de QDLE, 20 señales acabaron INVALID_GEOMETRY; el contrato universal exige que CIBO las razone y QDLE las audite, no quedar invisible. Revisar y corregir comparación entre entry/SL/target originales y precio de fill OHLC M5.
- 2 posiciones abiertas sin terminal completo; los cambios de sesión generan gaps y la ventana de 3200 barras limita horizonte. Resolver continuidad entre barras/sesiones legítimas sin interpolar precios falsos, sin reproducir Trader CONTROL outcomes.
- Los 537 cierres tienen fees OPEN descontados y net cashflow sin doble debit; pero sólo se midió DD cash post-event, no equity MTM ni riesgo intratrade. No publicar 85,20% como DD MTM real ni declarar $9,08 NAV final.
- Cada cierre queda calculado con policy fija por modo, no nueva decisión Native MAX por barra. La cognitiva de CIBO debe gobernar la vida de posición.
- OPEN/CLOSE PAPER modelados con spread constante de capturas 2026. Probar sensibilidad: base CEO bid/ask, spreads FX positivos, spread 2x/3x, JPY cambio de época y slippage. Los escenarios con datos construidos deben etiquetarse RESEARCH, no reales.

**Obligación P0:** un scheduler global de timestamps UTC y cola de eventos para todas las 3368 señales y posiciones concurrentes; preservar sincronía de múltiples símbolos. Valoración bid/ask de escenario M5 por lado; marcar al mercado LONG por BID/SHORT por ASK en cada evento compatible; procesos de gaps y STOP-FIRST intrabar cuando secuencia desconocida. Capital NAV QORE dinámico = capital inicial + cashflows realizados - fee open + flotante marcado + transferencias verificables, distinguiendo balance de caja y equity. Pérdidas por stop/commission/swap y P&L parcial; calendario de prioridad eventos definido. Fecha de apertura/cierre, precio, volumen y motivo de cada cierre firmado por CIBO.

**Gate DD:** reportar (1) DD sobre balance cerrado, (2) DD sobre equity MTM por instante, (3) min free margin, (4) máximo riesgo abierto simultáneo y violaciones/gaps, (5) PF WIN rate y cashflows NET de cierres, (6) NAV final sólo si las posiciones abiertas están correctamente marcadas. A falta de evidencia seria, métricas CIBO certificadas null, aunque se permita mostrar métricas PAPER del escenario como tales.

## 5. CLARIDAD INNEGOCIABLE SOBRE «3368 ENTRADAS»

**El universo de evaluación es 3.368/3.368 señales recibidas de Core.** Ninguna se suprime por filtros estratégicos/cognitivos previos. Deben existir 3368 filas (fingerprint único) con:

1. CIBO_SOVEREIGN_RECEPTION, episodio Native MAX evaluado para contexto de la oportunidad.
2. CIBO_MANAGEMENT_DECISION, al menos un plan de entrada/salida con tesis y riesgo.
3. FOUR_ECONOMIC_MOTOR_RECEIPTS generados AHORA desde NAV/contexto, no escalados desde otras ejecuciones.
4. QDLE_PHYSICAL_ASSESSMENT único/identificable sobre modo, fondos y SL/fee de ese ID, con lote o causa de no financiación.
5. TRADER_LAB_EXECUTION_OUTCOME: estado PAPER filled/partial/unfilled/unfundable/incomplete; administración causal de CIBO durante posiciones efectivamente abiertas.
6. FILL/EXIT/SETTLEMENT/P&L si y sólo si hubo fill PAPER físicamente permitido y camino suficientemente sólido.

**La exigencia de 3.368 registros administrados NO autoriza inventar 3.368 fills de 0,01 lote.** A $60 y 5% máximo=$3, algunos mínimos físicos son inviables. El arquitecto DEBE cuantificar la imposibilidad por instrumento/budget/fee/stop/margen, habilitar replan cognitivo legítimo si puede, y no silenciar filas. Si se desea una sensibilidad de «3368 paper orders sin volumen legal», debe ir en un estudio distinto explícitamente ABSTRACT_NO_BROKER_LOT, nunca hacerse pasar por la cadena QDLE real.

**ELIMINAR RESTRICCIONES QUE MUTILAN COGNICIÓN ≠ ELIMINAR LOS LIMITES FINANCIEROS Y CONTRACTUALES:** conservar equity realista, 5% máximo soberano all-in del NAV propio, broker lot min/step/max, stop level, free margin, fees, proveedor max loss, causalidad y seguridad LIVE.

## 6. ARQUITECTURA OPERATIVA REQUERIDA

~~~text
3368 Trader signals [2019-07—2022-06; fingerprints originales]
   |
   V
CIBO Native MAX FULL COGNITION [eval cada señal SIN PRE-FILTRO]
   |   Snapshot de mercado+QORE caja/equity+posiciones+riesgo/correlación
   |   Decide riesgo deseado (<=5%), modo, entry, SL, TP, plan vivo y razón
   V
Cuatro motores nuevos [Sizing, Cibo Compound, Adaptive Leverage, Portfolio]
   |   4 recibos FRESCOS por signal, capital/política causal
   V
QDLE PERSISTENTE / ÚNICO [capital propio QORE, broker margen, lots físicos]
   |   Emite quote, reserva, rechazo físico o alternativa/replan CIBO
   V
TRADER LAB PAPER ORDER [verdad sintética M5+spread del escenario]
   |   fill/no-fill posterior y SOLO si físico viable
   V
CIBO Native MAX re-evalúa posiciones a medida que llegan barras/contextos
   |   parcial, BE, trailing, SL/TP y defensa causal
   V
PAPER fills/cierre y fees -> QORE/BROKER ledgers -> NAV / MTM DD / PF
   |                                     |
   +--------------- EVENT LOOP ---------+
~~~

**Autoridades exclusivas:** Trader origina; CIBO interpreta y decide gestión; motores conocen y autorizan disponibilidad/finanzas; QDLE valoriza y cuantiza lote; Trader Lab simula ejecuciones; ledgers únicamente registran fills/marks verificables de PAPER. Shared puede enriquecer contexto, no reemplaza órdenes. Ningún módulo reintroduce el antiguo SELECTOR de exclusión ni la ganancia con multiplicadores abstractos como sustituto de física de lotes.

## 7. PLAN DE REPARACIÓN EN FASES / PROPIETARIOS

### A1 — P0.1 CIBO CEREBRO, ENTRADAS, POLÍTICA Y CIERRES
**Issue:** https://github.com/mezas3238-hue/qore-core/issues/737  
**Responsable:** interfaz real del episodio Native MAX por evento, no parseador de etiquetas.
- Trazar CiboNativeMaxCognitiveEpisode hasta modos (src/qore/infrastructure/cibo_native_mode_authority.py) y controller de exits (src/qore/infrastructure/cibo_managed_exit_replay.py). Eliminar umbrales y presets como autoridad FINAL cuando CIBO dispone de observación completa.
- CIBO debe decidir cuantía en USD/riesgo, stop económico, target, timing y modificaciones, y firmar causa con digest de evidencia. Long/short y las seis familias.
- Registrar 3368 decisiones CIBO al entrar al laboratorio y management continuo de toda posición abierta; pruebas de no-lookahead y ablation cognitiva; analizar NDX/GBPJPY/BANK en especial.
- Donde no exista estado suficiente, recibo NO_COGNITIVE_EVIDENCE bien visible; cero aprendizaje retrospectivo con outcomes Trader para decidir en t.

### A2 — P0.2 CUATRO MOTORES Y CAPITAL COMPUESTO
**Issue:** https://github.com/mezas3238-hue/qore-core/issues/738  
**Responsable:** producción de cuatro votos nuevos por evento de entrada sobre NAV/precios/posición re-conciliados, fuentes y limitación agregada.
- Eliminar del experimento la reutilización de four_engine_caps_usd × nav/60 y haircuts de Trader CONTROL. Modificar solo interfaces que les correspondan, con tests de correlación, pérdidas, reinversión/reciclado y riesgo concurrente.
- 4×3368 votos nuevos firmados; normalizar modo BANK/Medium/Attack de la dirección CIBO; documentar presupuesto efectivo frente 5% QORE.
- Si se desea un ensayo «NO STRATEGY CAPS», aislarlo en PAPER y preservar física del broker. No ocultar 3368 señales por low expected edge.

### A3 — P0.3 QDLE, TARIFAS Y BROKER PAPER
**Issue:** https://github.com/mezas3238-hue/qore-core/issues/739  
**Responsable:** QDLE único, persistente y realista con BUY/SELL y todos los contratos.
- Aceptar orden económica de CIBO+cuatro votos, consolidar ledger cuenta global con idempotencia y márgenes/reservas, mtm/fees y parciales de fills.
- Conservar módulo actualizado src/qore/infrastructure/qdle_stellar_instant_costs.py y reconciliación con MT5 src/qore/infrastructure/qdle_mt5_history_fee_audit.py; **prohibido cambiar a viejos $14 FX y $20 NDX** como modelo operativo.
- GBPUSD/EURUSD pip USD10 por 1 lote estándar (0,0001) y misma estructura de comisión $7/lot OPEN; GBPJPY/AUDJPY 1000 JPY/pip/lote convertido al USDJPY de época; XAU $1 por tick de $0,01 en lote; NDX $10 por punto/lote, $0 comisión. Validar contratos con snapshots. Separar spread BID/ASK de fee para evitar doble cómputo.
- Tests: mínimos/steps, $60 NAV5%=3 al inicio, NAV aumenta/disminuye, STOP+OPEN+CLOSE+slippage all-in, cross JPY, XAU porcentaje, free margin, clústers simultáneos, gaps, cuenta stale, fees real de 5 screenshots.

### INTEGRADOR — P0.4 SCHEDULER, LEDGER Y REPLAY TRADER LAB
**Responsable:** nuevo brazo integrado sin pisar módulos A1/A2/A3, conservar shell de workflow validado.
- Actualizar scripts/cibo_trader_lab_native_qdle_market_atlas_3368.py O sustituir por runner claramente canónico cuyo input y output son auditables. No usar el antiguo scripts/qdle_3368_dual_ledger_replay.py como modelo de fills/salidas; solo importador/escenario de QDLE corregido cuando sea necesario.
- Escuchar EVENTOS cronológicos CIBO/fills/MTM, conectarse a 4 motores por cada nueva entrada; QDLE única DB; reconectar estado con cada salida.
- Tratar 20 geometrías antes rechazadas con nueva resolución CIBO y registro QDLE, sin violar SL adverso, SL mínimo del broker ni TP consistente. Tratar las 2 paper abiertas; investigar discontinuidades reales de mercado/sesión; no inventar outcomes.
- Descargar seis artefactos Market Atlas M5 sellados y miembro walk-forward original; preservar pin exacto. Repetir escenario CEO de spreads como BASE; añadir escenarios robustos declarados. Registrar hashes del build/insumos y split OOS sin selección por resultado.
- JSON de 3368 audit rows + curva cash/equity con timestamps + por modo/símbolo/trader/año + causas de rechazo min risk, compound, margin etc + eventos cognitivos + pf/dd/win+comisiones OPEN/CLOSE/swap+gaps. Mostrar explícitamente lo que falta de 2019–2022.
- Benchmark contra la misma ejecución actual (539 paper opened/537 closed, PF .7167, DD CASH 85.2%) sólo para detectar integración/regresión; no compararla como si fuera el carrier 35.24% de otra metodología.

## 8. PRUEBAS DE ACEPTACIÓN — NO DECLARAR TRABAJO TERMINADO SIN EVIDENCIA

**AC01. 3368 inmutables:** hashes de fuente y set 3368 fingerprints iguales y únicos, recepción universal; conservar 3 años 2019-07—2022-06, seis instrumentos, orden temporal.
**AC02. 3368 CIBO cognition genuine:** 3368 episodios reales evaluados/re-evaluados en el estado económico relevante y 3368 recibos de plan, digests previos a resultados; cambio de FUTURO no altera presente.
**AC03. 3368 four-motor NEW:** 4 evidencias por cada una, con 4 salidas causales diferentes, cuentas y fuentes reconciliadas; no multiplicador cap viejo ni voto mock.
**AC04. 3368 QDLE assessments:** cada una tiene respuesta QDLE con volumen numérico/razón física/estado; cero descartes silenciosos o exit de script antes de QDLE por etiquetas/20 geometrías.
**AC05. QDLE singleton per account:** una cuenta/ledger/reservas/concurrencia/idempotencia con presupuesto residual y margen, all-in stop+fees ≤5% QORE NAV individual, lot broker grid, no LIVE.
**AC06. Semántica real de modo:** modo/riesgo/cierres decididos genuinamente por CIBO, no defaults por score confidence ni plantillas idénticas. Diferentes respuestas a un mismo estado cognitivo simulado explicadas; test causal.
**AC07. Fill y gestión autónoma:** ningún PAPER fill sin quote/fill price/fee/cuenta; cada posición con eventos CIBO y cierre causal o abierta MTM explícita. No publicar resultado de los 2809 sin lote como 2809 pérdidas ni como oportunidades ejecutadas.
**AC08. Capital correcto:** $60 QORE vs $2000 broker, P&L NET y fees separados, cargos debitados una vez, reinversión desde realized, floating MTM sobre equity, drawdown cerrado y MTM no mezclados, PF y win rate sólo operaciones settled.
**AC09. Datos/bidask:** documentar que spread fijo capturado en 2026 es sensibilidad sobre M5 2019–22, no market observation del instante de fills. NO usar 158.337 de 2026 para certificar JPYCROSS histórico; estrés 2×/3×, spread FX >0 y anotación de realismo.
**AC10. Reproducibilidad CI:** reproducir exactamente escenario base antes de afirmar mejoría, comparar SHA de seis corpora, manifest fuente, cognitivas y parámetros, publicar artifact JSON + resumen y workflow link. CI fast + integración + negative controls.
**AC11. Loss forensics:** reportar mínimo los 20 descartes pre-QDLE, 2809 sin lote, 2 abiertas, segmentos NDX100/GBPJPY/BANK por P&L/DD, fee breakdown y limitadores REALES vs estratégicos. Probar corrección con ablations no sobreajustadas.
**AC12. Certificación y ownership:** PR #745 se mantiene DRAFT/NO LIVE hasta superar gates físicos/causales/de rentabilidad científicamente probados. Meta interna DD ideal 20%, máximo tolerable 25% y PF >1 como objetivo de investigación, NO cifra que deba fabricarse; no degradar resultados por mezcla de engines/bases.

**Nota aritmética:** 3368 originales = 20 sin QDLE anterior + 2809 sin lot + 539 con lot. 539 openings = 537 cierres + 2 abiertos. Ninguna de estas cantidades permite concluir que 3368 fills sean físicamente posibles. Cualquier informe que aparente 3368 operaciones cerradas con SL/volumen de MT5 sin pruebas debe fallar CI.

## 9. ORDEN PRÁCTICO PARA PRÓXIMO ARQUITECTO (PRIMERAS 2 HORAS)

1. Leer este handoff y código en HEAD ACTUAL de rama/PR #745; leer el handoff de emergencia anterior: docs/research/CIBO_P0_MASTER_EMERGENCY_HANDOFF_2026-10-09_NATIVE_MAX_COGNITION_QDLE_UNIVERSAL_NO_STRATEGIC_BLOCKS.md y contrato doc/research/CIBO_P0_EXECUTION_MANAGED_LIFECYCLE_REPLAY_SPEC_2026-10-09.md.
2. Descargar artifact #11626195451, emitir tabla exacta de 20 INVALID_GEOMETRY, 2 PAPER_OPEN_UNRESOLVED, 2809 no-lot y 539 PAPER; agrupar binding causes, runtime mode y errores de código.
3. Hacer tests que reproduzcan **la falla**: CIBO cognition invocation count =0 en runner; four motor invocation count =0 o scalars reescaladas; QDLE SQLite DB count = por señal, no singleton; 20 skips antes de QDLE. Pruebas *red* deben fallar antes del cambio.
4. Arreglar loop de 3368 administradas, re-evaluar Native MAX contextual, cuatro motores y lote QDLE persistente, completar path/ledger; verificar tests *green* y ausencia leakage.
5. Repetir SOLO el escenario QDLE Stellar Instant corregido con el spread base enviado por CEO, no la vieja comisión. Emitir por separado resultado paper de PnL, PF, drawdown de CAJA y EQUITY, NAV completo/caveats, drawdown por modo y activos y causas de exclusión.
6. Publicar evidencias en PR #745, coordinar Issues #737, #738, #739 sin force-push/cherry-pick ciego, dejar commit y SHA/artefactos/trazabilidad.
7. No finalizar con "trabajo terminado" mientras sólo se hayan vuelto a contar 3368 receipts sin gestión cognitiva efectiva.

## 10. INVENTARIO CANÓNICO VERIFICADO Y ENLACES DE CONTINUIDAD

- [PR #745 Coordinación integradora](https://github.com/mezas3238-hue/qore-core/pull/745), DRAFT.
- [Trader Lab paper terminado 2026-10-09 — ejecución #37949977967](https://github.com/mezas3238-hue/qore-core/actions/runs/37949977967); [artefacto íntegro #11626195451](https://github.com/mezas3238-hue/qore-core/actions/runs/37949977967/artifacts/11626195451).
- [Reporte del último Trader Lab](CIBO_TRADER_LAB_NATIVE_QDLE_M5_SNAPSHOT_SPREAD_3368_RESULTS_2026-10-09.md).
- [QDLE Stellar Instant costos ACTUALIZADOS, escenarios y base científico #37947609981](https://github.com/mezas3238-hue/qore-core/actions/runs/37947609981), fuente actual de decisiones Native MAX integrada en script; NO usar viejo fee model.
- [5 operaciones MT5 con comisiones reales observadas](QDLE_P0_ACTUAL_FUNDEDNEXT_MT5_HISTORY_FEE_RECONCILIATION_2026-10-09.md): EURUSD, GBPJPY, AUDJPY, XAUUSD $0,07 a 0,01 lot, NDX $0.
- [Especificación P0 ciclo de vida y NAV](CIBO_P0_EXECUTION_MANAGED_LIFECYCLE_REPLAY_SPEC_2026-10-09.md).
- [Handoff de emergencia anterior que conserva hallazgos de historia y políticas legacy](CIBO_P0_MASTER_EMERGENCY_HANDOFF_2026-10-09_NATIVE_MAX_COGNITION_QDLE_UNIVERSAL_NO_STRATEGIC_BLOCKS.md).
- [Handoff maestro de integración 3 arquitectos](CIBO_SOVEREIGN_QDLE_MASTER_HANDOFF_2026-10-08_GENERAL_INTEGRATION_P0.md) y [contrato 3 arquitectos](QORE_CIBO_THREE_ARCHITECT_MASTER_HANDOFF_2026-10-08.md).
- scripts/cibo_trader_lab_native_qdle_market_atlas_3368.py — runner cuya cognitiva/four-votes/ledger deben repararse.
- src/qore/infrastructure/cibo_native_max_cognitive_episode.py — motor Native real; src/qore/infrastructure/cibo_native_mode_authority.py — emisión de instrucción; src/qore/infrastructure/cibo_native_sovereign_qdle.py — puente de autoridad.
- src/qore/infrastructure/cibo_managed_exit_replay.py — motor PAPER causal ya implementado en solitario, que requiere dirección CIBO dinámica.
- src/qore/infrastructure/qore_dynamic_lot_engine.py — QDLE singleton a mantener y ampliar adaptación PAPER.
- src/qore/infrastructure/qdle_stellar_instant_costs.py — tarifa moderna NO legacy.
- scripts/qdle_3368_dual_ledger_replay.py — investigación quote-only, no motor de 3368 settlements.
- .github/workflows/cibo-trader-lab-native-qdle-market-atlas-3368.yml — Trader Lab que realmente debe ejecutar final.

### Fases futuras fuera de alcance de la reparación inmediata
Certificar Market Atlas/bidask/historia account-specific y tarifas/contract sobre todo en JPY; batería científica fresco OOS y stress después de corrección, protección DD 20–25%, verificación VPS y provider compliance antes de potencial LIVE. Preservar gates negativos y auditoría soberana, no retirar protecciones físicas para simular ganancias.

**Cierre del handoff:** La integración cognitiva y financiera sigue P0 ABIERTA aunque el workflow anterior haya terminado SUCCESS. La tarea es conseguir **un CIBO que DECIDA cada entrada/salida y un QDLE que DECIDA cada lote**, con 3.368 señales universales y sin bloqueos estratégicos heredados, no un motor que copie presets y numere las señales. Se exige evidencia de mejoras desde Trader Lab y no declaraciones prematuras de victoria.
