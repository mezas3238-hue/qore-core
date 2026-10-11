# QORE NATIVE — G0 EJECUTADO: auditoría M1 nativa de nueve mercados

**Fecha:** 2026-10-11. **Estado:** G0_SOURCE_INTEGRITY_PASS; COVERAGE_PARTIAL; G1_PENDING_CALENDAR_AND_PREREG. **No edge, operaciones, PF, Sharpe ni certificación.**

**Evidencias:** [GitHub Actions #38166675573, todos los trabajos SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38166675573), [artefacto agregado #11712187623](https://github.com/mezas3238-hue/qore-core/actions/runs/38166675573/artifacts/11712187623), [PR #791](https://github.com/mezas3238-hue/qore-core/pull/791). Commit analítico verificado fb22970798a2bd93f097f1327ce9c864eec0bb9c. [Prerregistro previo](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-g0-native-m1-coverage-20261011/docs/research/QORE_NATIVE_G0_M1_SOURCE_INTEGRITY_PREREG_2026-10-11.md), commit 1e14b4480c6f9f0e83563604282864004377300f.

**Fuente única:** 9 archivos provider-native M1 read-only no interpolados de [run #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), SHA fuente 18c338aedd5013ce65a6cb6408ffbc2e904a6217. Ventana UTC 2025-09-17 a 2026-09-17 (final exclusivo), YA EXAMINADA por otros estudios; nunca considerarla OOS virgen. Para cada activo hubo verificación de manifiesto, símbolo exacto, OHLC positivo y consistente, timestamp UTC, M1 60 segundos, orden y duplicados, hashes SHA256 del manifest y de particiones RAW_M1_LEDGER. El código no importa detectores V49, TTrades ni lee retornos futuros.

## 1. Censo M1 verificado por mercado

| Mercado | M1 observadas | Días laborables UTC activos | M15 completas 15/15 | M15 incompletas 1-14 | Porcentaje completas entre M15 activas | H1 completas / H1 activas |
|---|---:|---:|---:|---:|---:|---:|
| EURUSD | 369.903 | 260 | 23.717 | 1131 | 95.45% | 5524 / 6213 |
| GBPUSD | 369.833 | 260 | 23.906 | 942 | 96.21% | 5572 / 6213 |
| USDJPY | 369.672 | 260 | 23.856 | 991 | 96.01% | 5624 / 6213 |
| AUDUSD | 369.269 | 260 | 23.642 | 1205 | 95.15% | 5576 / 6213 |
| AUDJPY | 371.156 | 260 | 24.168 | 677 | 97.28% | 5673 / 6213 |
| GBPJPY | 371.465 | 260 | 24.244 | 604 | 97.57% | 5681 / 6213 |
| XAUUSD | 353.355 | 259 | 23.086 | 534 | 97.74% | 5381 / 5909 |
| USDCAD | 368.740 | 260 | 23.599 | 1248 | 94.98% | 5461 / 6213 |
| NAS100 | 353.761 | 260 | 23.384 | 221 | 99.06% | 5689 / 5907 |
| **TOTAL** | **3.297.154** | — | — | — | — | — |

**Precisión crítica:** los bloques M15/H1 se etiquetan activos si tienen AL MENOS 1 M1. Que estén incompletos no demuestra error: pueden coincidir con cortes de mercado, rollover, domingos, feriados o ausencia legítima de cotización. La tasa de M15 completa es condicionada a bloque activo, NO cobertura total de horas de negociación del broker. No se infieren marcos H4 completos, fills, bid/ask reales ni costes del histórico.

## 2. Sincronización estricta de minutos entre activos (RELATIVE)

| Activos emparejados | Minutos UTC exactos compartidos | Solo A | Solo B | Intersección/Unión de minutos activos |
|---|---:|---:|---:|---:|
| EURUSD / GBPUSD | 368.289 | 1614 | 1544 | 99.150% |
| AUDUSD / GBPUSD | 367.835 | 1434 | 1998 | 99.076% |
| AUDJPY / GBPJPY | 370.858 | 298 | 607 | 99.757% |

En los tres pares, hay por lo menos un minuto sincronizado en 312 fechas UTC. La medición emplea la intersección de bitmaps de 1.440 bits por fecha de ambos símbolos, sin interpolar una cotización faltante y sin usar precios futuros.

**El porcentaje >99% acredita material para estudiar el factor relativo, NO cointegración, beta estable, reversión futura, spreads bajos ni posibilidad de monetizar dos piernas.** Los artefactos individuales publicados junto al agregado incluyen bitmap, manifest y hashes por fuente y censos de calidad.

## 3. Decisiones para los tres traders nativos

**QORE DRIVE — [Issue #792](https://github.com/mezas3238-hue/qore-core/issues/792):** NAS100, XAUUSD, EURUSD y GBPUSD tienen barras M1 nativas y bloques de M15/H1 observables, no siempre completos. Puede avanzarse a un diseño G1 DESPUÉS de auditar sesión oficial/venue y congelar feature, horizonte y baseline; **no se ha medido edge direccional**.

**QORE RESET — [Issue #793](https://github.com/mezas3238-hue/qore-core/issues/793):** EURUSD, GBPUSD y USDJPY con M1 observadas. Antes de cuantificar reversión, acreditar el calendario de fixing o evento horario, días con datos verificables, DST, controles placebo, costes por franja y conocimiento as-of; **no se ha medido edge de reversión**.

**QORE RELATIVE — [Issue #794](https://github.com/mezas3238-hue/qore-core/issues/794):** EURUSD/GBPUSD, AUDUSD/GBPUSD y AUDJPY/GBPJPY presentan cobertura temporal coincidente superior al 99% de la unión de minutos disponibles. Antes de afirmar spread convergente, estimar beta SOLO de pasado, evaluar estacionariedad, ruptura de régimen, ejecución de dos legs y baseline cubierto; **no se ha medido edge relativo**.

## 4. Bloqueos que G0 no resuelve

- Calendarios reales de mercado y horarios operables por símbolo, incluido CFD NAS100 y XAUUSD; diferenciar horas naturalmente cerradas de gaps del proveedor. Validación M15/H1 en sesiones específicas sigue pendiente.
- No existen en este G0 costes de ejecución broker-calibrados por franja ni spread, slippage, comisión, swaps. Bid/ask no se exige para investigar geometría, sí para cerrar rentabilidad física.
- La misma ventana anual ya fue explorada en QORE. El sucesor debe reservar OOS verdaderamente no inspeccionado o reportar OOS_BLOCKED.
- No se han calculado patrones, señales, retorno condicionado ni P&L; fuente íntegra en estructura de M1 no implica G1 ni certificación. Todos los candidatos siguen NO TESTED.

**Siguiente paso operativo (separado y con prereg previo a outcomes):** censar las ventanas de calendario por mercado; luego pruebas G1 individuales DRIVE/RESET/RELATIVE, con un único contraste primario y baseline de hora/volatilidad/factor, controls de no lookahead, y registro de todas variantes exploradas. Ningún entrenamiento de cognitiva hasta encontrar edge básico. Prohibido tocar VPS/MT5/live y producción.

**Resultado de G0:** nueve market jobs + contrato + agregación completados; la infraestructura inicial ya tiene testigos reproducibles, pero los tres traders aún no están certificados.
