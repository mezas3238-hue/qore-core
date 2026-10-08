# QORE CIBO H28 — USD 3 REALES AL STOP, NO USD 0.69 / INCUMPLIMIENTO DE RIESGO HISTÓRICO

**2026-10-08 | Estado: el replay H27 fue reproducido y H28 gate de lotaje pasó 6/6 tests. NUEVO REPLAY COMPLETO CON USD3 EFECTIVOS: NO DISPONIBLE; NO FINGIR RENTABILIDAD.**

## Orden inequívoca del propietario

Cuenta de capital inicial **USD 60**. **USD 3 monetarios efectivos al stop por entrada inicial** (5% del capital inicial), no un mero presupuesto máximo nominal ni 0.69. Con crecimiento de equity, evaluar 5% del **capital causal al momento de decidir**, salvo mandato posterior explícito de USD3 constantes. No modificar las entradas de los 3368 Traders, la cognitiva, la gestión de salida, los cuatro motores ni el modo de CIBO. No aumentar a ciegas apalancamiento ni cambiar R o TP para aparentar USD3; lo que debe cambiar es la cantidad **broker-legal** de volumen, conservando stop price original. Comisiones cobradas además del riesgo al stop.

## H27: prueba cuantitativa de 3368 operaciones con CIBO auténtico

- `agent/cibo-h27-3usd-stop-risk-hard-compliance-001`, workflow `.github/workflows/cibo-trader-lab-h27-strict-dollar-risk-full-replay.yml`, [run 37793406108 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/37793406108), artefacto `11557587185`.
- Resultado `docs/research/CIBO_H27_USD3_STOP_RISK_NONCOMPLIANCE_3368_REPLAY_VERIFIED.json` commit `499ee78c9ec162e2d89d23ed9a04dcefd25dd991`.
- **Research workflow SUCCESS validates the diagnostic, NOT the requested USD3 allocation!** Status explicit `NONCOMPLIANT_WITH_3USD_STOP_REQUEST`.
- Julio 2019: **84** entradas, **82** con stop risk <USD3, mediana **USD0.69277534**, 2/84 >=USD3. El primer trade NAS100 tiene stop risk **USD0.29500**. Para arriesgar USD3 con el mismo precio de stop y unidades enteras se precisaría **10.169491525x**, que el modelo no soporta. 10x=>USD2.950; 11x=>USD3.245, **excede presupuesto exacto inicial 5%**.
- Primer año **1109 operaciones cerradas**, 922 bajo USD3, mediana riesgo **USD0.96112458**. Ganancia de replay viejo **USD408.14184888** (~USD0.36802692 por operación), pero **NO ganancias verificadas de un replay con USD3 efectivos**.
- Todos 3368 recibos: 2237 con stop risk <USD3. Ignorando margen, en **3247/3368** stops no existe multiplicador ENTERO que dé exactamente USD3. **Este USD3 fijo a lo largo de 3 años solo es referencia cuantitativa; la especificación 5% dinámico necesita snapshots de preentrada de equity incl. flotante**.
- Incluso si un tamaño matemático se aproximara a USD3, la viabilidad real debe comprobar lotaje mínimo, paso, margen libre, comisiones, spread, presupuesto agregado concurrente, banco soberano y piso trailing/DD. En un estudio H10 anterior el primer 0.10 lot de NAS100 requería ~$77.79 de margen *estimado*, mayor a los USD60 (snapshot no certificado del broker para 2019). NO es prueba de la situación actual del broker sin specs reales.

## H28: implementación segura para el componente puramente monetario de Sizing

- En rama **`agent/cibo-h28-exact-3usd-broker-lot-sizing-001`**:
  `src/qore/infrastructure/trader_lab/cibo_exact_three_dollar_lot_sizing_h28.py`
- `BrokerLotContract`: paso legal, lotes mínimo/máximo, stop USD/lot, margen USD/lot, fee ida/vuelta USD/lot.
- `plan_exact_stop(...)`: resolución decimal al **centavo exacto** del stop monetario. Si lo representa lote legal y existe efectivo *libre/no reservado* capaz de cubrir margen+comisiones sin superar 5% de equity, da plan; en caso contrario devuelve `accepted=false` y causa explícita. **Jamás inventa ejecución ni imprime una ganancia**.
- 6 tests unitarios verdaderos en CI [H28 run 37793986650 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/37793986650). Casos: $3 exacto en 0.10 lote legal de stop $30/lot; NAS100 USD2.95 / USD3.245 paso de .1 no logra USD3 exactos; mínimo lote no alcanza margen USD60; efectivo libre insuficiente; operación excede 5% (rechaza); capital compone USD100→USD5 al stop.
- Este H28 **no se ha conectado a la administración canónica** y no valida márgenes ni lotes específicos del proveedor en producción. Los tests synthetic no sustituyen 3,368 replays financiados reales. Mantener original de CIBO intacto hasta integrar con comprobación de causalidad, stop-monetary precision y todos los invariantes.
- NO definir `0.69` como si cumpliera 5%, ni forzar a 1.1 lot sin fuente de margen y stop. Si falta especificación de broker/volumen real, estado **FUNDING_UNVERIFIED / FAIL_CLOSED**.

## Próximo trabajo de ingeniería P0

1. Descubrir especificaciones contractuales reales por símbolo, cuenta/broker concreta, lote mínimo/incremento, tick value, margen requerido, fee por lado, spread, stop points, equidad/capacidad y margen concurrentes, y legal stop-risk exactness; no asumir que `multiplier` entero significa lot legal.
2. Conectar `plan_exact_stop` a **solo el tamaño monetario de entrada de CIBO** y a un libro de riesgo financiable compartido por MEDIUM y ATTACK, preservando cognitivas/salidas/capital compuesto/banco. Debe explicar cómo mantiene 3368 entradas si ciertos símbolos no son físicamente financiables; una supuesta ejecución no financiable INVALIDA todo el replay.
3. Lanzar corrida integral USD60->36meses y cortes a 1,3,6,12 meses; no publicar ingresos de USD3 hasta que los 3368 tengan stop monetario causal correcto y fondos/broker suficientes, 0 sovereign floor breach, DD<=25% ideal20%, márgenes/fees positivos.
4. Evitar backtest-instrument hindsight con etiquetas futuras; sellar OOS nuevo tras hipótesis. Separar el escenario FundedNext Stellar Instant USD2000 de esta cuenta USD60. La tarifa proporcionada por usuario de USD7/lot por lado = USD14/lot round-trip, distinta del provider cost nativo utilizado en H26.

## Diagnóstico económico inmediato

Los cuatro motores H26 eran funcionales; que Sizing 1x sea frecuente, y el 5% fuese interpretado como **cap** y no como stop-risk aplicado, explica que gran número de entradas arriesgue menos que USD3. Pero NO autoriza a prometer un rendimiento anual 10x mayor: la serie incluye pérdidas, fees, riesgo y estados posteriores compuestos. El primer año modelo terminó $60->$468 con riesgo subasignado, por lo que ese valor no responde a la pregunta del usuario sobre ganancias con USD3 reales.

**DECISIÓN: RECHAZAR EL REPLAY ANTERIOR COMO VALIDACIÓN DEL REQUISITO MONETARIO; NO CERTIFICAR USD3 CON ESTE BROKER Y ESPECIFICACIONES INSUFICIENTES.**
