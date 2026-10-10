# QORE Scalper — Sensores de precisión temporal de entrada, integración sombra

**Fecha:** 2026-10-10. Arquitecto B metodología, [PR #759](https://github.com/mezas3238-hue/qore-core/pull/759); coordinación A1 cognitiva, [Issue #756](https://github.com/mezas3238-hue/qore-core/issues/756) / [PR #758](https://github.com/mezas3238-hue/qore-core/pull/758). **RESEARCH SHADOW ONLY. No VPS, LIVE, deploy, merge or trader certification.**

## Mandato y evidencia

Owner pide *todos los sensores posibles para saber cuándo Scalper debería entrar correctamente*.

La evidencia V49 **no permite presentar ningún momento como "correcto" a priori**. El nulo H1 direccional #38067672878 encontró -12.55 pp a +30m en entradas M1 originales frente a tiempos aleatorios dentro de la misma tesis. El stage forensic #38068938682 encontró una diferencia pareada de -12.56 pp (900 fuentes Sweep M1→CISD) y -2.83 pp (1023 fuentes FVG formado→CISD). **Son etiquetas de retrospectiva, no autorización de entrada antes de CISD ni prueba de rentabilidad de otro instante**. Cambiar stop/target o crear otro veto volvería a diezmar las 2876 fuentes V49. Por eso se necesita **observabilidad amplia y un panel causal**, no un invento de puntuación de acierto.

## Nuevo módulo implementado en GitHub

`src/qore/infrastructure/trader_lab/capitalizer_scalper_entry_timing_sensors_shadow_v1.py`

API: `observe_entry_timing_sensors(EntrySensorInput) -> EntrySensorFrame`. Se llama **en cada cierre real M1**. La entrada contiene únicamente M1 ya cerradas y datos H1/M15 que existían antes de la llamada. Si cualquier candle M1 cierra *después* del timestamp de decisión, si llega sin BID o sin ASK, o si H1/M15 se confirma después de la decisión: **falla cerrado**.

### Panel, todos los campos son datos/fuente con no-lookahead

| Familia | Sensores concretos | Alcance / advertencia |
|---|---|---|
| Contexto de fuente | `H1_BIAS_DECLARED`, `H1_THESIS_AGE_MINUTES` | Dirección y frescura H1 confirmadas upstream. **No** leer futuro `h1_state_until`. |
| Estructura M15 | `M15_PROTECTED_STOP_DECLARED`, `M15_TO_M1_ELAPSED_MINUTES`, `M15_ORIGINAL_RISK_PRICE_DISTANCE`, `ACTUAL_M15_STRUCTURE_REVALIDATION` | Stop orientado correctamente; la demostración independiente del protected swing M15 aún requiere velas nativas M15 y POI originales. |
| Calidad nativa M1 | `NATIVE_M1_GAP_COUNT`, `M1_LOCAL_MEDIAN_BAR_RANGE`, `M1_LAST_BODY_DIRECTIONAL` | Huecos declarados; nunca interpolar M1 ni usar spread sintético. Ningún ratio M1 noise se convierte automáticamente en veto. |
| H1 momento actual | `H1_CURRENT_CLOCK_FRACTION`, `H1_ASOF_PARTIAL_PRICE_RANK` | Reloj de la vela H1; precio situado en rango **PARCIAL** observado, jamás high/low de vela futura completa. |
| Sesión | `SESSION_REMAINING_MINUTES` | NY y DST conforme al horario original. No crear nuevo límite horario. |
| Barrido | `M1_SWEEP_OBSERVED`, `M1_OPPOSING_SERIES`, `M1_SWEEP_CISD_CLOSED` | Barrido local M1, serie de velas opuestas y cierre atravesando apertura de serie; fuente V49 preservada. |
| FVG | `M1_FVG_FORMED`, `M1_FVG_RETRACE`, `M1_FVG_CISD_CLOSED` | Tres velas, interacción de FVG y CISD estructural; el primer FVG detectado en un momento puede NO coincidir con el primero que acabará generando CISD válido. |
| Protected M1 | `M1_PROTECTED_SWING_ATTESTATION` | En Sweep no hay protected swing M1 independiente expuesto; en FVG el pivote solo se protege al confirmar CISD. **No inferir protección de un pivot aún no confirmado.** |
| Liquidez | `H1_TARGET_ROOM_R` | Solo si el target HTF tiene witness causal con fecha confirmada antes de decisión; el sensor no reconstruye automáticamente toda la jerarquía. |
| Costes físicos | `BROKER_BID_ASK_SPREAD`, `BROKER_COMMISSION_PER_LOT` | Si el broker no proporciona BID/ASK y comisión reales, el sensor queda NOT_AVAILABLE. Sin QDLE ni lotaje simulado. |
| Cognitiva integral | `FULL_COGNITIVE_MASTER_FRAME` | A1 aún tiene que conectar su Master Frame FULL y demostrar todo el razonamiento real en el replay. No declarar integrado por tener solo sensores de metodología. |
| Primera ruta de entrada original | `SOURCE_SIGNAL_OBSERVED` | Observa la primera CISD fuente legal entre Sweep/CISD y FVG/CISD; **no** autoriza una operación. |

Cada `SensorEvidence` publica `sensor`, `status`, `observed_at`, `value`, `explanation` y `provenance`. Estados: `OBSERVED`, `DEVELOPING`, `NOT_OBSERVED`, `NOT_AVAILABLE`, `CONTRADICTORY`. Un sensor `NOT_AVAILABLE` no se convierte en "señal negativa" ni en veto. El panel **no aprende** un umbral de acierto utilizando ganadoras V49 posteriores, no tiene `win_probability`, y no otorga `execution_authorized`, `trade_size_authorized`, `cognitive_master_frame_attested`, `trader_certified` ni `live_authorized` (todos falsos por construcción).

### Qué significa *momento correcto* y qué falta

Son tres niveles separados:
1. `EVENT_OBSERVED`: el detector fuente confirma al cierre M1 Sweep+CISD o FVG+CISD, o está desarrollándose. **Verificable ya** de forma causal y en tiempo de mercado.
2. `COGNITIVE_DECISION`: cognitiva A1 pondera narrativa H1, protected M15, liquidez, régimen, tiempo restante y condiciones microestructura **as-of**, dejando razonamiento explicable de POR QUÉ aceptar, esperar o abstenerse. **No implementado por este módulo**; se coordina en GitHub con A1. No extrapolar PF/etiquetas +30m ex-post hacia la decisión.
3. `EXECUTION_AUTHORITATIVE`: futura coordinación con CIBO/QDLE y condiciones físicas reales del broker (spread, comisión, slippage, lotaje, solvencia). **Prohibido activarlo** antes de pruebas unitarias/integración y certificación científica.

## Plan de prueba y barreras

- Contrato de tipos y causalidad en `tests/infrastructure/trader_lab/test_capitalizer_scalper_entry_timing_sensors_shadow_v1.py`: avance antes/después de CISD, dos rutas, exposición de datos no disponibles, lookahead futuro explícitamente rechazado, stop contradictorio rechazado, M15 después de cierre rechazado, sin `h1_state_until` ni MFE/future labels como input.
- CI: `.github/workflows/qore-scalper-a2-entry-timing-sensors-shadow.yml`, Ruff, mypy y pytest más aserción de autoridad cero.
- **Fase posterior**: instrumentar en la replay matriz 2876 oportunidades V49 exactamente, logueando cada snapshot M1 anterior al evento CISD sin filtrar poblaciones; evaluar si la progresión de sensores anticipa razonablemente eventos (calibración walkforward/OOS independiente por episodio H1, mercado/sesión) y comparar *instrumentación SHADOW* versus *control exacto* sin alterar una sola trade. Los efectos observados de sensores no son tradables por sí solos. Analizar edad H1/regímenes sin confundir etiquetas futuras con features.
- Fase posterior A1: adaptar el cuadro de sensores al Master Frame as-of; revisar contratos, independencia, prioridad fuente y convergencia con metodologías originales; evitar que la cognitiva aprenda de HOLDOUT ex-post.
- No crear un «sensor de éxito» basado en saber que el precio subirá 30m tras la CISD; eso sería lookahead. No imponer unanimidad de 20 sensores: destruiría frecuencia y ganadoras por conveniencia de ingeniería, reproduciendo V50-G.
- Seguir manteniendo controles de certificación Owner, incluida preservación por identidad de ganadoras originales (934/415.75R), PF **neto** OOS, drawdown muy bajo, robustez multianual y costes MT5 físicos; aún no están superados.

**Estado:** Sensores disponibles para investigación y pruebas causales GitHub; **no conectados a autorización real del Trader**, cero promesas de tasa de acierto, trader sigue NO CERTIFICADO.
