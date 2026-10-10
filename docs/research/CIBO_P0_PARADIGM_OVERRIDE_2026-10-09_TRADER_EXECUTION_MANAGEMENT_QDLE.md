# P0 — DIRECTIVA CEO: CIBO DE FILTRO DE ENTRADAS A ADMINISTRADOR ECONÓMICO

**PR #745 / rama `agent/cibo-sovereign-integration-p0-20261008`** · 9 octubre 2026  
**Estado:** norma de diseño en investigación, **no deployment LIVE**, reemplaza la interpretación operativa de `COGNITIVE_BLOCK` / `CAPITAL_BLOCK` del replay Native MAX anterior. QORE Risk, treasury, verificación MT5 y límites financieros siguen vigentes.

## 0. Corrección de autoridad y cronología

**Trader posee señal y estrategia:** oportunidad, dirección, precio, SL estructural, TP, timestamp, requisitos de ejecución e invalidación de tesis. CIBO **no re-clasifica ni veta** señales que ya han sido creadas por un Trader legítimo como condición de recepción.

**CIBO posee administración económica:** toma a cargo **cada señal** con un expediente auditable, decide cómo asignar fuentes permitidas, solicita volumen físico a QDLE, configura stop de salida económica / parciales / trailing / break-even / protección y gestiona posiciones realmente confirmadas. Los módulos Sizing, Compuesto, Adaptive Leverage y Portafolio Compuesto informan restricciones/equidad y propuestas; **no crean fills ni pueden falsear solvencia**.

**QDLE**: autoridad única del **lote físico** cuantizado, stop loss económico total a presupuesto, margen, comisiones OPEN+CLOSE, spread/slippage, lot grid, exposición y disponible de Bank/Cushion. **QORE Risk + Treasury** conservan aprobación de límites y reservas y el **gateway/MT5** valida `order_check` y el fill real. QDLE no sustituye las autorizaciones independientes.

### Secuencia real para **nueva orden**

```text
TRADER decide oportunidad (no es fill)
  -> CIBO registra recepción de las 3368/3368 oportunidades + modo y política económica
  -> evalúa opciones de SL económico y administra condiciones/contexto
  -> cuatro motores aportan cuotas independientes de capital/riesgo/margen
  -> QDLE computa lote legal y reserva capital, con QORE Risk/Treasury
  -> gateway MT5 check + send SOLO SI está totalmente autorizado
  -> reconciliación de fill real/ticket -> CIBO gestiona posición y salidas.
```

**Si el Trader YA ejecutó realmente**, el primer evento es un **fill/broker position verificado**; CIBO la incorpora a cartera, evalúa riesgo y propone protección o reducción. Es imposible calcular tamaño *antes* de una operación ya ejecutada; no falsificar cronología ni crear operaciones duplicadas.

## 1. Tres opciones económicas cuando el SL estructural excede 5% QORE NAV

**Presupuesto dinámico:** `B = min(0.05 × QORE_NAV_reconciled_at_entry, CIBO_allocated_loss_limit, motor caps, actual available source/risk)`. Con 60 USD, máximo teórico 3 USD. **Proveedor separado** (por ejemplo nominal USD2000) solo respalda margen real, no sustituye capital QORE. Comisiones OPEN+CLOSE, margen, swap si aplicable, gastos y slippage se auditan por símbolo.

1. **Proponer SL económico acotado**, separadamente del SL estructural original que sigue archivado. Con un lote mínimo válido, convertir presupuesto restante después de comisiones y buffers en **distancia de riesgo protectora** al stop; tick rounding conservador y `broker stop level` y patrón de entrada válidos. **Diferenciar claramente** una salida por presupuesto de invalidación de tesis: puede causar salidas prematuras, por eso NO atribuirle el resultado original del Trader. CIBO solo puede proponer una distancia con valuación contemporánea de `order_calc_profit`/ticks y garantías de precio de broker; no inventar ATR.
2. **Reducir lote** si `min_lot`/`lot_step` y todas las políticas de QDLE lo permiten. QDLE decide volumen, nunca CIBO fuerza 0.01. Probar volumen más pequeño sobre SL original ANTES de ajustarlo si hay margen de reducción; con lote mínimo ya en 0.01 no existe `0.009` permitido.
3. **Gestión anticipada como mitigación complementaria**: early exit, break-even, parcial, trailing, coberturas autorizadas pueden comprimir pérdidas, **PERO NO autorizan entrar con riesgo contractual hasta el SL > B**. Un stop prometido «cerrar antes» puede fallar por gaps, spreads, latencia, desconexión; solo se permite abrir si QDLE verifica un stop protector efectivamente financiable y el gateway confirma. En ausencia de (1) y (2), **la señal queda recibida y administrada como `RECEIVED_UNFUNDABLE`, sin orden**, y se conserva su identidad íntegra.

