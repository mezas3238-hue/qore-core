# HANDOFF MAESTRO — QORE-alpha V1 | Arquitecto sucesor

**Fecha de corte:** 13 de octubre de 2026 (America/Asuncion).  
**Repositorio:** [mezas3238-hue/qore-core](https://github.com/mezas3238-hue/qore-core).  
**Rama de trabajo:** `research/qore-alpha-96-frozen-20261011`.  
**PR de investigación:** [#797](https://github.com/mezas3238-hue/qore-core/pull/797) (DRAFT, no fusionar a producción).  
**Issue propietario / backlog:** [#798](https://github.com/mezas3238-hue/qore-core/issues/798).  
**Misión precedente:** VT08 #787 cerrada/sustituida. PR VT08 [#765](https://github.com/mezas3238-hue/qore-core/pull/765) se conserva como histórico, no es fuente autoritativa de QORE-alpha.  
**Nivel de autorización:** investigación solamente, sin órdenes reales, sin VPS, sin abrir el holdout 7Y reservado.

> **ORDEN DEL PROPIETARIO:** Dejar de reconstruir la fidelidad de TTrades. QORE-alpha es una **metodología nativa y cuantitativa de QORE**, inspirada en patrones M30/M3. El espacio se congeló en **exactamente 96 hipótesis**. El objetivo no es crear más patrones, sino obtener un GO/NO-GO reproducible con un criterio de parada. No inventar una variante 97 ni mover cortes temporales para suplir datos. **Todavía NO se ha ejecutado el walk-forward económico de las 96 variantes.**

## 0. RESUMEN EJECUTIVO — qué es verdad y qué NO

| Capa | Estado confirmado al corte | Prueba / advertencia |
|---|---|---|
| Hipótesis QORE-alpha | **96/96 congeladas**; archivo JSON permanente + generador/contrato de decisión | [Registro congelado](QORE_ALPHA_V1_FROZEN96_VARIANT_REGISTRY_2026-10-11.json), SHA256 de su manifiesto **4332e07f4a8fbdf1125ecd004a70c4216b8ea1a60e954847eedfe3b362184891** |
| Gates y ventanas | Implementado contrato de 96, filtros strict y una ganadora; **NO** está implementada/ensayada la estrategia de 96 completa | [CI #38170918767](https://github.com/mezas3238-hue/qore-core/actions/runs/38170918767) **SUCCESS 6/6**; 15 tests |
| Histórico cinco FX 2022–2023 **M5** | **5/5 SHA de originales verificados**, incluye año 2022 real | [CI #38259002749](https://github.com/mezas3238-hue/qore-core/actions/runs/38259002749) **SUCCESS 5/5**, fuentes inalteradas |
| Histórico cinco FX 2022–2023 **M3** | **NO VERIFICADO/NO DISPONIBLE** en dataset nativo previo. Dataset M3 conocido empieza 2023-09-24 | M5 NO permite calcular M3 exacto. Prohibido interpolar velas |
| BID/ASK y comisiones del protocolo | **NO VERIFICADOS físicamente para el periodo completo** | M5 normalmente OHLC proveedor; no presenta bid/ask tick o comisión |
| Nuevo proveedor alternativo 2022 M1 | **Piloto Dukascopy BID/ASK M1 PRERREGISTRADO**, todavía no se ha demostrado descarga ni QA exitosa | [Piloto de fuente 13-oct](QORE_ALPHA_V1_FREE_DUKASCOPY_2022_M1_BIDASK_SAMPLE_PREREG_2026-10-13.md) |
| Backtest oficial 96× TRAIN/VALIDATE/TEST | **0 variantes backtesteadas bajo el protocolo nuevo** | No divulgar PF/Sharpe/DD de QORE-alpha como si existieran |
| Prueba económica previa, otro sistema | **NO-GO** prototipo anterior QORE M30→M3 PS-only: POS PF bruto 0,964/0,10R supuesto 0,781; CISD retest bruto 0,895/0,10R supuesto 0,773 | 3.561 madres; **no** son ninguna de estas 96 hipótesis |
| Holdout/VPS/LIVE | **Excluidos de este trabajo** | No consultar `VT08_COGNITIVE_EXPANSION_M3_UNSEEN_VALIDATION` (7Y reserved); nunca operar capital |

**DIAGNÓSTICO:** Los cinco símbolos están archivados en GitHub desde 2022 **en M5**; sigue el bloqueo MATERIAL para operar un modelo con confirmación **M3**. No atribuir al proveedor ausencia de históricos: la verificación antigua de cTrader M3 de enero 2022 falló por autenticación, NO por una respuesta de cero velas. La ejecución actual del proyecto está **BLOCKED_NATIVE_M3_2022_AND_EXECUTION_COST_PROVENANCE**, con fuente M5 disponible.

## 1. Historia completa y lo hecho (no reiniciar el proyecto)

### 1.1 De VT08 a QORE-alpha — decisión de arquitectura

1. Se examinó extensamente la bibliografía TTrades: C2 closure, swings externos de tres velas cerradas, CISD/Protected Swing, EQ intra-C2 y stop del ejemplo alcista M30→M3 debajo de EQ M30 **Y** breaker low. Se determinaron bloqueos de selección causal en swing relevante, POI, breaker y dual-sweep. Se construyeron sensores M3/H1, tests anti-lookahead y auditorías independientes. **No** consiguieron probar una señal economicamente fiel al autor.
2. Se verificaron **8.982 geometrías madres M30→M3**, **8.979** independientes con H1 fuente completa (3 incompletas) y **3.542 formas geométricas de retesteo**. NO son trades, órdenes o señal cognitiva autorizada.
3. Se ejecutó un ensayo económico preregistrado del **prototipo QORE C** (stop exclusivamente PS, objetivo extremo opuesto C1, dos entradas simuladas) en **cinco pares y 3.561 primeras madres/día**. [CI #38160918903](https://github.com/mezas3238-hue/qore-core/actions/runs/38160918903) **SUCCESS 6/6**: entrada POS PF bruto **0,964**, POS con hipotético 0,10R **0,781**; retesteo LIMIT PF bruto **0,895**, con hipotético 0,10R **0,773**. Falta bid/ask físico. Conclusión cerrada: **NO-GO a este prototipo**, NO falsación de TTrades en general, NO resultado de las 96 variantes actuales. [Informe antiguo](VT08_A_M30M3_ECONOMIC_FALSIFICATION_NO_GO_PROXY_REPORT_2026-10-11.md) se encuentra en la rama histórica `agent/vt08-5m-methodology-source-20261010` y PR #765.
4. El propietario cambió explícitamente la misión a **QORE-alpha**: ya no exigir fidelidad al autor; sí protocolo acotado, stop rule estadística, train/validate/test y paper antes de dinero. Se creó rama **`research/qore-alpha-96-frozen-20261011`** y [PR draft #797](https://github.com/mezas3238-hue/qore-core/pull/797). [Issue #798](https://github.com/mezas3238-hue/qore-core/issues/798) centraliza la continuación; la misión VT08 autor-fiel #787 quedó cerrada/sustituida.
5. **Antes de correr nuevo PnL**, se guardó [prerregistro de 96 y stop rule](QORE_ALPHA_V1_96_FEATURE_SPACE_AND_STOP_RULE_PREREG_2026-10-11.md), commit inicial **ff1ede625180d3c1a06fc36d5964762df42b36bc**. Se implementó contrato con ID determinista `QALPHA-V001`…`QALPHA-V096`, validación de fechas NY/DST, controles de fuente, filtro de 96, una sola ganadora, exclusión de segmento test del ranking.
6. [CI manifest y fuente #38170918767](https://github.com/mezas3238-hue/qore-core/actions/runs/38170918767) **SUCCESS 6/6**, commit testeado **060fc20ff6c6fd55874bb1814bcda95f37ad9116**. Ruff PASS, **15 tests adversariales PASS**, manifiesto registrable y permanente [JSON de las 96](QORE_ALPHA_V1_FROZEN96_VARIANT_REGISTRY_2026-10-11.json) comprobado contra SHA **4332e07f4a8fbdf1125ecd004a70c4216b8ea1a60e954847eedfe3b362184891**. Este CI **NO calcula PnL**.
7. Auditoría temporal M3/M15 antigua (1095d) produjo **inicio 2023-09-24 19:45 NY / final 2026-09-23** para los cinco pares: faltaban 20 meses completos de TRAIN 2022-01→2023-08 y parte de septiembre de 2023. No cambiar splits ni inventar M3. [Informe original de bloqueo](QORE_ALPHA_V1_FROZEN96_VERIFIED_SOURCE_COVERAGE_AND_AUTH_BLOCKERS_2026-10-11.md).
8. El probe cTrader DEMO [#38170626976](https://github.com/mezas3238-hue/qore-core/actions/runs/38170626976) para enero 2022 **no autenticó** (`cTrader access token invalid and refresh failed`, otros con protocol auth failure). No significa que cTrader no tenga datos. No añadir tokens a issues/logs.
9. Una búsqueda posterior encontró datos QORE Native para **33 mercados M5**, incluidos **los cinco pares requeridos**, originados en GitHub Actions y sin nueva descarga: cuatro del [run #38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541); USDCAD del histórico CIBO 12 original [#35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458).
10. Se creó verificador de **manifiestos originales + SHA256 de `RAW_M5_LEDGER/2022.jsonl` y `2023.jsonl`**; código `src/qore/infrastructure/trader_lab/qore_alpha_v1_five_existing_m5_source_reuse_gate.py`, adversariales `tests/infrastructure/trader_lab/test_qore_alpha_v1_five_existing_m5_source_reuse_gate.py`; workflow `.github/workflows/qore-alpha-existing-five-2022-m5-source-g0.yml`. [CI #38259002749](https://github.com/mezas3238-hue/qore-core/actions/runs/38259002749) **SUCCESS 5/5**, SHA testeado **c359fddb0628d351427c4f7c8245fc1b7ec6327c**. Se verificaron originales 2022+2023, no se falsificó M3. [Informe G0 detallado](QORE_ALPHA_V1_2022_EXISTING5_M5_SOURCE_G0_SHA_VERIFIED_2026-10-12.md).
11. **Trabajo más reciente descubierto al revisar rama el 13-oct-2026:** commit **8de9719dc40c5a6de6fea293e05522cc418c6c78**, [prerregistro piloto Dukascopy M1/BID-ASK del 4 de enero 2022](QORE_ALPHA_V1_FREE_DUKASCOPY_2022_M1_BIDASK_SAMPLE_PREREG_2026-10-13.md). **Es SOLO una spec fuente sin PnL, no una descarga validada.** El nuevo arquitecto debe comenzar aquí antes de presentar la recuperación de M3 como concluida.

### 1.2 Qué infraestructura ya existe y se puede reutilizar sin reescribir

| Código GitHub | Función verificable / límites |
|---|---|
| `src/qore/infrastructure/trader_lab/qore_alpha_v1_frozen_96_decision_contract.py` | EXACTO espacio 96, hashes y ventanas, cobertura, screening train/validate y selección de 1 candidata. **Contrato**, NO motor de las 96 ejecuciones |
| `tests/infrastructure/trader_lab/test_qore_alpha_v1_frozen_96_decision_contract.py` | Protección 97ª variante, DST/splits, PF estricto, DD, trades mínimo, winrate, 3+ revisión, ranking independiente del test |
| `src/qore/infrastructure/trader_lab/qore_alpha_v1_five_existing_m5_source_reuse_gate.py` | Reconciliación SHA originales M5 2022/2023, no permite sustituir M5→M3 |
| `.github/workflows/qore-alpha-frozen96-source-coverage-v1.yml` | Manifiesto reproducible y preflight cobertura de 5 pares, sin retorno económico |
| `.github/workflows/qore-alpha-existing-five-2022-m5-source-g0.yml` | Reutiliza originales desde runs fuente y produce 5 recibos de SHA, sin PnL |
| `.github/workflows/qore-alpha-2022-demo-m3-feasibility-probe-v1.yml` | Probe enero 2022 read-only cTrader; anterior fallo OAuth; credenciales no equivalen a disponibilidad |
| `src/qore/infrastructure/trader_lab/vt08_5m_a_native_m30_m3_favorable_entry_v1.py` | Geometría/confirmación M3 heredada, requiere adaptar sesiones y objetivos congelados, NO reutilizar labels antiguos como trade completo |
| `src/qore/infrastructure/trader_lab/vt08_5m_m30m3_economic_proxy_falsification_v1.py` | Simulador economic-proxy previo y métricas R, **NO** evalúa 96 y NO fuente bid/ask real |
| `src/qore/infrastructure/trader_lab/cibo_market_atlas_10y_m5_consumer_v1.py` | Esquema físico proveedor M5 bruto con RAW_M5_LEDGER y hashes; desde histórico de CIBO; NO M3 |
| `docs/research/QORE_ALPHA_V1_FROZEN96_VARIANT_REGISTRY_2026-10-11.json` | Registro **canon** de las 96 IDs/entradas/sesiones/stops/targets, no editar |
| `docs/research/QORE_ALPHA_V1_96_FEATURE_SPACE_AND_STOP_RULE_PREREG_2026-10-11.md` | Semántica y aceptación **canon**; si discrepan otros docs, prevalece congelación original |

**No copiar** resultados 2024–2026 del prototipo viejo a la evaluación de 96; el universo y su esquema económico son diferentes. La eventual capacidad de Trader Lab / ultra-fast runner **no elimina la obligación de una fuente M3/BID-ASK completa**.

## 2. Universo de investigación y protocolos CONGELADOS — no modificar

**Markets fijos (los cinco, sin exclusión posthoc):** `EURJPY`, `USDCHF`, `NZDUSD`, `CADJPY`, `USDCAD`.

**Patrón madre, invariante:** barrido simple + reversión en M30 C2 respecto a C1, sin doble sweep, confirmación M3 CISD y Protected Swing conocidos antes de C3.open. Geometría y cantidad de series opuestas según el contrato original; no filtrar por RR observado en futuro. No derivar M3 a partir de M5.

| Dimensión | Opciones exactas | Número |
|---|---|---:|
| Entrada | Posicional C3 / limit retesteo CISD predeclarado | 2 |
| Sesión (hora New York con DST) | Asia 19:00–00:00 / Londres 02:00–05:00 / New York 08:00–11:00 (final excluido) | 3 |
| Stop | Protected Swing, midpoint EQ M30 full range, breaker **proxy QORE definido**, ATR Wilder 14 M30 ×1 | 4 |
| Target | 1R, 2R, 3R, high/low externo de sesión previa **intacto y conocido antes de entrar** | 4 |
| **Producto** | **2 × 3 × 4 × 4 = 96**; IDs exactas `QALPHA-V001…V096` | **96** |

**Pre-decision:** elegir como máximo la primera madre elegible por par/día/sesión/variante según timestamps antes del futuro; entry POS en primer M3.open del C3; LIMIT al nivel CISD anterior, válido solo dentro 10 M3 completas de C3; NO-FILL cuenta como 0R por oportunidad, no eliminar días con NO_FILL al medir expectancy por señal. Entrada/stop/target congelados antes de observar C3; si ambas barreras tocan una misma M3, stop-first pesimista. No son fills físicos hasta comprobar BID/ASK y costes.

**Stop PS/EQ/BREAKER:** definición y tick del broker antes de trade; no elegir low más favorable retrospectivamente. **ATR_X1** requiere exactamente 14 M30 completamente cerradas y previo close para True Range. **Target externo** requiere sesión anterior completa, sin barrido hasta momento de entrada. Grabar ID y hora de cada nivel y razón de abstención.

**Splits INAMOVIBLES, timezone America/New_York:**

| Segmento | Intervalo |
|---|---|
| TRAIN | [2022-01-01, 2024-07-01) |
| VALIDATE | [2024-07-01, 2025-07-01) |
| INTERNAL_TEST | [2025-07-01, 2026-07-01) |
| HOLDOUT 7Y | SELLADO; nunca leer sin proceso de autorización separado |

**Gates del propietario (NO cambiar):** TRAIN PF bruto **>1,40** y **≥50** fills; VALIDATE PF bruto **>1,30** y **≥25** fills; max drawdown **<20%** con riesgo simulado **0,1% equity**/operación, diferencial WR entre train y validate **≤0,15 absoluto** (15 puntos porcentuales). De 96 variantes puede pasar 0: **STOP feature set**; si pasan 1–2, seleccionar **una única** por mayor PF VALIDATE, desempate por ID; si pasan 3+, `OVERFITTING_REVIEW_REQUIRED` antes de pasar ninguna al test. Solo esa ganadora entra a INTERNAL_TEST: PF bruto **<1,20** = rechazar; PF **≥1,20** = prospectivo paper 3 meses, sin retocar; paper PF **neto >1,20** con costes broker verificables; recién entonces evaluar capital REAL riesgo inicial **0,1%** con autorización aparte.

**Advertencia estadística crucial:** PF bruto 1,40 **NO** equivale a Bonferroni. Para 96 hipótesis alfa global 0,05, `alpha_each=0.05/96≈0.0005208333`; sin p-values válidos ni estimación incertidumbre/dependencia serial **NO** reclamar corrección de múltiples pruebas o certificación estadística aunque una variante pase los umbrales heurísticos. Agregar test de significación preregistrado requeriría control de investigación y NO redefinir los 96 productos o escoger otra candidata a posteriori.

**Paper/LIVE:** el criterio de 3 meses es prospectivo, no se pueden usar meses incluidos en cualquier TRAIN/VALIDATE/TEST. Exigir broker distinto, comisiones y spread; no usar retención temporal del análisis previo como si fueran 3 meses paper.

## 3. Datos históricos encontrados: localización, hashes y lo que FALTA

### 3.1 Prueba FÍSICA de los cinco originales M5 de 2022/2023

[CI fuente y QA G0 #38259002749](https://github.com/mezas3238-hue/qore-core/actions/runs/38259002749), 5/5 PASS. Exact original events GitHub:

| Símbolo | GitHub run original | Artifact ID original M5 | Velas M5 **2022** | Velas M5 **2023** | SHA256 RAW_M5_LEDGER 2022 |
|---|---:|---:|---:|---:|---|
| EURJPY | 38193802541 | 11723592292 | 74.529 | 74.510 | `5eb3da3b30858873d3264a49c01990e1073d271802aad5bd78dbdc421dcb7767` |
| USDCHF | 38193802541 | 11722633876 | 74.466 | 74.431 | `b9b7f49997ce25b926a1aac205ea2221b8be657a9c0b4e399aabe414f9c1ba74` |
| NZDUSD | 38193802541 | 11723435593 | 74.524 | 74.431 | `37e841d85af830bfd2db0c697ca4804ff4019ed1557746a91744b5a7c5e9f107` |
| CADJPY | 38193802541 | 11726771423 | 74.526 | 74.495 | `2bbd280bf576e091e3e14f4ec7b2c2465aaf5d71ce2e2787950f954f52093566` |
| USDCAD | 35166210458 | 10475972108 | 74.534 | 74.455 | `9a91cbbd883ba3b204c1b6da60097f6938c3f0157a0e2beaea1e0ea0cb582794` |
| **Total 2022** | | | **372.579** | | |

Primera M5 2022 observada 2022-01-02T23:00Z; última 2022-12-30T21:55Z. En los cinco, manifest original `CLEAN_PROVIDER_PAYLOAD` y SHA raw + manifiesto reconciliados. **No** se ha adjudicado sesion-calendar gaplessness/ticks; `CLEAN_PROVIDER_PAYLOAD` = integridad original, no ausencia de huecos de mercado.

**GitHub evidencia de CI G0 (resumen 90d):** EURJPY artifact `11751911066`, USDCHF `11751867153`, NZDUSD `11751426987`, CADJPY `11751607263`, USDCAD `11751112747`. El registro permanente en branch es el [informe G0](QORE_ALPHA_V1_2022_EXISTING5_M5_SOURCE_G0_SHA_VERIFIED_2026-10-12.md). **Los originales están en GitHub Actions**, no son meras menciones de CIBO Memory. No confundir ID de artefacto CI resumido con ID de datos brutos.

### 3.2 El verdadero bloqueo M3 / fuente de precio

- QORE previo tiene **M3 real de ~1095 días**, comienzos 2023-09-24, hasta 2026-09-23, en los 5, [M3 nativo run #35941643396](https://github.com/mezas3238-hue/qore-core/actions/runs/35941643396), SHA fuente `bc1379d7661aac202495ec67afdd3098473ba723`. M15 fuente anterior [#35934924907](https://github.com/mezas3238-hue/qore-core/actions/runs/35934924907), SHA `b2d33e1b4829d8b4afc76983decca8a99131403c`. Es una *capa* parcialmente apta para VALIDATE y TEST en fechas, **no** prueba integridad BID/ASK.
- No existe evidencia aportada de **M3 nativo o M1 genuino enero 2022→septiembre 2023 de los cinco** en una partición de investigación de QORE-alpha. Buscar archivo M1/M3 adicional con provenance. Si aparece, verificar su periodo, fuente, SHA, bid/ask y **licencia**, evitar feeds incompatibles y datos sellados.
- **No inferir M3 de M5:** los cierres M3 caen en minutos diferentes de las velas M5; OHLC M5 no contiene toda la trayectoria intraperiodo. De M1 BID y ASK completos y contiguos SÍ se puede agregarse M3 por precio (sin inventar precios), pero no garantiza ticks bid/ask simultáneos para stop/fill dentro de cada minuto.
- De grupos completos de 3 M5 del mismo proveedor puede reconstruirse M15, registrando missingness/no relleno; NO declarar esto independiente de la fuente M5.
- Para spread/coste realista, documentar lado de orden BUY al ASK / cierre al BID, SELL al BID / cierre al ASK, comisiones, punto/pip por par, tamaño de tick, slippage prescrito, horarios de broker, DST, bid/ask simultáneo o bound intrabar. Precio midpoint OHLC no equivale a fill broker. Cualquier prueba solo gross debe rotularse diagnóstica, NO GO financiero.

### 3.3 Primer intento M3 cTrader y alternativa Dukascopy

- [Probe DEMO #38170626976](https://github.com/mezas3238-hue/qore-core/actions/runs/38170626976) 2022-01-03→10 por par falló **antes de observar cotizaciones**: access token inválido/refresh fallido/protocol error. No decir "cTrader no conserva 2022". Para reintentar: el owner tendría que reautorizar secrets QORE_CTRADER_* en Actions, **nunca pegar tokens en issue**. No cambiar a cuenta LIVE. Considerar proveedor alternativo primero para ahorrar tiempo/coste.
- **Prerregistro más reciente** [Dukascopy Jan4 M1 BID/ASK sample](QORE_ALPHA_V1_FREE_DUKASCOPY_2022_M1_BIDASK_SAMPLE_PREREG_2026-10-13.md), commit `8de9719dc40c5a6de6fea293e05522cc418c6c78`. Orden: sin PnL, una fecha fija **2022-01-04 UTC 00:00→24:00**, los 5 pares fijos, descargar dos feeds M1 `bid` / `ask`, SHA y versión del downloader, QA timestamp exacto, duplicados, minutos completos, bid/ask consistentes, construir M3 solo de tres M1 contiguas por lado, primer GO de factibilidad **SAMPLE_2022_DUKASCOPY_BID_ASK_M1_AVAILABLE** solo si realmente se obtuvieron barras válidas. No afirmar ya éxito: al corte está **PRERREGISTRADO PERO NO EJECUTADO/NO VALIDADO**.
- Si piloto pasa, completar 2022-01→2023-09 y análisis de solape proveedor Dukascopy vs IC Markets durante 2023-09 adelante, e idealmente cubrir TODO 2022–2026 con feed consistente. Fuente cruzada entre segmentos es riesgo de **edge artificial por cambio de broker/calidad/coste**, y obliga informe de equivalencia, no tuning del feature set. Dukascopy bid/ask no puede llamarse spread de IC Markets; comisión de IC Markets requiere fuente/documento independiente.

## 4. PROBLEMAS detectados (orden de prioridad para resolver; no ocultar)

| P | Problema | Causa probada | Criterio de resolución / evidencia exigida |
|---|---|---|---|
| **P0** | No M3/M1 auténtico 2022–2023 en investigación | Dataset M3 1095d empieza 2023-09; 2022 recuperado es **M5** | Source M1/M3 verificable por mercado, temporalidad correcta, originales SHA, calendario y bid/ask si posible; sin interpolar, sin 7Y sellado |
| **P0** | Costes BID/ASK + comisiones faltantes | Antiguo costo 0,10R solo sensibilidad | Prueba ejecutable por lado de cotización, fee schedule verificable, fills point-in-time, escenarios de incertidumbre documentados; ausencia bloquea aprobación financiera |
| **P0** | Motor de las 96 NO implementado | Código actual solo generador/decision gates, simulador previo PS-only | Construir runner ONE codepath con 96 combinaciones, parámetros congelados, no outcomes para seleccionar madre, tests de abstención/ambigüedad/intrabar |
| **P0** | Cambio de proveedor para cubrir 2022 | Potencial Dukascopy versus IC Markets | Solape medido y control de discontinuidad/husos/spread; preferir feed homogéneo; si no hay comparabilidad bloquear GO |
| P1 | Certificación de calendario/cobertura | M5 G0 clean ≠ sin gaps; M3 ~1095d ≠ complete | Censo de missing por día/sesión/mercado, no inventar velas, cruces M15/M30, evidencia de feriados y rollover |
| P1 | Selección causal de PS/CISD | Viejo VT08 produjo solo geometrías y varios PS, retest era OHLC | Evaluar exactamente antes C3.open, series M3 cerradas, ID estable; 2 PS o 0 PS según spec ⇒ abstención universal, no elegir éxito |
| P1 | Breaker, EQ, ATR y liquidez externa QORE C | Definiciones congeladas requieren código operacional sin grados escondidos | Tests deterministas, no alternar "nearest" ex post ni cambiar target / stop según PF; ATR full M30 Wilder 14; external untouched as-of |
| P1 | Sesiones Asia/London/NY y DST | Históricos previos se filtraron 01–13 NY (perdían Asia) | Reconstruir madre desde RAW para todas 3 bandas congeladas; test NY DST y fecha market-day |
| P1 | Ranking con dependencia estadística | 96 variantes correlacionadas por la misma señal madre y activo | Ejecutar gates congelados sin afirmar que PF>1,40 controla Bonferroni; p-values/correlación solo si preregistrados separadamente y sin modificar ranking |
| P1 | Drawdown de 5 instrumentos concurrentes | DD en R agregado viejo no era DD% de equity; 0,1% multiactivo | Orden temporal global de fills, 0,1% equity por operación y riesgo abierto máximo según prereg, drawdown % verificable |
| P1 | Dominio de estados NO-GO vs BLOCKED | Antes se confundió "M5 disponible" con "M3 listo" y "0 tests" con "0 pass" | Publicar `BLOCKED_SOURCE`, `BLOCKED_COST`, `NOT_RUN`, `NO_PASS_STOP`, `INTERNAL_TEST_REJECT`, `PAPER_PENDING`, `RESEARCH_GO` sin promoción silenciosa |
| P2 | Artefactos GitHub expiran | Actions originales con retention 90 días, posiblemente se pierden | Guardar **manifiestos y SHA en repo**; para datasets grandes utilizar repositorio de datos/licencia y ubicación durable autorizada, no subir gigantes a docs |
| P2 | Auditoría/participación de otro arquitecto | No basta "aprobado" por texto sin comparar código/recibos | Compartir issue #798 y PR #797, revisión independiente de hash y gates; registrar discrepancias antes de mirar PnL |
| P2 | Seguridad de secretos / procesos | cTrader OAuth vencido y 7Y clasificado holdout reservado | Nunca credenciales en logs/PR, no acceder a VPS, no tocar 7Y, no usar datos de otras investigaciones si son holdout del mismo método |

**Problema metodológico adicional:** el objetivo del propietario de "en 2 semanas saber sí/no" era un calendario estimado, no autorización para afirmar plazos imposibles sin feed M3/costes. Si fuentes no están, comunicar bloqueo verificable, no inventar rentabilidad.

## 5. Trabajos EXACTOS que debe ejecutar el siguiente arquitecto (orden de operaciones)

### Fase A — Recuperación del feed que falta (P0, NO outcomes)

**A1.** Abrir este handoff y comparar `git HEAD`, PR #797, issue #798 y SHA manifiesto 96 antes de actuar. Confirmar que existe [prerregistro Dukascopy M1](QORE_ALPHA_V1_FREE_DUKASCOPY_2022_M1_BIDASK_SAMPLE_PREREG_2026-10-13.md) y NO duplicarlo cambiando la fecha.

**A2.** Ejecutar **único piloto 2022-01-04 M1 BID y ASK Dukascopy**, para EURJPY/USDCHF/NZDUSD/CADJPY/USDCAD; no abrir holdout ni correr PnL. Controlar descargas con versioning/hashes, timestamps/minutos, datos vacíos, desfases, no bar-crossed, instrumento correcto; generar por par informe `SAMPLE_AVAILABLE` o `SOURCE_UNAVAILABLE`. Si falla buscar **otros datos libres/proveedor** documentando límites, no modificar la hipótesis congelada.

**A3.** Si A2 confirma disponibilidad, obtener serie íntegra M1 desde enero 2022 hasta septiembre 2023 para los cinco, construir M3 bid/ask de tres M1 **consecutivas completas**, agregación M30 desde diez M3, M15 desde cinco M3 y corroboración independiente con originales M5 (sin afirmar match perfecto entre proveedores). Guardar conteo por año y hash por chunk, metadata/licencia, timezone, lotes de faltantes, spread side.

**A4.** Resolver **sesgo de proveedor/ejecución**: evaluar solape Dukascopy/IC Markets en fechas comunes **sin mirar PnL**, escoger antes del análisis económico cómo se procederá con feed homogéneo o registrar que no se puede certificar; verificar instrumentos 5/5, tick-size/pip/commission y fees verificables. **No usar 2022 M5 para fabricar M3**.

**A5.** Emitir gate de fuentes independiente con fecha mínima enero 2022 para cada símbolo, cobertura mensual/horaria y M1/M3 as-of, hash y liveness; si incompleto se mantiene BLOCKED y no se puntúan 96.

### Fase B — Motor QORE-alpha v1 fiel al **prerregistro QORE**, no al autor (P0)

**B1.** Construir **único motor** en Trader Lab/ultra-fast runner sobre los cinco raw feeds + manifest 96: misma lógica M30 single sweep C1→C2 y un único CISD/PS M3; variantes solo cambian la cuadrícula entrada/sesión/stop/target. **No 96 motores dispares**.

**B2.** Contratos unitarios y adversariales: OHLC reconstruct/clock, anti-lookahead, as-of PS/serie opuesta, no doble sweep, pre-decision first mother per market/day, stop=PS/EQ/breaker/ATR14, external prior session high/low untouched; spread bid/ask buy/sell, commission, target/stop misma vela STOP-FIRST, LIMIT touch y no fill, expiración C3, gaps/rollover/fees.

**B3.** Congelar código fuente, versión de feed, comisiones, manejo de spread, timestamps de series y unit-tests **antes** de mirar cualquier PnL train. Emitir recibo JSON para cada mother y cada variante con ID/hash, timestamp y razón de abstención. Ningún parámetro nuevo.

### Fase C — Desarrollo y selección (solo cuando A+B GREEN)

**C1.** Correr **96** en TRAIN [2022-01, 2024-07), congelados, cinco mercados sin exclusión; verificar PF bruto, N trades, WR, equity/DD%, no fills y flags de costes. Si feed/coste incompleto bloquear.

**C2.** Correr **96** en VALIDATE [2024-07, 2025-07) SIN tocar INTERNAL_TEST, aplicar requisitos: TRAIN PF>1,40/50; VALIDATE PF>1,30/25; DD<20% y |WRdiff|≤0,15. Ordenar **una** por mayor VALIDATE PF y desempatar por ID. 0 ⇒ STOP esta generación de features; ≥3 ⇒ review de dependencia/split antes de seguir; 1–2 ⇒ lock winner.

**C3.** Registrar commit/hash decisión pre-test con listados de las 96 y única ganadora. Únicamente esa al INTERNAL_TEST [2025-07, 2026-07). PF bruto <1,20 ⇒ descarte irrevocable; ≥1,20 ⇒ candidato paper. No rescate ni ranking usando resultado test.

**C4.** Paper trading prospectivo **tres meses NUEVOS**, con PF neto>1,20 y costes medidos; si no supera, cerrar. Solo tras esto pedir autorización separada para real riesgo 0,1%; jamás desplegar automáticamente VPS ni aumentar riesgo porque pasó un backtest.

### Fase D — Auditoría, documentación, traspaso y protección

**D1.** Actualizar issue #798 en cada gate con: SHA código probado, dataset original hash, input/output SHA, variables bloqueadas, alcance y resultado; no escribir "avance" sin artefacto. Invitar al arquitecto B/cognitivo a revisar los gate receipts independientes si participa; DeepSeek externo puede revisar ambigüedades, pero ninguna sugerencia posterior a PnL altera v1.

**D2.** Conservar evidencia inmutable de FAIL/GO de cada etapa, y escribir dictamen final específico, nunca mezclar `NO_GO_PROTO_VT08` con QORE-alpha v1. Si se agota el feature set, investigación futura con features **realmente nuevas** exige otro ciclo/prerregistro independiente, nunca un ajuste oculto a las 96.

**D3.** Comprobar que HOLDOUT 7Y y VPS siguen excluidos del worktree, workflows y logs (no basta campo booleando falso si lo contrario ocurrió). No utilizar datos `VT08_COGNITIVE_EXPANSION_M3_UNSEEN_VALIDATION` para suplir TRAIN.

## 6. Evidencia GitHub mínima para reproducir el trabajo sin memoria de conversación

| Tipo | URL |
|---|---|
| Issue propietario vivo | [#798](https://github.com/mezas3238-hue/qore-core/issues/798) |
| PR draft de investigación | [#797](https://github.com/mezas3238-hue/qore-core/pull/797) |
| Manifest y 15 tests | [#38170918767](https://github.com/mezas3238-hue/qore-core/actions/runs/38170918767) |
| Auditoría M5 2022+2023 SHA 5/5 | [#38259002749](https://github.com/mezas3238-hue/qore-core/actions/runs/38259002749) |
| Fuente real 4 FX nuevos M5 10Y | [#38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541) |
| Fuente CIBO USDCAD M5 10Y | [#35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458) |
| Fuente M3 1095d previo | [#35941643396](https://github.com/mezas3238-hue/qore-core/actions/runs/35941643396) |
| Fuente M15 1095d previo | [#35934924907](https://github.com/mezas3238-hue/qore-core/actions/runs/35934924907) |
| cTrader DEMO probe fallido auth | [#38170626976](https://github.com/mezas3238-hue/qore-core/actions/runs/38170626976) |
| Económico NO-GO prototipo viejo (NO las 96) | [#38160918903](https://github.com/mezas3238-hue/qore-core/actions/runs/38160918903) |
| Prerregistro 96 congeladas | [QORE_ALPHA_V1_96_FEATURE_SPACE_AND_STOP_RULE_PREREG_2026-10-11.md](QORE_ALPHA_V1_96_FEATURE_SPACE_AND_STOP_RULE_PREREG_2026-10-11.md) |
| Registro permanente 96 JSON | [QORE_ALPHA_V1_FROZEN96_VARIANT_REGISTRY_2026-10-11.json](QORE_ALPHA_V1_FROZEN96_VARIANT_REGISTRY_2026-10-11.json) |
| G0 fuentes M5 originales | [QORE_ALPHA_V1_2022_EXISTING5_M5_SOURCE_G0_SHA_VERIFIED_2026-10-12.md](QORE_ALPHA_V1_2022_EXISTING5_M5_SOURCE_G0_SHA_VERIFIED_2026-10-12.md) |
| Piloto 2022 M1 BID/ASK prerregistrado | [QORE_ALPHA_V1_FREE_DUKASCOPY_2022_M1_BIDASK_SAMPLE_PREREG_2026-10-13.md](QORE_ALPHA_V1_FREE_DUKASCOPY_2022_M1_BIDASK_SAMPLE_PREREG_2026-10-13.md) |

**Última comprobación antes de este handoff:** HEAD rama `8de9719dc40c5a6de6fea293e05522cc418c6c78` (prerregistro Dukascopy), issue #798 abierto, PR #797 DRAFT abierto. El propio **commit de este handoff** se añade después y no estaba presente al hacer esa lectura. Los artefactos Actions tienen vencimiento; reconstruir a partir de código + referencias/hashes cuando sea posible.

## 7. ACUERDO DE PARADA, mandato al siguiente arquitecto

1. **Mantén 96, cinco pares, tres segmentos, umbrales y una sola ganadora.** No modificar después de ver PnL, ni cambiar sesión, ATR, stop, target o proveedor para escoger un ganador.
2. **Prioridad máxima: M1/M3 2022 genuino y BID/ASK físicos, NO más detectores.** Ya existen M5 2022 de los cinco; no equivale a M3, no vuelvas a perder tiempo descargando M5.
3. **Sin fuente suficiente: bloqueo honesto, no NO-GO ni PF ficticio.** Sin datos no existe muestra evaluada. No llamar 0 variantes pasantes a 0 variantes testeadas.
4. **Cuando existan datos, ejecutar 96 con los únicos gates congelados y no buscar una variante 97.** Si 0 pasan se cierra este espacio y solo entonces se puede preregistrar una hipótesis DISTINTA, con datos nuevos.
5. **Solo paper 3 meses antes del capital real; 0,1% inicial únicamente si se autoriza aparte.** Riesgo de patrimonio, sensibilidad costos/ejecución y posibles proveedores diferentes deben transparentarse siempre.

### ACCIÓN INMEDIATA PARA EL PRÓXIMO ARQUITECTO

**Ejecutar el piloto SOURCE-ONLY Dukascopy M1 BID+ASK del 2022-01-04 para los cinco pares** tal como quedó escrito en el commit `8de9719`; registrar éxito/fracaso con artefactos GH y hashes; si pasa, inventariar meses 2022–2023, completar consistencia de proveedores y bloqueo BID/ASK. **No iniciar el 96×3 hasta superar G0 fuente + costos.** Al completar cada tarea, comentar evidencia directa en [issue #798](https://github.com/mezas3238-hue/qore-core/issues/798) con SHA de commit y enlace de CI.

---

**Firma del handoff:** Arquitectura metodológica QORE-alpha, traspaso documental. Este archivo es un **registro de investigación**, NO aprobación económica, operativa, cognitiva, ni certificación de edge.
