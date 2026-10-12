# QORE Native — NZDUSD G1-PRE real BID/ASK source QA (post-acquisition, 2026-10-12)

## Antecedente verificado
- Fuente oficial IC Markets cTrader DEMO, **read-only**, commit `ef69b1b6ea2dbbd689bc3e090f9581e15bbb7ad6`; [Actions #38279593236](https://github.com/mezas3238-hue/qore-core/actions/runs/38279593236) ambos jobs SUCCESS.
- Artefacto [#11760547215](https://github.com/mezas3238-hue/qore-core/actions/runs/38279593236/artifacts/11760547215), SHA256 ZIP `e593ba684ae7073968371f4fa1d00673ce773e71a5fab000c80a672fbc33a64d`, expira 2027-01-10, por tanto NO es copia permanente.
- Piloto preregistrado **NZDUSD** sin selección por retorno: 3 ventanas de 10min, 2020-09-15 13:00Z, 2023-09-19 13:00Z y 2026-09-15 13:00Z. Los intervalos incluyen el periodo posterior al embargo de resultados de estrategias **solo para factibilidad de fuente**, sin acceder a outcomes.
- Autenticación DEMO y catálogo broker: SUCCESS. Traza BID+ASK recuperada por `ProtoOAGetTickDataReq` corregida para **timestamp y precio signed-delta** tras el primer valor absoluto, sin fabricar ticks de M1/M5.

## Evidencia de fuente, no economía
| Ventana | BID ticks | ASK ticks |
|---|---:|---:|
| 2020-09-15 | 251 | 243 |
| 2023-09-19 | 597 | 670 |
| 2026-09-15 | 523 | 391 |
| **Total** | **1,371** | **1,304** |

12 archivos (6 native-integer y 6 decimal-normalized) con SHA por lado, manifest y `OUTPUT_SHA256SUMS.txt`. Artefacto revisado sin subir raw prices al repo público (licencia/procedencia).

## Segunda línea independiente de QA
Módulo `qore_native_g1_nzdusd_real_side_source_audit_v1.py` consume **exclusivamente el ZIP original del run anterior**, valida 13 archivos SHA, conteo, reloj UTC, as-of, igualdad exacta de enteros de origen a decimal, SHA por lado, ausencia de future tick y divergencias de precio misma milisegundo. Cuantifica spreads **solo descriptivos**, separando `incomplete`, `stale`, `zero`, `crossed`, y `positive`; reloj de 5 segundos es una **política de cuarentena**, no prueba de coste histórico ejecutable ni supuesto de fill.

**Distinción esencial:** aunque los datos provienen de respuestas del SDK cTrader, no se conservó el Protobuf original para redecodificación independiente; `original_side_protobuf_attested_independently=false`, y esta QA revisa persistencias enteras creadas por el lector de fuente. También es imprescindible homologar comisión, símbolo/lote/tamaño/horario histórico y snapshots en entrada+salida para calcular NET; 3 ventanas × 10 minutos de un mercado no certifican costes de 33 mercados durante ocho años.

## Estado científico
`SOURCE_3_WINDOWS_G1_SHA_PASS` **solo si workflow real QA verifica completo**; `HISTORICAL_NET_BLOCKED`; `E2_E3_231_NO_POSITIVE_SUPPORT`; `CERTIFIED_0_OF_3`. Ultra Fast #845 23 tests OK, pero velocidad ≈1.005x en fixture sintética: no usar velocidad de simulador CIBO como reclamación de alpha. No modificar VPS, LIVE/MT5, CIBO, Shared o QDLE. No seleccionar nuevas ventanas por resultados.
