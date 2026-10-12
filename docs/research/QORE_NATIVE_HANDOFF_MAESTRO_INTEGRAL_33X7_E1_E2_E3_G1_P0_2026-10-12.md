# QORE NATIVE — HANDOFF MAESTRO INTEGRAL PARA EL SIGUIENTE ARQUITECTO
**Corte de evidencia: 12 de octubre de 2026. Estado: investigación, NO producción.**

> **LEER PRIMERO.** Este es el punto único de reanudación de QORE Native. Consolidación operativa nueva; **no sustituye ni reescribe** el registro de descubrimientos original [handoff #841](https://github.com/mezas3238-hue/qore-core/pull/841) ni el [addendum fuente G1 #855](https://github.com/mezas3238-hue/qore-core/pull/855). Los tres se complementan. Las referencias externas y los artefactos Actions citados pueden caducar. Las PR de investigación son DRAFT y no constituyen integración al producto.

## 0. Resumen ejecutivo, veredicto honesto y misión

**Misión del propietario:** construir **tres traders QORE Native originales** a partir de investigación del comportamiento del mercado en 33 activos, con metodología y —en fases posteriores— razonamiento cognitivo propios; robustez financiera comprobada antes de certificar. No copiar mecánicamente un método de un autor ni alterar las reglas viendo resultados. El uso de Trader Lab / Ultra Fast Runner es permitido **únicamente como infraestructura de investigación reproducible**.

**Estado innegociable** al entregar:
- **G0 33/33**: 24.377.420 barras históricas M5 auditadas por fuente/manifest/SHA, no todas de una misma cuenta históricamente homologada.
- **E1 7 metodologías × 33 mercados = 231 celdas gross** ejecutadas. Holm FWER 5%, BH FDR 5/10% y E3 bootstrap correlacionado **no demuestran edge positivo robusto y replicado**. No transformar «no demostrado» en «rentable» ni en «estrategia universalmente imposible».
- **373.611 eventos E1** son registros de investigación método×instrumento×fecha, altamente solapados, **NO 373.611 ejecuciones ni observaciones independientes**.
- **G1 BID/ASK**: auténticos datos históricos cTrader IC Markets DEMO disponibles en ventanas cortas; decodificación original Protobuf de delta de tiempo/precio auditada; as-of causal y cuarentena zero/stale validados. **NO existe histórico continuo BID/ASK 33×10 años, no hay ejecución real ni backtest NET validado**.
- **12/12 instrumentos CIBO originales**: nombre+ID de proveedor G0/G1 concuerdan a lo largo de 132 particiones anuales; además dígitos/pipPosition G0 coinciden con las **12 fichas actuales IC Markets DEMO**. Esto **NO verifica que la cuenta CIBO original fuese la cuenta actual ni que los contratos económicos de 2016–2024 sean idénticos**. **0/12 EXACT_CONTRACT**.
- **0/3 traders certificados**; no constan profit factor, Sharpe, Sortino, drawdown ni rentabilidad NET comprobados para certificar ninguno. No inventarlos.
- **PROHIBIDO** tocar, desplegar o operar en **VPS, MT5, LIVE, CIBO, Shared o QDLE**, o desbloquear órdenes o dinero real. Trabajo SOLO GitHub / ramas de investigación / Actions. Holdout económico desde **2024-09-17** bloqueado.

**Criterio de éxito de esta transición:** que el siguiente arquitecto pueda seguir con trazabilidad de fuente, corregir P0 y, solo tras suficiente evidencia, plantear una nueva hipótesis económica genuinamente preregistrada y certificable. El número de capturas, tests PASS o IDs iguales **no** es una prueba de rentabilidad.

## 1. Enlaces canónicos, ramas, SHA y relaciones

| Documento / bloque | Rama o enlace | Uso |
|---|---|---|
| Handoff original de métodos y G0-E3 | [PR #841](https://github.com/mezas3238-hue/qore-core/pull/841), rama **research/qore-native-master-handoff-33x7-bidask-e3-20261012**, HEAD congelado **ba64abffd8f74d8c1b5975014234790f4b3e6543** | Origen G0, ADR-002, E1/E2/E3, resultados negativos |
| Handoff incremental cronológico G1 | [PR #855](https://github.com/mezas3238-hue/qore-core/pull/855), rama **research/qore-native-master-handoff-g1-33-sources-addendum-20261012** | 14 capítulos anteriores con pilotos, QA, identidades |
| **Este documento maestro** | **docs/research/QORE_NATIVE_HANDOFF_MAESTRO_INTEGRAL_33X7_E1_E2_E3_G1_P0_2026-10-12.md**, en rama de #855 | Referencia de continuidad con TODOS los pendientes |
| Original E1/E2 231 gross | [PR #832](https://github.com/mezas3238-hue/qore-core/pull/832) [Actions #38257207836](https://github.com/mezas3238-hue/qore-core/actions/runs/38257207836), E1 source head **dfe78f115957a40f4188c30e78bd7f88c2ce6c42** | Reglas/artefactos originales, conservar inmutables |
| G0 SHA de universo de 33 | **1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85** | Validación de origen, no SHA de todos los ZIP |
| G0 12 Atlas CIBO original | [Actions #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), head **ab782b8e9f890f86a2b6500070f0556b4b685e3d** | Metadatos históricos originales y SHA por partición |
| E1 33 ZIP originales firmados | [Actions #38257207836](https://github.com/mezas3238-hue/qore-core/actions/runs/38257207836) | 33 testigos originales, NO PnL NET |
| G1 cobertura 33×7 source-only | [PR #867](https://github.com/mezas3238-hue/qore-core/pull/867), Actions [#38297791677](https://github.com/mezas3238-hue/qore-core/actions/runs/38297791677) y [#38298193812](https://github.com/mezas3238-hue/qore-core/actions/runs/38298193812) PASS | Ledger y presupuesto de shards |
| G0↔G1 ID original12 | [PR #869](https://github.com/mezas3238-hue/qore-core/pull/869), [Actions #38303158752](https://github.com/mezas3238-hue/qore-core/actions/runs/38303158752) PASS | Identidad histórica de proveedor, NO equivalencia económica |
| Especificaciones DEMO actuales 12 | [PR #870](https://github.com/mezas3238-hue/qore-core/pull/870), [Actions #38303807686](https://github.com/mezas3238-hue/qore-core/actions/runs/38303807686) PASS | Snapshot ACTUAL read-only, jamás tarifas retrospectivas |

**ATENCIÓN DE GIT:** PR #855 depende documentalmente de #841. #867, #869, #870 y otras PR de fuente son ramas **distintas** con bases encadenadas entre ramas research, no código automáticamente presente en la rama del handoff. Leer los archivos en **la rama HEAD de cada PR**, no en main ni asumidos mergeados. No realizar merge de toda la pila en producción.

## 2. Arquitectura científica: G0 → E1 → E2/E3 → G1 → certificado

**G0, identidad de fuente:** verifica barras originales M5 por instrumento, cuenta/familia/proveedor y SHA. Universo original en **src/qore/infrastructure/trader_lab/qore_native_universe_33_source_registry_v1.py**; fuente del atlas CIBO y 21 nuevos mercados IC Markets; 33 M5 / 24.377.420 barras. Histórico de los doce originales y archivos M1 separados; **M1 no es BID/ASK**. Está prohibido fabricar M1 desde M5 o atribuir a todos idéntico contrato.

**ADR-002/E1, estudio gross**: siete reglas congeladas antes de las nuevas salidas, baselines emparejados, calendarios UTC/DST y 33 instrumentos. Motor **src/qore/infrastructure/trader_lab/qore_native_e1_33x7_seven_gross_per_market_v1.py**, registro **qore_native_33x7_method_market_registry_v1.py**. Horizonte teórico M5: **OPEN_INITIAL_REACTION 15 minutos; SWEEP_RECLAIM/RANGE_BREAK_CONT/POST_OPEN_CONT 120 minutos; REVERSAL_12H/PERSISTENCE_12H/TREND_MULTI_DAY 240 minutos**. Estos nombres no deben leerse como tenencia horaria de ejecución demostrada. Los timestamps **reference_entry_utc** representan un reloj de oportunidad de investigación y pueden no ser tiempos de orden colocable: verificar disponibilidad de barra cerrada y señales sin futuro antes de inferir trading.

**E2, inferencia por celda y dependencia:** 231 tests, diferencia delta = gross del método menos baseline matched gross; Holm 5% y sensibilidad BH FDR 5/10%. **5 nominales positivos en DEV y 2 en DIAG a p≤0,05, CERO celdas coincidentes positivas replicadas**; Holm/BH no desbloquean edge positivo robusto. No practicar HARKing usando DIAG o el archivo de outcomes para elegir 45 ejemplos.

**E3, dependencia temporal/modelo:** bootstrap conjunto por semanas con bloques 1,2,4 semanas y 4.000 draws sobre siete familias, igual peso por mercado; **0/7 familias** con gross y delta positivos replicados. Desarrollo 2016-09-17→2022-09-17; diagnóstico 2022-09-17→2024-09-17 (ya expuestos); tiempo desde 2024-09-17 **embargado para economía y certificación nueva**. La corrección Holm puede ser conservadora, pero la alternativa FDR tampoco detectó un edge replicado y no se debe relajar ex post hasta «encontrar» ganancias.

**G1, verdad de lado de cotización:** quote native historical BID y ASK desde **ProtoOAGetTickDataReq** por separado. Primer tiempo/precio absolutos, después deltas **signed de tiempo y de precio acumulados**; verificar **hasMore**, framing de campo original, orden de eventos 1 ms, número entero native / 100.000 y SHA de manifest. Pareo **last-known-side at or before** instante: BID y ASK ambos presentes, **edad individual ≤5.000 ms** en pruebas de QA, ASK>BID estrictamente; zero/stale/missing/crossed/ambigüedad de orden => **cuarentena, no cotización gratis**. El tope 5s es prueba de calidad fuente, **NO tolerancia demostrada de fill**.

**Frontera de ejecución:** LONG compra ASK/vende BID; SHORT vende BID/compra ASK, pero solo después de una secuencia realista causal de señal→orden→ejecución→salida y contratos, tamaño/lote/moneda, spreads en ambos lados, comisión ida-vuelta, slippage, swap/financiación, horarios y noticias point-in-time. E1 gross de barra **no proporciona** stops, fill ni condiciones de cierre ejecutables. No calcular PF, Sharpe, Sortino o MaxDD NET antes de esta frontera.

**Cognitivas y tres traders:** son objetivo de diseño FUTURO, **no se certificó ni implementó aquí una cognitiva de producción**. Separar futuro software en: sensor de mercado causal, estado/cambio de régimen, decisión de estrategia y abstención, control de riesgo y órdenes, explicación/replay, observabilidad auditada. No conectar QORE Native a CIBO/Shared ni tomar prestadas cognitivas sin contrato y permiso de producción. Diseñar las tres metodologías diferenciadas SOLO tras evidencia nueva o revisión explícita de falsación.

## 3. Universo congelado y cohortes — 33 activos

| Familia | Símbolos |
|---|---|
| Índices (3) | NAS100, SP500, US30 |
| Metales (2) | XAUUSD, XAGUSD |
| Mayores (7) | AUDUSD, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF, USDJPY |
| Cruces (21) | AUDJPY, AUDCAD, AUDCHF, AUDNZD, CADCHF, CADJPY, CHFJPY, EURAUD, EURCAD, EURCHF, EURGBP, EURJPY, EURNZD, GBPAUD, GBPCAD, GBPCHF, GBPJPY, GBPNZD, NZDCAD, NZDCHF, NZDJPY |

**12 M5 originales CIBO Atlas:** AUDJPY, AUDUSD, EURUSD, GBPJPY, GBPUSD, USDCAD, USDJPY, NAS100, SP500, US30, XAUUSD, XAGUSD; resto 21 nuevas fuentes IC Markets DEMO. No confundir 33 M5 recopilados con identidad económica histórica homogénea; NAS100→USTEC y SP500→US500 solo aliases de proveedor validados por ID.

## 4. Registro COMPLETO de las investigaciones realmente ejecutadas

| Trabajo | Evidencia Actions/PR | Resultado medido — estatus |
|---|---|---|
| G0 M5 33 y SHA | [#829](https://github.com/mezas3238-hue/qore-core/pull/829) [run #38207337960](https://github.com/mezas3238-hue/qore-core/actions/runs/38207337960) | 33, 24.377.420 M5 |
| Ensayos exploratorios anteriores | PR [#822](https://github.com/mezas3238-hue/qore-core/pull/822) [#825](https://github.com/mezas3238-hue/qore-core/pull/825) [#827](https://github.com/mezas3238-hue/qore-core/pull/827) [#830](https://github.com/mezas3238-hue/qore-core/pull/830) | 4 bloques sin soporte económico |
| E1/E2 7×33 | [#832](https://github.com/mezas3238-hue/qore-core/pull/832) [run #38257207836](https://github.com/mezas3238-hue/qore-core/actions/runs/38257207836) | 231/231 pruebas gross; Holm sin positivo replicado |
| Sensibilidad BH FDR | [#834](https://github.com/mezas3238-hue/qore-core/pull/834) [run #38260058465](https://github.com/mezas3238-hue/qore-core/actions/runs/38260058465) | 0 positivos ajustados replicados |
| E3 bloques temporales | [#836](https://github.com/mezas3238-hue/qore-core/pull/836) [run #38262585848](https://github.com/mezas3238-hue/qore-core/actions/runs/38262585848) | 0/7 familias positivas robustas |
| Fotos BID/ASK puntuales | [#839](https://github.com/mezas3238-hue/qore-core/pull/839) [run #38265563869](https://github.com/mezas3238-hue/qore-core/actions/runs/38265563869) | 33 snapshots actuales; NO spread histórico |
| G1 pre quote causal | [#842](https://github.com/mezas3238-hue/qore-core/pull/842) [run #38271254152](https://github.com/mezas3238-hue/qore-core/actions/runs/38271254152) | SHA y as-of; 16/16 tests |
| G1 NZDUSD BID/ASK real | [#844](https://github.com/mezas3238-hue/qore-core/pull/844) [run #38279593236](https://github.com/mezas3238-hue/qore-core/actions/runs/38279593236); [QA #846](https://github.com/mezas3238-hue/qore-core/pull/846) | 2.675 ticks, 3×10min; decoder signed y fuente auditados |
| Metal/índice G1 | [#847](https://github.com/mezas3238-hue/qore-core/pull/847) [run #38282585181](https://github.com/mezas3238-hue/qore-core/actions/runs/38282585181); [QA #848](https://github.com/mezas3238-hue/qore-core/pull/848) | XAGUSD 5.782, SP500/US500 1.891 ticks cortos |
| Resto 29 instrumentos G1 | [#849](https://github.com/mezas3238-hue/qore-core/pull/849) [run #38283737706](https://github.com/mezas3238-hue/qore-core/actions/runs/38283737706); [QA #851](https://github.com/mezas3238-hue/qore-core/pull/851) | 111.451 ticks, 29/29, fuente short-window |
| NAS100↔USTEC fuente | [#850](https://github.com/mezas3238-hue/qore-core/pull/850) [#853](https://github.com/mezas3238-hue/qore-core/pull/853) [#854](https://github.com/mezas3238-hue/qore-core/pull/854) | ID 10014, 6.129 ticks, alias aún NO contrato |
| Trader Lab as-of fast parity | [#845](https://github.com/mezas3238-hue/qore-core/pull/845) [run #38278895976](https://github.com/mezas3238-hue/qore-core/actions/runs/38278895976) | Byte-identidad scalar/NumPy con 5k+5k sintéticos, **1,005×**; NO aceleración sustancial |
| G1 zero spread forense | [#858](https://github.com/mezas3238-hue/qore-core/pull/858) [run #38286343956](https://github.com/mezas3238-hue/qore-core/actions/runs/38286343956) | 5.727 snapshots BID=ASK en 29, 4.320 con marcas de último tick simultáneas |
| Protobuf original 5×2×30m | [#859](https://github.com/mezas3238-hue/qore-core/pull/859) [run #38288411671](https://github.com/mezas3238-hue/qore-core/actions/runs/38288411671); [QA #860](https://github.com/mezas3238-hue/qore-core/pull/860) | **34.761 native ticks redecodificados**, 6.640 zero, 15.355 positive |
| Forense mismo milisegundo | [#861](https://github.com/mezas3238-hue/qore-core/pull/861) [run #38290229370](https://github.com/mezas3238-hue/qore-core/actions/runs/38290229370) | 12.381 same-ms, 5.371 zero y **7.010 positivos**; same-ms ≠ causa suficiente de zero |
| QA horarios ficticios | [#862](https://github.com/mezas3238-hue/qore-core/pull/862) [run #38290734217](https://github.com/mezas3238-hue/qore-core/actions/runs/38290734217) | 20 pares horarios FICTICIOS, 11/20 source elegibles |
| E1 reloj real investigación 5 mercados | [#864](https://github.com/mezas3238-hue/qore-core/pull/864) [run #38293096998](https://github.com/mezas3238-hue/qore-core/actions/runs/38293096998) | 56 oportunidades E1; 0/56 entrada + cierre teórico cubiertos por ventanas 13:00–13:30 |
| Captura guiada por 6 E1 existentes | [#865](https://github.com/mezas3238-hue/qore-core/pull/865) [run #38293565282](https://github.com/mezas3238-hue/qore-core/actions/runs/38293565282); [QA #866](https://github.com/mezas3238-hue/qore-core/pull/866) [run #38294099883](https://github.com/mezas3238-hue/qore-core/actions/runs/38294099883) | **13.445 ticks originales redecodificados**, seis fuentes 13:00→15:00; 3/6 pares con BID/ASK causal positivo, 3/6 zero/stale; NO 3 rentables |
| Ledger 33×7 completo y shards | [#867](https://github.com/mezas3238-hue/qore-core/pull/867) [run #38297791677](https://github.com/mezas3238-hue/qore-core/actions/runs/38297791677) y [run #38298193812](https://github.com/mezas3238-hue/qore-core/actions/runs/38298193812) | **33 originales SHA**, 373.611 eventos, 412.012 shards máx30min, **824.024 consultas side mínimas presupuestadas NO ejecutadas** |
| Homologación campo nativo G0/G1 | [#869](https://github.com/mezas3238-hue/qore-core/pull/869) [run #38303158752](https://github.com/mezas3238-hue/qore-core/actions/runs/38303158752) | 12/12 provider name+ID, **132/132** year-partitions originales; 0/12 contrato económico completo |
| Ficha contractual ACTUAL DEMO 12 | [#870](https://github.com/mezas3238-hue/qore-core/pull/870) [run #38303807686](https://github.com/mezas3238-hue/qore-core/actions/runs/38303807686) | 12/12, **7/7 pruebas** y lectura real SymbolsList/SymbolById **sin órdenes**; precios de precisión coinciden, tarifas y swaps históricos no demostrados |

**Importante sobre los contadores:** 127.928 ticks en las capturas de 3×10min para los 33 puestos + 34.761 ticks de otras dos fechas = **162.689 registros de fuente en ventanas cortas**. Los 13.445 ticks de las ventanas E1 adicionales **solapan parte** de datos existentes; **no sumarlos sin deduplicación**, no dar tamaño muestral independiente ni 33 años de ticks. Los 3 source-eligible de seis **no** son operaciones ni traders certificados.

## 5. E1 histórico real: oportunidad versus ejecución; seis pares especialmente críticos

Las 56 oportunidades iniciales de cinco mercados/dos fechas tenían entrada teórica en algunos casos justo a **13:00 UTC** y horizontes 15/120/240 minutos. Las ventanas previas 13:00–13:30 nunca cubrían un par entrada+cierre válido. En seis eventos E1 con entrada a las 13:00 y cierre teórico M5 **15:00**, se capturó BID/ASK [12:55,13:05) y [14:55,15:05) y un auditor de **Protobuf original distinto del colector** verificó SHA/time+price/hasMore:

| Oportunidad E1 original | Fuente a 13:00 | Fuente a 15:00 teóricas | Dictamen |
|---|---|---|---|
| SP500→US500 2021-03-16 SWEEP | STALE | POSITIVO | SOURCE BLOCK |
| SP500→US500 2023-03-21 SWEEP | POSITIVO | POSITIVO | SOURCE PASS |
| GBPUSD 2021-03-16 RANGE | ZERO | ZERO | SOURCE BLOCK |
| USDJPY 2021-03-16 RANGE | ZERO | ZERO | SOURCE BLOCK |
| USDJPY 2023-03-21 SWEEP | POSITIVO | POSITIVO | SOURCE PASS |
| XAGUSD 2023-03-21 SWEEP | POSITIVO | POSITIVO | SOURCE PASS |

**3/6 passes son calidad de fuente, NO trades rentables.** Ni siquiera una entrada teórica de E1 significa que la vela/confirmación estuviera conocida en ese momento o que se hubiese enviado orden al broker. Exigir testigo por cada estado (pre-decisión, señal disponible, orden admisible, orden enviada, fill, stop/target/expiración, cierre as-of).

## 6. Cobertura total de fuente y presupuesto realista SIN descargar

[PR #867](https://github.com/mezas3238-hue/qore-core/pull/867) conservó un registro clock-only de **33 ZIP E1 originales**, 373.611 oportunidades (DEV **278.983**, DIAG **94.628**), 747.222 ventanas inicio/cierre sin dedup, **412.012** intervalos BID/ASK de hasta 30min deduplicados por símbolo y reloj, **mínimo 824.024 solicitudes totales**, contando separadamente una llamada BID y una llamada ASK por fragmento (puede aumentar con hasMore/retries). Esto es una **estimación**, no una cola autorizada y no una descarga ejecutada.

Dos fechas previamente expuestas: 2021-03-16 y 2023-03-21 → **368** eventos, **403** shards, **mínimo 806** llamadas. Pilot Phase0 de cuatro clases: EURGBP (10 eventos/11 shards), USDJPY (12/14), XAGUSD (11/12), SP500→US500 (12/12) = **45 oportunidades E1/49 fragmentos/mínimo 98 llamadas BID/ASK**, todas **pendientes/no ejecutadas**. Dataset privado licenciado y presupuesto/restore son bloqueos anteriores a cualquier nueva descarga. **No cambiar familias ni fechas a posteriori por PnL**.

Archivos ejecutados en rama #867:
- **docs/research/QORE_NATIVE_E1_SOURCE_CLOCK_BUDGET/artifact_register.txt** — 33 artefactos ZIP fuente con SHA.
- **audit.py** — lee cada SHA+original signed E1, reconstruye solo reloj/ID/horizonte de barra y limita fragmentos a 30min; emite ledger gzip sin sign/gross.
- **calendar_pilot.py** — limita el presupuesto a dos fechas ya investigadas.
- **phase0_source_plan.py** — cuatro familias/98 llamadas máximas mínimas sin acceso al broker.
- **verify_reports.py** — control separado de 373.611/412.012/824.024, embargo, 56 y seis E1 previos, no filtración de PnL.
- **fetch_original_signed_E1_zip_artifacts.sh**, workflow **.github/workflows/qore-native-g1-all33-original-e1-source-budget.yml**.

**QA fuente que no debe relajarse:** G1 source solo para 33×3×10min en 2020-09-15/2023-09-19/2026-09-15 y cinco×2×30min en 2021-03-16/2023-03-21, más seis pares de 2×10min; no hay grilla continua de eventos E1 ni mercados negociables equivalentes aún.

## 7. Contratos actuales y P0 de equivalencia histórica: estado último

[PR #869](https://github.com/mezas3238-hue/qore-core/pull/869) probó frente al índice histórico G0 CIBO y las capturas G1 originales que **12/12 provider_symbol + symbolId son iguales, 132/132 particiones G0 íntegras**:
- NAS100→USTEC **10014**; SP500→US500 **10013**; US30 **10015**; XAUUSD **41**; XAGUSD **42**.
- FX originales: AUDJPY **11**; AUDUSD **5**; EURUSD **1**; GBPJPY **7**; GBPUSD **2**; USDCAD **8**; USDJPY **4**.
- Nombre/ID pueden repetirse en distintas cuentas y no prueban el mismo contrato.

[PR #870](https://github.com/mezas3238-hue/qore-core/pull/870) recuperó la **ficha actual** de los doce bajo broker autenticado IC Markets DEMO, isLive=false, vía exclusivamente **SymbolsListReq y SymbolByIdReq**; whitelist evita órdenes/ticks/refresh. Todas las precisiones **digits y pipPosition** concuerdan con G0 histórico:

| Clase de fichas actuales | lotSize entero RAW | minVolume RAW | stepVolume RAW | commission RAW |
|---|---:|---:|---:|---:|
| 7 FX originales | 10.000.000 | 100.000 | 100.000 | 3000 |
| USTEC/US500/US30 | 100 | 10 | 10 | 0 |
| XAUUSD | 10.000 | 100 | 100 | 3000 |
| XAGUSD | 100.000 | 1.000 | 1.000 | 3000 |

**commissionType RAW=1** en estos símbolos; **swapLong/swapShort y baseAssetId/quoteAssetId no estaban explícitamente presentes en los 12 reportes**. NO convertir commission=0 en ejecución gratis, commission=3000 en dólares o lotSize raw en lotes sin escala y moneda del proveedor y cuenta. No extrapolar specs ACTUALES a 2016–2024: la cuenta original CIBO, broker, tabla de comisiones RT, swaps y valores por punto no constan probados. **0/12 EXACT_CONTRACT**; ni USTEC ni US500 certificados como contratos históricos negociables.

Módulos precisos en PR #869:
- **src/qore/infrastructure/trader_lab/qore_native_g1_g0_12_original_provider_id_concordance_v1.py**
- **tests/infrastructure/trader_lab/test_qore_native_g1_g0_12_original_provider_id_concordance_v1.py**
- **.github/workflows/qore-native-g1-g0-original12-provider-id-concordance.yml**

Módulos en PR #870:
- **src/qore/infrastructure/trader_lab/qore_native_g1_current12_demobroker_symbol_specs_snapshot_v1.py**
- **tests/infrastructure/trader_lab/test_qore_native_g1_current12_demobroker_symbol_specs_snapshot_v1.py**
- **.github/workflows/qore-native-g1-current12-readonly-contract-spec-snapshot.yml**

## 8. Evidencias/artefactos críticos y vencimiento

Usar siempre GitHub API para verificar existencia, **head SHA, run ID, digest zip, expiración real** y SHA internos (no asumir que un Actions SUCCESS es un backup duradero). Los datos sensibles o de precio raw permanecen SOLO en artefactos transitorios, no añadir al repositorio público ni releases:

| Evidencia | Run / Artifact ID | ZIP SHA256 |
|---|---|---|
| G0 33 | [#38207337960](https://github.com/mezas3238-hue/qore-core/actions/runs/38207337960), artifact **11727643288** | buscar digest en API antes de reuso |
| E1 33 testigos originales | [#38257207836](https://github.com/mezas3238-hue/qore-core/actions/runs/38257207836) | 33 hashes por símbolo en branch #867 |
| G1 29 BID/ASK | [#38283737706](https://github.com/mezas3238-hue/qore-core/actions/runs/38283737706), **11762222336** | **be123f91e2069390e3bb44f9ce8b9398e3216b9ce483b7441f7f2aebb918f1c0** |
| G1 Protobuf original cinco mercados | [#38288411671](https://github.com/mezas3238-hue/qore-core/actions/runs/38288411671), **11764163362** | **b4eb9e66d76bcd439d4db8f2b8707afa06fe2d211a275c8af8b8605714b58684** |
| G1 seis E1 Protobuf fuente | [#38293565282](https://github.com/mezas3238-hue/qore-core/actions/runs/38293565282), **11767003876** | **01075ecd534de104caf4fb8702aebef86468b611aafb5fcec366722ac12eea9b** |
| QA independiente seis E1 | [#38294099883](https://github.com/mezas3238-hue/qore-core/actions/runs/38294099883), **11767229334** | **f8906269cf04a56aed8e6803ed540f636f141f9953fde588de9b9293914ee132** |
| 33×7 reloj/shards último | [#38298193812](https://github.com/mezas3238-hue/qore-core/actions/runs/38298193812), **11769206137** | **7dee72fea6be809f78b66845ee7541849f480a6a41015afc0b488b8651eb89c7** |
| Comparación 12/132 proveedor | [#38303158752](https://github.com/mezas3238-hue/qore-core/actions/runs/38303158752), **11771092739** | **a2fbdea1c8db620043fc81d95a9c9c65bd0986b6dc7597b3062bced588b82ec7** |
| 12 specs DEMO actuales | [#38303807686](https://github.com/mezas3238-hue/qore-core/actions/runs/38303807686), **11771294113** | **99c09642b8d55a152c5d1c961f542f4700f7e6ee80485137b651edf404921ce7** |

Para las últimas capturas la expiración API observada es **2027-01-10** (hora específica en el addendum #855). Los artefactos viejos pueden vencer antes. **Issue #837** exige vault licenciado con restore byte-exact, no dejarlo como tarea administrativa menor: sin fuente recuperable, la investigación deja de ser reproducible. No mezclar la matriz metadata con los ZIP raw; una copia local de conversación tampoco es custodia permanente.

## 9. Problemas encontrados que el siguiente arquitecto TIENE que resolver

| Prioridad | Bloqueo / evidencia faltante | Acción precisa y Gate de salida |
|---|---|---|
| **P0 #837** | Archivo privado permanente y derechos/costo/retención de barras/ticks; Actions temporal 90d | Inventario hasta 33×M5+33×M1+ticks con run/id/SHA/expiry; seleccionar vault autorizado y legal, copiar fuera de Git público, hash por shard, restore por lector independiente. Registrar SOURCE_ARCHIVED_PERMANENTLY **solo después de restore** |
| **P0 #857** | Cuenta CIBO fuente original no vinculada a DEMO actual; valor de punto/lote/moneda, escalas native, comisiones RT históricas, swaps y sesiones desconocidos | Solicitar fuentes/account metadata históricos con **identidad protegida por fingerprint no reversible**, timestamp de vigencia y pruebas de contratos/currency/min-max vols/fee table por cada símbolo. Comparar antes de PnL; 12 proveedor name/ID y precisión ya PASS, no repetir eso como contratación |
| **P0 #856** | BID=ASK en Protobuf raw (p.ej., 5.727 QA29; 6.640 QA five-market), semántica/executability indeterminada | Consultar docs oficiales cTrader/IC Markets y crear testigo de feed PAPER sin órdenes; diferenciar timestamp mismo ms de orden real; añadir pruebas negative same-ms/zero/stale y decisión ex ante de cuarentena/sensibilidad. Nunca imputar coste cero |
| **P0 #863** | E1 tiene clocks de oportunidad y target bar horizon, **no órdenes reales**, cierres/stops/expiración ni valores entry/exit contractuales | Especificación de ledger de **decisión causal** por evento: bar-close-known, señal observable, order eligibility, cancelación/entrada, stop/target, tiempo de fill y de cierre, BID/ASK as-of ambos lados, price validity, clock skew. Pruebas anti-lookahead, no fabricar fills |
| **P0 news PIT** | No filtro as-of news ni revisión de calendario/halts/tz de cada instrumento | Archivo point-in-time con publicación efectiva y revisión, timezone DST, latencia, horarios y feriados, “known-at-decision” test; sin señal basada en revisión futura |
| **P0 costes** | Faltan comisión realmente cargada, cost conversion, slippage, swaps, spread executable, sesiones/liquidez, margen | Fee ledger por instrumento/cuenta/volumen/periodo con SHA, no campos brutos ambiguos, backtest side-aware sólo con fuente validada; stress por tamaño y horarios |
| **P1 throughput** | Ultra Fast #845 tuvo sólo **1,005×**, no el speed-up de CIBO | Perfilar parseo+IO/source join, test escalar vs optimizado byte-idéntico con datos reales; SHA de caché, no contar cache hits como replicaciones |
| **P1 validez alpha** | Cero edge robusto con 231/231 E1/E2/E3, datos DIAG expuestos, múltiple testing | Nuevo problema/hypothesis económico original PRE-register, mecanismos falsables, sample effective n/power, baseline, costes completos, WFO purged y bootstrap dependiente; prespecificar regla STOP y gobernanza holdout |
| **P1 arquitectura traders** | No hay 3 traders certificados/cognitivas nativas de producción | Diseñar 3 metodologías solo tras evidencia, módulos cognitivos auditables + riesgo + cartera + kill-switch + explicación; PAPER con telemetría antes de plan LIVE; certificar SOLO Gates Core verificables |

### Dos problemas epistemológicos específicos

1. **Eventos E1 “reales” = filas originales del estudio**, no tickets emitidos. No confundir “tienen timestamp real en un archivo firmado” con “existió una orden real a esa hora”. Las 56 oportunidades y 3/6 fuentes elegibles prueban la puente de cobertura, no un modelo explotable.
2. **Homologación parcial del símbolo = metadatos**, no transferibilidad del histórico. G0 CIBO podía tener cuenta/configuración diferente aunque símbolo/id/digits/pip coincidan; no usar cotizaciones G1 del mismo nombre para escribir un PF hipotético G0 como si fuera exacto.

## 10. Secuencia obligatoria de trabajos — sin perder contexto ni malgastar datos

**ETAPA A — Restablecer custodia y reproducibilidad sin brokers:** revisar PRs #841/#855/#867/#869/#870, verificar sus ramas/head y workflows, realizar inventario de artefactos/expiración; ejecutar pruebas de #867 con 33 ZIP ya existentes (no outcome/holdout), #869 sobre seis ZIP metadata originales, #870 si estrictamente necesita revalidación de actuales; mantener reporte con HEAD y SHA. Corregir cualquier divergencia reproducible en PR hija, no sobrescribir los datos originales.

**ETAPA B — Resolver P0 contratos en paralelo con almacenamiento:** atacar #837 y #857. Para G0 original 12 solicitar cuenta, broker, símbolo original por periodo, contrato cash-value, equivalencia de volumen de orden, divisa depósito/PnL y comisiones/swap/sesión. Tablas source historic vs current, fechas de validez, clasificación **EXACT_CONTRACT / DOCUMENTED_NEAR_EQUIVALENCE / UNHOMOLOGATED** y falsación. No etiquetar EXACT basado en ID.

**ETAPA C — Adjudicar BID=ASK:** consultar documento oficial del histórico cTrader, evidencia broker y captura forward quote-only separada. Diferenciar actualizaciones por BID/ASK, empates en ms, staleness y costo ejecutable. Políticas conservadoras por prereg, tests no-lookahead y stop si la fuente no soporta ejecución.

**ETAPA D — Ledger de ejecución CAUSAL:** derivar nuevos eventos sobre estrategia congelada con sólo datos conocidos antes de la orden, cerrar ventana de entrada, stop y salida conforme a regla causal. Incluir testigos pre-decision contra OHLC original y PIT news. El E1 gross no debe promoverse sin estos eventos: si fallan, reestructurar hipótesis PREREG y volver a datos de desarrollo; no reciclar p-values anteriores como nuevo holdout.

**ETAPA E — Adquisición BID/ASK controlada tras A-D:** aprobar licencia/vault, límites de requests y GB, reintentos/hasMore, capturar fuente en ventanas necesarias y auditar Protobuf original por SHA y decoder independiente. Elegir Phase0 plan **49 shards / 98 llamadas mínimas** solo como prueba de alcance pre-expuesto, no como selección de los “mejores” trades. **No lanzar 824.024** llamadas a ciegas.

**ETAPA F — Economía NET, robustez y tres traders:** especificar valoración y sizing en cuenta realista, baseline, slippage/commission/swap/FX, sensitivities, WFO/purged, clusters, Holm/FDR correctamente prereg, evitar falso descubrimiento. Calcular PF, Sharpe, Sortino, MaxDD únicamente sobre trades simulados con fuente y coste de ejecución auditables; si pruebas no son favorables, dictamen STOP/NO_SUPPORT. Solo con nueva evidencia sólida crear tres estrategias autónomas, cognitiva y gestión del riesgo; PAPER primero y aprobación separada para producción.

### Definición de «terminado» que debe escribir el siguiente arquitecto

- **Source Gate:** 33/33 manifest+SHA+provider identity + datos temporalmente completos para el estudio objetivo, vault restore real y licencias.
- **Contract Gate:** cuenta original o separación explícita por contrato; point/lot/value/fees/swap/divisa/año verificados, estados individualizados.
- **Causal Gate:** por trade viable, señal conocida antes de orden, BID/ASK válido ambos lados sin lookahead, sin spreads cero gratuitos; hechos demostrados por tests.
- **Economic Gate:** métodos preregistrados y NET medido con baselines/holdout apropiados y falsación, no selección después de ver PnL.
- **Certification Gate:** revisar umbrales Core vigentes desde documento canónico (no inventar metas de PF/DD/Sharpe), CI, risk limits, PAPER, control de cartera, autorización humana **independiente** de todo LIVE. Hasta completar: 0/3.

## 11. Trader Lab Ultra Fast y buenas prácticas CI

**CIBO Trader Lab Ultra Fast** está documentado en rama de CIBO **agent/cibo-trader-lab-ultrafast-20261008-001**, archivo **docs/research/CIBO_TRADER_LAB_ULTRAFAST_2026-10-08.md**: aceleraciones constatadas en *replay específico H4M5 de CIBO*, no trasladables automáticamente a G1 native 33 quotes. [QORE #845](https://github.com/mezas3238-hue/qore-core/pull/845) comparó join escalar y vectorizado de 5k BID+5k ASK, resultados JSONL byte SHA idénticos y velocidad **1,005×**; bottleneck de parsing, no pregonar “Ultra Fast” sin benchmark verdadero. Diseñar shards cached por SHA y ejecutar tests de **paridad bit a bit** antes de optimizaciones; no cambiar mercado ni reglas por rapidez.

Cada PR debe incluir contrato prereg, fuente inmutable y hash, scripts/tests, workflows Actions, run IDs, artifacts SHA, distinción métricas observadas vs hipotéticas, blockers, adversarial tests (timestamp futuro, missing BID/ASK, zero/crossed, DST, catalog duplicate, token refresh/orden, comisión ausente). Nunca un informe “SUCCESS” reemplaza comprobar jobs/artifacts; no promocionar investigación al VPS.

## 12. Plan de coordinación, revisión y decisiones externas

- **GitHub es el canal de coordinación** con otro arquitecto: dejar issue/PR comment con mensaje CONTEXTO / CAMBIOS / SHA / RUN / MEDICIÓN / NO demostrado / PENDIENTES. Evitar conversaciones privadas que no dejen auditoría. Commits y PRs separados por fuente, QA independiente, inferencia estadística y compatibilidad contractual.
- Se puede consultar a **DeepSeek como auditor metodológico externo**, sobre anomalías de spread, supuestos estadísticos o reglas causales. Su respuesta NO sustituye prueba con data SHA, versión, código y GitHub Actions; guardar conclusiones/rechazos verificables.
- No borrar los dictámenes negativos históricos ni proclamar progreso económico por más cantidad de datos. Si hay un hallazgo que cambia una regla, preregistrar una nueva familia y aislar desarrollo/diagnóstico/holdout.
- El siguiente arquitecto no tiene autorización para cambiar LIVE/producción por la instrucción genérica “avanza”. Sólo acciones de investigación read-only y commits controlados en rama.

## 13. Matriz final rápida de trabajos hechos / pendientes

**HECHO (verificado):** fuente 33 M5 y 24.377.420 barras; 231 ensayos E1-E2-E3 con inferencia negativa; BID/ASK nativo short-windows para 33 puestos, Protobuf QA; detección y rechazo de spread cero; 56 E1 clocks investigados y seis parejas quote (3/6 fuente elegibles), ledger 373.611 E1 y 412.012 shards presupuestados; identidad proveedor G0/G1 original 12×11 partes concordante; 12 specs ACTUALES read-only consultadas; handoffs #841/#855 y este.

**PENDIENTE (NO ejecutado/NO demostrado):** licencia y restauración permanente de raw source, historic account CIBO original y contratos económicamente equivalentes, tarifas/point-value/FX y swaps históricos, significado de los zeros y fill real, ledger de órdenes con stops/salidas causales, cobertura quote histórica en operaciones y noticias PIT, G1 NET backtest reproducible, reexamen riguroso de edge económico con verdadera validación, tres estrategias/cognitivas listas, métricas PF/Sharpe/Sortino/DD NET y certificados.

**Dictamen final a mantener en todas las continuaciones:**
G0_SOURCE_33_PRESENT; E1_E2_E3_231_GROSS_NO_POSITIVE_REPLICATED_SUPPORT; G1_SHORT_NATIVE_BIDASK_SOURCE_VALIDATED_ONLY; G0_G1_12_PROVIDER_ID_AND_CURRENT_PRECISION_CONCORDANT_NOT_HISTORIC_CONTRACT; HISTORICAL_NET_BLOCKED; EXACT_HISTORIC_CONTRACT_0_OF_12; CERTIFIED_TRADERS_0_OF_3; HOLDOUT_FROM_2024_09_17_EMBARGOED; PRODUCTION_UNTOUCHED.

**FIN DEL HANDOFF MAESTRO — siguiente arquitecto comenzar en los tickets [#837](https://github.com/mezas3238-hue/qore-core/issues/837), [#857](https://github.com/mezas3238-hue/qore-core/issues/857), [#856](https://github.com/mezas3238-hue/qore-core/issues/856) y [#863](https://github.com/mezas3238-hue/qore-core/issues/863) en el orden de dependencias indicado, nunca desde especulación de rentabilidad.**