**Ejemplo EURUSD** (solo proxy, USD10/pip/lot + USD14/lot RT): SL estructural 35 pips -> 0.01 lot arriesga `0.01×(350+14)=USD3.64 > USD3`. Si es elegible una salida económica a 28 pips, 0.01 lote costaría `0.01×(280+14)=USD2.94`, sujeto a spread/tick/broker minimum/evidencia. Sin un stop protector permitido, NO ejecutar 0.01 por promesa de early exit.

## 2. Contratos mínimos obligatorios

- `TraderSignalIntake`: id único/símbolo/trader/BUY|SELL, `entry`, `structural_stop`, `TP`, `decision_at`, contexto/ATR opcional, fuente del Trader. **La recepción está separada** de una decisión de ejecutabilidad.
- `CiboAdministrationReceipt`: por **cada** ID, estado `RECEIVED`, modo, SL estructural intocable, SL económico `PROPOSED`/no disponible, estrategia de salida/manejo, presupuesto `B`, source lane, razón `UNFUNDABLE` o `READY_FOR_QDLE`; no señal «rechazada por cognición».
- `QDLEPhysicalFundingReceipt`: lote real / `UNFUNDABLE`, desglose SL loss + OPEN/CLOSE fees + otros + margen; lote 0 cuando no existe factibilidad; `fills=0` hasta verificación real.
- `ManagementPlan`: para movimientos favorables/parciales/trailing y adversos/reducción, con reglas de activación causales y reservas, sin suplantar un stop duro inicial. En posiciones ya existentes, reconciliar lotes y stop real antes de emitir instrucciones de cierre.
- `MT5ExecutionReceipt`: ticket/deal, fill price, comisión OPEN, slippage, stops/protección, cierre y comisión CLOSE, timestamps y posiciones.
- `ATRStopShadowReceipt`: BAR SOURCE last closed <= `decision_at`, ATR14 por timeframe, multiplicador `BANK=0.50`, `MEDIUM=1.0`, `ATTACK=1.5–2.0`; **candidato económico**, nunca fuente de PnL histórico si se cambia stop.

## 3. Corregir significado del replay, sin destruir evidencia previa

El replay Native MAX antiguo del 9 oct 2026 dio `3357` señales sin solicitudes Risk (`1804 COGNITIVE_BLOCK + 1553 CAPITAL_BLOCK`) y `11` revisadas, `9` físicamente propuestas. **Es evidencia del diseño OLD SELECTOR, no tasa de calidad de señales ni política vigente de administración**. Mantener intactos esos artefactos y el censo causal pre-registrado como **auditoría de código legado**, pero no reutilizarlos como gate de admisión. Los módulos cognitivos siguen razonando sobre cómo administrar exposición, cómo salir y cuándo reducir capital, no sobre borrar la señal del Trader.

El objetivo bajo el paradigma nuevo es:
- `signals_received=3368`, `administration_receipts=3368` y razón para **cada** resultado, incluso no financiable.
- `qdle_evaluated + explicitly_invalid_research_input = 3368` si están disponibles las especificaciones; distinguir `funded_proposals`, `broker_confirmed_fills` y `actual_positions`.
- preservar riesgo `<= 5%` dinámico, mínimos/máximos de volumen, Bank/Cushion contables, costes de apertura/cierre y verificación del riesgo al stop.
- reconstruir resultados **secuencialmente**, con SL económico/TP/gestión intrabar, stops/gaps/spreads/comisiones y **no** reutilizar `structural R` del Trader al modificar el stop; `closed DD` no equivale a `MTM DD`.
- evaluar 6 instrumentos AUDJPY, EURUSD, GBPJPY, GBPUSD, NDX100 y XAUUSD con provider pricing/costs sólidos. Si faltan barras/ATR/ticks, `RESEARCH_DATA_MISSING`, no resultados inventados.

