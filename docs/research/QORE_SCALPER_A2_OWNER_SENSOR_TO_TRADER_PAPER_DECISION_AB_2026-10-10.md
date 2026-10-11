# Trader Scalper — de sensores a decisiones de entrada y comparación PAPER PF/DD

**Owner**: «Lo que yo quiero es que los sensores trabajen para dar información al trader y así ejecutar su entrada y de acuerdo a eso ver si baja su Drawdown».

**Alcance:** GitHub exclusivamente, rama B `agent/scalper-architect-b-methodology-20261010`, PR #759. A cognitiva: rama `agent/scalper-architect-a-cognition-20261010`, PR #758, issue #756. En producción cero modificaciones. Investigación PAPER offline sin VPS/MT5/LIVE.

## Entregable operativo: cadena verificable completa

1. Cada vela M1 cerrada alimenta `observe_entry_timing_sensors`: 20+ sensores H1 dirección/frescura, protected M15 y stop, H1 rango parcial/posición, reloj y runway de sesión NY, M1 Sweep/opposing series/CISD, FVG/retrace/CISD, ruido/volatilidad, huecos de datos, H1 target room solo con timestamp testigo, broker bid/ask/comisión solo con evidencia física. Ningún outcome futuro en features.
2. **Cognitiva del Trader**, arquitecto A1: suministrar `scalper-a1-master-sensor-decision.jsonl` para **TODAS las 2876 oportunidades originales**, no solo las ganadoras, con `source_opportunity_id`, `symbol`, `observed_at` igual a fecha original decisión, `disposition=ACCEPT|WAIT|ABSTAIN`, `why`, `cognitive_engine_identity`, `master_frame_artifact_sha256`, `master_frame_evaluated=true`, `sensor_evidence_evaluated=true`, `outcome_visible=false`, `used_future_h1_expiry=false`, `authorization_is_live=false`. **No inventar el archivo** cuando aún no existe Master Frame real. `WAIT` o `ABSTAIN` NO se convierte en un fill en el futuro: la señal original concreta no se ejecuta. Si quiere retiming habrá que construir un motor real distinto usando candles futuras solo a medida que llegan.
3. **Motor PAPER de decisiones** `capitalizer_scalper_sensor_paper_decision_ab_v1.py` consume las entradas originales V49, 9 market books, los 2876 frames de sensores con join SHA-256 y *si existe* el log causal A1 con todos los IDs. El módulo rechaza una fecha no coincidente, sensor corrupto, cognición falsa declarada, futuro H1 expiry, outcomes, missing 9 market logs, y cualquier capacidad live. Las decisiones se hacen **antes** de consultar los resultados V49. Portfolio MAX3: tres primeras oportunidades admitidas por sesión y día según cronología, sin mirar R/winner futuro; si una se descarta se puede sustituir por otra oportunidad posterior con SL/TP originales; se informa explícitamente del reemplazo.
4. **A/B y drawdown** usando el mismo modelo económico V49 original sin falsos fills:
   - `FROZEN_V49_CONTROL`: todas las señales originales, MAX3, 2020 trades / 1167 ganadores, -233.269R.
   - `NOOP_SENSORS_OBSERVED`: sensores leídos pero sin influir en decisiones, debe reproducir bit a bit CONTROL y su PF/DD. Prueba de trazabilidad **obligatoria**.
   - `RESEARCH_SOURCE_SENSOR_CONSISTENCY_ONLY`: un primer caso diagnóstico en el que el trader PAPER sólo considera fuentes cuyo primer evento reconstruido por el sensor coincide exactamente con el V49. **Este NO es el cerebro del Trader**, es un experimento de integridad tecnológica, y su DD no debe presentarse como causalidad de la cognitiva. No promocionar el filtro a regla.
   - `A1_FULL_COGNITIVE_SENSORS_PAPER`: aparece **SOLO** después de que A1 entregue e integre evidencia de razonamiento Full Master Frame por oportunidad. Este es el test que responde al mandato Owner: fuentes→sensores→cognitiva real→PAPER entradas→PF/DD. En ausencia de ese archivo, el informe debe decir `a1_full_master_frame_attested=false` y NO inventar una simulación de cerebro.
