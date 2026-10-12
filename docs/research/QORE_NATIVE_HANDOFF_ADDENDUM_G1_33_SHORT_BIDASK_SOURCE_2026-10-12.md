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

## 6. Nuevo testigo Protobuf original y ampliación temporal independiente (2026-10-12)

La investigación avanzó de **solo JSONL int/decimal reconstruidos** a **bytes Protobuf originales de cada campo `ProtoOATickData`**, sin guardar account ID/tokens de la envolvente. Preregistro de 5 activos y 2 ventanas nuevas×30 minutos ANTES de capturar nuevos precios: [PR #859](https://github.com/mezas3238-hue/qore-core/pull/859) commit `8d72803ce988c800286b7ac19c4aa2ed47301ba1`. Real source GHA [#38288411671](https://github.com/mezas3238-hue/qore-core/actions/runs/38288411671) SUCCESS, source artifact #11764163362, SHA ZIP `b4eb9e66d76bcd439d4db8f2b8707afa06fe2d211a275c8af8b8605714b58684`. Ventanas: 2021-03-16, 2023-03-21, 13:00-13:30 UTC, no coincidentes con 2020/2023-sept/2026-sept fuente anteriores. Instrumentos: EURUSD/GBPUSD/USDJPY (dirigidos por problema de spread cero), controles XAGUSD y SP500/US500 (selección ex ante, **no muestra aleatoria**).

Auditor nuevo independiente [PR #860](https://github.com/mezas3238-hue/qore-core/pull/860) GHA [#38288815999](https://github.com/mezas3238-hue/qore-core/actions/runs/38288815999) SUCCESS; SHA y páginas `hasMore`, Protobuf tick field framing, decoder independiente precio/tiempo delta signed y reconciliación byte-exact de 34.761 ticks enteros/decimales PASARON. Reporte #11764626981, SHA ZIP `83ae0ae936631af362481a126dde3ef4b6d70ef9cdefdb785821130040494fc4`. Documento íntegro: `docs/research/QORE_NATIVE_G1_PROTO_WIRE_ORIGINAL_FIELD_SECOND_AUDIT_RESULTS_2026-10-12.md` en rama PR #860.

| Fuente en ventanas nuevas | BID | ASK | Zero as-of | Zero mismo ms | Positivos |
|---|---:|---:|---:|---:|---:|
| EURUSD | 3541 | 3454 | **3194** | 2740 | 766 |
| GBPUSD | 4568 | 4140 | **1814** | 1465 | 3791 |
| USDJPY | 4470 | 4532 | **1632** | 1166 | 4210 |
| XAGUSD | 3848 | 3943 | 0 | 0 | 5154 |
| SP500→US500 | 1157 | 1108 | 0 | 0 | 1434 |
| **TOTAL** | **17.584** | **17.177** | **6.640** | **5.371** | **15.355** |

382 snapshots source stale, 3 missing y 0 crossed. Los **6.640** zeros sobreviven a redecodificar los bytes serializados originales, refutando su explicación exclusiva como falla del decoder original (aunque pueden existir problemas de fuente o semántica). Un timestamp mismo ms no es prueba de bid/ask efectivamente ejecutable ni spread gratuito. Causas y contract equivalence **P0 sin resolver** en [Issue #856](https://github.com/mezas3238-hue/qore-core/issues/856). El source antiguo 127.928 + nuevos 34.761 = **162.689 eventos bid/ask totales en muestras cortas**, con instrumentos repetidos en ventanas distintas, **NO** 33 mercados con histórico continuo ni fuente NET.

Próxima misión del arquitecto: obtener interpretación de cTrader/IC Markets respecto a BID=ASK históricos, testigo forward cotizado sin órdenes, comparar contracts históricos 12 CIBO, soporte licenses/vault con restauración verificada, y elaborar plan de cobertura por shards de calidad hasta poder mapear todas las entradas/salidas de nuevas hipótesis preregistradas. **NINGUNA métrica NET ni trader certificado, 0/3; 231 Holm/FDR/E3 NO_SUPPORT intactos.**

## 7. Control temporal: BID/ASK mismo ms también produce spreads POSITIVOS

Forense **EXPLORATORIO post-hoc, NO hipótesis prereg alpha** en [PR #861](https://github.com/mezas3238-hue/qore-core/pull/861), [Actions #38290229370](https://github.com/mezas3238-hue/qore-core/actions/runs/38290229370) SUCCESS, 7/7 tests y mismo original Protobuf verificado desde #860. HEAD `89a523a76bb823ee9ba2cd735c067988bc33ad2b`; reporte `artifact #11764801993`, ZIP SHA256 `a433df35eb72b667d553c8aafbb44a4d5d5a145f8bdbc1d56b2e4507f20e9507`.

Entre **12.381** instantes únicos en que BID y ASK actualizan simultáneamente con timestamp del mismo milisegundo, **5.371 tienen precios idénticos** y **7.010 tienen ASK>BID (spread positivo)**. No se detectaron spreads cruzados, y los 6.640 zeros del QA original y 15.355 positivos concuerdan exactamente. **Mismo ms no es causa suficiente de cero**, aunque 5.371 de los zeros coincidan en ms. Los episodios máximos consecutivos (en instantes de actualización, NO minutos negociables) son EURUSD 93 y 86, GBPUSD 101 y 10, USDJPY 66 y 8 (2021/2023); controles XAGUSD y SP500/US500 cero episodios.

**Fuente externa:** Spotware explica que los feeds históricos BID y ASK se actualizan separadamente, a veces simultáneamente, y que OnTick se emite con cambio de cualquiera de los dos lados (https://community.ctrader.com/forum/connect-api-support/24165/). Su guía histórica define quote type separado, escala 100.000, `hasMore` y límite de 604.800.000 ms por solicitud (https://help.ctrader.com/open-api/symbol-data/). Es compatible con as-of last-known-side, **NO prueba spread cero ejecutable o fills**. Bloqueo #856 sigue abierto.

## 8. Gate causal no-económico sobre 20 pares de timestamps ficticios

Nuevo contrato de ingeniería definido ANTES de ejecutar los checkpoints aunque después de examinar el histórico FX: [PR #862](https://github.com/mezas3238-hue/qore-core/pull/862), prereg commit `72a31b325ace26cb9aec698793faefc748633ae0`, script `src/qore/infrastructure/trader_lab/qore_native_g1_causal_quote_checkpoint_pair_gate_v1.py`, [Actions #38290734217](https://github.com/mezas3238-hue/qore-core/actions/runs/38290734217) **SUCCESS**, 8/8 tests y SHA/protobuf parent #860 pass. Source-only artifact #11766210564 ZIP SHA256 `35f9593df32d2a1e2b549aeb20ca273890f7b056d604990a364128b16667a346`.

**Política previa:** último BID y ASK con timestamp de evento `<= decisión`, edad individual `<= 5000ms`, spread estrictamente positivo (cero/cruzado/ausencia/stale => rechazo), prueba idéntica tanto en tiempo de entrada como salida. Prohibido usar ticks futuros, promedios inventados, M1/M5 sintéticos, asignar fee 0 o reclamar fill. Los checkpoints son **horarios creados para probar calidad de fuente** (+5/+15 y +10/+25min del inicio de cada una de dos ventanas), **NO operaciones reales de trader ni entradas E2/E3**.

| Símbolo | Pares de checkpoints con los dos lados válidos en ambos tiempos |
|---|---:|
| EURUSD | 1/4 |
| GBPUSD | 2/4 |
| USDJPY | 3/4 |
| XAGUSD | 4/4 |
| SP500→US500 | 1/4 |
| **Total** | **11/20 (9 bloqueados correctamente)** |

En las 20 evaluaciones iniciales, `OK_POSITIVE_BIDASK=13`, `ZERO_SPREAD=5`, `STALE_SIDE=2`. En las 20 finales, `OK_POSITIVE_BIDASK=17`, `ZERO_SPREAD=2`, `STALE_SIDE=1`; crossed/missing=0. Contadores no suponen independencia entre entry/exit ni tamaño de muestra estadístico de una estrategia.

**Clave del handoff:** avanzar ahora a testigos originales de **eventos de trading realmente preregistrados con timestamps de decisión y cierre**, que necesitarán histórico nativo bid/ask correspondiente y contratos/costes originales demostrados. Hasta entonces **G1_SOURCE_GATE_PRE_COST_OK** significa ingeniería causal probada, **NO G1 NET económico desbloqueado**. 231 gross Holm/FDR/E3 tienen cero edge positivo replicado, 0/3 traders certificados, no VPS/MT5/LIVE/CIBO/Shared/QDLE. Resolver tickets #856, #857 y #837 primero.

## 9. Issue concreta para la siguiente fase (NO utilizar checkpoints como trades)

Creada [Issue P0 #863 — Timestamps causales de decisiones reales de los traders y cobertura source BID/ASK en ambos lados de operación](https://github.com/mezas3238-hue/qore-core/issues/863). La diferencia es crítica: los 20 pares `PR #862` usan tiempos de fuente FICTICIOS para probar el Gate, no eventos de trading. Para liberar un estudio real, el nuevo arquitecto debe congelar identificadores de señales/decisiones del motor 231, tiempos UTC pre-decision y cierre, contrato/broker SHA, sesgo de zona horaria y sesiones, luego testigos as-of de side BID/ASK con reglas de fuentes y comisiones reales. **No mezclar sample original 12 CIBO con broker actual antes de homologación #857, no imputar zeros #856, no usar holdout sellado ni anunciar NET/EDGE sin la cobertura.**
