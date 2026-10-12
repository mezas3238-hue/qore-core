# ADDENDUM al HANDOFF MAESTRO QORE NATIVE — G1 BID/ASK, 33 posiciones con 1 alias provisional

**Fecha:** 2026-10-12. **Parent handoff inmutable:** commit `ba64abffd8f74d8c1b5975014234790f4b3e6543`, [PR #841](https://github.com/mezas3238-hue/qore-core/pull/841). Este documento complementa, NO reemplaza, los ensayos 7×33=231 y sus dictámenes Holm/FDR/E3. El resultado original sigue `E2_E3_NO_POSITIVE_REPLICATED_EDGE`, `CERTIFIED_0_OF_3`.

## 1. Dictamen verificable y alcance MUY específico

**Resultado G1 fuente:** se recuperaron **127.928 eventos BID/ASK nativos** en solo **TRES ventanas de 10 minutos por instrumento** (2020-09-15, 2023-09-19 y 2026-09-15, siempre 13:00–13:10 UTC). Cobertura de *nombres de proveedor:* 31 exactos, SP500→US500 ya declarado y verificado como provider actual, NAS100→USTEC **solamente CANDIDATO NO HOMOLOGADO**. Así hay un piloto en los **33 puestos del universo**, pero **solo 32/33 sin el bloqueo de identidad NAS100** y otros contratos de CIBO originales tampoco equivalentes todavía. **NO significa 33×10 años** de BID/ASK, NO cubre necesariamente entradas/salidas de las 231 reglas, NO mide costes ni fills.

| Bloque | BID | ASK | Total | Evidencia |
|---|---:|---:|---:|---|
| NZDUSD | 1.371 | 1.304 | 2.675 | [#844](https://github.com/mezas3238-hue/qore-core/pull/844) |
| XAGUSD | 2.923 | 2.859 | 5.782 | [#847](https://github.com/mezas3238-hue/qore-core/pull/847) |
| SP500→US500 | 961 | 930 | 1.891 | [#847](https://github.com/mezas3238-hue/qore-core/pull/847) |
| Otros 29 nombres exactos | 55.154 | 56.297 | 111.451 | [#849](https://github.com/mezas3238-hue/qore-core/pull/849) |
| NAS100→USTEC *provisional* | 3.075 | 3.054 | 6.129 | [#853](https://github.com/mezas3238-hue/qore-core/pull/853) |
| **TOTAL fuente** | **63.484** | **64.444** | **127.928** | **Sólo source, nunca NET** |

El G0 M5 heredado (33/33, SHA `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`) es fuente distinta; 12 de los 33 originales pueden provenir de cuenta/contrato diferente del actual IC Markets DEMO y **no** están homologados sin comparación explícita.

## 2. Ejecuciones, commits, artefactos, integridad

- **G1-PRE formato y as-of:** [PR #842](https://github.com/mezas3238-hue/qore-core/pull/842) — manifest SHA, UTC, decoder sides, fail-closed, 16/16 pruebas sintéticas [run #38271254152](https://github.com/mezas3238-hue/qore-core/actions/runs/38271254152). No ticks en esos fixtures.
- **Primer auténtico NZDUSD:** [PR #844](https://github.com/mezas3238-hue/qore-core/pull/844), código `ef69b1b6ea2dbbd689bc3e090f9581e15bbb7ad6`, [run #38279593236](https://github.com/mezas3238-hue/qore-core/actions/runs/38279593236) SUCCESS, [artefacto #11760547215](https://github.com/mezas3238-hue/qore-core/actions/runs/38279593236/artifacts/11760547215), ZIP SHA256 `e593ba684ae7073968371f4fa1d00673ce773e71a5fab000c80a672fbc33a64d`. [PR QA #846](https://github.com/mezas3238-hue/qore-core/pull/846), [run #38280521951](https://github.com/mezas3238-hue/qore-core/actions/runs/38280521951) SUCCESS, 13 archivos/stream SHA, source 2.675 ticks, 7/7 tests, artifact #11760418464.
- **XAGUSD y SP500/US500:** prereg congelado antes de captura en [PR #847](https://github.com/mezas3238-hue/qore-core/pull/847), code `626909b960525dbf3ca0c7ab0a554b56d03c0170`, [run #38282585181](https://github.com/mezas3238-hue/qore-core/actions/runs/38282585181) SUCCESS. [XAGUSD #11761892358](https://github.com/mezas3238-hue/qore-core/actions/runs/38282585181/artifacts/11761892358) ZIP SHA `aaa32406dd4e2a5cc826da47e088f645f3963b88735d4ced4d7f366e5f00843e`, [SP500 #11761419260](https://github.com/mezas3238-hue/qore-core/actions/runs/38282585181/artifacts/11761419260) SHA `a1fa1a7c22062f2b20970c5a8540634f3fc3ab0a165f136dce97aa3cbe26f5f5`. [PR QA #848](https://github.com/mezas3238-hue/qore-core/pull/848) / [run #38283148986](https://github.com/mezas3238-hue/qore-core/actions/runs/38283148986) SUCCESS: 13 SHA/mercado, 8/8 synthetic tests/mercado.
- **Los 29 restantes:** prereg commit `807806b4f27965f6f1bdcc3ed7ab349f5437239b` antes de la consulta, [PR #849](https://github.com/mezas3238-hue/qore-core/pull/849), code `f8262bd7cdea1fbfb2287c3c1fe0dae3be2b0efc`; [run #38283737706](https://github.com/mezas3238-hue/qore-core/actions/runs/38283737706) SUCCESS `29/29`, una sesión autenticada DEMO sin repetir 29 handshakes. [Fuente #11762222336](https://github.com/mezas3238-hue/qore-core/actions/runs/38283737706/artifacts/11762222336) ZIP SHA `be123f91e2069390e3bb44f9ce8b9398e3216b9ce483b7441f7f2aebb918f1c0`; archivos originales 29×13=377 (29 manifests, 348 side streams) SHA individual verificados. [PR QA #851](https://github.com/mezas3238-hue/qore-core/pull/851), [run #38284672957](https://github.com/mezas3238-hue/qore-core/actions/runs/38284672957) SUCCESS, 8/8 tests, artifact #11763145888, 111.451 eventos reales cotejados integer↔decimal.
- **NAS100/USTEC**: [PR #850](https://github.com/mezas3238-hue/qore-core/pull/850) / [run #38284304699](https://github.com/mezas3238-hue/qore-core/actions/runs/38284304699) SUCCESS, actual USTEC enabled `symbolId=10014`, digits=2, pipPosition=1, lotSize=100, minVolume=10, stepVolume=10, fuente catálogo #11762018327. **No es prueba de equivalencia con NAS100 CIBO.** [PR #853](https://github.com/mezas3238-hue/qore-core/pull/853), [run #38285063753](https://github.com/mezas3238-hue/qore-core/actions/runs/38285063753) SUCCESS, [fuente #11762668603](https://github.com/mezas3238-hue/qore-core/actions/runs/38285063753/artifacts/11762668603), ZIP SHA `402831fcf2ba60070bdcf92671a1470838bda44208bf40ff373d95dc066c5da4`. [PR QA #854](https://github.com/mezas3238-hue/qore-core/pull/854), [run #38285419067](https://github.com/mezas3238-hue/qore-core/actions/runs/38285419067) SUCCESS: 13 source files SHA, 6.129 ticks y 6/6 tests, QA artifact #11763385912.
- **Trader Lab Ultra Fast:** [PR #845](https://github.com/mezas3238-hue/qore-core/pull/845) / [run #38278895976](https://github.com/mezas3238-hue/qore-core/actions/runs/38278895976) SUCCESS, 23/23 tests y 9.999 snapshots parity SHA de fixtures sintéticos (5.000+5.000 eventos); **1,005×** velocidad, no mejora material. Reusar principos de custody cache SHA del CIBO, NO la memoización de outcomes como si fueran nuevos trades.
- **Antiguo PR EURUSD #803:** source auth previo bloqueado y decoder antiguo INCORRECTO para tick side streams: cTrader usa primera timestamp y price ABSOLUTAS, cada siguiente TIME y PRICE como delta **con signo**. Bug corregido en #844 y regresión real; notificado en comentario de PR #803. No promover decoder antiguo ni confundir M1 con tick.

## 3. Problemas relevantes descubiertos (P0 hasta reparación)

La QA as-of opera exclusivamente sobre snapshots a `last-known-bid + last-known-ask` a la hora del evento, con política **5s** de edad máxima, nunca usando ticks futuros. Los contadores NO son fills. Rechazar mismo milisegundo con precios distintos hasta conocer orden causal original.

| Lote QA | Spreads positivos source | Zero quarantined | Stale quarantined | Missing side | Crossed |
|---|---:|---:|---:|---:|---:|
| 29 mercados, QA #851 | 66.543 | **5.727** | 1.093 | 48 | 0 |
| XAGUSD, QA #848 | 3.451 | 0 | 4 | 0 | 0 |
| SP500/US500, QA #848 | 1.007 | 0 | 47 | 0 | 0 |
| USTEC candidato, QA #854 | 3.403 | 0 | 6 | 0 | 0 |

**Problema profundo:** en varios majors se concentran spreads spot reconstruidos 0 (EURUSD 1.331, GBPUSD 864, USDJPY 1.107, USDCHF 643, AUDUSD 841; recuentos 3×10min). Causas por investigar: resolución nativa, limitación de precio de historia del broker, side synchronization y contrato. Jamás meter zero como coste `0` en un backtest NET. Si hay spread/fee negativa o incoherente en timestamp de orden, **abstenerse científicamente**, no imputar datos arbitrarios sin contrato ex ante.

## 4. Próximo arquitecto: orden explícito y Gates

1. **P0 contrato de fuente**: adjudicar contrato vivo de cTrader DEMO contra los 12 instrumentos originales CIBO, especialmente SP500/US500 y NAS100/USTEC; comparar symbolId original, digit/pip/tick size, tamaño del contrato, pipValue, lot unit, currencies, min step, trading sessions, costos/swap/comisión por periodo. Alias de nombre NO basta. `NAS100_EQUIVALENCE_BLOCKED`.
2. **P0 interpretación de spreads 0** y QA temporal entre lado BID/ASK. Reproducir con fuente original, y si es posible preservar Protobuf bytes de respuesta para redecodificador independiente: hoy los 13 manifests por symbol incluyen integer normalizados, NO bytes raw Protobuf. Revisar `hasMore`/empates 1ms y sincronización/latencia antes de permitir cost modeling. QA de la otra cuenta, si disponible, para corroboración cross-broker.
3. **P0 largo plazo/archivo legal**: 3×10min por instrumento es solo prueba de fuente; planificar adquisición en shards semanales/mensuales **solo después de evidenciar dónde se guardarán, derechos de broker, tamaño/coste estimado, SHA + restauración probada**, artefactos Actions se vencen ~2027-01-10, vigilar [Issue #837](https://github.com/mezas3238-hue/qore-core/issues/837). El repositorio es **público**; NO subir datasets crudos al Git público ni Releases sin licencia.
4. **P0 costos ejecutables**: cobertura causal en **entrada y salida** de reglas pre-registradas, comisiones RT reales por símbolo/lote/periodo, spread real, slippage/ruteo, swaps, financiación y horarios/NEWS PIT. Solo entonces reportar `NET`. Cero líneas de E2 deben convertirse retroactivamente en positivos por seleccionar/fijar costes desde fotos o 30min de ticks.
5. **P1 investigación económica**: 231 celdas iniciales 7×33 tienen dictamen negativo (Holm/FDR/E3). No buscar hiperparámetros ex post sobre 2024-09-17+; preregistrar hipótesis ECONÓMICAS originales, potencia/trade density, familia de multiplicidad (Holm vs FDR según decisión) y WFO/purged time blocks/bootstrap dependiente antes de inspeccionar PnL. Tras nuevo resultado, certificar traders únicamente si cumplen Gates de Core **medidos en economía NET robusta**.
6. **P1 desempeño de Trader Lab**: #845 es correcto por paridad, **no es más rápido materialmente**. Perfilado del parser JSONL vs módulo SIMD, caché deterministic SHA por shard, pruebas exactas scalar-vs-fast, sin dar a un cache-hit valor de evidencia independiente.
7. **Prohibido producción**: todas las ramas/pruebas son research Draft. Mantener `HISTORICAL_NET_BLOCKED`, `NATIVE_TRADERS_CERTIFIED_0_OF_3`, `NO_VPS_MT5_LIVE_CIBO_SHARED_QDLE_CHANGES`. El siguiente arquitecto puede consultar a DeepSeek como revisor metodológico externo, pero la evidencia debe verificarse en GitHub con SHA, fuente y CI antes de modificar cualquier gate.

**Nota de identidad:** 33/33 source spots es la disponibilidad de cotizaciones cortas; **NO** significa 33/33 instrumentos contractual/históricamente equivalentes o 33×10Y tick data. Todos los artifacts pueden expirar; hashes expuestos documentan custodia actual, NO backup permanente.

## 5. Forense de los 5.727 spread-zero source snapshots (nueva verificación)

[PR #858](https://github.com/mezas3238-hue/qore-core/pull/858), prereg posterior a QA de fuente y previo a análisis forense, [Actions #38286343956](https://github.com/mezas3238-hue/qore-core/actions/runs/38286343956) **SUCCESS** con 6/6 tests, mismo artifact source original 29 mercados #11762222336, más QA integral #851 verificada.

Del total de **5.727** snapshots BID=ASK dentro de edad máxima as-of de 5s:
- **4.320** tienen BID y ASK *último conocido* con marcas temporales exactamente iguales al instante de evaluación (0ms; ≈75,4% del total). Esto NO demuestra entrega simultánea a la plataforma ni fill ejecutable; sí impide atribuir automáticamente todos los zeros a un lado anticuado.
- **0** desfase entre 1 y 100 ms; **469** entre 101 y 500 ms; **313** entre 501 y 1.000 ms; **625** entre 1.001 y 5.000 ms.
- La auditoría reproduce exactamente el recuento del parent QA29; [artefacto de estadísticas sin raw precios #11763457401](https://github.com/mezas3238-hue/qore-core/actions/runs/38286343956/artifacts/11763457401), SHA ZIP `46e12c05bdf13c6bc81107f7bfb4cb74e3875f13848058834668e6c020331823`.

**P0 no resuelto:** confirmar con semántica oficial de cTrader/IC Markets si BID y ASK históricos identicamente timestamp y precio son verdaderamente cotizables, límites de resolución, precios derivados o datos paralelos del mismo feed. Sin prueba independiente en fuente/contratos, 4.320 nunca equivalen a spread cero ejecutable. [Issue #856](https://github.com/mezas3238-hue/qore-core/issues/856) sigue abierto. Los Gates `NET` y 0/3 cert permanecen bloqueados.