5. Informes por rama: nº autorizaciones, nº ejecutadas, PF bruto, DD máximo por cierres y R total, ganadores del V49 preservados por ID exacto, R ganador preservado (934/415.75R exigidos), cuántos slots MAX3 se rellenaron y comparación vs V49. No hay inferencia de costes BID/ASK, slippage, comisión ni prop firm; se marca `broker_bid_ask_commission_slippage_simulated=false`. El DD es **retrospectivo sobre trades originales, filtrados**, no un replay de órdenes retemporizadas.

## Hallazgo P0: contrato de primer evento de sensores ≠ ledger V49

El primer censo `#38070589243` abortó **correctamente**: detectó que para algunas fuentes, el primer evento M1 seleccionado por el sensor as-of no coincidía con la ruta/hora archivada V49. Ejemplo observado AUDJPY: V49 FVG+CISD 2025-09-29 04:21 UTC vs primer Sweep+CISD sensor 04:16 UTC, misma fuente con M15 original 04:00. **NO asumir que una entrada distinta es mejor** ni añadir veto ciego. El nuevo censo preserva **todos los 2876 source IDs** y reporta `source_cisd_identical` y `source_cisd_mismatch` cada uno explícito, sin afirmar que todas las 2876 coinciden. La discrepancia debe resolverse en el generador/cadena del original, especialmente por ventanas M15 y preferencia de evento, antes de dar autoridad real. El PAPER de consistencia es un **stress científico** y no validación de un algoritmo predictivo.

## Gate de certificación

No certificar aunque el DD de un brazo de investigación mejore, si PF neto OOS, preservación 934/415.75R, número de operaciones útil, estrés multianual y costes físicos no cumplen simultáneamente. No evaluar gain de un cerebro simulado cuando `A1_FULL_COGNITIVE_SENSORS_PAPER` falta. No permitir `h1_state_until`, `exit_reason`, R, MFE/MAE, o retorno a +30 min en el modelo decisor.

