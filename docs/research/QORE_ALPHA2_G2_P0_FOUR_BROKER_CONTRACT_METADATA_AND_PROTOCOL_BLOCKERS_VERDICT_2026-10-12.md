# QORE-Alpha 2 — G2 P0 cierre contractual por instrumento y protocolo de cTrader (2026-10-12)

**Rama research only** `research/qore-alpha2-original-intermarket-propagation-20261012` / Draft PR #840 / Issue #868. **Estado económico: NET_BLOCKED y UTC001=0.** El objetivo de esta ronda no fue mejorar PnL, sino cerrar documentalmente qué especificaciones originales son comprobables, qué consultas corrientes fallaron y cómo saber exactamente cuándo detenerse.

## 1. Protocol contract — 11/11 tests en las tres versiones, fuente viva bloqueada

- Preregistro inicial antes del acceso: `QORE_ALPHA2_G2_P0_FOUR_SYMBOL_DEMO_CONTRACT_PRIMITIVES_PREREG_2026-10-12.md`, ancestor `4f2372d4cb96fe40a51c642d27d9ff56131bb190`.
- Source V1 [GitHub Actions #38300633695](https://github.com/mezas3238-hue/qore-core/actions/runs/38300633695): Ruff + 11/11 PASS; source DEMO `P0_CATALOG_RESPONSE_UNTRUSTED`; **NO metadata aprobada**.
- Fuente V1 desambiguada [#38300858851](https://github.com/mezas3238-hue/qore-core/actions/runs/38300858851): preflight 11/11 PASS, segunda consulta redundante `ProtoOASymbolsListReq` retornó `P0_CATALOG_RESPONSE_FAILURE`. Confirmado que el preflight DEMO inicial ya tenía fuente de catálogo autenticada, no supone ausencia de instrumento.
- Preregistro V2 adaptador antes de su acceso: `QORE_ALPHA2_G2_P0_BROKER_CONTRACT_SOURCE_V2_DUPLICATE_CATALOG_FIX_PREREG_2026-10-12.md`, ancestor `e2bc4db9339a07c9d94b303a27661e7a4b5bcbc0`. Suprime segundo SymbolsList y usa el catálogo ICMarkets DEMO autentificado ya verificado. Source [#38301197700](https://github.com/mezas3238-hue/qore-core/actions/runs/38301197700) preflight 11/11 PASS, pero **`ProtoOASymbolByIdReq` multi-ID retornó `P0_FULL_SYMBOL_RESPONSE_FAILURE`**. No fichas de fuente aprobadas.
- Preregistro V3 máximo seis solicitudes individuales y **sin reintentos**: `QORE_ALPHA2_G2_P0_CONTRACT_SOURCE_V3_SINGLE_ID_MAX6_PREREG_2026-10-12.md`, ancestor `26359559301edff5024e8b1cae8d3f514550fb3b`. Source [#38301475947](https://github.com/mezas3238-hue/qore-core/actions/runs/38301475947) preflight 11/11 PASS, primera lectura de un solo ID respondió `P0_SYMBOLBYID_SINGLE_REQUEST_FAILED`. **STOP; ninguna consulta adicional a cTrader en esta ronda.** Intentos GHA separados pueden generar costes/rate-limit; no se concluye por especulación si es permiso, rate-limit o rechazo de protocolo. Pruebas sintéticas verifican algoritmo, no cuenta/certificación.
- Todas las versiones emitieron manifiestos de fuente bloqueada (GHA artifact), con 0 órdenes, sin refresh y sin exponer credenciales. No se descargaron ticks históricos ni se abrió el holdout de septiembre 2026.

## 2. Evidencia original ya existente — reutilizada, verificada independientemente

En vez de reclamar éxito del cliente fallido, se reusó exclusivamente el artefacto inmutable del otro arquitecto QORE Native [PR #850](https://github.com/mezas3238-hue/qore-core/pull/850), source [GitHub Actions #38284304699](https://github.com/mezas3238-hue/qore-core/actions/runs/38284304699), HEAD `716996e0f893af0aeb2b990ac11d644cf62a5c5f`. `qore-native-G1-NAS100-USTEC-source-alias-catalog-only-716996e0f893af0aeb2b990ac11d644cf62a5c5f` artifact #11762018327, GitHub original ZIP `sha256:7f927792e575c5cccb9932c55a8db6733430c34629681701c6acd98491ac5c2e`.

Nuevo auditor independiente, sin secrets, broker login ni compra de datos: `src/qore/research/alpha2_g2_p0_ustec_original850_source_qa.py`, test `tests/research/test_alpha2_g2_p0_ustec_original850_source_qa.py`, prereg antes de lectura `QORE_ALPHA2_G2_P0_INDEPENDENT_ORIGINAL_USTEC_BROKER_METADATA_850_PREREG_2026-10-12.md` commit `4a1fc31172adf5ce4ee2c8bfca267aaeaac8b7f4`.

**[GitHub Actions #38301861733](https://github.com/mezas3238-hue/qore-core/actions/runs/38301861733) SUCCESS**: Ruff / 5/5 tests, GitHub ZIP digest comparado contra API original, fuente original cuenta DEMO y estado not-NET, prueba anti-tampering original. Testigo firmado propio artifact #11771250981, HEAD `b163b37f5681abfae5cfb6a0a38890c7db14506b`.

Datos auténticos de ficha DEMO original USTEC: `provider symbolId=10014`, `digits=2`, `pipPosition=1`, `lotSize(raw)=100`, `minVolume(raw)=10`, `stepVolume(raw)=10`. Como indica cTrader, el valor bruto lotSize es en centésimos y el volumen se expresa en unidades codificadas; **NO es un valor de US$ por punto de NAS100 original**. Esta fuente corresponde a un momento de consulta de **otra ejecución** y no prueba la cuenta histórica del Atlas 12.

## 3. Matriz de evidencias de 4 puestos canónicos todavía sin certificación económica

| Canónico G0 | Nombres fuente/proveedor | Verificación SOURCE obtenida | HOMOLOGACIÓN CONTRACTUAL |
|---|---|---|---|
| NAS100 | USTEC (hint original) | DEMO original por ID 10014, fuente catalog #850, source histórica BIDASK PR #853 QA #854 | **BLOCKED**; USTEC no está probado económicamente igual a NAS100 original |
| SP500 | US500 | Source BIDASK original [PR #847](https://github.com/mezas3238-hue/qore-core/pull/847), independiente [PR #848](https://github.com/mezas3238-hue/qore-core/pull/848), 3 ventanas | **BLOCKED**; nombre alterno/contrato original no conciliado |
| NZDUSD | NZDUSD | G1 source [PR #844](https://github.com/mezas3238-hue/qore-core/pull/844)/QA #846, Alpha2 forward DEMO source #38296610948 + QA #38297614422 | **BLOCKED** cuenta original/fees/multiplicador |
| XAGUSD | XAGUSD | G1 BIDASK [PR #847](https://github.com/mezas3238-hue/qore-core/pull/847) / QA #848, 3 ventanas | **BLOCKED** cuenta original/fees/multiplicador |

Contexto fuente: 29 DEMO exactos simultáneos en Alpha2 [#38298399112](https://github.com/mezas3238-hue/qore-core/actions/runs/38298399112) y QA [#38298920851](https://github.com/mezas3238-hue/qore-core/actions/runs/38298920851): 1.033 cotizaciones, 890 source spreads positivos, 36 zero y 107 stale/missing. QORE Native certificó de forma documental un **piloto de tres ventanas breves** en todos los 33 puestos usando 31 nombres exactos y dos alternos, con 127.928 eventos nativos BID/ASK, según [handoff G1 #855](https://github.com/mezas3238-hue/qore-core/pull/855). Estas fuentes de 10min **NO cubren entrada+salida** de los 24.487 W3: intersección Alpha2 CI #38297579449: 2 entradas y 0 trayectorias completas.

## 4. Qué falta para pasar a NET

1. **Evidencia original 12 Atlas a nivel de símbolo y cuenta broker** con identidad de cuenta no secreta y versionado temporal comprobable. Datos nuevos21 DEMO no suplantan G0. Diferencia contractual NAS100/USTEC y SP500/US500 explícitamente resuelta, no por la forma del gráfico.
2. Precisión/pip/lotSize/step/min volume Y conversiones cuenta/moneda/valor de cash por 1 unidad de movimiento, comisiones por ejecución (no `commissionType=0` supuesto), swaps/financiación, deslizamiento, LAT/market-session, fills reales o calibración paper si separadamente aprobada; firma SHA/as-of para 2016–2024.
3. Cobertura bid/ask verificable en DECISIÓN y CIERRE durante años/folds, y `available_at` operativo, no timestamp ex post.
4. Nuevos datos prospectivos/OOS auténticamente no expuestos y evaluación economía-per-fold UTC-001; **W1/W2/W3 GROSS_NO_SUPPORT** ya congeladas y no deben retunearse.

**Resultados operativos:** source 29/29 forward PASS, USTEC *catalog metadata historical observation* SHA PASS, new current contracts batch / individual **BLOCKED**, original 12 broker equivalence **UNKNOWN**, net 0 certified, 0 órdenes, PR #840 DRAFT, issue #868 OPEN, VPS/MT5/CIBO/Shared/QDLE/LIVE intactos. La ronda finaliza sin más llamadas API DEMO.
