# HANDOFF MAESTRO — QORE-alpha V1 / 96 variantes congeladas

> **ADENDA OBLIGATORIA 14-OCT-2026 — CERTIFICACIÓN QORE CORE:** [QORE_ALPHA_V1_HANDOFF_ADENDA_GATES_CERTIFICACION_CORE_2026-10-14.md](QORE_ALPHA_V1_HANDOFF_ADENDA_GATES_CERTIFICACION_CORE_2026-10-14.md). El screening de las 96 variantes **NO equivale** a LAB CERTIFIED, DEMO CERTIFIED ni LIVE. Son obligatorios PF y drawdown con evidencia económica, Sharpe/Sortino cuando válidos, OOS fresco, stress/Monte Carlo, Risk, CIBO, validación independiente y firmas externas según issues canónicos [#469](https://github.com/mezas3238-hue/qore-core/issues/469), [#473](https://github.com/mezas3238-hue/qore-core/issues/473) y [#468](https://github.com/mezas3238-hue/qore-core/issues/468). Los mínimos numéricos institucionales de Sharpe/Sortino no se deben inventar: recuperar commit exacto de la política aplicable antes de certificar. **Sizing del Trader prohibido como rescate; volumen CIBO/QDLE después de la evidencia.**


**Fecha de corte:** 13 de octubre de 2026 · **Estado:** BLOQUEADO POR DATOS M3/M1 ANTERIORES A 2023-09 Y EVIDENCIA BID/ASK+COSTES, PERO M5 2022/2023 YA VERIFICADO EN LOS CINCO PARES.  
**Repositorio soberano:** `mezas3238-hue/qore-core`.  
**Rama actual de investigación (NO MERGE):** `research/qore-alpha-96-frozen-20261011`.  
**PR de investigación:** [#797](https://github.com/mezas3238-hue/qore-core/pull/797), DRAFT. **Issue principal:** [#798](https://github.com/mezas3238-hue/qore-core/issues/798).  
**Predecesor documental:** VT08 metodología [PR #765](https://github.com/mezas3238-hue/qore-core/pull/765), misión única fiel al autor [#787](https://github.com/mezas3238-hue/qore-core/issues/787) CERRADA/SUPERSEDED; no borrar ni reactivar.  
**Responsable siguiente:** arquitecto de datos/ejecución científica QORE-alpha; coordinación con el arquitecto de cognitiva #763 solo para semántica causal, sin autorizar señales.  
**Objetivo del Owner:** DESCUBRIR SI HAY EDGE RENTABLE; detener búsqueda sin sesgos. El marco actual es una investigación nativa de QORE, **NO** pretende reproducir fielmente el método de TTrades.

> **LECTURA OBLIGATORIA antes de modificar algo:** [PRERREGISTRO COMPLETO DE 96 Y STOP RULE](QORE_ALPHA_V1_96_FEATURE_SPACE_AND_STOP_RULE_PREREG_2026-10-11.md), [REGISTRO CANÓNICO JSON de 96](QORE_ALPHA_V1_FROZEN96_VARIANT_REGISTRY_2026-10-11.json), [G0 M5 2022/2023 verificadas](QORE_ALPHA_V1_2022_EXISTING5_M5_SOURCE_G0_SHA_VERIFIED_2026-10-12.md), [REPORTE BLOQUEOS de autenticación](QORE_ALPHA_V1_FROZEN96_VERIFIED_SOURCE_COVERAGE_AND_AUTH_BLOCKERS_2026-10-11.md). El presente handoff **NO sustituye** la especificación congelada, ni autoriza variar ni una coma del contrato económico a raíz de un PnL.

---

## 1. Dictamen ejecutivo — SIN confundir estados

1. El proyecto **VT08 / prototipo QORE PS-only** tuvo una falsación económica específica: PF bruto agregado 0,964 (entrada posicional) y 0,895 (limit CISD) sobre 3.561 madres; ambas estrategias pierden incluso sin costes; en sensibilidad artificial 0,10R los PF fueron 0,781 y 0,773. **NO-GO para ESE PROTOTIPO**, no demostración de que todo TTrades falle.
2. La misión cambió explícitamente a **QORE-alpha**, features inspiradas en reversión M30+CISD/PS M3 y **96 variantes EXACTAS** preregistradas, sin obligación de fidelidad TTrades. No arrastrar el NO-GO económico anterior como si fuera resultado de QORE-alpha v1.
3. **El generador y el registro canónico de 96 están verificados:** SHA256 de contenido de manifiesto `4332e07f4a8fbdf1125ecd004a70c4216b8ea1a60e954847eedfe3b362184891`. No agregar variante 97, filtro sesgado ni nuevo split.
4. **Los cinco mercados SÍ tienen RAW M5 2022 y 2023 originales en GitHub y hashes cotejados:** [Actions #38259002749](https://github.com/mezas3238-hue/qore-core/actions/runs/38259002749), **5/5 SUCCESS**; es una corrección material del informe viejo que decía que “faltaba 2022” sin matizar. Faltaba 2022 en los archivos **M3/M15 de 1095 días**, NO en GitHub M5.
5. **El bloqueo económico permanece:** el modelo original exige **CISD/PS en velas M3 auténticas**; un grupo de velas M5 no permite reconstruir de forma única M3 OHLC. Tampoco hay un contrato acreditado de BID/ASK+spread/comisión/slippage históricos para el período. **0/96 variantes backtesteadas bajo el nuevo protocolo**; no existe aún un veredicto de rentabilidad nuevo.
6. **No usar datos sellados de 7 años/VPS/LIVE ni financiación real.** Preservar a GitHub como fuente de verdad.

## 2. Trabajo completado — cronología real y reproducible

### 2.1. Arquitectura originaria y recolección geométrica VT08

- Se estudió la familia C2→C3 de M30 y M3 con base en fuentes TTrades, separando reglas autor-A de formalizaciones QORE-C e incógnitas-D. Archivos: `docs/research/VT08_A_AUDITOR_M30M3_FIVE_FAMILY_CAUSAL_SOURCE_SPEC_2026-10-10.md`, `docs/research/VT08_A_AUDITOR_M30M3_H1_CAUSAL_POI_PIVOT_VERIFIED_RESULTS_2026-10-10.md`.
- Fuente M3 real cTrader DEMO 1095 días: [run #35941643396](https://github.com/mezas3238-hue/qore-core/actions/runs/35941643396); M15 independiente para cruces: [#35934924907](https://github.com/mezas3238-hue/qore-core/actions/runs/35934924907). Periodo observado por la auditoría de QORE-alpha desde **2023-09-24 19:45 NY** hasta **2026-09-23 19:42 NY** en M3 para los cinco pares.
- Se verificaron 8.982 madres **geométricas** M30/M3, 8.979 con H1 fuente contextual verificable y 3 H1 incompletas, 3.542 retesteos geométricos M3. Esos conteos **no son candidatas autorizadas, órdenes, fills ni rentabilidad**. Se marcó EQ referencia a swing D, selección POI D, breaker-stop ex post D y doble sweep D.
- Source stop A escrito: [Time Frame Alignment Example 1](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/) describe long con SL debajo **EQ M30 Y breaker low**, la desigualdad matemática long es `SL < min(EQ_M30, breaker_low)`, pero los niveles autor-concretos no estaban causalmente determinados. Esta historia se conserva para auditoría, NO impone fidelidad al nuevo QORE-alpha.
- Se implementaron verificadores independientes de M3/M15 y tests de anti-futuro: `src/qore/infrastructure/trader_lab/vt08_5m_a_native_m30_m3_favorable_entry_v1.py` y `vt08_5m_a_m30m3_h1_liquidity_swing_asof_verifier_v1.py`. CI [#38105786480](https://github.com/mezas3238-hue/qore-core/actions/runs/38105786480) 5/5 y 55 pruebas en verificación H1. Fuente/código PS-only es PROXY C, no promover como autentificación TTrades.

### 2.2. Falsación económica antigua — ÚTIL COMO LÍMITE, NO COMO SELECCIÓN NUEVA

- Preregistrado un ensayo QORE antiguo **una madre por fecha NY y mercado antes de conocer reversiones**. Se compararon dos formas contrafactuales sobre las mismas madres: entrada posicional C3.open con stop PS-only y target opuesto C1; limit en CISD previa, 10 barras M3 para fill/expiry, stop-first por ambigüedad.
- Run reproducible [#38160918903](https://github.com/mezas3238-hue/qore-core/actions/runs/38160918903), **6/6 SUCCESS**: 3.561 madres, posicional 3.561 fills OHLC hipotéticos, limit 1.818 fills y 1.743 no-fill. PF POS sin costes **0,9642**, con coste artificial 0,10R **0,7808**; PF LIMIT sin costes **0,8950**, con coste artificial 0,10R **0,7729**. Cero prueba BID/ASK física; no extrapolar DD R como DD % de cuenta.
- Reporte fuente: [VT08_A_M30M3_ECONOMIC_FALSIFICATION_NO_GO_PROXY_REPORT_2026-10-11.md](VT08_A_M30M3_ECONOMIC_FALSIFICATION_NO_GO_PROXY_REPORT_2026-10-11.md).
- Se dejó la misión única autor-fiel VT08 [#787](https://github.com/mezas3238-hue/qore-core/issues/787) con 3 resultados y [gate #38164147226](https://github.com/mezas3238-hue/qore-core/actions/runs/38164147226) de 17 tests, pero el **Owner la sustituyó** por el plan de QORE-alpha 96. No correr vieja familia como un experimento adicional ni mezclar resultados en el nuevo screening.

### 2.3. Cambio de mandato y congelación QORE-alpha V1

- Rama creada aparte: `research/qore-alpha-96-frozen-20261011`, PR DRAFT [#797](https://github.com/mezas3238-hue/qore-core/pull/797), issue [#798](https://github.com/mezas3238-hue/qore-core/issues/798). El trabajo previo VT08 permanece como referencia técnica histórica, sin merge.
- Prerregistro `docs/research/QORE_ALPHA_V1_96_FEATURE_SPACE_AND_STOP_RULE_PREREG_2026-10-11.md` fue creado **ANTES** de volver a medir PnL. Registro estable `docs/research/QORE_ALPHA_V1_FROZEN96_VARIANT_REGISTRY_2026-10-11.json`, 96 entradas desde `QALPHA-V001` a `QALPHA-V096`.
- Código de contrato (aún **no** motor de backtest de 96): `src/qore/infrastructure/trader_lab/qore_alpha_v1_frozen_96_decision_contract.py`. Lógica y tests `tests/infrastructure/trader_lab/test_qore_alpha_v1_frozen_96_decision_contract.py` para calendario NY, split fijo, PF estricto, DD/WR, elección de una ganadora, 3+ revisión y rechazo de variante 97.
- CI [#38170918767](https://github.com/mezas3238-hue/qore-core/actions/runs/38170918767) **SUCCESS 6/6, 15 tests de contratos**; manifiesto SHA256 `4332e07f4a8fbdf1125ecd004a70c4216b8ea1a60e954847eedfe3b362184891`.
- Se probó viabilidad de datos existentes 1095d y quedó acreditado que su M3 comienza 2023-09, **NO en 2022**. Test de consulta Jan2022 DEMO por GitHub [#38170626976](https://github.com/mezas3238-hue/qore-core/actions/runs/38170626976) FALLÓ por token OAuth `access token invalid and refresh failed` / error de autorización. Esto NO es demostración de que el proveedor NO conserve 2022. Otras ramas en el repositorio pudieron tener credenciales válidas después: volver a verificar hechos actuales antes de concluir credenciales caducadas globalmente.

### 2.4. Recuperación de fuentes originales de 2022 — CORRECCIÓN POSTERIOR

Se localizó el universo nativo **33 mercados M5** completado por otro equipo [QORE Native run #38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541), y CIBO Atlas original **12 mercados M5** [run #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458). Los primeros **cuatro** pares faltantes para QORE-alpha fueron descargados en el universo 33; **USDCAD** ya existía en CIBO original.

Se implementó verificador G0 research-only:
- `src/qore/infrastructure/trader_lab/qore_alpha_v1_five_existing_m5_source_reuse_gate.py`.
- `tests/infrastructure/trader_lab/test_qore_alpha_v1_five_existing_m5_source_reuse_gate.py`, **6 tests adversariales** (SHA falsificado, metadata manipulada, partición 2022 faltante, símbolo fuera del universo).
- Workflow `.github/workflows/qore-alpha-existing-five-2022-m5-source-g0.yml` que descarga **exactamente** los cinco artefactos origen de GitHub y compara el archivo `RAW_M5_LEDGER/2022.jsonl` y `2023.jsonl` con cada huella original de `PARTITION_MANIFEST/*.sha256`.
- Resultado: [CI #38259002749](https://github.com/mezas3238-hue/qore-core/actions/runs/38259002749) **SUCCESS 5/5**, commit ensayado `c359fddb0628d351427c4f7c8245fc1b7ec6327c`. Recibos archivados 90 días; las fuentes originales completas están en Actions, **no** se commitearon millones de velas al repo.
- Informe de prueba: [QORE_ALPHA_V1_2022_EXISTING5_M5_SOURCE_G0_SHA_VERIFIED_2026-10-12.md](QORE_ALPHA_V1_2022_EXISTING5_M5_SOURCE_G0_SHA_VERIFIED_2026-10-12.md).

| Mercado congelado | Run original | Artifact ID original | M5 2022 | M5 2023 | RAW 2022 SHA256 |
|:--|--:|--:|--:|--:|:--|
| EURJPY | 38193802541 | 11723592292 | 74.529 | 74.510 | `5eb3da3b30858873d3264a49c01990e1073d271802aad5bd78dbdc421dcb7767` |
| USDCHF | 38193802541 | 11722633876 | 74.466 | 74.431 | `b9b7f49997ce25b926a1aac205ea2221b8be657a9c0b4e399aabe414f9c1ba74` |
| NZDUSD | 38193802541 | 11723435593 | 74.524 | 74.431 | `37e841d85af830bfd2db0c697ca4804ff4019ed1557746a91744b5a7c5e9f107` |
| CADJPY | 38193802541 | 11726771423 | 74.526 | 74.495 | `2bbd280bf576e091e3e14f4ec7b2c2465aaf5d71ce2e2787950f954f52093566` |
| USDCAD | 35166210458 | 10475972108 | 74.534 | 74.455 | `9a91cbbd883ba3b204c1b6da60097f6938c3f0157a0e2beaea1e0ea0cb582794` |
| **TOTAL** | | | **372.579** | **372.322** | |

Recibos verificación G0 Actions #38259002749: EURJPY `11751911066`, USDCHF `11751867153`, NZDUSD `11751426987`, CADJPY `11751607263`, USDCAD `11751112747`. Apertura primer M5 del año 2022 `2022-01-02T23:00:00Z` y última `2022-12-30T21:55:00Z` en todos los pares. `CLEAN_PROVIDER_PAYLOAD` y SHA original ≠ verificación completa de cada tramo horario del calendario (faltantes/gaps aún deben auditarse).

**Advertencia gravísima:** la presencia en GitHub de 2022 M5 **no** significa disponer de 2022 M3. Reconstruir M15 desde M5 es posible cuando hay ternas consecutivas; **M3 desde M5 es matemáticamente imposible** sin ticks/M1 originales. Nunca interpolar 3 minutos ni etiquetar M5 como M3 para hacer que pase el programa 96.

---

## 3. Especificación congelada — LO QUE NO DEBE CAMBIARSE

Patrón base fijo: `M30_SINGLE_SWEEP_C2_CLOSURE` (C2 barrida solo un lado de C1 y cierre de reversión, fuera doble sweep) + `M3_CISD_PROTECTED_SWING_CLOSED_BEFORE_C3`. Investigación **QORE-C**, no certificación del autor. Ambas direcciones según preregistro (a diferencia de VT08 FINAL #1 antiguo, que era solo long). Se requiere una sola madre predecisión por mercado/día NY **por variante**, sin condicionar selección a retests futuros, profit ni reward observado.

| Factor | Opciones SIN AGREGADOS | Cantidad |
|---|---|---:|
| Entrada | `POSITIONAL_C3`, `CISD_RETEST` | 2 |
| Sesión | `ASIA`, `LONDON`, `NEW_YORK` | 3 |
| Stop | `PS`, `EQ_M30`, `BREAKER`, `ATR_X1` | 4 |
| Target | `R1`, `R2`, `R3`, `EXTERNAL_LIQUIDITY` | 4 |
| **Total** | IDs V001→V096 | **96** |

Sesiones por hora de **C3.open** en zona `America/New_York` y DST: Asia **19:00–00:00** (se representa por horas 19,20,21,22,23 del día NY), Londres **02:00–05:00**, NY **08:00–11:00**, extremos finales excluidos. El dataset anterior VT08 únicamente tomó 01:00–13:00: **NO reciclar sus listas filtradas para Asia**. Leer los M3 crudos completos.

Stops:
- PS: extremo M3 protegido conocido antes C3.
- EQ: `(C2.high+C2.low)/2`, geometría QORE C.
- BREAKER: patrón secuencial M3 QORE C definido en prerregistro, **no** autor-verdadero.
- ATR×1: Wilder ATR(14) sobre M30 completas previas a C3, exige true range con cierre previo; **no** ATR con vela C3 futura.
Targets:
- 1R, 2R, 3R definidos ex ante usando riesgo actual de cada variante.
- EXTERNAL: high/low de sesión/día anterior según definición fija del preregistro; requiere nivel **untouched** al instante de orden. No seleccionar el mejor target tras ver recorrido de C3.
Entrada:
- POS al primer M3.open dentro de C3.
- CISD_RETEST orden predeclarada al nivel conocido antes C3, expira en 10 M3, con NO-FILL correctamente contabilizado. OHLC sin secuencia intrabar ⇒ stop-first/peor caso y evento `AMBIGUOUS_TOUCH`.
- Nunca operar con capital; **96 backtests puramente contrafactuales**, no 96 órdenes.

## 4. Segmentos y gates — exactos y no negociables

| Segmento | Desde NY (inclusive) | Hasta NY (exclusivo) |
|---|---|---|
| TRAIN | 2022-01-01 | 2024-07-01 |
| VALIDATE | 2024-07-01 | 2025-07-01 |
| INTERNAL_TEST | 2025-07-01 | 2026-07-01 |
| HOLDOUT 7Y | SEALED | NO ACCESO |

Requisitos TRAIN: PF bruto **>1,40**, al menos **50 operaciones/fills** por variante. VALIDATE: PF bruto **>1,30**, **≥25 fills**. Ambos max drawdown **<20%**, con riesgo simulado predefinido **0,1% del equity** y control de simultaneidad, y diferencia de win rate Train↔Validate **≤0,15 absoluto (15 puntos porcentuales)**. Aplicar en los cinco mercados congelados, jamás eliminar alguno por rendimiento.

Si **0 pasan** ⇒ `NO_PASS_STOP_FEATURE_SET` y se **descarta el feature set**; no añadir filtros a estas mismas señales. Si pasan **1–2**, escoger **UNA** por mayor `VALIDATE PF`, empate menor ID. Si pasan **3 o más**, `THREE_PLUS_PASS_SPLIT_REVIEW_REQUIRED`: inspeccionar datos/split/correlaciones **sin mirar test ni re-rankear**, hasta auditoría. Una sola ganadora entra INTERNAL_TEST: **PF bruto ≥1,20** ⇒ pasar a 3 meses PAPER real prospectivo, si PF<1,20 ⇒ cierre. PAPER requiere PF **neto >1,20** durante **3 meses** con costes verificables; solo después **autorización expresa** para programa real hipotético de 0,1% riesgo por entrada (esta rama NO autoriza operación real).

**Corrección estadística:** `PF Train 1,40` es un umbral heurístico del Owner, **NO un Bonferroni estadístico**. En 96 contrastes la cota familiar `α=0,05` implicaría `α_i=0,05/96≈0,0005208333` para p-values calculados bajo hipótesis formal y dependencia temporal controlada. No afirmar “significancia Bonferroni alcanzada” usando únicamente PF 1,40. El protocolo congela PF y debe publicar esta limitación.

## 5. Problemas detectados — prioridad/causa/acción demostrable

### P0-A · **M3 auténtico 2022 a septiembre 2023 ausente en fuentes habilitadas examinadas**

**Síntoma:** GH M3 para 5 pares de #35941643396 comienza 2023-09-24. Fuente M5 antigua está ahora recuperada 2022/2023. **Causa:** diferentes temporalidades y extensión de archivo, no pérdida completa de datos FX.

**Instrucción concreta siguiente arquitecto:** buscar en GitHub Actions y ramas QORE Native (33 assets), CIBO, Scalper, London y Trader Lab **M1 o M3 genuinos** por exactamente EURJPY, USDCHF, NZDUSD, CADJPY y USDCAD, desde enero 2022. Inspeccionar artifact schema, timestamps, símbolos, provenance, hashes, si es fuente de entrenamiento o **reservada/sellada**. **No consumir 7Y sealed ni deducir autorización de que el artefacto sea visible.** Puede existir M1 en otra investigación posterior: esta revisión no lo ha certificado, por eso el diagnóstico es `NOT_VERIFIED`, no `DOES_NOT_EXIST`.

- Si existe M1 nativo auténtico, agregar **exactamente tres M1 consecutivas** a M3 OHLC: `open=primer.open`, `high=max`, `low=min`, `close=último.close`; comprobar UTC boundary, sin barras sintéticas, duplicados, huecos, feed, DST, y conservar nivel de primer/último timestamp y SHA.
- M15 puede reconstruirse con **3 M5 auténticas consecutivas** y auditarse contra M15 independiente si disponible. M30 con 10 M3 cerradas o 6 M5 cerradas, compare checksums/valores solo cuando existen fuentes separadas.
- Si no hay M1/M3 suficiente, investigar read-only **cTrader DEMO** con nuevos secretos válidos GitHub (sin revelarlos), u otra fuente autorizada de M1/tick 2022 (sin capital, VPS, holdout o licencia no aprobada). No lanzar 96×3 mientras falte M3.

**Criterio de salida:** datos 5/5 de todos los segmentos con cobertura/retenciones, SHA de fuentes, faltantes/sessions auditados, reproducibilidad 100%; no significa ya probar edge.

### P0-B · **BID/ASK, spread, comisión, slippage por orden NO certificados para 2022-2026**

Los RAW_M5_LEDGER contienen OHLC y metadatos de trendbars, **no historial físico suficiente de BID/ASK/ticks de cada entrada/stop**. El coste 0,10R de antigua falsación era **escenario hipotético**, nunca costes reales.

**Siguiente:** localizar dataset BID/ASK (tick/M1 bid ask) y condiciones IC Markets DEMO y del instrumento/fecha; validar timezone, símbolos, cotizaciones de apertura, orden SL/TP intrabar, comisiones por lote, conversiones de FX, min tick, volumen, deslizamiento y gaps. Asegurar que no se use barras midpoint/mid-ohlc como si fueran fills broker. Preinscribir fórmula única y documentar si son costes conservadores modelizados. **No prometer PnL neto “real” sin prueba de estos inputs.**

### P0-C · **Implementación económica completa de 96 aún NO EXISTE como suite end-to-end**

Está creado **generador/manifest/selector de ganadora** y tests de gates, además de un motor económico ANTIGUO de 2 modalidades PS-only **NO comparable**. No se ha implementado ni verificado la ejecución de las 96 sobre los tres segmentos con todos los stops, targets y sesiones específicos. Reusar utilidades de timestamps, CISD/PS y runner ultra fast de Trader Lab cuando sea compatible, pero **no pasar como resultado nuevo los 3.561 old trials**.

**Siguiente:** añadir runner determinista para EXACTAMENTE registro JSON, controles por cada variante, ejecución sobre native M3 con B/A y fees, sin tuning. Separar constructora de señal (sólo historia disponible en C3.open), simulador de ejecución (datos futuros solo DESPUÉS de anclar entrada), métricas por split, selector de ganador que NO puede leer test anticipadamente. Test adversarial de stop-first, partial no-fill, DST, HHMM split, dup/truncation, calendar missing, 97th variant, status failclosed, costes, drawdown portafolio y sesgo de selección.

**Criterio de salida:** 96/96 reproducidas en Train y Validate con recibo independiente por símbolo, split, semilla (si alguna), SHA y firma del manifiesto, **0 leakage**, sin leer Test hasta una sola selección.

### P0-D · **Auditoría de significancia múltiple/muestras y determinación de edge**

No tratar `PF>1.40` como p-valor ajustado. Los 96 son correlacionados y cinco mercados correlacionados por FX. Si se calcula intervalo de confianza/p-value, predefinir método apropiado para dependencia temporal y familia de pruebas **antes de revisar PnL nuevo**; no alterar los PF threshold. Rechazar win rate poco robusto, DD de perfil sin simultaneidad, “mejor PF” elegido después de ver test. En la documentación final distinguir **PF bruto**, **PF neto**, **nº fills**, **no fills**, **potencia**, **sesgo de costes**, **criterio de parada**.

### P1-E · **Credenciales cTrader DEMO fallo registrado, pero posiblemente ahora cambiaron**

[#38170626976](https://github.com/mezas3238-hue/qore-core/actions/runs/38170626976) no obtuvo 2022 M3 por token inválido / fallo refresh. Más tarde otras ramas del repo sí descargaron M5 de 2022; ello prueba que ciertas credenciales/caminos cTrader **funcionaron para M5**, NO que hayan dado M3 o que esta rama tenga autorización válida. Prioridad: usar los originales archivados, luego resolver OAuth read-only si todavía hace falta. Nunca exponer secretos ni saltar DEMO→LIVE.

### P1-F · **Dependencia GitHub Actions, expiración, bitácoras y protección de sellos**

Los ZIP de GH Actions tienen retención acotada. Guardar **en repo** hashes, URL/run/artifact-ID, schema, código exacto, verificadores, y un inventario inmutable de provenance antes de caducar. Conservar nombres fuente originales y no sustituir por resúmenes E1. Verificar que los archivos extraídos en nuevos runs coincidan con SHA del productor y que el holdout 7Y de VT08 no haya sido empleado. No publicar credenciales, datos privados ni código a rama de producción.

## 6. Propuesta de ejecución paso a paso para el próximo arquitecto (orden obligatorio)

**ETAPA 0 — Congelación preservada:** leer los cuatro documentos encabezados; consultar [#798](https://github.com/mezas3238-hue/qore-core/issues/798) y [#797](https://github.com/mezas3238-hue/qore-core/pull/797). Verificar manifest SHA `4332e07f4a8fbdf1125ecd004a70c4216b8ea1a60e954847eedfe3b362184891` y JSON 96 sin alteraciones. Prohibido añadir variantes. Reproducir CI [#38170918767](https://github.com/mezas3238-hue/qore-core/actions/runs/38170918767) y [#38259002749](https://github.com/mezas3238-hue/qore-core/actions/runs/38259002749). Reportar **G0 PASSED M5; NOT PASSED M3 & costs**.

**ETAPA 1 — Censo M1/M3 2022-2023:** buscar GitHub Actions artifact index/commit docs en todas las ramas nombradas, clasificar temporalidad, cobertura real, licencia/holdout, fuente y SHA por los cinco pares. Crear informe `M1_M3_G0_SOURCE_DISCOVERY` sin resultados PnL. Si no hallazgo, registrar BLOQUEADO y activar ruta read-only DEMO u origen externo autorizado, sin falsear el split.

**ETAPA 2 — Auditoría datos/costes:** reconstruir M3 a partir de M1 auténtico SOLO si se demuestra 3×M1 contiguous; usar M5 original como **testigo M15/M30**, no como sustituto de M3. Verificar tick/BID/ASK, spread/commission, topología de ventanas C3, timezone NY; cerrar QA por hash/cobertura. Si fallan → `BLOCKED_DATA_COVERAGE` o `BLOCKED_COST_EVIDENCE`, 0 resultados económicos.

**ETAPA 3 — Backtester 96:** usar código del manifiesto como ÚNICA fuente del factorial. Ex ante seleccionar primera madre por sesión/día/mercado según contrato, implementar todos stops y targets, pruebas adversariales no-leak, CI matrix five markets, strict set of 96, recibo completo por variante y segmento. No resultados que seleccionen parámetros antes de congelar el motor.

**ETAPA 4 — TRAIN y VALIDATE SOLAMENTE:** aplicar criterios PF >1,40 / >1,30, N≥50/25, DD<20% y WR diferencia≤15pp. Documentar excluidas con razón, 0 pasa ⇒ STOP permanente del feature set. ≥3 pasa ⇒ revisión de integridad antes de autorizar test. Máximo una ganadora por Validate PF, empate ID, sin acceder Test.

**ETAPA 5 — INTERNAL_TEST de UNA ganadora:** ventana 2025-07→2026-06; PF gross ≥1,20 ⇒ PAPER durante 3 meses prospectivos; <1,20 ⇒ NO-GO para QORE-alpha v1. No reabrir train/validate ni retocar stops.

**ETAPA 6 — Paper prospectivo:** 3 meses con precios nuevos, ejecución simulada BID/ASK y fees medidos, PF net >1,20; sin excepción/reinicio y sin pedidos de real/vps durante papel. Tras pasar, elevar petición explícita de programa riesgo 0,1%: **este handoff NO autoriza LIVE**.

**ETAPA 7 — Dictamen final y cierre:** publicar GO/NO-GO/BLOCKED con evidencia, hashes, PF/WR/DD/N/costes y límites; enlazar issue #798 y PR #797; no mezclar histórico antiguo VT08 ni usar sellos 7Y.

## 7. Matriz de fuentes y archivos importantes (ruta precisa)

| Recurso | Ruta / referencia |
|---|---|
| Soberano | `mezas3238-hue/qore-core` |
| Rama | `research/qore-alpha-96-frozen-20261011` |
| PR / Issue | [PR #797](https://github.com/mezas3238-hue/qore-core/pull/797) · [Issue #798](https://github.com/mezas3238-hue/qore-core/issues/798) |
| Prerregistro | `docs/research/QORE_ALPHA_V1_96_FEATURE_SPACE_AND_STOP_RULE_PREREG_2026-10-11.md` |
| Registro 96 | `docs/research/QORE_ALPHA_V1_FROZEN96_VARIANT_REGISTRY_2026-10-11.json` |
| Código gates | `src/qore/infrastructure/trader_lab/qore_alpha_v1_frozen_96_decision_contract.py` |
| Tests gates | `tests/infrastructure/trader_lab/test_qore_alpha_v1_frozen_96_decision_contract.py` |
| Workflow 96 + cobertura M3 previa | `.github/workflows/qore-alpha-frozen96-source-coverage-v1.yml` |
| Fuente M5 G0 verificador | `src/qore/infrastructure/trader_lab/qore_alpha_v1_five_existing_m5_source_reuse_gate.py` |
| Tests M5 G0 | `tests/infrastructure/trader_lab/test_qore_alpha_v1_five_existing_m5_source_reuse_gate.py` |
| Workflow M5 G0 | `.github/workflows/qore-alpha-existing-five-2022-m5-source-g0.yml` |
| Reporte M5 + hashes | `docs/research/QORE_ALPHA_V1_2022_EXISTING5_M5_SOURCE_G0_SHA_VERIFIED_2026-10-12.md` |
| Reporte caveat OAuth + cobertura | `docs/research/QORE_ALPHA_V1_FROZEN96_VERIFIED_SOURCE_COVERAGE_AND_AUTH_BLOCKERS_2026-10-11.md` |
| Intento Jan2022 M3 DEMO | `.github/workflows/qore-alpha-2022-demo-m3-feasibility-probe-v1.yml`, run #38170626976 (FAIL auth) |
| Consumer CIBO RAW M5 | `src/qore/infrastructure/trader_lab/cibo_market_atlas_10y_m5_consumer_v1.py` |
| Fuente original USDCAD 10Y M5 | [Actions #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), artifact `10475972108` |
| Fuente original 4 pares nuevos 10Y M5 | [Actions #38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541) |
| CI 96/15 tests | [Actions #38170918767](https://github.com/mezas3238-hue/qore-core/actions/runs/38170918767) |
| CI 2022 M5 SHA 5/5 | [Actions #38259002749](https://github.com/mezas3238-hue/qore-core/actions/runs/38259002749) |
| CI prototipo anterior NO-GO | [Actions #38160918903](https://github.com/mezas3238-hue/qore-core/actions/runs/38160918903) |
| Reporte NO-GO antiguo | `docs/research/VT08_A_M30M3_ECONOMIC_FALSIFICATION_NO_GO_PROXY_REPORT_2026-10-11.md` |
| Manifiesto de prueba antiguo TTrades (SUPERSEDED) | `docs/research/VT08_A_FINAL_ONE_FAMILY_AUTHOR_FIDELITY_FROZEN_TRIAL_PREREG_2026-10-11.md` |

## 8. Tests mínimos y controles de aceptación del siguiente arquitecto

- **Integridad de fuentes:** SHA256 RAW vs productor original, 5 mercados, timestamps 2022/2023, upstream 33 M5; ningún archivo de periodo reservado.
- **Temporalidad:** los M3 usados tienen **origen M3 o M1 real** (nunca repartos M5), ventanas de exactamente 3×M1 cuando aplique, 10×M3→M30 y 3×M5→M15, DST y sesiones NY, sin mirar 2026-07 para train/validate.
- **Causalidad:** un `CandidateEvent` de C3.open solo usa datos cerrados antes C3.open; series M3 CISD/PS correctas; target de liquidez externa intacto conocido as-of; orders limit no-fill evaluados sin escoger ex-post retest.
- **Ejecución:** BID/ASK y comisiones físicamente fundamentadas o BLOQUEO claro; stop-first si OHLC ambiguo; RR bruto y neto diferenciados.
- **Múltiples hipótesis:** exactamente 96 (ni 95 ni 97), un solo ganador por Validate PF, diferencia WR≤0,15, DD<20% (equity simulator 0,1%), ninguna optimización posthoc; bandera `PF_1_40_IS_NOT_BONFERRONI_ADJUSTMENT`.
- **Separación de datasets:** TRAIN→VALIDATE→INTERNAL_TEST estricto. El runner de validación no puede leer INTERNAL_TEST antes de congelar `winner_id`, hash, código y fuente. HOLDOUT/VPS/LIVE jamás.
- **Economía:** resultado `BLOCKED` si faltan datos. Un PF no disponible **no es PF=0 ni NO-GO**. El anterior PF negativo de QORE PS-only es un experimento distinto y **no cuenta como una de las 96 pruebas nuevas**.

## 9. Lo que está expresamente prohibido

**NO MERGE sin orden**, no auto LIVE ni FundedNext LIVE, no VPS, no utilizar capital real, no reabrir holdout sellado 7Y, no filtrar mercados después de conocer resultados, no p-hacking, no 97.ª variante, no estimar M3 desde M5, no convertir spreads 0,10R hipotéticos en evidencia física, no confundir “sello GitHub SUCCESS” con “estrategia rentable”, no incorporar reglas autor-verdaderas por obligación de fidelidad al viejo VT08, no publicar secretos. Si los datos actuales NO permiten el protocolo, reportar BLOQUEADO y detener test económico en lugar de alterar el plan.

## 10. Mensaje al siguiente arquitecto — orden ejecutiva

> Tu tarea ya NO es reconstruir fielmente VT08/TTrades. La metodología v1 QORE-alpha y su espacio de 96 opciones están congelados. Debes primero **encontrar temporalidad nativa M1/M3 de 2022 para cinco mercados y BID/ASK/costes**, dentro de fuentes GitHub/autorizadas no selladas; demostrar hashes y fechas, nunca inventar velas. Los cinco historiales M5 de 2022 ya fueron verificados el 12-oct (no repetir descargas salvo fallo SHA). Luego construir el runner 96 exacto en Trader Lab, validar Train+Validate, seleccionar máximo una ganadora y solo entonces el INTERNAL_TEST. Tu éxito se mide por una **decisión económica reproducible con criterio de parada**, no por más geometrías o documentación. Si falta evidencia esencial, entregar BLOCKED bien probado. Comunicar progresos reales en [issue #798](https://github.com/mezas3238-hue/qore-core/issues/798), no esperar al Owner para pedir instrucciones que ya constan en este documento.

**Estado al cierre del presente handoff (13-oct-2026):** `M5_2022_2023_5_OF_5_SHA_VERIFIED / M1_M3_2022_NOT_VERIFIED / EXECUTION_COSTS_NOT_VERIFIED / 96_PREREG_FROZEN / 0_OF_96_BACKTESTED / 7Y_VPS_LIVE_UNTOUCHED`.  

**NO confundir con GO, NO-GO o cierre científico:** aún no existe suficiente evidencia para ejecutar el protocolo congelado. Este handoff sí cierra el contexto y transfiere los trabajos pendientes sin perder decisiones anteriores.
