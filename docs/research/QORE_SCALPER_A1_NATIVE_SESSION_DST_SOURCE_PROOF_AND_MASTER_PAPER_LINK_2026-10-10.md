# QORE Scalper A1 — Session-clock causal real del V49, DST y enlace a Master Frame PAPER

**Fecha:** 2026-10-10. **Responsabilidad:** A1 cognitiva, no A2 metodología. **Rama:** `agent/scalper-architect-a-cognition-20261010`, PR #758 DRAFT. Sin merge, VPS, live, riesgo ni permiso de trading.

## Validación de 2.876 oportunidades originales sobre reloj NY

[A1 Session Clock/DST GitHub Action **#38091938032 — SUCCESS**](https://github.com/mezas3238-hue/qore-core/actions/runs/38091938032) consume **nueve libros originales V49 inmutables** [#38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695), no un fixture o trades seleccionados. El módulo `capitalizer_a1_native_source_session_clock_attestation_v1.py` compara cada `source_opportunity_id`, `symbol`, `session`, `operating_date` y cierre M1 contra el verdadero `capitalizer_session_at`, `_operating_date` y `session_end_at`. Conversión **Europe/??? NO**: usa `ZoneInfo("America/New_York")` en instante UTC histórico para respetar cambios DST. Pruebas adversariales verifican invierno y verano, sesión nocturna asiática que cruza medianoche NY, fuente falsa, falta de tzinfo, y **diferencia entre bucket QORE y otra ventana**.

| Comprobación real sobre V49 | Conteo |
|---|---:|
| Fuente conserva ID original y bucket QORE revalidado | **2.876 / 2.876** |
| Fecha operativa por zona NY revalidada | **2.876 / 2.876** |
| NY EDT (UTC−4) | **1.913** |
| NY EST (UTC−5) | **963** |
| Asian broad QORE: apertura autor ICT no disponible (no inferida) | **1.154** |
| London: dentro ventana ICT registrada [02:00,05:00) NY | **253** |
| London: fuera de ventana ICT, dentro bucket amplio QORE | **408** |
| New York: fuera ventana ICT [07:00,09:00) NY pero dentro bucket QORE | **1.061** |
| IDs descartados por discrepancia horaria o ICT | **0** |

**Interpretación crítica:** El **bucket operativo original V49/QORE no es la killzone ICT**. El segundo contraste emplea un módulo ICT de otro programa en QORE, *no* una regla de origen TTrades validada por A2. Es un atlas **diagnóstico** para evitar conflaciones, **NO razón para rechazar 408 London, 1.061 NY o 1.154 Asia**. El Atlas original QORE usa ASIA 20:00–02:00, London 02:00–08:30 y New York 08:30–16:00 hora de NY, con sus asignaciones de nueve activos por sesión. La validación original de bucket y fechas **sí prueba la procedencia del calendario operativo histórico V49**, no evidencia independiente de efectividad de la metodología del autor. Reloj válido no aporta por sí solo fresh quotes BID/ASK, microestructura completa, régimen, relaciones dirigidas, mundo nueve mercados ni libro de cartera.

### Conexión implementada a verdadero Master Frame/Trader PAPER, con control de autoridad

`run_sensorized_master_frame_paper(..., source_clock_witnesses: Mapping[str, A1V49SourceClockEvidence] | None)` en `capitalizer_a1_sensorized_paper_runtime_v1.py`. Entrada **opt-in**, exige cada ID del censo y concilia símbolo, sesión, operating date, timestamp exacto de cierre y apertura de la vela M1 frente a su `A1PaperSource`. Solo añade tokens probados `SCALPER_A1_QORE_OPERATIONAL_BUCKET`, `SCALPER_A1_SOURCE_CLOCK_NY_UTC_OFFSET_MINUTES`, `SCALPER_A1_SOURCE_METHOD_WINDOW`, y `NOT_TTRADE_AUTHOR_GATE=YES` a `A1MultiHypothesisBarrier.alternatives[].context.observation_tokens` antes del Full Master Frame. Devuelve contadores `independently_attested_source_clocks` y `source_methodology_windows_unresolved`. No modifica `A1SourceHypothesisAlternative` autor-fiel, spread, posición, trade selection, payout ni política de veto.

Tests `test_capitalizer_a1_sensorized_paper_runtime_v1.py`: un escenario de **tres fuentes con mundo cognitivo de fixture**, demuestra `Master Frame→Trader PAPER` invocado con el nuevo witness de reloj y las tres fuentes elegidas, con Asia ICT desconocida; ledger incompleto e identidad falsa disparan excepción y no se registran como pérdidas. Esta prueba demuestra **conexión real del código**, no histórico full-brain de nueve mercados con percepción GOOD.

### Límites científicos y continuación prioritaria

- El nuevo reloj responde **«¿coincide el calendario operativo V49 y su fecha con el NY DST correcto?»**: sí para las 2.876 fuentes. A2 es responsable de determinar **qué ventanas temporales verdaderamente exige TTrades**, si exige alguna ventana diferente. No copiar inadvertidamente ventanas ICT en scalper.
- **A1 percepción:** `capitalizer_a1_native_nine_market_epistemic_inputs_v1.py` ya construye 25.398 snapshots tipados desde 2.822 instantes de nueve M1 provider-native; previamente todas eran BAD por falta de pruebas de `session_clock_valid`, `quote_fresh`, `microstructure_complete`. El nuevo test de reloj acredita sesiones de FUENTES originales, pero no permite declarar `quote_fresh` ni `GOOD` en percepción nine-market sólo por OHLC. La promoción de reloj debe ser **por source-ID** y con justificación, nunca cambiar toda la matriz sólo por timestamp aware.
- **A1 World Model real:** faltan Market Brains con snapshots as-of, actividad H1/M15, régimen obtenido de series sin lookahead, relaciones causales dirigidas realmente evidenciadas, cross-factor, ledger de ejecuciones por sesión y posiciones elegidas/settled. Hasta entonces `FULL_COGNITIVE_MASTER_FRAME` histórico permanece NO ejecutado, sin PF/DD cognitivo real, sin certificación.
- **A2 faltantes:** protected pivot M1 501/2876 con ventana previa no validada contra autor, 12 M15 +124 H1 sin witness y 381 discrepancias CISD que no deben convertirse en filtro (anterior abstención empeoró DD).
- **Económico:** las 2.876 son **oportunidades originales**, no 2.876 trades de P&L. El control V49 seleccionaba 2.020 trades, PF~0,664 y DD~236,13R. El nuevo reloj NO modifica esas cifras. El próximo ensayo completo debe registrar PF/DD/retención real de full nine-market Brain con broker costes probados, sin tomar ausencia de datos como 0 trades certificados.

**Prueba clock** #38091938032 GREEN; ejecución de enlace Master Frame en versión A1 bajo [CI quality](https://github.com/mezas3238-hue/qore-core/actions/runs/38092111744), verificar resultado final antes de declararlo GREEN. Código y artefactos escritos exclusivamente en GitHub; no VPS.
