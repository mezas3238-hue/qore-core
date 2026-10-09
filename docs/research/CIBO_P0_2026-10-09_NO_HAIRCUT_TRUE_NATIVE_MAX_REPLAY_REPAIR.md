# QORE — P0/CIBO — Eliminación definitiva del haircut + Native MAX genuino en replay

**Fecha:** 2026-10-09
**Branch:** `agent/cibo-p0-replay-qdle-persistence-20261009`
**PR:** [#747](https://github.com/mezas3238-hue/qore-core/pull/747) DRAFT / NO LIVE
**Rama integradora destino:** `agent/cibo-sovereign-integration-p0-20261008`.
**Handoff de origen:** `CIBO_MASTER_P0_HANDOFF_2026-10-09_TRADER_LAB_3368_FULL_COGNITION_QDLE_REPAIR.md`.

## Decisión del propietario — trabajo antiguo no sanciona operaciones nuevas

`THREE_SETTLED_LOSSES_HAIR_CUT` eliminado **del algoritmo canónico**
`src/qore/infrastructure/cibo_compound_capital.py::propose_p0_compound_vote`.
No hay bandera on/off, ni reducción retrospectiva al 50%. CIBO COMPUESTO
ahora limita su propuesta al presupuesto de la cuenta realmente libre y el
5% dinámico del NAV en el evento actual, descontando solo obligaciones y
reservas auténticas. Pérdidas realmente liquidadas afectan aritméticamente al
NAV actual; rachas antiguas y resultados Trader CONTROL no forman una política
de entrada. Tests y ablation actualizados para no esperar contribución
ficticia de un haircut retirado.

No se eliminan los límites físicos del broker, la malla 0.01 de lotes,
comisiones all-in verificables ni el máximo soberano de riesgo 5%.

## Causa real de la cognitiva ausente y la nueva integración

El runner anterior consumía:
- `d["cibo_max_native_management_mode"]`
- `d["cibo_max_native_requested_risk_fraction_of_nav"]`
- `d["cibo_manager_stop_proposed"]`
- `d["cibo_max_native_proposed_exit_management"]`

Todos se habían generado en una ejecución anterior y **no** demostraban
razonamiento individual con capital, reservas y posiciones cambiantes.

Nuevo `scripts/cibo_p0_native_replay_runtime.py`:
1. Reconstruye el `TraderOpportunityEnvelope` original del manifiesto sellado,
   respetando la percepción de mercado predecisión.
2. Recalcula `CiboCapitalRegimeState` con caja QORE causal, exposición
   pendiente, margen retenido, DD sobre caja y conteo de posiciones abiertas.
3. Ejecuta `consult_cibo_economic_faculties` real de CF01–CF19 y
   `run_native_maximum_intelligence`, produciendo un
   `CiboNativeMaxCognitiveEpisode` nuevo en el timestamp causal.
4. Emite `issue_native_sovereign_mode_instruction` desde ese episodio
   tipado, con digest de consulta, semántica, instrucción y estado.
5. El runner utiliza SOLO la instrucción recién emitida para el riesgo y
   protocolo de salida; usa el SL de protección original del Trader en vez
   del `cibo_manager_stop_proposed` histórico.
6. Cuando la percepción causal falta o el episodio no puede reconstituirse,
   emite `NATIVE_COGNITION_UNAVAILABLE` explícito y QDLE lo recibe con
   lotaje cero. **Nunca reusa la etiqueta de una operación anterior.**

Limitación importante: la clase
`NativeSovereignModeInstruction` sigue emitiendo fracciones fijas por
BANK/MEDIUM/ATTACK y `CiboExitPolicy` todavía es un conjunto de
plantillas. Haber ejecutado el cerebro **no** demuestra que CIBO gestione
cognitivamente cada vela intratrade; AC06/AC07 continúan ABIERTOS. Se
requiere contrato Native MAX por evento de posición, sin mirar velas futuras,
que produzca acción HOLD/MODIFY_STOP/PARTIAL/EXIT para cada decisión y
conectarlo al motor PAPER de ejecución, riesgo y fee de QDLE.

## Eliminación adicional de dependencia heredada del corpus QDLE

La revisión siguiente elimina por completo `stellar-instant-3368.json`
de la CLI de replay y del workflow. Ya no puede decidir orden temporal,
Trader, símbolo, clase de modo, stop ni salida. El único calendario de
oportunidades viene de `walk-forward-manifest.json` con `manifest_sha256`
validado, 3368 fingerprints únicos y timestamps UTC conscientes.
`scripts/cibo_p0_replay_manifest_source.py` preserva todos los IDs
originales y realiza el orden temporal causal. Las seis particiones Atlas M5,
tarifas research y QDLE actual siguen siendo los insumos económicos/mercado.
La fuente anterior permanece exclusivamente como comparación en el handoff;
**no participa en el nuevo replay**.

Nuevo run del contrato sin datos antiguos:
https://github.com/mezas3238-hue/qore-core/actions/runs/37957305555.
No afirmar resultado antes de SUCCESS + artifact.

## Evidencia reproducible

- [Unit tests actualizados](https://github.com/mezas3238-hue/qore-core/actions/runs/37956391200) — SUCCESS, SHA `9ab5f19f6a730aa83cafa18a520acc9f7f85aac2`.
- [Native MAX sobre manifiesto SELLADO](https://github.com/mezas3238-hue/qore-core/actions/runs/37956499075) — SUCCESS, SHA `84444533ca8b292c09fc02049bcf9425bcf453c4`.
  Prueba un caso original por cada Trader: **7/7 episodios** correctos,
  16 facultades aplicables + tres justificadamente no aplicables,
  0 bloqueos, con emisores y digests reales.
- [Full PAPER 3368 con Native MAX en el loop](https://github.com/mezas3238-hue/qore-core/actions/runs/37956606145) — proceso de aceptación.
  **No afirmar 3368/3368 cognitivas hasta verificar audit y artifact.**

## Gates

- **ELIMINACIÓN DE HAIRCUT:** implementada en rama y tests unitarios PASS.
- **CIBO nuevo por señal:** invocación genuina implementada, 7/7 muestra
  nativa validada; cobertura 3368 y efecto financiero pendientes de workflow.
- **QDLE 3368 receipts:** anteriormente verificado, nuevo replay por validar.
- **Gestion intratrade autónoma:** NO CERTIFICADA, clase EXIT_POLICIES estática.
- **Broker real, bid/ask histórico y MTM NAV:** NO CERTIFICADOS.
- **VPS / order_send:** NO TOCAR. Todo research.

Informe anterior `docs/research/CIBO_P0_2026-10-09_PHASE1_QDLE_PERSISTENT_ECONOMIC_VOTES_PROGRESS.md`
describe la fase anterior y NO debe usarse como si ya midiera esta nueva
reparación cognitiva. No mezclar curvas de la versión anterior con esta.
