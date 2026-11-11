# R4-A — Corrección de 6 ventanas H4 y prueba causal de pivotes con USDCHF real

**Corte: 2026-11-11 · Investigación QA · NO LIVE · NO VPS · NO MERGE**

## Hallazgo científico bloqueante

La fuente Pine R4-A original Git blob `693e3f49719e86e2ea0702f7b355af33bd0c4c7c` tiene en `f_allowed` (aprox. líneas 149–155) **seis** C1 H4 diarias:

- Forex/metales/BTC: **01, 05, 09, 13, 17, 21** NY.
- Índices: **02, 06, 10, 14, 18, 22** NY.

El decodificador histórico heredado de QORE CRT PR #1004 fija `C1_HOURS` únicamente en `(1,5,21)` / `(2,6,22)`. El proxy histórico [run #43094233453](https://github.com/mezas3238-hue/qore-core/actions/runs/43094233453) consumía el campo `H4.c1_allowed` de esa fuente **con mitad de ventanas no habilitadas**. Por ello **su rentabilidad 2024–2025 no equivale a probar el universo completo de R4-A**. No invalidar los datos subyacentes ni modificar retroactivamente sus resultados; reportar como V1 parcial / BURNED.

## Corrección implementada en PR #1007

- `pine_h4_geometry.py`: 6/6 relojes NY exactos, reglas estrictas de C2 retorno y TRUE 3C tras H4 completas, y rechazo de doble barrida/continuidad defectuosa (L1348–1359, 1550–1594).
- `pine_swing_primitives.py`: pivote M5 confirmado L2/R2 tras barra cerrada, congelación **anterior** al sweep, acumulador M15 nativo 3×M5 con continuidad y MSS mediante cruce de cierres; semántica de empates M5 pendiente de contrastar con `ta.pivothigh` real.
- `tests/test_pine_h4_geometry.py`: 22 controles sintéticos de seis horas, geometría, DST y rechazo doble sweep.
- `tests/test_pine_swing_primitives.py`: 25 controles sintéticos de causalidad, gaps, pivotes y MSS.
- `archived_h4_clock_probe.py` y `archived_pivot_audit.py`: instrumentos de medición sin PnL sobre el histórico original verificado SHA.

### Resultado REAL USDCHF de 2024 y 2025

Evidencia: [Actions #43106243811](https://github.com/mezas3238-hue/qore-core/actions/runs/43106243811), **SUCCESS**.

| Métrica | Valor |
|---|---:|
| M5 originales USDCHF (sha256 2024/2025 verificados) | **149.342** |
| H4 completas reconstruidas | **3.041** |
| H4 incompletas | 73 |
| Tramos discontinuos M5 observados | 174 |
| M15 completas de 3 M5 | **49.606** |
| Pivotes M5 altos / bajos (QA) | 17.958 / 18.202 |
| Pivotes M15 altos / bajos (QA) | 6.146 / 6.237 |

**Comparación de cobertura H4 sobre el mismo USDCHF y la misma fuente**, solo geometría, sin MSS:

| Detección | Tres relojes del proxy heredado | Seis relojes de R4-A |
|---|---:|---:|
| H4 elegibles como C1 | 1.554 | 3.041 |
| Geometría C2 RETURN de un único sweep | 436 | 893 |
| Geometría TRUE 3C de un único sweep | 16 | 108 |

Estas cifras **no son operaciones**, no tienen entrada/SL/TP ni costos y no corresponden a paridad global del motor Pine. La diferencia de 16→108 en TRUE 3C se debe a los horarios adicionales y cómo se distribuyen los patrones por bloque; no extrapolar a todo el universo o futuros.

## Estado de certificación

| Puerta | Estado |
|---|---|
| Pine R4-A SHA exacto inmutable | PASS fuente |
| Geometría 6/6 H4 y pivotes causales aislados (tests + USDCHF original) | QA PASS |
| Paridad evento por evento con TradingView Pine `f_engine()` | **NO CERTIFICADA** |
| Comportamiento de empates `ta.pivot*`, fases M5, C1 completa por instrumento | REVISIÓN PENDIENTE |
| Señales MSS exactas de TRUE3C y 2C contra Pine con mismos timestamps | **NO CERTIFICADO** |
| 34.º BTCUSD con feed IC equivalente | **FALTANTE** |
| Costos históricos bid/ask y cartera | **FALTANTES** |
| Holdout nuevo 24 meses intactos | **NO APERTURADO**; 2024–2025 BURNED |

## Siguiente etapa

Integrar **las seis ventanas H4 y los pivotes congelados causales en una sola máquina de estados M5→H4** de investigación. Reproducir exactamente 2C RETURN+MSS15 y TRUE3C+MSS5, instrumentar eventos completos `event_id/timestamps/pivote` en la misma feed y pasar `parity_gate.py` frente a evidencia Pine real; NO retocar TP buscando ganar en los dos años ya examinados.

**Conclusión:** los resultados anteriores de 33 mercados no deben llamarse evaluación completa del R4-A; se conserva investigación retrospectiva, no HOLDOUT ni rentabilidad neta.