## 4. Orden P0 de integración

1. Crear frontera **recepción incondicional**: un expediente de administración por señal Trader válida, sin `COGNITIVE_BLOCK` como corte de flujo.
2. Dar a CIBO capacidad de proponer **SL económico** con riesgo comprobable y dejar SL estructural inmutable.
3. Integrar QDLE y sus cuatro motores con `0.05×QORE NAV` dinámico, mínimo broker estricto, margin/fee al entrar y al cerrar.
4. Integrar los recibos de gestión: parcial/trailing/BE/adversa y lifecycle de posiciones real o simulado con datos adecuados.
5. Trader Lab Fast: comparar OLD SELECTOR y **NEW MANAGER** en los mismos 3368 IDs. Reportar factibles vs no factibles, PnL/DD solo con replay causal verificable; no mezclar.
6. Mantener PR #745 DRAFT/NO LIVE y gates de riesgo intactos mientras falte broker evidence.

**Directiva de precedencia:** este documento reemplaza para el flujo operativo las recomendaciones de aflojar filtros, calibrar CF07 para autorizar más señales y el shadow de solo 200 bloqueadas sugeridos en `CIBO_P0_PRE_REGISTERED_BLOCK_TAXONOMY_AND_BLIND_COUNTERFACTUAL_2026-10-09.md`. Aquella investigación se conserva para explicar por qué el diseño legacy bloqueó 3357 señales, **no** como el plan para el nuevo paradigma. No se permite declarar completada la migración por publicar solo este documento.

## 5. Primer ensayo real de recepción de 3.368 señales: resultado verificable

[GitHub Actions #37888164184](https://github.com/mezas3238-hue/qore-core/actions/runs/37888164184): **SUCCESS**, 11 tests de recepción económica PASS, fuente `11451743578` hash validado; [artefacto con recibos señal por señal #11596279890](https://github.com/mezas3238-hue/qore-core/actions/runs/37888164184/artifacts/11596279890). Programa `scripts/cibo_p0_3368_manager_intake_sensitivity.py`; test `test_cibo_trader_signal_administration.py`.

- **3368/3368 señales originales** recibidas y con identidad única sin ejecutar el gate Native de admisión; ningún `COGNITIVE_BLOCK` desaparece de auditoría legacy, pero ya no elimina una señal de la ruta de gestión.
- Escenario **hipotético individual aislado** con NAV constante USD60, 5%=USD3, `min_lot=0.01` y coste proxy OPEN+CLOSE por instrumento: **3068 SL estructurales asequibles** al mínimo y **300 SL económicos propuestos** cuando el original excedía USD3.
- Conteos de propuestas económicas por instrumento: AUDJPY **24**, EURUSD **1**, GBPJPY **29**, GBPUSD **38**, NDX100 **30**, XAUUSD **178**; suma = **300**.
- **TODOS** esos resultados significan `RECEIVED_READY_FOR_QDLE` como **candidato geométrico**, **NO FINANCIABLES DEMOSTRADOS**: escenario optimista con distancia mínima provider=0 **desconocida**, buffer de gaps/slippage=0, sin margen, sin ATR causal, sin verificación de stop estructural alternativo, sin prueba de ejecución `order_check`, sin exposición simultánea ni Bank/Cushion real. No usar el conteo 3368 como `funded_proposals`.
- **0** lotes físicos QDLE confirmados aquí, **0** fill real MT5, **0** salidas CIBO reconstruidas, **PF/DD = NO MEDIDOS**. El único resultado comprobado es cobertura administrativa, no rentabilidad. La comparación histórica `11/3368` permanece control del selector obsoleto.
- **Siguiente bloqueo P0:** conectar este intake de 3368 al director A1, fuentes de los cuatro motores, QDLE y lifecycle, con broker min_stop/costs, ATR closed-bar, financiación por SL y NAV 5% **dinámico secuencial**, reconstrucción de stop hits y exits, sin confundir cotización con ejecución. Hasta entonces no desplegar.

