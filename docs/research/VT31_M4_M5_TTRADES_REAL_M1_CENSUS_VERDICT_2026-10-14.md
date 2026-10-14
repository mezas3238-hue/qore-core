# QORE CORE — VT31 M4/M5 PRUEBAS REALES: primer FVG M1, C2 y limitaciones económicas

**Checkpoint:** 2026-10-14 · **PR #935 DRAFT** · No main/merge/LIVE/orders/sizing/OOS/PNL.

## Evidencia reproducible del experimento
- **Prereg antes de implementación:** `e7470c9cc9e48cf7e869baf35ac8fc80bc6279c8`, [documento](./VT31_M4_M5_TTRADES_SOURCE_FVG_PATH_PREREG_2026-10-14.md). No cambio de umbral después de censo.
- **GitHub Actions SUCCESS:** [#38633923056](https://github.com/mezas3238-hue/qore-core/actions/runs/38633923056) en **commit ejecutado** `1cd6d385a77ae897d4a3e8e15265178eb8191234`. **174/174 pruebas PASS**, Ruff, compile, G3 COG+OPS+DOC original blob hashes intactos, SHA del original histórico M1 comprobado, controles de no-trading confirmados.
- **Artifact de reproducción:** [#11926284057](https://github.com/mezas3238-hue/qore-core/actions/runs/38633923056/artifacts/11926284057), ZIP SHA256 `cf1d6db6df5d95b59da2029ef928ade14be42af827353c9d16ff9b27f97b96de`. Incluye `VT31_M4_M5_REAL_M1_SOURCE_CENSUS.json`, `summary.json`, JUnit, SHA256SUMS y source scope.
- **Dato original**: NAS100 CFD, 1.059.784 M1, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, [artifact original #11459859004](https://github.com/mezas3238-hue/qore-core/actions/runs/38018856150), recuperado y verificado directamente por GitHub Actions CI #38633923056 y #38634407465. Development 3Y ya examinado; **NO OOS**.
- **Baseline metodológico exactamente congelado:** PR #934 775 días: 128 M2-M3 cognitivamente corroborados, 483 primer retorno sin MSS, 92 barrido sin regreso, 65 sin barrido, 6 incompletos, 1 rechazo fuente. Su reproducción **concuerda byte-poblacionalmente por conteos** con la CI de #934.

## Resultados M4 sobre los 128 contextos nativos, sin seleccionar por futuro
| Clasificación M4 ex ante | Contextos |
|---|---:|
| `FVG_GEOMETRY_ATTESTED_NOT_EXECUTABLE` (primera FVG estricta M1 con lado correcto, 10 puntos anclados al MSS, DOL opuesto, CE derivado y C2 mecha) | **119** |
| `NO_ELIGIBLE_FVG` | **8** |
| `WINDOW_CLOSED_FOR_NEW_LIMIT` (primer FVG califica al cierre 11:00 NY, no se emite nueva orden) | **1** |
| **Total** | **128** |

**119/128 = 92,97% de los 128 contextos** presentaron geometría QORE; el porcentaje NO es win rate, ni fill rate, ni respaldo de OB/Breaker autoral. La selección no mira si tocó CE después. El MSS se mantiene en su cierre original, la verificación FVG usa tres M1 cerradas y el stop tiene SOLO referencia C2 sin precios negociables.

## Resultados M5 sobre las 119 formas FVG
| Estado del precio M1 posterior, diagnóstico SIN ORDER | Conteo |
|---|---:|
| `TOUCH_NOT_FILL` — M1 cruza CE; ningún ACK | **61** |
| `AMBIGUOUS_M1_SEQUENCE_NO_FILL` — misma M1 toca CE y CIERRA fuera del borde de invalidación, sin secuencia intrabar observada | **31** |
| `EXPIRED_NO_ORDER_OR_ACK` — no toque/cierre invalidante observable hasta final de ventana | **27** |
| **Total** | **119** |

Este diagnóstico observa únicamente M1 después de C3; no cuenta el OHLC de C3 como fill. El cuerpo y mechas de C2 se distinguen explícitamente. En caso de toque y close invalidante en misma M1, no se crea una secuencia falsa ni un trade. El first-hit path se registra sin pretender que sean órdenes o cancelaciones reales.

## Diferencia crítica fuente versus contrato/economía
[PR #901 G5 BID/ASK USTEC](https://github.com/mezas3238-hue/qore-core/pull/901): 483.103 registros BID/ASK lado-tick de USTEC IC Markets cTrader DEMO para 30 horas y 10 fechas development, verificación 1.800/1.800 M1 HIGH/LOW/CLOSE iguales a BID en esas horas; 1.789/1.800 OPEN. **Esto acredita coexistencia de feeds/precios, NO equivalencia contractual NAS100↔USTEC**. Sólo 30 horas frente a 3 años, 0 ACK de nuestras 119 propuestas, falta rejilla/tick exacta/fees/stops_level y cobertura completa. Ver también [issue #857](https://github.com/mezas3238-hue/qore-core/issues/857) y [#900](https://github.com/mezas3238-hue/qore-core/issues/900). **No es correcto afirmar «no hay ningún BID/ASK», tampoco correcto afirmar «tenemos BID/ASK NAS100 ejecutable de 3 años».**

## Certificación independiente M0–M7
- M0/M1: perfiles diferenciados, data M1 de NAS100 SHA PASS para este corpus.
- M2/M3: 128 contextos H1 TTrades + MSS proxy QORE respaldados; TTrades desplazamiento/MSS como norma del autor no certificado.
- M4: 119 geometrías FVG estrictas, **QORE formalización exclusivamente**; OB y Breaker Block autorales no probados/implementados, M4 **NO CERTIFIED**.
- M5: C2 wick y CE causal verificados solo como **referencias de investigación**; sin tick/broker, stops/limit/ACK/cancel/position no identificados; 31 same-M1 ambiguos. **NO CERTIFIED**.
- M6: **G3_PENDING_DUAL_SIGNATURE** Issue #897; no una sola cuenta pretendiendo dos personas.
- M7: **EDGE_NOT_DEMONSTRATED**, curva económica no medible con este OHLC; PR #902 directional prior negative en cohorte antigua NO demuestra que CE-C2 del nuevo perfil pierda, pero indica investigación sin fundamento económico favorable previo. Falta OOS prospectivo, contrato NAS100 homologado y historial BID/ASK/ACK.
- **Trader certified = FALSE, trading/live authorized = FALSE.**

## Problemas para arquitecto sucesor (orden, sin ajuste por retorno)
1. Identidad doctrinal perfil TTrades: verificar fuente primaria y definir cuándo su displacement, FVG, OB/Breaker son alternativos/exclusivos; no confundir Silver Bullet 2023 ICT general con TTrades 2025.
2. La política del **primer regreso más MSS en la misma vela** es QORE proxy y filtró 483 días. No afirmar que el autor exige esa simultaneidad. Otro modelo necesita prereg distinto y OOS aparte; no ajustar tras el censo.
3. Revisar contradicción entre los dos testigos ICT general #930/#932 (gaps e identidad DOL) antes de consumir la misma fuente en certificación.
4. Resolver doble firma real COG y OPS del G3 con SHA exactos bajo #897.
5. Resolver identidad exacta de contrato/símbolo NAS100↔USTEC con fuente/mercado, tick_size, stops/freeze, spread, comisiones y periodos históricos completos bajo #857/#900. No inferir especificaciones de una etiqueta.
6. Completar un motor **no trading** de ciclo order/ACK y expiración/time exit, primero con fixtures de quotes y datos correctamente autorizados. Touch OHLC != fill; 31 situaciones ambigüas exigen tick/order event stream.
7. Preregistro económico en desarrollo tras bloqueadores (NO realizar replay V1 antes G3 firmas), seguido de validación realmente OOS sin usar el corpus ya estudiado para mejorar reglas. Solo resultados negativos/positivos medidos permiten decisión de PF/DD.

**Firmado por metodología de investigación (automatización), NO por los roles humanos COG/OPS.** Ningún comentario automático sustituye aprobaciones independientes. Este documento es posterior al run verde; el resultado de CI mencionado aplica exactamente al commit ejecutado, no afirma reejecución del HEAD documental.

## CI posterior — pruebas adicionales M4/M5 realmente ejecutadas (mismo censo)
Para eliminar una posible laguna de certificación de estructura, se añadieron ANTES de esta ejecución 5 pruebas adversariales: perfiles LONG/SHORT con potencial de **9 puntos** medido desde CLOSE del MSS que deben rechazar, perfiles LONG/SHORT con **10 puntos exactos** que conservan elegibilidad de geometría, y un primer FVG que cierra a **11:00 NY** cuando ya no se puede ofertar nueva LIMIT. Estas pruebas no modifican ni vuelven a calibrar reglas.

**[CI #38634407465 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38634407465)**, SHA exacto de código y test `2c4c521e242ac44ed7cdfb7bb83e55ba5d062236`. **179/179** pytest PASS, Ruff, compile, G3 locks, fuente M1 SHA y censo congelado PASS. **Resultado del censo idéntico:** 119 FVG fuente, 8 sin FVG, 1 ventana vencida; M5 61 touch/no fill, 31 misma M1 ambiguos, 27 expiraron. [Artifact verificado #11927986218](https://github.com/mezas3238-hue/qore-core/actions/runs/38634407465/artifacts/11927986218), ZIP SHA256 `3662ec537e72ba7bccbbc9da503299768773b2ac9c0a976d677b9731c54767e2`. El informe permanece meramente descriptivo sin gate económico.

## Auditoría G5 adicional sobre fuente externa ya existente (NO nuevo backtest)
La [auditoría original del PR #901](https://github.com/mezas3238-hue/qore-core/blob/291dfcafc6beb0a7cc72f75e4947b92611305767/docs/research/VT31_G5_REAL_USTEC_30H_BIDASK_AND_3Y_M1_CROSSSOURCE_RESULT_2026-10-13.md) discrimina **242.554 instantes de eventos BID/ASK en 30 horas**, de los cuales **242.552 spread positivo, 2 crossed en cuarentena**, spread mediano 0,80 puntos de índice y p95=1,40 (histórico descriptivo NO coste fijo negociable). Reporta 184 inter-arrival gaps BID >5 segundos y 11 discrepancias OPEN de las 1.800 velas, concentradas el 2025-04-16. **M1 NAS100 original coincide con BID y no con MID** en esas 30 horas para high/low/close: el modelo económico basado en `MID ± spread` no puede usar esos M1 como MID, se invalida esa interpretación. Por tanto un replay económico CE-C2 exigiría **quotes completas desde oferta hasta stop/TP/time-exit 15:55**, no solamente las horas Silver Bullet y no sólo un spread p50. Este hallazgo ya estaba identificado en GitHub antes de la ronda actual; aquí se incorpora para la certificación sin comprar datos ni simular órdenes.
