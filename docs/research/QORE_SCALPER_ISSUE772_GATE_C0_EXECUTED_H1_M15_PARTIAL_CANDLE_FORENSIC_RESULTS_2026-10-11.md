# QORE Scalper P0 #772 — Gate C0 EJECUTADO: 9 mercados, velas H1/M15 parciales afectan señales V49
**Fecha:** 2026-10-11. **Estado:** C0 COMPLETE en alcance integridad y sensibilidad; **Gate C independiente NO realizado; NO CERTIFICAR**.

## Trazabilidad estricta
- [Orden del auditor, Issue #772](https://github.com/mezas3238-hue/qore-core/issues/772#issuecomment-6105818202)
- [Prerregistro C0 congelado previo a resultado](QORE_SCALPER_ISSUE772_GATE_C0_FROZEN_CANDLE_INTEGRITY_PROTOCOL_2026-10-11.md), commit **1f856c038ba3286fcaea11819ce06ee2c82805ea**
- [GH Actions C0 run #38115273268](https://github.com/mezas3238-hue/qore-core/actions/runs/38115273268), SHA del código auditado **1e06a09acd2501a6b404195ef7d5d918b2f70b8e**, **11/11 jobs SUCCESS** (1 contract + 9 mercados + 1 aggregate). Tests Ruff/Mypy/Pytest, incluidos negativos para 45/60, 11/15, gap, premature, duplicate.
- [Artefacto científico nueve mercados #11693302771](https://github.com/mezas3238-hue/qore-core/actions/runs/38115273268/artifacts/11693302771) incluye summary JSON, 2876 witness source IDs, 2020 A witness source IDs y 20 source-traces C0; nueve artefactos independientes por mercado contienen ledger de velas deficientes, input originales y detalle de reconstrucción.
- [PR Draft de investigación #773](https://github.com/mezas3238-hue/qore-core/pull/773)
- Fuente sellada V49 run 38053946695 SHA e356e7a52541e99533b25ecfef0ab9c4e9ce03c0, provider-native M1 run 35548099334 SHA 18c338aedd5013ce65a6cb6408ffbc2e904a6217. **Cero** outcomes, R económicos, PF, PnL, precios BID/ASK o señales invertidas para generar/seleccionar datos.

## Criterios técnicos congelados
Legacy V48 _aggregate(bars, minutes) permite H1 con 45–59 M1 y M15 con 11–14 M1, y guarda como closed_at la última M1 disponible, aunque sea anterior al límite del bucket. El escenario estricto exige 60/15 timestamps M1 consecutivos, exactos, sin duplicados, first open = límite nominal de inicio y última close = límite nominal final. Una barra incompleta nunca recibe un cierre nominal fabricado: real_complete_at UNAVAILABLE. Los huecos de datos NO se atribuyen automáticamente a fallas del proveedor o a cierre normal de mercado sin calendario independiente.

Las estadísticas por vela reflejan buckets **observados por native M1** dentro de la misma ventana lookback original de V49, no todas las horas teóricas de mercado en el año. Las cifras de exposición por operación reflejan SOLO velas directamente consumidas en el Candle2/Candle3 local y en el swing left/center/right, serie contraria y cierre CISD M15 del original; **el upstream POI H1 completo no tiene ID en V49 y sigue sin resolver**.

## Hallazgo A: universo de velas originales H1 y M15

| Integridad del bucket | H1 | M15 |
|---|---:|---:|
| Buckets nativos observados | 57.447 | 229.715 |
| Velas aceptadas por agregación V48/V49 | 57.147 | 228.426 |
| Aceptadas y NO estrictamente completas | **5.028 (8,80% de aceptadas)** | **6.542 (2,86%)** |
| Aceptadas con cierre adelantado | **2.357** | **2.687** |
| Buckets existentes rechazados por legacy (bajo mínimo) | 300 | 1.289 |
| Velas estrictas de 60/15 M1 nativas y cierre nominal | 52.119 | 221.884 |

La integridad estricta también registra leading, trailing e internal gaps, sin interpolar ni inventar cierres. La presencia de una vela parcial NO equivale a que aparezca en una operación.

## Hallazgo B: impacto SOBRE LAS MISMAS 2.876 oportunidades y 2.020 A

| Mecanismo, cuentas por source ID único | Fuentes 2.876 | A MAX3 2.020 |
|---|---:|---:|
| C2/C3 H1 directamente usa vela no estricta | **517 (17,98%)** | **375 (18,56%)** |
| C2/C3 H1 directamente usa cierre prematuro | 290 | 201 |
| M15 pivot/swing/serie CISD directamente usa vela no estricta | 17 | 15 |
| M15 component witness incluye gap entre velas del span | 4 | 4 |
| H1 O M15 directamente con componente no estricto (unión, no sumar) | **526 (18,29%)** | **382 (18,91%)** |
| Evento H1 original NO conserva firma exacta con H1 estricto + MISMO detector V48 | **531 (18,46%)** | **382 (18,91%)** |
| Setup M15 original NO conserva firma exacta con M15 estricto dentro del MISMO estado H1 original | 12 | 10 |

**Atención a los denominadores:** 5.028 H1 deficientes son candles únicas aceptadas, pero 517/375 son oportunidades cuyo Candle2/Candle3 local las consume. El análisis no infiere "todos los trades afectados pierden"; no se leyeron outcomes. M15 es mucho menos prevalente como contacto directo parcial que H1.

**Discrepancia importante dentro de A:** entre las 375 con H1 local parcial, **334** perdieron la firma H1 en shadow estricto y **41** conservaron la firma. Además, otras **48** entradas de H1 local completamente íntegro perdieron la firma del evento al cambiar todo el historial H1 por velas estrictas. Esto impide adjudicar la sensibilidad H1 únicamente a las últimas 2–3 velas: existe dependencia potencial del POI o estados previos y debe reconstruirse exhaustivamente antes de declarar cobertura.

**Estas divergencias son observaciones condicionadas:** el H1 estricto se compara con el observador V48 original y el M15 estricto con el observador estructural V48 original, bajo **el mismo estado H1 histórico**. NO es un generador de señales nuevo, ni test de autor ni test first-online independiente. Los 10 setups M15 divergentes no equivalen automáticamente a 10 errores causales.

## Distribución por mercado para el cohort A 2.020 (H1 + M15 directo)

| Símbolo | A | H1 directa parcial | M15 directa parcial | Alguna H1/M15 parcial | Evento H1 con firma estricta distinta |
|---|---:|---:|---:|---:|---:|
| AUDJPY | 181 | 70 | 2 | 70 | 70 |
| AUDUSD | 171 | 101 | 5 | 103 | 88 |
| EURUSD | 285 | 25 | 0 | 25 | 30 |
| GBPJPY | 194 | 85 | 1 | 85 | 89 |
| GBPUSD | 288 | 5 | 1 | 6 | 11 |
| NAS100 | 258 | 0 | 0 | 0 | 3 |
| USDCAD | 215 | 5 | 3 | 7 | 10 |
| USDJPY | 179 | 82 | 3 | 84 | 77 |
| XAUUSD | 249 | 2 | 0 | 2 | 4 |
| **Total** | **2020** | **375** | **15** | **382** | **382** |

Incidencia **heterogénea**: AUDUSD 103/171 con alguna vela directa no estricta, frente a NAS100 0/258. No asumir un mecanismo universal de señal; investigar calendario de sesiones y proveedor de cada activo antes de adjudicar calidad del dato o efecto económico.

## Evidencia a nivel de evento — casos mínimos reproducibles

**AUDJPY fuente d176554461d5de7ffff8b74940a549c963c7d92b1ff482dc320b600f3c2a655d:** H1 bucket 2025-09-18 20:00–21:00 UTC, **59/60 M1**; legacy declara cierre **20:59**, no el nominal 21:00. Evento origen H1 a 20:59, oportunidad entra 2025-09-19 01:40 UTC. El evento no conserva firma exacta al excluir velas parciales. No se ha atribuido por ahora pérdida, lookahead ni fallo de autor.

**AUDJPY fuente 342be938740f4bbaeebe7276af12d811691669918e58730a904bd287b0e32460:** H1 del 2025-10-20 20:00 tiene 59/60; swing/serie M15 incluye bucket 2025-10-21 00:00 con **14/15 M1**, gap interno sin cierre prematuro, y ese setup M15 no conserva la firma bajo agregación estricta condicionada. La vela derecha del swing estaba disponible a 00:30 y CISD original a 01:00; entrada 01:30 UTC. Verificar metadatos en ledger para reconstrucción nueva.

**AUDJPY fuente cb2d1f6fe6f5e6e0dc7b597a6d31ddb41908f064f5ae51a9bf13d6673b073cec:** Candle2/Candle3 local H1 usa 60/60 y 60/60, sin embargo la firma de evento desaparece con strict histórico. Esta observación ilustra que el POI y la historia upstream deben rastrearse, y que una etiqueta local COMPLETE_AND_CLOSED NO certifica la cadena.

## Hallazgo C: benchmark H1 cinco velas NO consecutivas

En las 2.020 A, la ventana last-five-AVAILABLE-full-H1 que alimentó el benchmark anterior es realmente continua en **1.529 (75,69%)** y no continua en **491 (24,31%)**. En 2.876 fuentes, 2.328 continuas y 548 no continuas (19,05%). Por tanto el anterior 1.017 MATCH / 999 OPPOSE / 4 FLAT no es válido como comparación homogénea de "últimas cinco horas".

Una unión por source-ID de los dos artefactos previos (C0 2020 y #772 Gates A/B 2020; SIN payoffs) da descriptivamente:

| H1 último cinco COMPLETE disponibles | MATCH | OPPOSE | FLAT | N |
|---|---:|---:|---:|---:|
| Cinco horas nominales consecutivas | 753 | 773 | 3 | 1.529 |
| Cinco velas completas con algún salto horario | 264 | 226 | 1 | 491 |
| Total | 1.017 | 999 | 4 | 2.020 |

Aun con cinco consecutivas, la pendiente precio H1 de cuatro retornos sigue siendo NO AUTORAL; no adjudicar dirección o causalidad a partir de ella.

**El campo entry_distance_from_stored_swing_R anterior es tautológico 1R al dividir el propio entry-stop por esa misma distancia. No mide desplazamiento de impulso ni timing tardío. Queda descalificado expresamente como evidencia de agotamiento o retraso.**

## Dictamen STOP/GO para Gate C independiente

- **C0 PASA como diagnóstico de prevalencia y sensibilidad a velas H1/M15** (2876/2876 fuente, 2020/2020 A, 20/20 IDs inmutables, 11/11 jobs successful). Se confirma incidencia relevante de velas incompletas y cierres prematuros en señales originales, no un mero defecto posible.
- **No afirmar lookahead:** las velas parciales usan datos observados; el problema es disponibilidad/cierre nominal y posible semántica no equivalente a una vela H1/M15 completa. El estatus autoral de uso de vela parcial es UNKNOWN.
- **Gate C todavía bloqueado** hasta ejecutar desde M1 native prefijos independientes: H1 C2/C3 y POI ID exacto, swing M15 left/right con available_at y serie CISD, M1 sweep/first CISD/FVG, identidad y divergencia por timestamp/dirección/familia/swing. No usar detectores V48/V49 como oráculo para nuevas decisiones.
- No determinar qué hace rentable Scalper con estos datos. Queda prohibido introducir filtros "strict bars", TTL H1, inversión de señales o tuning económico sobre el histórico consultado.
- Mantener coordinación con auditor metodológico #759/#768. DeepSeek puede recibir evidencia de reglas ambiguas, sin sustituir texto original. Sin VPS, MT5, LIVE, PROD, MERGE ni CERTIFICACIÓN.
