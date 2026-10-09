# QDLE — Arquitecto 3/3, reporte de implementación y continuidad P0

**Fecha:** 2026-10-08  
**Repositorio:** `mezas3238-hue/qore-core`  
**Rama aislada:** `agent/cibo-architect-3-qdle-mt5-physical-20261008`  
**Issue:** [#739](https://github.com/mezas3238-hue/qore-core/issues/739)  
**PR de este arquitecto:** [#741](https://github.com/mezas3238-hue/qore-core/pull/741) (**DRAFT, NO LIVE**)  
**PR integrador original QDLE:** [#735](https://github.com/mezas3238-hue/qore-core/pull/735) (**DRAFT, NO LIVE**)  
**Handoff común de tres arquitectos:** `docs/research/QORE_CIBO_THREE_ARCHITECT_MASTER_HANDOFF_2026-10-08.md`  
**HEAD base recibido:** `df10bf9d3def78a69c02dfc1292de49a0027529f`.

## 1. Cambios comprobables hechos por Arquitecto 3

1. El workflow `.github/workflows/qdle-p0-atomic-engine.yml` ahora escucha `push` en la rama 3 e incluye las suites `test_qdle_partial_fills.py` y `test_qdle_mt5_fee_publisher.py` además de la batería QDLE precedente.
2. Se añadieron **14 tests sintéticos de fills parciales y conciliación**: fills completados por dos deals; remanente cancelado por evento broker; overfill; deal ID globalmente único; idempotencia de replays; ticket de posición no compartible entre señales; remanente cancelado impide nuevos deals; bloqueo de multi-ticket/netting/hedging no soportados; no liberación sin cobertura QORE; comprobación de volumen broker, crash/restart, settlement de cierre única vez y estado desconocido retenido.
3. Se reparó una avería de producción en `scripts/qdle_mt5_metadata_publisher.py`: instanciaba `VerifiedFee(usd_per_lot, evidence)` sin el indicador exigido `covers_open_and_close=True`, de modo que la publicación de cualquier tarifa siempre fallaba. La nueva función `verified_roundtrip_fee_for_symbol` exige que el objeto JSON de comisión incluya **un booleano real `covers_open_and_close: true`**, importe USD por lote finito y no negativo, e identificador de evidencia no vacío. Tarifa FX apertura solamente, comisión NDX100 desconocida o base XAUUSD no verificada **no cumplen** el contrato y no deben marcarse verificadas. El booleano no convierte una pantalla o declaración del operador en prueba autenticada.
4. Se corrigió `src/qore/infrastructure/qdle_mt5_read_only.py`: `VerifiedFee` comprobaba `NaN < 0` antes de verificar finitud, provocando una excepción decimal no controlada. Ahora un valor no finito es rechazado como `QDLEError` fail-closed.
5. Se añadieron **6 tests de contrato de tarifas** (campo faltante, bool falso/string/entero, índices desconocidos, importes negativos/NaN, fuente vacía, flujo hasta símbolo MT5 y tasa cero solo con evidencia explícita).
6. No se editaron los módulos de Arquitecto 1 (#737) ni Arquitecto 2 (#738).

### Evidencia CI exact-SHA

- [Run 37851542935](https://github.com/mezas3238-hue/qore-core/actions/runs/37851542935): SUCCESS, commit `0dedd1f6a772c6332441e66679dcc444a3cc379c` (14 tests nuevos parciales; el conjunto QDLE anterior pasó).
- [Run 37851774703](https://github.com/mezas3238-hue/qore-core/actions/runs/37851774703): FAIL, se descubrió `Decimal('nan')` no atrapado por `VerifiedFee`; fallo reparado en código, **no ocultado**.
- [Run 37851841818](https://github.com/mezas3238-hue/qore-core/actions/runs/37851841818): **SUCCESS** exact-SHA `98ffeea3a218e231dabe09b6525c43091643b999`; 89 unittest de los 13 módulos invocados y 3 gateway pytest passed (12 deselected), incluyendo los **14+6** nuevos. Esta es evidencia técnica sintética, NO prueba broker-real ni aprobación de estrategia.

## 2. Investigación solo lectura sobre VPS

Repositorio puente GitHub de operaciones: `mezas3238-hue/qore-vps-control`. La política expuesta `CONTROL_POLICY.json` prohíbe live/real capital y arbitrary shell; respeta solo operaciones tipadas.

- Resultado previo `results/20261008T180400Z-qdle-mt5-readonly-processes-001.json`: operación `list_processes` dio `ok:true` y señaló un proceso `terminal64`; eso NO demuestra cuenta conectada/servidor ni respuesta de `order_calc_profit`.
- Resultado previo `results/20261008T180400Z-qdle-mt5-readonly-qore-directory-001.json`: `C:\\QORE` existe y contiene directorios `scripts`, `src`, `tests`; no demuestra que el checkout incluya QDLE HEAD.
- Último heartbeat leído durante esta intervención: `2026-10-08T21:59:03.2517003Z`, puente `0.4.2`. **No asegurar que el puente siga online**.
- Se publicaron **dos solicitudes de solo lectura** en el puente, `commands/20261008T220845Z-architect3-qdle-git-head-readonly-001.json` (`git_head` para `C:\\QORE`) y `commands/20261008T220845Z-architect3-qdle-scripts-readonly-001.json` (`list_directory` de `C:\\QORE\\scripts`). Al redactar este reporte, sus `results/` **no estaban presentes**: NO atribuir lectura ni cifras actualizadas hasta ver el resultado.
- **NO se ejecutó** un probe broker nativo desde este arquitecto. `qore-vps-control` no tiene operación tipada `order_calc_profit/order_calc_margin/order_check`; no intentar evadir la política con comandos arbitrarios, `pytest_target` u órdenes.

## 3. Invariantes congelados para Arquitectos 1/2/3

- Broker FundedNext **USD 2000 para margen**, capital propio QORE **USD 60 inicial**. Presupuesto bruto inicial de pérdida económica por entrada **5% x NAV QORE = USD 3**. Esta fracción permanece en 5%, dólares cambian con NAV realmente conciliado.
- QDLE interseca los límites de Sizing, CIBO Compuesto, Adaptive Leverage y Portafolio Compuesto. No sumar 4 veces 5%, no usar equity MT5 como referencia 5%, no forzar volumen mínimo no financiable ni confundir señal con fill.
- `order_calc_profit`, `order_calc_margin`, `order_check`, grid volumen, free margin, fee completa, margen abierto y provider rules deben estar causalmente frescos y autenticados antes de LIVE.
- Fills parciales actuales están soportados en **un solo ticket de posición**. Multi-ticket, netting agregativo o hedging que comparten posición quedan **fail-closed**, no reconciliados. Estado `SENDING` desconocido conserva fondos; no liberar por timeout.
- El replay económico de 3.368 señales (2019-2022) y fichas broker de fotos 2026 sigue `FINANCIAL_CERTIFICATION=REJECTED` por causalidad/fees/MTM. No promover PnL, DD, lotes o viabilidad como resultados LIVE.

## 4. Bloqueos P0 que deben seguir visibles

1. Recuperar resultados actuales del puente y verificar `git_head`, rama y disponibilidad del terminal, sin mezclarlo con un examen broker autenticado.
2. Crear una vía **READ-ONLY explícitamente permitida, autenticada y no mutante** para consultor `account_info`, `positions_get`, `orders_get`, `symbol_info`, `symbol_info_tick`, `order_calc_profit`, `order_calc_margin`, `order_check` sobre seis símbolos, sin credenciales de cuenta/secretos en GitHub.
3. Verificar tarifa efectivamente cobrada **open+close** para Forex, fórmula y base de `XAUUSD 0.0016%`, tarifa NDX100 (actualmente desconocida), swaps, sesiones y spread/slippage. Valorar coste dependiente de nocional, precio y duración con quotes contemporáneas; no rellenar cero ni extrapolar tasas sin prueba.
4. Diseñar broker deal reconciliation que vincule **order_id, deal_id, position_id, volumen neto, cancelación y cierre parcial**, también netting/hedging y múltiples tickets con pruebas con snapshots reales. El estado actual **rechaza seguro** los casos no soportados, pero eso no los implementa.
5. Construir replay con datos actuales auténticos (sin fecha as_of falsificada), PnL causal, MTM intratrade, stop-out irreversible, provider trailing MLL, costos completos, ablations auténticas de los cuatro motores y atribución separada de señal → propuesta → orden → fill → cierre.
6. Revisar defectos **globales**, `Zero Open Work Gate` y `Legacy Stack Quarantine`, por sus arquitectos dueños; no modificarlos ni silenciarlos desde este PR.
7. Mantener PR #735 y #741 **DRAFT / NO LIVE**. Nunca conectar `order_send` antes de cerrar estos gates y autorización explícita.

## 5. Contrato de entrada al publicador de tarifas

La clave por símbolo en `--verified-fees` debe ser:

```json
{
  "EURUSD": {
    "usd_per_lot": "IMPORTE_TOTAL_USD_POR_LOTE_DOCUMENTADO",
    "evidence": "IDENTIFICADOR_DE_DOCUMENTO_O_RECIBO_BROKER",
    "covers_open_and_close": true
  }
}
```

**No es un valor ejemplar de comisión:** `IMPORTE_TOTAL...` debe sustituirse por el dato broker auténtico antes de ejecutar; la sola presencia del campo `true` no acredita la procedencia. El lector QDLE rechaza la omisión de esa bandera y valores no numéricos/incompletos. Dejar instrumentos sin tarifa confirmada en modo no-live.

**Conclusión:** se cerró una brecha concreta de cobertura de parciales y se repararon dos defectos verificables del contrato de tarifas. El alcance unitario es GREEN exact-SHA; certificación financiera y física broker-real permanecen NO.

## 6. Ampliación: QDLE universal, SL del Trader y lotajes objetivo variables

**Mandato recibido:** QDLE atiende a TODOS los integrantes que necesiten lotaje (Traders, CIBO y los cuatro motores económicos). El Trader es dueño de dirección/entrada/stop; Sizing, CIBO Compuesto, Portafolio Compuesto y Adaptive Leverage son productores de límites económicos independientes. **Solo QDLE calcula y reserva el lotaje final; no ejecuta `order_send`**.

### Contrato implementado en Arquitecto 3

- Campo nuevo opcional `requested_target_lots: Decimal | None` en `CiboFourEngineLimits`, `QDLEIntent` y `CiboLotSizingInput`, más `/v1/reserve` y `/v1/finance-approval`. Se conserva el comportamiento de lotaje dinámico automático cuando el campo no aparece.
- `requested_target_lots` acepta volúmenes positivos **arbitrarios**, incluyendo 5, 10, 20 y 100, pero funciona como **techo de cantidad solicitada**. No es autorización de riesgo ni promesa de ejecución. Se rechazan cero, valores negativos, no finitos o tipos no decimales; se redondea **hacia abajo** al `volume_step` real; un objetivo inferior al lote mínimo financiable produce `UNFUNDABLE`.
- Algoritmo: partir del **precio de entrada + stop adverso del Trader** → `order_calc_profit` nativo / costo stop por 1 lote contemporáneo → sumar comisión total apertura+cierre verificada y allowance de deslizamiento → intersecar techo 5% × NAV QORE **actual**, presupuesto solicitado, riesgo Sizing, riesgo CIBO Compuesto, fondos autorizados Portafolio, riesgo libre soberano, margen MT5 libre, margen autorizado y máximo en lotes de Adaptive Leverage, `volume_max`, `volume_step`, `volume_limit`, lotaje metodológico mínimo y nuevo `requested_target_lots`.
- El objetivo completo viaja en el **hash de la aprobación financiera soberana** de cada señal/cuenta. Reusar `request_id` con otro target o alterar el target tras la firma es un error, no redimensiona silenciosamente. Al reconstituir la intención en el chequeo one-shot anterior a LIVE, el Decimal opcional se deserializa correctamente. Pre-send verifica riesgo físico y volumen exacto y **nunca envía una orden**.
- CIBO **no adquiere veto sobre señales**; un `UNFUNDABLE` informa que ese lote no es ejecutable bajo los límites físicos o financieros actuales, sin falsificar volumen mínimo ni convertir decisión en fill. El Trader conserva la ejecución sujeto a la autorización del gateway.
- El capital propio de QORE y el broker siguen separados. Solicitar 100 lotes **NO** permite saltarse el 5% por entrada, ni convertir USD 2000 de equity FundedNext en el NAV propio de USD 60.

### Evidencia y entrega entre arquitectos

Archivos de implementación: `src/qore/infrastructure/cibo_physical_lot_sizing.py`, `src/qore/infrastructure/qore_dynamic_lot_engine.py`, `src/qore/infrastructure/qdle_cibo_bridge.py`, `src/qore/infrastructure/qdle_local_api.py`. Suite añadida: `tests/infrastructure/test_qdle_universal_lot_targets.py`; CI en `.github/workflows/qdle-p0-atomic-engine.yml`.

- Fixtures sintéticas: 5/10/20/100 lotes cuando todo el presupuesto lo permite; sin target, cálculo por USD; stop más amplio reduce lotes; cada motor puede ser limitante; dos identidades de Trader compiten por el **mismo banco de riesgo atómico**, sin doble gasto; retícula y mínimo broker; target firmado inmutable y presend one-shot; NAV USD 60/120 y pedido de 100 lotes dan techos de riesgo USD 3/6 respectivamente.
- Las cantidades de fixtures provienen de un calculador ficticio explícito y **NO corresponden a contratos auténticos FundedNext**.
- Arquitecto 1: conservar el `TraderOpportunityEnvelope` (SL, entry, símbolo, identidad) íntegro hasta QDLE. No sustituir stop con multiplicadores.
- Arquitecto 2: enviar caps económicos **por señal, cuenta y epoch**, firmados de forma independiente. `requested_target_lots` es opcional si se quiere expresar una preferencia de volumen, pero **ningún motor puede elevar los techos soberanos**. Documentar el capital de origen y tratamiento de fees.
- Arquitecto 3: permanece responsable de broker-native `order_calc_profit`/`order_calc_margin`/`order_check`, margen, comisión completa, retícula y fills/settlements. Sin evidencia broker autenticada y gates P0 verdes: **NO LIVE**.

PR [#741](https://github.com/mezas3238-hue/qore-core/pull/741) permanece **DRAFT**. La ampliación de lotaje universal está **VERIFICADA EN CI SINTÉTICO**: [GitHub Actions run 37857035541](https://github.com/mezas3238-hue/qore-core/actions/runs/37857035541), exact-SHA de código `fc48cc71ae8fc8f88fe1fe6efadb0875864a175e`, resultado SUCCESS, **98 unittest** (incluidas 9 pruebas de lotaje universal) + **3 pytest gateway** (12 deselected), job `113583571564` íntegramente verde. La certificación física FundedNext y los gates globales siguen **PENDIENTES / NO LIVE**.

## 7. Cambio expreso de alcance: NO VPS; simulación como si fuera operativa real

**Directiva del usuario (2026-10-08):** **no se operará en VPS**. El trabajo prioritario pasa a ser simular la operativa, ejecutar replays causales y comparar resultados de lotaje/stop/riesgo/margen/comisiones/capital. Cualquier sección previa sobre desplegar en el VPS queda en segundo plano y **no es un paso autorizado de esta misión**. No usar `order_send`, no conectar capital real, no afirmar que existe un fill físico. El contrato físico de bróker (metadatos y tarifas reales) sigue siendo deseable como **dataset verificable o fixture offline**, nunca como permiso para operar.

### Ejecución de replay confirmada por GitHub Actions

[Run 37858772829](https://github.com/mezas3238-hue/qore-core/actions/runs/37858772829), **SUCCESS**, SHA `20966f17edfc0fefefe4eb35e3473ab6dc8bb008`, job `113589245360`. Origen pinneado por ZIP SHA256 del manifest original 2019–2022, **3.368 señales únicas comprobadas** en los tres escenarios. Artefacto de informes/decisiones/auditoría: **11585371062** (`qdle-3368-dual-capital-RESEARCH-37858772829`) en el mismo run. Esta ejecución fue disparada en rama 3 al habilitarla en `.github/workflows/qdle-3368-dual-capital-replay.yml`, no en VPS.

| Escenario | Propuestas financiables | No financiables/bloqueadas | QORE NAV final USD | Broker equity proxy USD | PnL net proxy USD | Max DD cierre | Provider stop |
|---|---:|---:|---:|---:|---:|---:|---|
| `original_trader` + $120 trailing supuesto | 697 | 2671 | 5.50230747 | 1945.50230747 | -54.49769253 | 92.8591% | No |
| `broker_grid` min 0.01 + $120 trailing supuesto | 1628 | 1740 | 125.05318843 | 2065.05318843 | +65.05318843 | 87.7482% | **Sí, 2021-05-05** |
| `broker_grid` min 0.01 + provider rule disabled | 2113 | 1255 | 9.83837158 | 1949.83837158 | -50.16162842 | 97.5319% | No |

**Auditoría:** `audit_integrity=PASSED`, `financial_certification=REJECTED` en todos. Recuentos de pérdidas realizadas con -PnL superior al presupuesto original 5%: **91 / 201 / 272** respectivamente. Tarifas NDX100 asumidas cero por desconocimiento en **0 / 247 / 306** propuestas. Sizing y CIBO Compound usan idéntico techo proxy 5% y no son decisiones históricas independientes; por tanto **NO atribuir PnL a los cuatro motores**. La simulación aplica screenshot MT5 2026 sobre oportunidades 2019–2022, solo comisión de apertura Forex $7/lot, cierre sin demostrar, XAU fee base estimada y NDX fee desconocida, swaps con reloj UTC inventariado, sin bid/ask verdadero ni estados intratrade. El DD es **closed-equity**, no max DD físico intratrade.

**Diagnóstico causal operativo:** el mínimo original del Trader deja sin financiamiento ~79.3% de las señales; bajar ese mínimo a 0.01 incrementa participación simulada, pero el riesgo del capital QORE sigue altísimo. El caso de NAV USD 125.05 es **stopped temprano por un umbral provider no verificado**, no una solución. Sin esa regla arbitraria, el mismo broker-grid simulado finaliza con USD 9.84. Así, **no extrapolar rentabilidad, no declarar listo a QDLE/traders/capital**. Demuestra que un número de señales esperado no implica ese mismo número de entradas financiadas.

**Prioridad de continuación científica sin VPS:** (1) modelar fill parcial, spread, slippage y comisión completa por parámetros de sensibilidad explícitos, sin llamar reales a costes no confirmados; (2) stop-loss intratrade/MTM y trailing provider irreversibles con series temporales o cotizaciones reproducibles; (3) recuperar snapshots y decisiones independientes de los cuatro motores del Arquitecto 2, con trazas causales por señal; (4) comparar sensibilidad de `requested_target_lots` (5/10/20/100, nunca encima de presupuesto 5% NAV, margen ni grid); (5) no reinterpretar un mínimo de 0.01 como autorización para modificar metodología original del Trader; (6) reproducir resultados con semillas, versiones de manifest y escenarios y reducir DD documentando el sacrificio/retención de capital y densidad.

**Estado definitivo del replay de esta entrega:** terminado y verificado CI **como simulación investigativa**, no certificado como broker-real ni como estrategia aprobada; usuario no desea VPS.

## 8. P0 integrado: cuatro productores nativos -> QDLE -> replay de 3.368 señales

**Directiva del usuario:** finalizar integración de lotaje de Sizing, CIBO Compuesto, Portafolio Compuesto y Adaptive Leverage y ejecutar replay, **sin VPS, sin orders**.

Se integraron en la rama aislada del Arquitecto 3 los productores implementados por Arquitecto 2 en su rama canónica (sin fusionar ni modificar su rama): `propose_p0_sizing_vote`, `propose_p0_compound_vote`, `propose_p0_adaptive_leverage_vote`, `propose_p0_portfolio_vote`, `FourMotorObservation`, `ReconciledQoreCashflow`, `FourMotorProposal`, `build_four_motor_qdle_intent`, `sign_producer_receipt`, y sus ablations de capacidad control+4. Cada productor opera en su propio módulo nativo. QDLE mantiene la reserva atómica final y no ejecuta órdenes. En integración definitiva entre ramas, usar una revisión de diferencias con Arquitecto 2 antes de merging porque esos archivos se copiaron **para habilitar el replay en la rama 3**.

**Regla económica implementada:** QDLE utiliza stop-loss/entry/side del Trader, riesgo 5% de NAV QORE causal, presupuesto de Sizing USD, reinversión compuesta USD, fondos de Portafolio USD, máximo lotes y margen de Leverage, dinero soberano libre, grid y margen broker. Interseca límites: no suma cuatro asignaciones como cuatro riesgos autorizados. `requested_target_lots` sigue opcional 5/10/20/100 lotes en el builder nativo, pero es techo y se aplica antes de cualquier cálculo físico. Identidad, epoch y SHA de las cuatro fuentes deben coincidir; firma HMAC independiente probada por suite sintética (el replay histórico NO lleva recibos broker reales).

**Comisión completa:** en EURUSD ejemplo de 10 pips con USD100 stop/lot, USD60 NAV y 5% USD3, comisión $7 por lote **OPEN + $7 por lote CLOSE = $14/lot**. 0.03 lotes daría $3.42 de riesgo y **no cabe**. QDLE debe reservar 0.02 lotes, USD2 stop + USD0.28 comisión = USD2.28 all-in, sin margen adicional ficticio. La nueva suite verifica el ejemplo con QDLE real y test broker determinístico. En replay `independent_four_motors`, QDLE reserva 100% de tarifa ida/vuelta al inicio, pero el libro simulado **debita la primera mitad al abrir y la otra mitad al cerrar**; para XAU se supone simétrico 2 × 0.0016% * notional, fórmula y base aún NO verificadas, para NDX se exige parámetro explícito (la corrida utiliza **USD20/lot TOTAL ASUMIDO, solo sensibilidad**, NO tarifa del broker). Swap/estructura 2026 sobre señales 2019–2022 sigue siendo proxy.

Se agregó cuarto escenario al workflow `.github/workflows/qdle-3368-dual-capital-replay.yml`: `--motor-policy independent_four_motors --min-policy broker_grid --ndx-roundtrip-fee-proxy-usd-per-lot 20`. Este consume las mismas **3.368 señales únicas** del artefacto fijado por hash, construye en cada epoch las cuatro propuestas nativas desde observaciones causalmente simuladas (book synthetic, no fee statement ni BID/ASK real) y envía el `QDLEIntent` único al motor físico. Se conservaron los tres escenarios históricos de referencia. Resultados contienen trazas de caps de cada motor y razones, lotes, financiación, NAV, pérdidas, DD cierre, comisiones apertura/cierre y auditoría de integridad.

La auditoría `qdle_3368_financial_truth_gate.py` ahora distingue costo FX de apertura $7/lot en los escenarios históricos vs $14/lot ida/vuelta en el nuevo; verifica NDX sensibilidad explícita y que **OPEN pagado + CLOSE pagado + CLOSE pendiente = TOTAL comprometido**. Ninguno constituye broker fill, ni DD intratrade, ni valor conocido de las tarifas NDX/XAU.

**Evidencia unitaria:** [GitHub Actions run 37862343025](https://github.com/mezas3238-hue/qore-core/actions/runs/37862343025), código exact-SHA `e245cc6229f121c5fe0940cb1006e83eae4195bc`, SUCCESS: **110 unitarias en 15 suites + 3 pytest gateway**. Contiene 11 tests del comité económico, integración firmada, 10 tests de objetivos universales, comisión EURUSD 14/lot, 3.368 IDs synthetic capacity, rechazo de cross-epoch y evidencia adulterada. **No certificación física, ni live**.

La primera ejecución de cuatro motores fue [run 37862041350](https://github.com/mezas3238-hue/qore-core/actions/runs/37862041350), exact SHA `db8c2bd8a156484ab4dbaf20d5c600f22b1e4b3b`, SUCCESS. Resultado **pre-corrección de calendario de comisiones**: 304/3.368 propuestas financiables; 3.064 no financiables, capital QORE simulado USD6.51298 y DD cierre 93.2984%, PF ~0.6964; `financial_certification=REJECTED`. Este resultado es histórico para diagnóstico, **NO usar como final** después de la corrección de tiempos y streak. Siguió refinamiento para cobrar comisiones de apertura/cierre por separado, preservar tres settlements recientes para defensa compuesta y auditar cashbook completo.

**Criterio para concluir esta etapa:** esperar el último replay exact-SHA con estos cambios y actualizar resultados; el motor puede quedar integrado/verificado como SIMULACIÓN de laboratorio aun si el PnL del experimento es malo, pero NUNCA "trading rentable", "broker real", "certificado" ni "operación MT5". Reproducción OOS actual y DD intratrade/costos auténticos siguen pendientes de verdadera certificación.

### Cierre: replay integrado definitivo y contrastación

**RUN FINAL DE CÓDIGO:** [GitHub Actions #37862345666](https://github.com/mezas3238-hue/qore-core/actions/runs/37862345666), **SUCCESS** con exact-SHA `e245cc6229f121c5fe0940cb1006e83eae4195bc`, job `113600794997`. El artefacto `11586553959` contiene informes completos `qdle-3368-*.json` y los cuatro `qdle-truth-gate-*.json`. Se validaron 3.368 IDs/señales únicas y coberturas completas en cada escenario. Todas las auditorías devuelven `audit_integrity=PASSED` y `financial_certification=REJECTED` por ausencia de datos brokers temporales auténticos, MTM intratrade, tarifas completas certificadas y outcomes MT5.

**CUARTO ESCENARIO — CUATRO MOTORES REALES EN CÓDIGO (solo simulación):** 329 propuestas QDLE financiables, 3.039 no financiables; desde **USD60 a USD9.032083** de capital QORE simulado; PnL neto **-USD50.967917**, **DD máximo de capital cerrado 87.299075%**, PF proxy **0.74047**, ninguna parada provider en este escenario hipotético. Comisiones totales de apertura+cierre comprometidas **USD90.10846592**, de ellas **USD45.05423296 debitadas en apertura y USD45.05423296 en cierre**; ninguna comisión de cierre pendiente al finalizar. El truth gate detecta **19** pérdidas realizadas cuyo -PnL excede el techo 5% con el que se autorizó su trade: NO declararlo un límite realizado garantizado; saltos, R estructural proxy, swap y costes pueden exceder stop previsto.

Comparación de control: escenario `original_trader`: 697 propuestas, NAV USD5.50, DD 92.86%; `broker_grid` + trailing $120 supuesto: 1.628 propuestas, NAV USD125.05 pero paró temprano en 2021-05-05, DD 87.75%; `broker_grid` sin provider límite: 2.113 propuestas, NAV USD9.84, DD 97.53%. **No usar cifras de escenarios incongruentes para afirmar mejoras causales de PnL por los cuatro motores**, porque difieren fees y fuente de capital/riesgo además de controles. Preparar próxima batería ablation con costes iguales por rama y trazas causalmente contemporáneas.

**Resultado de la MISIÓN DE INTEGRACIÓN:** QDLE está conectado funcionalmente a los cuatro productores económicos para replay offline; 110 pruebas unitarias + 3 gateway PASSED, replay íntegro 3.368 PASSED de auditoría. **Resultado de TRADING:** sigue NO RENTABLE en la simulación actual y NOT CERTIFIED para rentabilidad ni provider. No operar en VPS; no orden MT5; PR #741 DRAFT. Siguiente prioridad reproducible: DD intratrade, stops y fees con series de precios, porcentaje provider auténtico o sensibilidad claramente simulada, R de pérdidas reales, cuatro ablations con MISMA política de fees/mínimo, y diagnóstico de 3.039 no financiables por instrumento y causalidad. Arquitecto 2 debe revisar cambios copiados a rama 3 antes del merge.

## 9. DIRECTIVA PROPIETARIO — CIBO manda, QDLE sirve (reparación posterior al replay USD9,03)

**Advertencia P0:** No seguir diciendo que USD9,03 es el resultado integrado de CIBO. El escenario anterior generaba por su cuenta topes de investigación y colocaba 100% en `SOVEREIGN_BANK`; no tenía decisiones CIBO originales de las 3.368 señales ni salidas administradas por CIBO. El viejo USD~670k también está **invalidado** por H8, de modo que no existe un baseline CIBO solvente certificado contra el que se pueda afirmar coincidencia.

### Contrato corregido y ejecutado

- `src/qore/infrastructure/qdle_cibo_authority.py`: nuevo `CiboEconomicInstruction` define ID señal/Trader/símbolo/lado/entry/SL, `source_lane` aprobado explícitamente por CIBO, `allocated_source_funds_usd` **capital de trabajo**, `authorized_all_in_risk_usd` **riesgo incluyendo stop y fees**, máximo de lotes opcional, epoch/cuenta/timestamp/hash. No convierte capital de trabajo en riesgo ni permite >5% de NAV QORE.
- `build_cibo_directed_qdle_intent`: combina la orden económica de CIBO con los **4 votos nativos**, preserva la fuente y geometría; QDLE sólo redondea el lote según min/max/step, stop, fees completos, margen/volumen real y reservas. Si falta la instrucción o cambia source/signal/epoch falla cerrado.
- `scripts/qdle_3368_dual_ledger_replay.py --cibo-instructions PATH --motor-policy independent_four_motors`: NUEVA ruta opcional de replay CIBO-directed. Exige documento de 3.368 señales originales completas (IDs únicos sin extraneous), fuente inicial `initial_bank_usd + initial_cushion_usd = USD60`, transfers explícitos con respaldo, votación causal actualizada con cada `account_sequence`. No hay transferencia de fondos implícita: banco y colchón se contabilizan separados, pagando comisiones al abrir y cerrar y reconociendo PnL en la fuente de la posición. Si un fondo queda insolvente, se bloquea en lugar de salvarlo silenciosamente con el otro.
- Formato externo `qore.cibo.qdle-authoritative-economic-input.v1` con `instructions[]` (signal_id, trader_id, symbol, BUY/SELL, entry_price, stop_price, source_lane, allocated_source_funds_usd, authorized_all_in_risk_usd, maximum_requested_lots, account_sequence, issued_at UTC, evidence_sha256), `capital_transfers[]` (at, from_lane, to_lane, usd, evidence_sha256) y `managed_settlement_receipts[]` (signal_id, exit_at, gross_outcome_r, evidence_sha256). Si CIBO autoriza dinero para una señal pero **no proporciona recibo de cierre/gestión**, el replay integrado falla cerrado: NO heredar silenciosamente la antigua salida structural R del Trader Lab. Los resultados de cierre sólo se aplican al settlement, nunca al presupuesto de entrada. Esto es contrato de **RESEARCH**, no autenticación live de firmas ni deals.
- Los comandos antiguos SIN `--cibo-instructions` siguen siendo **PROXIES ECONÓMICOS SIN DIRECCIÓN CIBO**. No atribuir sus DD/PnL a CIBO aunque produzcan números y pasen validación contable.
- `tests/infrastructure/test_qdle_cibo_authority.py`: **9 pruebas**: ATTACK/PORTFOLIO_CUSHION con USD50 fondos no implica USD50 pérdida; stop de EURUSD 10 pips + USD14/lote ida/vuelta → USD3 máximo → QDLE 0,02 lotes, USD2,28 total; presupuesto reducido disminuye volumen; no suplantar Trader/activo/epoch/fondo; cero gasto sin presupuesto; bloquea capital asignado no respaldado; no sustituye directiva CIBO faltante.
- `scripts/qdle_synthetic_cibo_authority_fixture.py` + `.github/workflows/qdle-cibo-authority-negative-control.yml`: prueba exactas 3.368 señales selladas y **solo de interfaz sintética**, nunca decisiones históricas CIBO verdaderas.

### Prueba ejecutada de control causal (NO ganancias reales)

**[GitHub Actions #37864937747](https://github.com/mezas3238-hue/qore-core/actions/runs/37864937747), SUCCESS**, commit `565fc377b7dae36ae2766a95da25e2598e69a0e5` (antes del posterior endurecimiento de insolvencia/proveniencia), **9 pruebas unitarias PASS**; fuente 3.368 señales históricas auténticas pero directivas CIBO **generadas expresamente como ficción de prueba**.

- Control negativo 3.368 directivas con autorización **USD0**: **0** propuestas financiables, QORE **USD60**, fondos banco USD30 / colchón USD30, ningún broker fill. Prueba que QDLE no abre por su cuenta.
- Control positivo: de 3.368 señales, exactamente **1** EURUSD con presupuesto CIBO USD3 y máximo 0,01 lotes, 3.367 autorizadas en USD0; cierre CIBO **sintético** +1R. **1** propuesta financiable, 3.367 inviables por orden, NAV SIMULADO USD60,95, banco USD30, colchón USD30,95, cero fills reales. Es únicamente una prueba de obediencia de QDLE a la orden CIBO/cobro apertura+cierre; **no evidencia de rendimiento ni de una operación real**.

### Bloqueo que impide un replay VERDADERAMENTE integrado de CIBO

**Arquitecto 1 (#737):** el director `cibo_trade_ops_director.py` es actualmente contrato de gestión SHADOW y no ha entregado 3.368 autorizaciones preentrada más la cronología de gestión/SL/TP/salida y recibos de exit por señal. **Arquitecto 2 (#738):** exige 3.368 asignaciones causalmente respaldadas por Portafolio (ATTACK vs MEDIUM, transferencias interfuente, bank/cushion) y decisiones independientes de Sizing, CIBO Compuesto y Adaptive Leverage con account sequence. El pipeline histórico research no es un broker ledger verificado. No crear recibos supuestamente reales sintéticamente para salvar la comparativa.

**Próxima prueba obligatoria:** cuando los dos productores entreguen evidencia CIBO real de research con 3.368 IDs y misma cronología, correr `--cibo-instructions` con cuatro motores y comparar operaciones señal a señal: Trader entry/SL, CIBO risk/allocation/gestión, QDLE lote+costo+margen, cada cierre y PnL, DD cerrado e intratrade. Mantener gateway bloqueado a live y PR DRAFT hasta broker comprobado y autorización del dueño.