**Ejecución automatizada del puente PAPER**: `.github/workflows/qore-scalper-a2-sensor-cognitive-paper-ab.yml`, fuente control [#38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695), sensores [#38071138991](https://github.com/mezas3238-hue/qore-core/actions/runs/38071138991), outputs inmutable SHA GH artifact por job.

**Estado del mandato:** código de integración PAPER B listo para validar; cognitiva A1 pendiente de aportar decisiones reales. Se prohíbe afirmar reducción del DD por cognitiva antes de la comparación completa.

## EVIDENCIA EMPÍRICA — PAPER A/B FINAL 9/9

GitHub [#38071484777](https://github.com/mezas3238-hue/qore-core/actions/runs/38071484777), GREEN, importó nueve source ledgers V49 originales, nueve libros economics y nueve ledgers del **censo causal 2876 sensores** [#38071138991](https://github.com/mezas3238-hue/qore-core/actions/runs/38071138991), 11/11 GREEN. El nulo sensor-only reproduce exactamente 2020 trades, 1167 winners, -233.269327R, PF 0.6644630742, DD 236.134284R. No se fabricaron ejecuciones ni retemporizaciones.

| Brazo PAPER | Trades | PF bruto | DD máximo R | R ganador original preservado | # winners originales preservados |
|---|---:|---:|---:|---:|---:|
| CONTROL V49, MAX3 | **2020** | **0.664463** | **236.134R** | 461.943R | 1167 |
| SENSORES SOLO INFORMATIVOS, NOOP | **2020** | **0.664463** | **236.134R** | 461.943R | 1167 |
| SOLO INVESTIGACIÓN: abstenerse si la primera señal reconstruida ≠ señal V49 | **1910** | **0.621312** | **252.103R** | **385.079R** | **1000** |

**CONFLICT con objetivo owner**, predefinido: la mera política de descartar entradas por diferencia técnica de ruta produce DD **+15.969R** (EMPEORA), PF **−0.04315**, deja de preservar 90% de R de las ganadoras originales: 385.079R es inferior al suelo obligatorio 415.75R. Aunque 1000 supervivientes superan el mínimo numérico 934, **no conserva masa R**. Por ello **RECHAZADO** como gate, no promocionar a trader. Se confirma la decisión de mantener sensores como *evidencia cognitiva* y no apilarlos como vetos automáticos.

**Contradicción de datos fuente 381/2876 (13.25%)**: 2495 coincidían exactamente; el primer detector CISD as-of eligió distinta ruta o timestamp en 381 que el ledger histórico V49. Es hallazgo P0 de contratos y causalidad de ventanas, NO un label de rendimiento de operación ni evidencia de una señal mejor. Resolver precedencia de rutas y fuente original con reproducción M1 en los ejemplos, antes de fiar una política al panel. No ocultar estas 381, ni contarlas todas como pérdidas, ni asumir que el nuevo sensor tiene razón.

**NO CONFUNDIR**: este resultado PAPER no utilizó aún **A1_FULL_COGNITIVE_SENSORS_PAPER**, ausente de la corrida: `a1_full_master_frame_attested=false`. **No se ha medido DD de la cognitiva real de Scalper administrando entradas**. La política experimental de integridad técnica no sustituye razonamiento del Master Frame. Costes físicos BID/ASK/comisión/slippage aún no simulados; los PF/DD son BRUTOS.

## Contrato real de sensorización hacia Master Cognitive Frame

Nuevo módulo `src/qore/infrastructure/trader_lab/capitalizer_scalper_sensor_master_frame_bridge_v1.py` utiliza **el tipo de producción existente** `CapitalizerCandidateCognitiveContext` de `capitalizer_master_cognitive_frame.py`, consumiendo cada `EntrySensorFrame` y emitiendo **tokens de los >20 sensores, todos status+provenance as-of**. Procesa evento CISD genuinamente nuevo (solo si timestamp CISD == cierre decisión), H1 edad, liquidez actual confirmada, protected swing M15 y datos no disponibles; construye huella determinista y **no afirma tener lleno el Master Frame** si no existen 9 percepciones/World/Portfolio/Regime. El contexto está listo para incorporarse mediante `build_master_cognitive_frame` de A1 con el snapshot real de nueve mercados y luego dictaminar `ACCEPT/WAIT/ABSTAIN`.

Pruebas unitarias verifican que context sea del **tipo concreto QORE de Master Frame**, que información no disponible no se convierta en confirmación y que ninguna lectura futura o repetida otorgue derecho de operación. A2 NO creará fingidamente la cognitiva completa. La implementación definitiva de A1 debe producir las 2876 decisiones como contratos de evidencia para habilitar la rama `A1_FULL_COGNITIVE_SENSORS_PAPER` y recién entonces medir PF, DD, frecuencia y winner retention antes de LIVE/MT5.

## Estado final

- **Hecho**: sensores H1/M15/M1 predecision, censo real 9 mercados, divergencias 381 cuantificadas, motor PAPER de decisiones A/B, DD/PF/retention reporte de baseline y estrés experimental, adaptador a Context real de Master Frame QORE.
- **Bloqueante**: A1 todavía **no** aportó los nueve Master Frames reales y 2876 decisiones de entradas en formato causal; además el método de extracción M15 y la procedencia de target/spread siguen sin atestar en el panel. El usuario no quiere solo log de sensores: exigir A1 Master Frame con datos completos, no simularlo.
- **Veredicto**: ensayo de sensor integrity rechazado, DD no disminuyó, **Scalper no certificado**, cero VPS/LIVE/merge.
