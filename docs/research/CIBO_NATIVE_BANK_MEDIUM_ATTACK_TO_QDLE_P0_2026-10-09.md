# CIBO Native MAX BANK / MEDIUM / ATTACK → QDLE — P0 2026-10-09

## Autoridad correcta

**Cada señal del Trader** se administra cognitivamente en CIBO Soberano Native MAX. CIBO elige el **modo económico** (BANK/MEDIUM/ATTACK) y su presupuesto máximo relativo al NAV de QORE, con decisión tipada y registro causal de los sensores. Sizing, CIBO Compound, Adaptive Leverage y Portfolio Compound emiten límites económicos independientes. **Solo QDLE** convierte la petición en `lots` físicamente financiables, descontando la pérdida al SL, ambas patas de comisión, margen, grid del bróker y límites de riesgo.

**El modo NO es volumen y no salta QDLE.** Si QDLE devuelve 0.00, CIBO ha administrado y registrado la señal como `UNFUNDABLE`, no como trade silenciosamente filtrado; no existe derecho a fabricar un lote inferior al grid MT5 ni a aplicar un riesgo superior al 5% del NAV.

```text
3368 sealed Trader opportunities, indexed by signal_fingerprint
 → CIBO Sovereign Native MAX actual reasoning / executive synthesis / 4 scenarios
 → CIBO Native MAX typed, sealed, per-signal mode instruction
    BANK  → at most 0.0125 * current QORE NAV (research policy)
    MEDIUM→ at most 0.0250 * current QORE NAV
    ATTACK→ at most 0.0500 * current QORE NAV
 → four independent economic motor votes / explicit source/funds
 → QDLE.reserve_for_trader [SOLO calculador físico del lotaje]
 → CIBO lifecycle acknowledgement: LOT QUOTE or UNFUNDABLE
 → management/SL/partials/trailing/defensive events require market paths
 ```

Las fracciones anteriores son el esquema experimental vigente sujeto a optimización cognitiva posterior; **nunca pueden fabricar lotes físicos ni exceder los límites de QDLE o las reglas del bróker**.

## Reparación de arquitectura efectuada

1. `src/qore/infrastructure/cibo_native_mode_authority.py`: nueva instrucción tipada `NativeSovereignModeInstruction`, sellada por identidad, fecha, semántica, modo, calibración, escenarios y política SHADOW de gestión. `issue_native_sovereign_mode_instruction` solo acepta episodio Native MAX tipado. Sus campos explícitos son `qdle_lot_authority_only=True`, `broker_execution_authorized=False`.
2. `src/qore/infrastructure/cibo_native_sovereign_capital_runtime.py`: `CiboNativeSovereignCapitalDecision.native_qdle_mode_instruction`, derivada directamente del episodio Native MAX en vez de fabricarse a posteriori a partir de un reporte. Señal explícita para épocas con oportunidades simultáneas.
3. `src/qore/infrastructure/cibo_single_account_sovereign_ceiling_run.py`: incorpora `native_mode_instruction` al recibo cronológico real y valida su identidad, semántica y tiempo.
4. `src/qore/infrastructure/cibo_p0_native_cognitive_management.py`: consume esa instrucción nativa antes de conectar con QDLE, cotejándola con seis sensores cognitivos; no permite falsificar un modo ATTACK por editar un label o `capital_disposition`. Si falta el nuevo campo en datos antiguos, conserva el viejo mapeador marcado como investigación para compatibilidad, **pero el replay FRESH actualizado lo prohíbe**.
5. `scripts/cibo_p0_native_max_manager_advisory_3368.py`: serializa fuente/digest de la instrucción soberana y contabiliza `native_cibo_bank_medium_attack_instructions_issued`.
6. `src/qore/infrastructure/cibo_native_sovereign_qdle.py`: acepta la nueva procedencia Native MAX (y el camino antiguo test/research) y aplica el máximo de presupuesto sobre el QDLEIntent calculado junto a los cuatro motores.
7. `scripts/qdle_3368_dual_ledger_replay.py`: para origen **FRESH Native** exige instrucción nativa válida en cada señal antes de llamar a QDLE y contabiliza, desglosado por BANK/MEDIUM/ATTACK, todos los retornos de QDLE (quote físico positivo o grid/riesgo NO financiable).
8. `.github/workflows/cibo-p0-native-max-manager-qdle-3368.yml`: se cierra en rojo si las 3.368 no tienen instrucciones nativas, si no atraviesan QDLE, si algún modo queda sin contabilizar o si se inventan fills/DD/PF.
9. `tests/infrastructure/test_cibo_native_sovereign_qdle_p0.py`: prueba los tres modos con broker sintético (NAV QORE $60, comisión $14/lot ida y vuelta, grid 0.01); confirma lotes calculados por el QDLE real 0.00/0.01/0.02, identidad y 0 órdenes LIVE.
10. `tests/infrastructure/test_cibo_native_mode_authority_real_runtime.py`: invoca **cognitiva Native MAX auténtica** antes de generar instrucción soberana, hace round-trip de documento causal y rechaza ataques de escalado/autoridad LIVE con digest incorrecto.

## Evidencia verificada

- [Fast CI #37937998624](https://github.com/mezas3238-hue/qore-core/actions/runs/37937998624) **SUCCESS**: pruebas de generación por Native MAX real, QDLE físico, control de cashflows, rutas de salida/bid-ask y seguridad.
- [Full FRESH #37937821428](https://github.com/mezas3238-hue/qore-core/actions/runs/37937821428): lanzamiento automático originado por modificación del contrato/workflow; estaba **EN CURSO** al publicar el presente checkpoint. No afirmar 3.368/3.368 instrucciones pasadas hasta ver su **PASS y el artefacto**. Su último resultado comparable anterior [#37932270093](https://github.com/mezas3238-hue/qore-core/actions/runs/37932270093) SUCCESS devolvió 3.368 Native sensor-management requests, 1.961 lot quotes SHADOW, 1.407 unfundable, 0 fills; los nuevos contadores de autenticidad del origen no existían todavía.
- El código **NO** transmite órdenes MT5, no genera deals ni liquida posiciones ni computa rendimiento auténtico. Broker/live ≠ research. El último replay es SHADOW y **CIBO aun no está certificado**.

## P0 aún abierto para certificación y NAV genuino

**Falta** conectar `CiboEconomicInstruction` con origen de fondos y gobernanza autónoma de CIBO, broker FundedNext/MT5 de solo lectura para precios/ticks/comisiones/márgenes verificables, trayectorias bid/ask para replay manejado de SL+parciales+BE+trailing+defensa, contabilización de comisiones en apertura/cierre según fills, settlement global único, NAV compuesto dinámico por resultados SOLO gestionados por CIBO y drawdown MTM. No contaminar el Manager con `TRADER_CONTROL` ni retirar las restricciones físicas de seguridad. PR #745 sigue DRAFT y nunca pasar a LIVE sin consentimiento y certificación independiente.
