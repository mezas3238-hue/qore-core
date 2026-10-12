# QORE-ALPHA 2 — HANDOFF MAESTRO INTEGRAL PARA EL SIGUIENTE ARQUITECTO
**Fecha:** 12 de octubre de 2026.  
**Repositorio:** [mezas3238-hue/qore-core](https://github.com/mezas3238-hue/qore-core).  
**Rama de investigación (única):** `research/qore-alpha2-original-intermarket-propagation-20261012`.  
**Pull Request custodio:** [#840, DRAFT](https://github.com/mezas3238-hue/qore-core/pull/840).  
**Documento de checkpoint complementario:** [QORE_ALPHA2_RESEARCH_MASTER_CHECKPOINT_THREE_HYPOTHESES_AND_G2_2026-10-12.md](QORE_ALPHA2_RESEARCH_MASTER_CHECKPOINT_THREE_HYPOTHESES_AND_G2_2026-10-12.md).  
**NO MERGE A MAIN / NO VPS / NO MT5 / NO PAPER / NO LIVE / NO ÓRDENES.**

> **Estado indeclinable:** QORE-Alpha 2 no tiene ninguna metodología que haya superado su contraste bruto preregistrado; **0 Traders Alpha2 certificados**, **0 operaciones habilitadas**, **0 rentabilidad NET demostrada**, **UTC-001 BLOQUEADO**. Sí existe infraestructura cuantitativa y evidencia real de fuente BID/ASK bajo controles SHA, pero la evidencia de fuente NO se puede presentar como ventaja económica ni como ejecución. W1/W2/W3 quedan congeladas. No se permite reoptimizar en el histórico ya expuesto.

---

## 1. Misión, filosofía y alcance real del proyecto

La visión del owner es construir **traders originales y cuantitativos, nativos de QORE Core**, a partir de investigaciones falsables del mercado; no copiar TTrades, ICT ni adjudicarse como invención original un método estadístico conocido. El objetivo **no** es maximizar el número de trades artificialmente ni presentar curvas gross atractivas: es descubrir un edge económico reproducible que sobreviva costes reales, años y folds independientes, pérdidas consecutivas, pruebas de estrés, auditoría causal y certificación universal UTC-001. Solo un trader realmente certificado puede considerarse para integración posterior con los otros agentes de QORE. La investigación es separada de QORE Native G1, los otros Traders, Shared y CIBO.

El owner pidió avanzar autónomamente con **Trader Lab / Ultra Fast Runner** y que **todos los cambios, pruebas, artefactos y seguimiento queden en GitHub, no en el VPS**. Los trabajos cuantitativos efectivamente ejecutados han utilizado GitHub Actions por símbolo, comprobación de integridad de originales antes de consumir OHLC y auditores independientes. El archivo `trader_lab.fast_forward.py` del Core valida cronología: **no** confundirlo con un simulador real de órdenes. El motor W1 fue vectorizado para escala `O(T*N²)`, con paridad sintética; las demás pruebas originales usaron replay de trayectoria nativa M5. Si hace falta un nuevo proyecto con edge, empezar por fuente nueva, teoría/prerregistro y verdadera OOS, no por minería de hipótesis en datos consumidos.

## 2. Mapa de propiedad, ramas y documentación obligatoria

- **Owner Alpha 2:** [Issue #838](https://github.com/mezas3238-hue/qore-core/issues/838); procedimiento de investigación y PR [#840](https://github.com/mezas3238-hue/qore-core/pull/840), que **debe permanecer DRAFT**.
- **Tick-volume, PADE:** [Issue #843](https://github.com/mezas3238-hue/qore-core/issues/843), informe de fuente tick-volume W2.
- **BID/ASK, costes, PIT y OOS:** [Issue #852](https://github.com/mezas3238-hue/qore-core/issues/852), **P0 NET**.
- **Identidad contractual 33 y NAS100/USTEC, SP500/US500:** [Issue #868](https://github.com/mezas3238-hue/qore-core/issues/868), **P0 CONTRACT**.
- **Custodia legal y preservación de históricos M5:** [Issue #837](https://github.com/mezas3238-hue/qore-core/issues/837), **P0 SOURCE EXPIRY**.
- **Spreads históricos cero y cotizaciones inválidas:** [Issue #856](https://github.com/mezas3238-hue/qore-core/issues/856), cuarentena y causas fuente.
- **Investigación de QORE Native distinta de Alpha2:** [Handoff Native PR #855](https://github.com/mezas3238-hue/qore-core/pull/855), [captura 29 #849](https://github.com/mezas3238-hue/qore-core/pull/849), QA #851, catálogo USTEC [#850](https://github.com/mezas3238-hue/qore-core/pull/850); NO confundir un resultado Native con una certificación Alpha2.
- **Constitución de certificación:** [UTC-001](QORE-UNIVERSAL-TRADER-CERTIFICATION-STANDARD-001.md). Es la fuente de verdad sobre umbrales; ningún análisis desarrollo o agregado global puede sustituir un año/fold.

El checkpoint maestro preexistente debe leerse **antes** de tocar código. Los informes de cada fase y sus preregistros están en `docs/research/QORE_ALPHA2_*.md`, los motores `src/qore/research/alpha2_*.py`, sus pruebas `tests/research/test_alpha2_*.py` y los workflows aislados `.github/workflows/qore-alpha2-*.yml`. El presente handoff **no sustituye los hashes de las pruebas**, los enlaza.

## 3. Fuente G0: 33 mercados, dos cohortes, once años de archivos SHA

**Universo completo cerrado**, sin seleccionar ganadores a posteriori:

| Familia | Canónicos G0 |
|---|---|
| Índices (3) | NAS100, SP500, US30 |
| Metales (2) | XAUUSD, XAGUSD |
| Mayores FX (7) | AUDUSD, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF, USDJPY |
| Cruces FX (21) | AUDJPY, AUDCAD, AUDCHF, AUDNZD, CADCHF, CADJPY, CHFJPY, EURAUD, EURCAD, EURCHF, EURGBP, EURJPY, EURNZD, GBPAUD, GBPCAD, GBPCHF, GBPJPY, GBPNZD, NZDCAD, NZDCHF, NZDJPY |

Identidad original del manifiesto 33: `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`. Cohorte **Original 12 CIBO Atlas**: [Actions #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), productor HEAD `ab782b8e9f890f86a2b6500070f0556b4b685e3d`. Cohorte **21 nuevos ICMarkets DEMO**: [Actions #38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541), HEAD `e0ca5a13c866a19d8505c68cffc473598984b340`. Original manifiesto 33 [Actions #38207337960](https://github.com/mezas3238-hue/qore-core/actions/runs/38207337960), HEAD `dba0e0c3b61e430d3ed51abab562ebd92060a0ff`. Auditoría de SHA de RAW y QUALITY por partición anual antes de abrir OHLC.

En W2 se probaron los 33 productores: [#38273144621](https://github.com/mezas3238-hue/qore-core/actions/runs/38273144621), 35/35 PASS, `19.496.136 / 19.496.136` barras M5 anteriores al embargo poseen `volume` entero positivo. El valor es **`ProtoOATrendbar.volume`, volumen en TICKS, NO volumen negociado ni agresión compradora/vendedora**. Genealogía exacta del código Original12+New21: [#38287282241](https://github.com/mezas3238-hue/qore-core/actions/runs/38287282241), PASS, testigos SHA. Identidad económica de las dos cuentas originales **NO HOMOLOGADA**.

**Ventanas de análisis**: DEV `[2016-09-17, 2022-09-17)` y diagnóstico temporal `[2022-09-17, 2024-09-17)` UTC. **Embargo OHLC `2024-09-17+`**. Advertencia crítica: desarrollo y diagnóstico se han expuesto repetidamente durante investigaciones QORE; **NO son un fresh holdout**, aunque la fecha futura de embargo se mantenga sellada.

### P0 irrepetible: caducidad real de los 33 archivos históricos

La custodia es URGENTE y **no está hecha**. Auditor de metadatos de Github, sin leer precios, [Actions #38302743314](https://github.com/mezas3238-hue/qore-core/actions/runs/38302743314) **SUCCESS 7/7**, HEAD `7e5279eb07a09275a452fc3f57aaf87d75dc1f77`, SHA testigo artifact #11771227114. **33/33 ZIPs originales presentes y no expirados al momento del censo**, tamaño combinado comprimido **728.048 MB** (~260 MB original12, ~468 MB nuevo21). **Primera expiración: 16 diciembre 2026 a las 00:21:18 UTC**, Original12; nuevos21 expiran aproximadamente el 10 enero 2027. NO es un backup permanente: `authorized_private_durable_vault_backup_verified=false`; `archive_restore_rehearsal_verified=false`. [Informe P0 completo](QORE_ALPHA2_P0_33_ORIGINAL_M5_728MB_ARTIFACT_EXPIRY_VERDICT_2026-10-12.md).

**El siguiente arquitecto debe priorizar #837**: verificar primero licencia/contrato y derechos de conservación de datos cTrader/bróker; obtener aprobación para un vault privado con cifrado, control de acceso, versionado, retención y suficiente capacidad, y ejecutar custodia conforme a lo autorizado, antes del vencimiento. Jamás mover 728MB de historial potencialmente licenciado a GitHub público, Release pública, bucket sin autorización ni VPS. Preservar ZIP SHA oficial, IDs, fechas, SHA internos por año, original12 y nuevo21 separados. Una **segunda restauración y rehash independiente** es obligatoria antes de afirmar `SOURCE_ARCHIVED_PERMANENTLY`. Si falta licencia/almacén aprobado, marcar `P0_ARCHIVE_BLOCKED_AWAITING_OWNER_AUTHORIZATION`; NO afirmar backup hecho.

## 4. W1 PATR — metodología y resultado cerrado

**Hipótesis original:** propagación asíncrona de información/tendencia entre mercados H4; motor intermercado y control emparejado; preregistro `QORE_ALPHA2_ORIGINAL_PATR_METHOD_AND_UTC001_PREREG_2026-10-12.md`. Código principal `src/qore/research/alpha2_intermarket.py`, `alpha2_ultrafast.py`, `alpha2_lab_h4_extract.py`, `alpha2_g1a_native_m5_gross.py`, `alpha2_g1a_panel_stats.py`. Fuente G0 SHA 33. [Actions #38268654596](https://github.com/mezas3238-hue/qore-core/actions/runs/38268654596) 35/35 PASS, **224 señales**. GROSS nativo M5 [Actions #38270999595](https://github.com/mezas3238-hue/qore-core/actions/runs/38270999595) 35/35 PASS, **176 pares (130 DEV/46 DIAG)** y **48 censuras**; bruto DEV **−0,16743 bps**, DIAG **−3,42366 bps**; diferencia con control DEV **−0,72876 bps**, DIAG **0 bps**. El comparador W1 resulta casi tautológico/no discriminante donde la dirección H4 propia no es cero; la potencia es insuficiente. Diagnóstico fuente independiente [#38272270791](https://github.com/mezas3238-hue/qore-core/actions/runs/38272270791).

**Dictamen:** `UNDERPOWERED_NO_SUPPORT`; sin edge bruto probado y sin NET. No cambiar thresholds, timeframes ni comparador ex-post intentando rescatar W1 en el mismo histórico. Si alguna vez se plantea una nueva hipótesis de propagación, será **nuevo experimento independiente** con control materialmente distinto preregistrado y datos no adaptativamente utilizados; no llamarlo validación W1.

## 5. W2 PADE — tick-activity vs desplazamiento, resultado cerrado

**Hipótesis:** régimen de actividad tick relativo a desplazamiento H1 y dirección; comparador de tendencia rezagada causal, replay M5. Código `src/qore/research/alpha2_w2_pade_native_m5.py`, `alpha2_w2_pade_panel.py`. Prereg `QORE_ALPHA2_W2_PADE_FIRST_ECONOMIC_PREREG_2026-10-12.md` HEAD ancestral `43688569fa8d9c5ba93a127ff6ae66f9091aeede`. [Actions #38283326547](https://github.com/mezas3238-hue/qore-core/actions/runs/38283326547) 35/35 PASS: **265 señales/265 pares**, 134 con señal opuesta al control. DEV n220 bruto **−1,79805 bps**, delta **−4,55863 bps**; DIAG n45 bruto **+3,39427 bps**, delta **−1,97277 bps**; gate muestral DIAG falla. Auditor posterior [#38283910730](https://github.com/mezas3238-hue/qore-core/actions/runs/38283910730): IC95 del delta DEV semanas 4 [−13,5758; +1,6414] bps, DIAG [−8,1538; +2,4867] bps, ambos cruzan cero. **Seis activos 0 señal** por falta de 20 H1 consecutivas, muy común con sesiones de índices/metales; **204.203** instancias carentes de esa continuidad. El campo `volume` es tick-count, no inventario institucional negociado.

**Dictamen:** `UNDERPOWERED_NO_SUPPORT`. No alterar retrospectivamente la continuidad temporal, ratios volumen, horarios ni stops para «rescatar» PADE. No confundir origen positivo de tick volume con flujo institucional fiable.

## 6. W3 CMTRL — aprendizaje online de morfologías H1, última exploración cerrada

Preregistro ANTES de outcomes `QORE_ALPHA2_W3_CMTRL_LAST_EXPLORATORY_PREREG_2026-10-12.md`, commit `a18cb43a6fb69eab948d840c6e6101c6a7251906`. Código `src/qore/research/alpha2_w3_cmtrl_native_m5.py`, `alpha2_w3_cmtrl_panel.py`, `alpha2_w3_posthoc_census.py`.

Regla H1 causal: 12/12 M5 completos, 20 H1 observadas en las 72 horas pasadas (sin inventar horas cerradas), **8 estados** por cuerpo direccional, rango alto/bajo y asimetría mecha; **240 transiciones maduras** con máximo 90 días; posterior Beta(1,1), probabilidad condicionada superior a 0,65 o inferior a 0,35 con delta frente a base incondicional mínimo 0,10; ≥20 observaciones por estado; máximo 1 señal por símbolo/día, 08:00–15:00 UTC. Control independiente momentum H1 previo; entrada proxy open de M5 a H1+65min, stop rango mediano de pasadas 20 H1, objetivo 2×stop, caducidad 4h, stop-first y gaps adversos, sin rellenar trayectorias. Ningún `available_at` del bróker se prueba por ello.

[Gross all33 #38284821503](https://github.com/mezas3238-hue/qore-core/actions/runs/38284821503) **SUCCESS 35/35**: **24.487 señales, 24.399 pares completos, 88 censuras, 10.841 señales opuestas control**, cero mercados sin señales. DEV 18.266 pares: media **+0,18660 bps** brutos, delta **−0,01516 bps** contra control; DIAG 6.133: **+0,06924 bps** brutos, delta **+0,53516 bps**. [Auditor #38285345503](https://github.com/mezas3238-hue/qore-core/actions/runs/38285345503): IC95 delta DEV [−0,4443; +0,4252]bps, DIAG [−0,2418; +1,2782]bps, ambos cruzan cero; 2.178 señales índices, 1.623 metales, 5.137 mayores, 15.549 cruces. Densidad y potencia pasan, **hipótesis económica relativa original FALLA** por DEV delta negativo/IC. Los retornos brutos minúsculos no permiten atribuir edge; sin costes no se computa NET.

**Dictamen:** `NO_SUPPORT_PREDECLARED_GROSS`. **W3 era el TERCER Y ÚLTIMO método exploratorio sobre este mismo panel temporal**. Cierre obligatorio de minería W4 y sus variantes; nuevo holdout verdaderamente no expuesto si se investiga otra hipótesis original.

## 7. G2 histórico BID/ASK — fuentes auténticas, solo ventanas cortas

Fuente previa QORE Native [PR #849](https://github.com/mezas3238-hue/qore-core/pull/849), original run [#38283737706](https://github.com/mezas3238-hue/qore-core/actions/runs/38283737706), HEAD `f8262bd7cdea1fbfb2287c3c1fe0dae3be2b0efc`; auditor independiente #851. Alpha2 volvió a auditar SHA y paridad de enteros/decimales de 29 mercados en ventanas UTC **2020-09-15 13:00–13:10** y **2023-09-19 13:00–13:10**, excluyendo 2026-09-15 reservado y excluyendo canónicos NAS100, NZDUSD, SP500, XAGUSD. [Source QA #38288561813](https://github.com/mezas3238-hue/qore-core/actions/runs/38288561813), 5/5 PASS, 29/29: **37.430 ticks BID + 37.342 ASK = 74.772**. Código `alpha2_g2_29_real_bidask_reuse.py`, prereg `QORE_ALPHA2_G2_SHARED_SOURCE29_BIDASK_REUSE_PREREG_2026-10-12.md`.

Prereg fijo 1 segundo por ventana × 29 mercados: `QORE_ALPHA2_G2_QUOTE_29_SECOND_GRID_SOURCE_QUALITY_PREREG_2026-10-12.md`, commit `cfd82a0b0e7a36e2bd27181742123bcc137e5430`; [QA #38289175880](https://github.com/mezas3238-hue/qore-core/actions/runs/38289175880), 14/14 PASS, **34.800 puntos**: **27.866** ASK>BID fresco, **4.297** spread=0 **CUARENTENA**, **2.637** lado faltante o >5 segundos, **0** crossed. Código `alpha2_g2_29_quote_quality_grid.py`. Defensa ejecución contra spread cero [#38289518769](https://github.com/mezas3238-hue/qore-core/actions/runs/38289518769) 9/9 PASS, `alpha2_g2_bidask_causal_contract.py`.

**Importante:** son cotizaciones de **20 minutos históricos por símbolo**, NO datos continuos desde entrada a salida, ni cotizaciones conocidas por el cliente en aquellos años. El evento `provider_event_at` recobrado en 2026 no demuestra el `first_received_at` del terminal en 2020/2023; long ASK→BID, short BID→ASK, side stale/crossed/zero fail closed. **CERO spread no equivale a fill gratis**. Para investigación futura preserva filas ausentes/censuradas, no interpolar ni inferir costes sin fuente.

Prueba decisiva de cobertura W3 versus cotizaciones existentes [#38297579449](https://github.com/mezas3238-hue/qore-core/actions/runs/38297579449) **SUCCESS 9/9**: comparó **24.487 eventos W3** sin leer PnL ni precios de ticks, exactamente **2 timestamps de entrada** dentro de alguna ventana 29×2 y **0 trayectorias completas de entrada y ambas salidas** en una misma ventana. **El porcentaje de trayectorias W3 elegibles para costes reales G2 aquí es 0**. Código `alpha2_g2_w3_quote_window_coverage.py`, prereg `QORE_ALPHA2_G2_W3_EVENT_VS_QUOTE_SOURCE_WINDOW_COVERAGE_PREREG_2026-10-12.md`. No ejecutar engine NET con esto.

## 8. G2 recepción prospectiva cTrader DEMO — hecho y auditado

**Piloto NZDUSD 45 segundos:** prereg `QORE_ALPHA2_G2_NZDUSD_DEMO_FORWARD_RECEIPT_45S_PREREG_2026-10-12.md`, código `alpha2_g2_nzdusd_forward_spot_receipt.py`. Primeros intentos se detuvieron en imports de fuente originales no disponibles en fase synthetic; se corrigió para carga diferida. [Captura #38296610948](https://github.com/mezas3238-hue/qore-core/actions/runs/38296610948) SUCCESS, HEAD `ca32ad2311c5c6b4a9312073ca0b4c7b53109a75`, artifact #11767978684, **11 eventos DEMO**, sin órdenes ni refresh. [QA independiente #38297614422](https://github.com/mezas3238-hue/qore-core/actions/runs/38297614422) SUCCESS 7/7, artifact #11768424790, 4 updates BID, 8 ASK, **4 eventos con lados frescos/positivos, 1 spread cero y 6 faltantes/stale** (0 crossed). Hash, reloj del proveedor y reloj first-observed tras dequeue comprobados independientemente.

**Piloto 29 símbolos exactos simultáneos 60 segundos:** prereg `QORE_ALPHA2_G2_29_EXACT_DEMO_MULTISPOT_60S_PREREG_2026-10-12.md`, commit `34a2c20d285d86a16c95bac217a0dc9225a6d799`; código `alpha2_g2_29_exact_demo_forward_multispot.py`, no alias automático. [Captura #38298399112](https://github.com/mezas3238-hue/qore-core/actions/runs/38298399112) 2/2 jobs SUCCESS, HEAD `33068c720fedb3d358a2f73e7323508abd8365f6`, artifact #11769446263, **1.033 eventos**, los **29 mercados** recibieron BID y ASK, cero órdenes/refresh. Auditor independiente prereg `QORE_ALPHA2_G2_29_FORWARD_SOURCE_INDEPENDENT_SHA_QA_PREREG_2026-10-12.md`, [#38298920851](https://github.com/mezas3238-hue/qore-core/actions/runs/38298920851) SUCCESS 7/7, HEAD `a80702b40e2242f7da05d392137cc76ce7124b8b`, artifact #11770276257: **890 positivos, 36 cero en cuarentena, 107 lados faltantes/stale, 0 crossed**. Verificado original SHA, cada secuencia global y por mercado, `provider timestamp`, primer visto del runner, frescura por lado hasta 5s, exactitud de cuenta DEMO sin revelar credenciales.

**Límite:** estas capturas demuestran recepción de una muestra breve por un cliente GitHub DEMO; NO son fills, NO prueba de latencia/efectividad de ejecución ni continuidad durante años, NO prueban la cuenta bróker de Original12, NO NET. Los 29 exactos + NZDUSD en **sesión separada** no son «30 activos homologados simultáneamente».

## 9. G2 motor económico y pruebas de causalidad: implementado, NO NET real

`alpha2_g2_bidask_causal_contract.py` y `alpha2_g2_causal_economic_stress.py`, prereg `QORE_ALPHA2_G2_CAUSAL_ECONOMICS_STRESS_ENGINE_PREREG_2026-10-12.md`, commit `fff976831ea68502f85322d76e73ebea96d19e2f`. [Actions #38293812287](https://github.com/mezas3238-hue/qore-core/actions/runs/38293812287) **SUCCESS 25/25** pruebas (solo fixtures sintéticos). Testa `available_at <= decision_at`, BID/ASK long y short correctos, cuenta y proveedor iguales, freshness, cero spread bloqueado, contratos válidos temporalmente, exactos `symbolId`, lotes y cash exposure en moneda cotizada, conversión FX a moneda de depósito, comisiones entrada/salida, swap, financiación, slippage adverso, todo `Decimal` y jamás datos ausentes sustituidos por 0. Producto único `HYPOTHETICAL_QUOTE_COST_STRESS_NOT_NET_CERTIFICATION`; `utc001_certified=False`.

**Advertencia técnica:** `source_mode="PROSPECTIVE_RECEIVED_QUOTES"` es una afirmación del llamador, NO una prueba criptográfica de recepción por sí misma. El arquitecto debe unir testigo SHA/proveedor first-received/account/contrato de forma independiente antes de atribuir capacidad real a una operación. Además, el motor es estrés con precios de referencia, **no** reproducción exacta de liquidación/fills; no restar slippage dos veces cuando se disponga de fills, y no usar un `lotSize` bruto como US$ por punto.

## 10. Identidad contractual P0 — cuatro mercados, protocolo fallido y USTEC recuperado

Canónicos fuera de la captura 29 simultánea: **NAS100, SP500, NZDUSD, XAGUSD**. Contrapartes de broker candidatas: **USTEC** para NAS100 y **US500** para SP500. Coincidencia de nombre o de gráfica **NO prueba multiplicador, divisa, swap, tick, ejecución, spread ni contratos históricos**. Owner [#868](https://github.com/mezas3238-hue/qore-core/issues/868).

Nuevo adaptador de `ProtoOASymbolByIdReq`: `src/qore/research/alpha2_g2_four_broker_contract_primitives.py`, fixtures `tests/research/test_alpha2_g2_four_broker_contract_primitives.py`. 11/11 synthetic tests PASS. Iteraciones **preregistradas antes de cada consulta**:
1. [V1 #38300633695](https://github.com/mezas3238-hue/qore-core/actions/runs/38300633695) y diagnóstico [#38300858851](https://github.com/mezas3238-hue/qore-core/actions/runs/38300858851): segunda consulta redundante `SymbolsListReq` falló `P0_CATALOG_RESPONSE_FAILURE`.
2. [V2 #38301197700](https://github.com/mezas3238-hue/qore-core/actions/runs/38301197700): catalog autenticado preexistente resuelto, `SymbolByIdReq` multi ID => `P0_FULL_SYMBOL_RESPONSE_FAILURE`.
3. [V3 #38301475947](https://github.com/mezas3238-hue/qore-core/actions/runs/38301475947): 1 ID por request y techo no adaptable de 6 llamadas => `P0_SYMBOLBYID_SINGLE_REQUEST_FAILED`.
**STOP — no más retry en misma cuenta / sesión / rama sin diagnóstico externo real de SDK/permisos/rate-limit.** Causa precisa del rechazo API todavía `UNKNOWN`. Todas las ejecuciones fuente terminaron con bloqueo seguro, manif. sin credenciales, 0 órdenes. No reportar fichas actuales obtenidas: **no** las hubo por esta vía.

Alternativa offline de fuente original ya disponible: QORE Native [PR #850](https://github.com/mezas3238-hue/qore-core/pull/850), [GHA #38284304699](https://github.com/mezas3238-hue/qore-core/actions/runs/38284304699) original HEAD `716996e0f893af0aeb2b990ac11d644cf62a5c5f`, artefacto #11762018327 ZIP SHA256 `7f927792e575c5cccb9932c55a8db6733430c34629681701c6acd98491ac5c2e`. Auditor independiente Alpha2 [#38301861733](https://github.com/mezas3238-hue/qore-core/actions/runs/38301861733) **SUCCESS 5/5**, artifact #11771250981: **USTEC** DEMO proveedor ID **10014**, `digits=2`, `pipPosition=1`, `lotSize(raw)=100`, `minVolume(raw)=10`, `stepVolume(raw)=10`. **No** demuestra valor monetario por punto, contrato histórico 2016–2024 Original12 ni relación causal igualitaria NAS100↔USTEC.

**Matriz obligatoria:** NAS100↔USTEC SOURCE candidato registrado pero CONTRATO `BLOCKED`; SP500↔US500 SOURCE Native [PR #847](https://github.com/mezas3238-hue/qore-core/pull/847)/QA #848 pero CONTRATO `BLOCKED`; NZDUSD fuente Native PR #844/#846 y DEMO single actual pero fee/cuenta/payout `BLOCKED`; XAGUSD fuente Native #847/#848 pero contrato fee/cuenta `BLOCKED`. Criterios y cronología en [informe forense P0](QORE_ALPHA2_G2_P0_FOUR_BROKER_CONTRACT_METADATA_AND_PROTOCOL_BLOCKERS_VERDICT_2026-10-12.md). Otro arquitecto no debe «reparar» problemas API relajando comprobación del mismo account ID, ni inventando cero comisiones.

## 11. Estado de cada gate — SIN COMPENSACIÓN

| Gate/fase | Evidencia | Resultado honesto |
|---|---|---|
| G0 fuentes originales M5 33 | 33 source SHA e inventario de caducidad | **SHA/PRESENCIA PASS temporal**; vault privado/restauración NO |
| G1 W1 PATR | 224 señales/176 paired, gross no diferencial favorable | **NO SUPPORT / UNDERPOWERED** |
| G1 W2 PADE | 265 pares, gross delta negativo + potencia DIAG insuficiente | **NO SUPPORT / UNDERPOWERED** |
| G1 W3 CMTRL | 24.399 pares, diferencial DEV -0,01516bps, bootstrap cruza 0 | **NO SUPPORT GROSS** |
| G2 BID/ASK fuente histórica | 29 × dos 10min, QA SHA | **SOURCE PARTIAL PASS**, no trayectorias W3 |
| G2 BID/ASK forward fuente | 29 DEMO simultáneos 1.033 mensajes, QA SHA | **RECEIPT SAMPLE PASS**, no fills |
| G2 contrato/cuentas históricas | 12 Atlas vs 21 DEMO, 2 aliases índices | **BLOCKED** |
| G2 comisiones, slippage, swaps, conversión, PIT macro | stress synthetic 25/25; fuentes reales incompletas | **NET BLOCKED** |
| Holdout verdaderamente nuevo | DEV/DIAG ya expuestos; +2024 histórico reservado no demostrado limpio | **NOT QUALIFIED** |
| UTC001 por año y fold, MC/DD/PF/Sharpe/Sortino | no NET verificable ni edge gross | **0 CERTIFIED** |
| Producción/orden | no autorización | **NO DEPLOY / NO ORDERS** |

**UTC-001 HARD GATES, cada año de 12 meses y cada fold OOS por separado:** PF≥1,50; expectancy≥+0,15R/operación; Sharpe≥1,50; Sortino≥2,00; payoff≥1,50; DD observado≤6R; Monte Carlo probabilidad resultado positivo≥90%; MC p95 DD≤15R; PF neto>1 y expectativa neta>0; supervivencia a clusters, tamaño muestral, causalidad, winners, MAE/MFE y análisis de pérdidas. Preservación de winners cuando existan filtros: número≥80% y R de winners≥90%. El agregador no salva año/fold reprobado. Full Risk/Shared/CIBO/Independent Validation solo en fase con candidatos reales, sin atribuir certificación por autoridad externa.

## 12. Problemas, riesgos, ambigüedades y severidad

| Prioridad | Problema a solucionar | Prueba que falta / conducta obligatoria |
|---|---|---|
| **P0-URGENTE** | **ZIP M5 33 ~728,048MB expiran** a partir de 2026-12-16 UTC | Derechos/licencia + vault privado aprobado + backup SHA + prueba independiente de RESTORE; **#837** |
| **P0** | No se detecta un edge estadístico robusto para W1/2/3 | Conservar dictámenes negativos; no retunear; prereg una hipótesis realmente nueva solo con datos nuevos independientes |
| **P0** | G2 histórica cubre 0 trayectorias W3 | Plan fuente por segmento temporal original entrada+salida, BID y ASK con gaps y versiones, sin interpolar |
| **P0** | Historical event timestamp ≠ as-of recibido por consumidor | Preservar ambos clocks `event_at/first_seen_at`; red/fill latency no certificada; no retroconvertir ticks de 2020 en `available_at` |
| **P0** | Atlas Original12 vs ICMarkets New21 no comparten identidad contractual demostrada | Cuenta pseudonimizada/versionada, broker/producto/servidor, equivalencia PIT y no mezcla indebida |
| **P0** | NAS100↔USTEC y SP500↔US500 aliases sin contrato probado | Comprobar multiplicadores, trading-hours DST, pip/tick, monedas, swap/fees, histórico Original12 con testigos separados; **#868** |
| **P0** | Costes monetarios completos ausentes | Tarifario causal broker, comisión, swap, financing, rollover, conversión FX, slippage, rechazo/partial fills con fuente SHA, sin 0 implícitos; **#852** |
| **P0** | API `SymbolById` en runtime DEMO rechaza request (V1–V3) | No repetir; depurar permisos/SDK/errores bajo autorización con diagnóstico seguro, no cuentas/secretos en GitHub |
| **P0** | No fresh holdout científico que pruebe edge | Congelar fingerprints antes de nuevos eventos, evitar minería del reservado, muestra/potencia OOS prereg |
| **P1** | 4.297 spreads cero históricos; 36 forwards en 29 | Quarantine obligatoria y auditoría por origen/precisión/timestamp; no asumir spread 0 ejecutable |
| **P1** | Lados BID/ASK stale/faltantes (2.637 grilla; 107 forward 29) | Monitorizar por símbolo/sesión, side age ≤5s, gaps y silencio de feed, no forward-fill indefinido |
| **P1** | 60 segundos de 29 cotizaciones no significa operación continuada | Canal con sesiones/schedule, rate limits, budget, segmentado, long-term SHA, QA horarios fin de semana, cobertura y validez |
| **P1** | Volumen cTrader es tick activity, no tamaño económico | No usar como valor negociado ni order-flow institucional |
| **P1** | Prototipos G2 de economía solo sintéticos | Integrar costos firmados y recepción real en validator por identidad; no false NET/PF |
| **P2** | Fichas cTrader API con campos proto ausentes / enums sin unidades | Mantener `UNKNOWN`, consultar docs fuente y evidencias, no convertir raw lotSize a USD/pip sin contrato |
| **P2** | Retención de futuros artefactos Actions ~90 días y secretos de usuarios | Catálogo de expiración, bitácora SHA, política de custodia y borrado conforme licencias |
| **P2** | Coordinación de arquitectos Native vs Alpha2 | Enlaces de archivos/HEAD/proveedor/cuenta, no copiar evidencias como resultados propios sin nuevo QA |

### Causas de falsos positivos que el siguiente arquitecto NO debe permitir
No llamar «positivo» a solo bruto antes de costes; no mezclar fuente DEMO actual con ejecución Original12 histórica; no llamar «0 spread» a un coste cero; no proclamar FX tick-volume como tape institucional; no usar valores del reservado para ajustar thresholds; no adjudicar `SOURCE_PASSED` a un workflow cuyo preflight sintético pasó pero cuyo job de broker falló; no inferir igualdad NAS100/USTEC por correlated OHLC; no contabilizar 890 quotes positivas como 890 trades; no reabrir W1/W2/W3 para búsqueda adaptativa; no publicar datos privados/licenciados en GitHub público.

## 13. Plan de acción para siguiente arquitecto, con criterios objetivos de cierre

**Paso 0 — recuperación del estado y frontera Git.** Abrir PR #840, este handoff, checkpoint maestro, issues #837/#852/#868. Verificar **HEAD actual de la rama** y que PR permanezca DRAFT; NO cherry-pick a main. Comprobar los Actions enlazados y sus SHA artifact, distinguir PASS preflight vs fuente real. Cerrar una tabla de ejecución/custodia con `input SHA, code HEAD, run ID, artifact ID, source state, UTC001 state`. La rama evoluciona, por eso **el commit de publicación del handoff debe registrarse como ancla de partida**.

**Paso 1 — P0 preservation antes de 2026-12-16 00:21:18Z.** Abrir #837 y atenderlo ANTES de otras optimizaciones: pedir autorización explícita para custodia privada licenciada. La reposición requiere 12 Atlas originales +21 nuevos, ZIP/GitHub SHA y manifiestos RAW/QUALITY 11 años, validación independiente de restauración. Un inventario metadata no es backup. Si no existe capacidad/licencia, elevarlo al owner como riesgo irreversible de pérdida de fuente.

**Paso 2 — cerrar procedencia e identidad contractual #868 (sin más retries indiscriminados).** Crear matriz 33/33 de G0 symbol, provider symbol, source cohort, account-scope nonsecret, symbolId por momento, server, lot/volume units, base/quote/account currency, tick/pip units, cash payout, sesiones/swap/fee plan y evidencia histórica PIT. Comenzar por cuatro canónicos bloqueados NAS100, SP500, NZDUSD, XAGUSD; recuperar evidencias Native #844/#847/#848/#850/#853/#855 y QA SHA. Si `SymbolById` no funciona, no aumentar reintentos; estudiar exactos payload/error códigos con guía SDK/permisos, manteniendo fuentes originales separadas. **Deliverable:** JSON SHA por instrumento, `EXACT_MATCH / SOURCE_ONLY_ALIAS / CONTRACT_BLOCKED` y explicación, sin false 33 certified.

**Paso 3 — ampliar data-plane BID/ASK real sin enviar órdenes.** Diseñar captura prospectiva de datos DEMO por sesiones fijadas y presupuesto de bytes/eventos y retención, clock event vs client received, source account scope, símbolo exacto, num líneas, parser integer signed vs decimal, SHA, monotonic sequence, files split/restart, no órdenes y no refresh no aprobado. Contrastar con fuentes históricas extensas legales si el broker las proporciona. El objetivo de calidad es **cobertura de trayectorias completas entrada+salida**, no maximizar número de ticks arbitrarios. Censurar data gaps. Los ejemplos existentes de 29×60s y NZDUSD×45s son **solo pruebas de conectividad, no baseline económico**.

**Paso 4 — coste económico completo con as-of.** Por cada fuente/línea guardar versión del contrato y comisión efectiva en el momento, símbolo/cuenta, fee min, swap, rollover, conversión moneda cuenta, spread two-sided con availability, slippage reproducible y riesgo por trade. Implementar nueva prueba de contrato económico contra fuente real, nunca usar `source_mode` textual como prueba. Mantener solver `alpha2_g2_causal_economic_stress.py` etiquetado `STRESS_ONLY` hasta haber verificado broker fills/ledger o supuesto validado. Pruebas adversas stop-first, gaps, rounding, FX conversion timestamp, DST, sesiones y fondos; si falta prueba, `NET_BLOCKED`.

**Paso 5 — decidir inteligentemente ciencia futura.** W1/W2/W3 ya falsaron soporte relativo bruto: **no existe un candidato aprobado a evaluar net** y no hay justificación para ponerlos a operar. Para nuevo trader rentable, definir primero hipótesis que explique mecanismo de mercado y control realmente discriminativo, muestra/potencia, universo, variables, fecha de congelación y algoritmo, publicar prereg **antes** de consultar los nuevos resultados. Elegir `holdout` genuinamente no expuesto, no renombrar al diagnóstico quemado. Si fracasa, informar NEGATIVO, detener o diseñar una hipótesis independiente sin reutilizar holdout como virgen.

**Paso 6 — certificación completa UTC-001, si y solo si existe edge candidato.** Freezar algoritmo, params, fuente, HEAD, data signatures y motor execution as-of. Evaluar costos NET, todos los años y OOS folds independientemente, bootstrap dependencia temporal, MC clusters/correlaciones, drawdown, PF/Sharpe/Sortino/payoff/expectancy, sample sufficiency, winners preservados, MAE/MFE, anticorrelación, tail survival, macro PIT, independientes y revisión risk/CIBO. Rechazar por mínimo gate no pasado; *nunca promediar aprobaciones entre años*. Integración paper/live requeriría aprobación adicional del owner y control de riesgo separado.

**Paso 7 — documentación continua y handoff verificable.** En cada avance: prereg SHA anterior al outcome, código, pytest/Ruff, GitHub run, artifact hash, evidencia, anomalías, costo demostrado/no demostrado y actualización al Issue/PR. Al cerrar cada sesión actualizar este documento maestro con nuevas fechas, decisiones y bloqueo más urgente, con enlace/commit confirmado por GitHub.

### Orden de prioridad real (no intercambiar)
1. **Salvar legalmente fuente original M5** antes de expiración 2026-12-16.  
2. **Homologar identidades y contratos** Original12↔New21 y aliases cuatro instrumentos.  
3. **Lograr cobertura BID/ASK y costes reales causales** durante entry+exit, recepción por lado y fee PIT.  
4. **Nueva hipótesis genuinamente independiente con poder estadístico y fresh holdout**; NO W4 a posteriori.  
5. **UTC-001 por año/fold**, independiente + CIBO/Risk, y únicamente después evaluar integración.

## 14. Reproducción práctica en GitHub para el nuevo arquitecto

**Git branch:** `research/qore-alpha2-original-intermarket-propagation-20261012`. Nunca trabajar sobre `main`. Workflows ya verificables por URL:

- Source H4 33 [#38268654596](https://github.com/mezas3238-hue/qore-core/actions/runs/38268654596), W1 gross [#38270999595](https://github.com/mezas3238-hue/qore-core/actions/runs/38270999595).
- W2 source [#38273144621](https://github.com/mezas3238-hue/qore-core/actions/runs/38273144621), gross [#38283326547](https://github.com/mezas3238-hue/qore-core/actions/runs/38283326547), bootstrap [#38283910730](https://github.com/mezas3238-hue/qore-core/actions/runs/38283910730).
- W3 gross [#38284821503](https://github.com/mezas3238-hue/qore-core/actions/runs/38284821503), source-only posthoc [#38285345503](https://github.com/mezas3238-hue/qore-core/actions/runs/38285345503).
- Original broker source [#38283737706](https://github.com/mezas3238-hue/qore-core/actions/runs/38283737706), 29 historical source QA [#38288561813](https://github.com/mezas3238-hue/qore-core/actions/runs/38288561813), 1sec source quality [#38289175880](https://github.com/mezas3238-hue/qore-core/actions/runs/38289175880), zero spread guard [#38289518769](https://github.com/mezas3238-hue/qore-core/actions/runs/38289518769).
- Cost engine synthetic [#38293812287](https://github.com/mezas3238-hue/qore-core/actions/runs/38293812287). W3 quote coverage [#38297579449](https://github.com/mezas3238-hue/qore-core/actions/runs/38297579449).
- NZDUSD forward [#38296610948](https://github.com/mezas3238-hue/qore-core/actions/runs/38296610948) / independent QA [#38297614422](https://github.com/mezas3238-hue/qore-core/actions/runs/38297614422).
- 29 forward simultaneous [#38298399112](https://github.com/mezas3238-hue/qore-core/actions/runs/38298399112) / independent QA [#38298920851](https://github.com/mezas3238-hue/qore-core/actions/runs/38298920851).
- Broker spec V1/V2/V3 blocked [#38300633695](https://github.com/mezas3238-hue/qore-core/actions/runs/38300633695), [#38301197700](https://github.com/mezas3238-hue/qore-core/actions/runs/38301197700), [#38301475947](https://github.com/mezas3238-hue/qore-core/actions/runs/38301475947). USTEC original independent QA [#38301861733](https://github.com/mezas3238-hue/qore-core/actions/runs/38301861733).
- G0 source33 ZIP metadata expiry [#38302743314](https://github.com/mezas3238-hue/qore-core/actions/runs/38302743314).
- [UTC-001](QORE-UNIVERSAL-TRADER-CERTIFICATION-STANDARD-001.md) y [all33 G0 source expiry](QORE_ALPHA2_P0_33_ORIGINAL_M5_728MB_ARTIFACT_EXPIRY_VERDICT_2026-10-12.md) para revisión.

**Ejemplo conceptual de verificación de identidad antes de confiar en artefacto** (comandos ilustrativos, no equivalen a licencia o restore):
```bash
git fetch origin
git switch research/qore-alpha2-original-intermarket-propagation-20261012
git rev-parse HEAD
gh pr view 840 --repo mezas3238-hue/qore-core
gh run view 38302743314 --repo mezas3238-hue/qore-core
gh run view 38301861733 --repo mezas3238-hue/qore-core
# Verificar metadatos de ZIP, SHA256 y expiración ANTES de usar raw prices.
# No gh run download -> repo público; usar únicamente destino autorizado
# si derechos de archivo y acceso privado se han aprobado.
```

Cuando se necesiten módulos cTrader originales que no están vendorizados en la rama research, los GHA los restituían **solo al runner efímero y con hash de Git blob exacto**, no se debe asumir que el import local existe ni copiar código a producción. Los imports del forward pilot se cargan diferidos para que el preflight pytest pueda pasar sin SDK/archivo anterior; nunca confundir `pytest PASS` con `broker SOURCE PASS`.

## 15. Decisiones de arquitectura vigentes y prohibiciones

- El CEO/owner dirige Core; las fuentes research Alpha2 no habilitan capital ni arquitectura productiva.
- **Shared** ofrece hechos causales y contexto; **CIBO** gobierna capital/riesgo; **trader** es responsable de su edge, entradas, stops, objetivos y salidas. La prueba de inteligencia no puede arreglar inexistencia de edge bruto.
- No migrar source-only experimentos a VPS; no órdenes DEMO reales tampoco sin autorización adicional; los pilotos DEMO solo han usado Market Data read-only.
- Si hay ambigüedades causales, contractuales o estadísticas, puede consultarse **DeepSeek como auditor externo**, manteniendo la decisión en fuentes primarias, pruebas falsables y artefactos reproducibles; opiniones externas NO certifican un resultado.
- Nunca publicar secretos o ID de cuenta personal en reportes; preferir pseudónimos hash y account-scope versionado.
- No alterar un contrato o prereg ya consumido sin añadir en un fichero nuevo **causa, alcance exacto y estatus del resultado anterior**. La investigación negativa se conserva, no se oculta.
- Ante duda entre dos fuentes: priorizar evidencia SHA, mismo contrato y conocimiento causal previo a decisión; de lo contrario `UNKNOWN / BLOCKED`.

## 16. Mensaje listo para el arquitecto entrante

> Continúa QORE-Alpha 2 exclusivamente en la rama research de PR #840. Primero abre este Handoff Maestro, el checkpoint maestro, los issues #837/#852/#868, UTC-001 y los run IDs originales. No existe trader Alpha2 certificado: W1 PATR, W2 PADE y W3 CMTRL fueron explorados y **no demostraron soporte bruto relativo**. No retunar sobre 2016–2024 ya expuesto ni abrir 2024-09-17+ reservados para minería. Urgencia máxima: archivos originales 33 M5 de 728.048 MB comprimidos expiran desde 2026-12-16, aún NO existe vault/back-up restaurado; verificar licencia y autorización de depósito privado antes de guardar bytes. Después resolver cuenta original12↔nuevo21, NAS100↔USTEC/SP500↔US500 y contratos/costes PIT; cero comisiones por defecto están prohibidas. Las fuentes históricas 29 × dos ventanas sólo cubren 2 entradas y 0 trayectorias W3, aunque la fuente DEMO forward capturó 1.033 eventos 29/29 y fue auditada. El motor económico tiene 25/25 tests sintéticos, no es certificación NET. La API `SymbolById` se bloqueó V1/V2/V3: no repetir ciegamente; catalog anterior USTEC 10014 tiene SHA independiente y NO homologa NAS100. No tocar main, VPS, MT5, CIBO, Shared, QDLE, PAPER ni LIVE. Mantén todos los resultados y errores en GitHub, etiqueta claramente SOURCE/PROXY/SYNTHETIC/NET_BLOCKED, documenta cada avance con prereg + SHA + run + artifact y exige UTC-001 año por año y fold por fold antes de certificar.

---

**CIERRE FORMAL AL 12/10/2026:** investigación y G2 fuente documentados; tres hipótesis no soportadas, solo recepción y calidad de datos parcialmente verificadas; sin custodia duradera/licencia todavía, sin especificaciones históricas suficientes, sin PATH BIDASK neto, sin edge certificado y sin despliegue. **Handoff de continuación, NO entrega de trader operativo.**


---

## Anexo de continuación — 2026-10-12, P0 restore SHA local (sin transferencia)

**Ronda posterior al handoff del commit original `4a7640f5a0d23d82ced7d5279b52600273a4260c`.** Se revisaron PR #840 e issues #837, #852 y #868, se confirmó que la investigación W1/W2/W3 sigue congelada y que la expiración de los ZIP originales continúa como P0. No se han tocado señales, PnL, histórico reservado, bróker, VPS ni producción.

**Trabajo nuevo implementado en esta misma rama:**
- Contrato previo al código: [QORE_ALPHA2_P0_PRIVATE_RESTORE_SHA_VERIFIER_CONTRACT_2026-10-12.md](QORE_ALPHA2_P0_PRIVATE_RESTORE_SHA_VERIFIER_CONTRACT_2026-10-12.md), ancestro **`e95af04b63a20a583d145896534514a7ae933a02`**.
- Verificador **OFFLINE** `src/qore/research/alpha2_p0_private_restore_sha.py` con comparación de SHA256 por streaming y tamaño original para 33 ZIP, más SHA de 2 ZIP de metadatos (35 en total). Rechaza inventario ajeno al roster/cohortes/HEADs, SHA alterado, tamaños, alias, archivos faltantes/extra, rutas indirectas, symlink y hardlink. No descarga ni extrae fuentes.
- Pruebas exclusivamente sintéticas `tests/research/test_alpha2_p0_private_restore_sha.py`, CI aislada `.github/workflows/qore-alpha2-p0-offline-private-restore-sha-ci.yml`. **GitHub Actions [#38308796703](https://github.com/mezas3238-hue/qore-core/actions/runs/38308796703) SUCCESS, 12/12 tests + Ruff PASS**, exact código HEAD **`827db26cde2c2a90b29834a57e044646b5822a68`**. El primer run #38308722701 falló solo en Ruff por dos imports no usados, corregidos en ese HEAD; no había llegado a pytest, no existió lectura de fuentes reales.

**Significado estricto del PASS**: funcionamiento sintético del validador. El verificador podría funcionar sobre una restauración local privada *después* de aprobación del owner y evidencia licenciada. Nunca crea backup, verifica una cuenta/corredor, demuestra retención ni autentica por sí mismo un JSON de inventario. Su salida incluso con coincidencia 35/35 mantiene `SOURCE_ARCHIVED_PERMANENTLY=false`, `private_vault_authorized_and_durable_verified=false`, `independent_offsite_reader_verified=false`, `broker_retention_license_verified=false`, `yearly_raw_quality_partition_sha_verified=false` y `UTC001_certified=false`.

**P0 aún pendiente, SIN solución material**: licencia/condiciones de datos, Data Vault privado aprobado, presupuesto/seguridad/retención, recuperación externa real y comprobación de 33×RAW/QUALITY anual, segunda restauración en entorno/operador separado; conservar Atlas12 antes de **2026-12-16T00:21:18Z**. Los original21 vencen después. No subir históricos brutos al repositorio público ni a artifacts CI; los profits vault de arquitectura QORE no equivalen automáticamente a un Data Vault de mercado autorizado. Si no se obtiene autorización, seguir `P0_ARCHIVE_BLOCKED_AWAITING_OWNER_AUTHORIZATION`; **no presentar un PASS sintético como preservación**.

**Siguientes prioridades tras P0**: #868 identidad contractual original entre cuentas de NAS100/USTEC, SP500/US500, NZDUSD y XAGUSD (no reintentar cTrader SymbolById sin diagnóstico previo); #852 BID/ASK causal y primera recepción real, costes de entrada/salida, NEWS-PIT y fuentes prospectivas realmente independientes. W1/W2/W3 no se reabren en el histórico consumido; 0 candidatos UTC-001, 0 traders Alpha2 certificados y 0 órdenes.


---

## Anexo II — 2026-10-12: contrato G2 original33 fuente-contrato y CI 20/20

**Evidencia nueva post-handoff:** [QORE_ALPHA2_G2_P0_EXACT33_SIX_ORIGINAL_SHA_CONTRACT_MATRIX_VERDICT_2026-10-12.md](QORE_ALPHA2_G2_P0_EXACT33_SIX_ORIGINAL_SHA_CONTRACT_MATRIX_VERDICT_2026-10-12.md). Preregistro previo al código y a las consultas nuevas metadata-only `QORE_ALPHA2_G2_P0_EXACT33_OFFLINE_CONTRACT_EVIDENCE_CENSUS_PREREG_2026-10-12.md`, commit ancestral `34a6f76c209e8e8e1f5aff2f4763bca435eba877`.

El arquitecto continuador recuperó de GitHub los seis *runs originales* de demostración y auditoría fuente ya ejecutados (29 mercados exactos 60 segundos, NZDUSD 45 segundos en sesión separada y USTEC catálogo histórico actual DEMO). Construyó `src/qore/research/alpha2_g2_p0_exact33_contract_evidence_census.py`, `tests/research/test_alpha2_g2_p0_exact33_contract_evidence_census.py` y un workflow aislado metadata-only `qore-alpha2-g2-p0-exact33-offline-contract-evidence-census.yml`. El programa fija y vuelve a cotejar 6 identificadores run, SHA HEAD originales, 6 IDs de artefacto y 6 ZIP digests exactos, todos todavía no expirados según API de Actions; compara roster G0 12+21 y excluye explícitamente dos índices alias/los cuatro fuera del piloto 29. **NUNCA descarga los originales en este workflow.**

**Prueba real exitosa:** [GitHub Actions #38315787886](https://github.com/mezas3238-hue/qore-core/actions/runs/38315787886), exact HEAD `2048c6b58765fc713d3551f8b1846a9e6471a429`, **Ruff PASS, 20/20 pytest PASS, 6/6 metadatos originales SHA API cotejados**. Salida JSON de 33 filas SHA-recibida en nuevo Actions **artifact #11776593111**, ZIP SHA256 `5491b74cb6338c39e6206d7b10a0fad1d00a31aaeb42728bacb1f3c6869e2aa5`; no cotizaciones/segredos ni OHLC. Las primeras iteraciones fallaron únicamente preflight sintético Ruff y regex erróneo para formato de SHA de commit Git; se corrigieron antes del primer source-run API del nuevo workflow, no son optimizaciones de mercado.

**Resultado exacto / INNEGOCIABLE:** `G2_EXACT33_GITHUB_SOURCE_METADATA_VERIFIED_CONTRACTS_0_OF_33_BLOCKED`. **33/33 filas**, original12 12 y new21 21 separados, 29 símbolos DEMO en sesión única 60s, NZDUSD demo 45s separado, NAS100→USTEC alias fuente sin contrato homologado, SP500→US500 referencia histórica no homologada, XAGUSD ventanas breves históricas reportadas. **0/33 contratos ejecutables**; 0 NET, 0 certificaciones UTC001, 0 órdenes. QA de seis metadatos **NO** equivale a recálculo de los datos ZIP ni a cotizaciones suficientes para una estrategia; SP500 y XAGUSD siguen testimonios externos referenciados, no nuevos originales independientemente reauditorizados en este censo.

**Prioridad siguiente** sigue: #837 licencia+vault+restore antes de vencimiento Atlas12 2026-12-16; #868 identidad de cuenta/contrato original, fees, valores por punto, símbolo PIT y resolver V3 SymbolById sin reintentos injustificados; #852 PIT BID/ASK entry+exit, costes, NEWS y OOS realmente independiente. W1/W2/W3 permanecen congelados, no reformular resultados a posteriori. PR #840 permanece DRAFT, NO MAIN/MT5/VPS/Shared/CIBO/QDLE/PAPER/LIVE.


---

## Anexo III — 2026-10-12: diagnóstico estático y taxonomía segura cTrader SymbolById 30/30

Comparación documental sin bróker de la ejecución DEMO QORE Native USTEC **SUCCESS** [#38284304699](https://github.com/mezas3238-hue/qore-core/actions/runs/38284304699) contra tres consultas contractuales DEMO Alpha2 V1/V2/V3 **BLOCKED**, incluida [#38301475947](https://github.com/mezas3238-hue/qore-core/actions/runs/38301475947). Informe fuente [QORE_ALPHA2_G2_P0_SYMBOLBYID_OFFLINE_DELTA_FORENSICS_2026-10-12.md](QORE_ALPHA2_G2_P0_SYMBOLBYID_OFFLINE_DELTA_FORENSICS_2026-10-12.md). En Native, el catálogo se consulta en la misma sesión que luego emite `ProtoOASymbolByIdReq`; Alpha2 V2/V3 reutiliza un catálogo obtenido por otra sesión autenticada y luego consulta por ID. Ambas implementaciones preservan whitelist para `ProtoOASymbolByIdReq`, por lo que no se demostró una prohibición local de ese mensaje. La diferencia de secuencia es **hipótesis**, no root cause confirmado, especialmente porque V1 ya falló un segundo `SymbolsList`. El error técnico real de cTrader V3 fue descartado por sanitización de logs; **CAUSE_UNKNOWN**, no repetir automáticamente.

Contrato prereg previo a código `QORE_ALPHA2_G2_P0_SYMBOLBYID_SAFE_OFFLINE_FAILURE_CLASSIFIER_PREREG_2026-10-12.md`, ancestor `ab9853647f5a12e75f6511f630a6cfb50a573f78`. Clasificador offline `src/qore/research/alpha2_g2_p0_symbolbyid_failure_taxonomy.py`, negative tests `tests/research/test_alpha2_g2_p0_symbolbyid_failure_taxonomy.py`, workflow `qore-alpha2-g2-p0-symbolbyid-offline-failure-taxonomy.yml`. [GitHub Actions #38316324978](https://github.com/mezas3238-hue/qore-core/actions/runs/38316324978) **SUCCESS Ruff + 30/30 tests**, exact HEAD `d48e64cca1062dffc79766bbe19d0df159ffa86b`. Código solo convierte **sintéticos** `Failure(error)` a enums seguros (local whitelist/SDK/field/decoding/provider/transport/UNKNOWN), sin publicar `str(error)`; no hay broker I/O, cuentas, cotizaciones ni órdenes en CI. **Este nuevo clasificador no vuelve mágicamente conocidos los errores de V3 ya perdidos.**

Al continuar: mantener #868 **contract 0/33**, #837 vault/licencia/restore pendiente y #852 NET/PIT/OOS bloqueado; nunca reoptimizar W1/W2/W3 ni reabrir 2026 reservado; solicitar fuente propietaria autorizada con metadatos no secretos y evidencia de correctitud antes de cualquier nueva consulta broker preregistrada. PR #840 sigue DRAFT/NO MAIN.
