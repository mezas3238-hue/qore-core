# QORE NATIVE — HANDOFF MAESTRO DEFINITIVO — 2026-10-12

**ESTADO:** investigación 33/33 y 7 metodologías × 33 activos ejecutada; auditorías Holm, FDR y E3 terminadas; capturas BID/ASK inventariadas y cruzadas descriptivamente con retornos. **0/3 traders certificados.** Este documento es el punto de entrada OBLIGATORIO del siguiente arquitecto.

**Repositorio:** [mezas3238-hue/qore-core](https://github.com/mezas3238-hue/qore-core)  
**Rama de custodia:** `research/qore-native-master-handoff-33x7-bidask-e3-20261012`, creada desde `research/qore-native-33-bidask-visual-snapshot-20261012` @ `22f37bed88a2744e720d3c23d799580a3d170a34`.  
**Mandato del propietario:** desarrollar **3 traders originales** QORE Native con metodología propia y cognitivas, explorar todos los 33 instrumentos con rigor, evitar falsos edges, y **trabajar exclusivamente en GitHub/GitHub Actions, nunca en el VPS**. **Prohibido modificar o activar MT5, LIVE, CIBO, Shared y QDLE.**

## 1. Estado verificable y localización de evidencias

| Bloque | Veredicto / resultados | Evidencia |
|---|---|---|
| Fuente G0 | 33/33 mercados; **24.377.420 barras M5** originales, SHA y procedencia auditados | [PR #829](https://github.com/mezas3238-hue/qore-core/pull/829), [Actions #38207337960](https://github.com/mezas3238-hue/qore-core/actions/runs/38207337960), [artefacto #11727643288](https://github.com/mezas3238-hue/qore-core/actions/runs/38207337960/artifacts/11727643288) |
| Cuatro modelos previos | 4 NO_SUPPORT: persistencia EURUSD, reversión XAUUSD, NAS100 reacción apertura, sweep-reclaim 33 | [PR #822](https://github.com/mezas3238-hue/qore-core/pull/822), [#825](https://github.com/mezas3238-hue/qore-core/pull/825), [#827](https://github.com/mezas3238-hue/qore-core/pull/827), [#830](https://github.com/mezas3238-hue/qore-core/pull/830) |
| ADR-002: siete métodos × 33 | **231/231 pruebas gross**, 35/35 trabajos completos; Holm 5%: **0 ventajas positivas confirmadas** | [PR #832](https://github.com/mezas3238-hue/qore-core/pull/832), [Actions #38257207836](https://github.com/mezas3238-hue/qore-core/actions/runs/38257207836), [artefacto #11749739981](https://github.com/mezas3238-hue/qore-core/actions/runs/38257207836/artifacts/11749739981) |
| Sensibilidad FDR | BH-FDR 5/10% sobre los mismos 231 p: **0 positivas corregidas**; 5/5 tests OK | [PR #834](https://github.com/mezas3238-hue/qore-core/pull/834), [Actions #38260058465](https://github.com/mezas3238-hue/qore-core/actions/runs/38260058465), [artefacto #11751248539](https://github.com/mezas3238-hue/qore-core/actions/runs/38260058465/artifacts/11751248539) |
| E3 correlación temporal | Métodos agregados con peso igual por mercado, bootstrap conjunto bloques 1/2/4 semanas, 4000 draws; **0/7 métodos** con gross y delta positivos en ambos períodos; 8/8 tests OK | [PR #836](https://github.com/mezas3238-hue/qore-core/pull/836), [Actions #38262585848](https://github.com/mezas3238-hue/qore-core/actions/runs/38262585848), [artefacto #11753217479](https://github.com/mezas3238-hue/qore-core/actions/runs/38262585848/artifacts/11753217479) |
| Tres capturas del usuario BID/ASK | **33 cotizaciones spot registradas** y SHA de 3 imágenes; 7/7 tests OK | [PR #839](https://github.com/mezas3238-hue/qore-core/pull/839), [Actions #38265563869](https://github.com/mezas3238-hue/qore-core/actions/runs/38265563869), [artefacto #11754836116](https://github.com/mezas3238-hue/qore-core/actions/runs/38265563869/artifacts/11754836116) |
| E2 vs spread fotográfico | 231 comparadas, 21 bloqueadas por alias/cero spread, 210 ilustrativas; 22 gross DEV > spread spot, 33 DIAG, **solo 5 en ambos**; 5/5 tests OK; **NO beneficio neto** | [Actions #38266242429](https://github.com/mezas3238-hue/qore-core/actions/runs/38266242429), [artefacto #11755375097](https://github.com/mezas3238-hue/qore-core/actions/runs/38266242429/artifacts/11755375097) |

**SHAs inmutables:** fuente G0 33 `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`; E2 JSON original `5161dbdf157805af3e37957ec25acad3657962a50c99d214883005cb03945f80` y código original E1/E2 `dfe78f115957a40f4188c30e78bd7f88c2ce6c42`; E3 JSON `bddfb37a859acbd4d607c18790c4ab752399e951e010e62a479f1597db941616`, código probado `845a7e351c1641025a6131271ae3ada37ebf37f1`; snapshot→E2 code probado `22f37bed88a2744e720d3c23d799580a3d170a34`.

## 2. Universo congelado: fuente y clases

| Familia | Símbolos | M5 |
|---|---|---:|
| Índices 3 | NAS100, SP500, US30 | 2.095.377 |
| Metales 2 | XAUUSD, XAGUSD | 1.414.232 |
| FX mayores 7 | AUDUSD, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF, USDJPY | 5.216.165 |
| FX cruces 21 | AUDJPY, AUDCAD, AUDCHF, AUDNZD, CADCHF, CADJPY, CHFJPY, EURAUD, EURCAD, EURCHF, EURGBP, EURJPY, EURNZD, GBPAUD, GBPCAD, GBPCHF, GBPJPY, GBPNZD, NZDCAD, NZDCHF, NZDJPY | 15.651.646 |
| Total | 33 | **24.377.420** |

**Procedencia:** 12 originales cTrader DEMO procedentes de infraestructura CIBO, 21 nuevos IC Markets cTrader DEMO. Sus cuentas, brokers y contratos **NO están homologados** entre sí ni con las capturas BID/ASK. **No descargar M5 de nuevo por rutina** y **no extrapolar equivalencia entre feeds**. Fuente G0 en `docs/research/QORE_NATIVE_FULL33_GROSS04_MASTER_HANDOFF_2026-10-12.md`, `docs/research/QORE_NATIVE_ALL33_SOURCE_CENSUS_AND_RESEARCH_GATES_2026-10-12.md`, workflow `.github/workflows/qore-native-final33-m5-g0.yml`.

## 3. Las siete metodologías y resultados por familia

Se probaron **UNA definición causal por mecanismo**, NO infinitas ventanas, stops, targets ni entradas, sobre cada uno de los 33 símbolos: `REVERSAL_12H`, `POST_OPEN_CONT`, `PERSISTENCE_12H`, `OPEN_INITIAL_REACTION`, `SWEEP_RECLAIM`, `TREND_MULTI_DAY`, `RANGE_BREAK_CONT`.

- Preregistro/matriz: `docs/research/QORE_NATIVE_ADR002_33_MARKETS_7_METHODS_FACTORIAL_PLAN_2026-10-12.md`, `docs/research/QORE_NATIVE_E1_33X7_FROZEN_RULES_BEFORE_NEW_OUTCOMES_2026-10-12.md`, `docs/research/QORE_NATIVE_E2_33X7_PRE_OUTCOME_MULTIPLICITY_CLUSTER_PLAN_2026-10-12.md`.
- E1: `src/qore/infrastructure/trader_lab/qore_native_e1_33x7_seven_gross_per_market_v1.py`. E2: `src/qore/infrastructure/trader_lab/qore_native_e2_33x7_holm_synchronized_weeks_v1.py`. Workflow `.github/workflows/qore-native-e1-e2-all33-seven-methods.yml`.
- Desarrollo `2016-09-17→2022-09-17`; diagnóstico temporal `2022-09-17→2024-09-17` (NO holdout virgen del proyecto). **Embargo OHLC 2024-09-17 en adelante, mantener cerrado**. 313 semanas dev, 105 semanas diagnóstico; 278.983 y 94.628 **eventos método×símbolo, NO independientes**.
- De 231 celdas, 33 sweep/reclaim ya expuestas en panel #830; 3 pares originales EURUSD/XAUUSD/NAS100 expuestos por ensayos antiguos; 195 nuevas combinaciones de diseño. Nunca etiquetar reproducción como segunda validación independiente.
- Diferencia primaria `strategy gross bps − matched baseline gross bps`, mismo calendario y exposición.

| Método | Delta media DEV bps | Delta media DIAG bps |
|---|---:|---:|
| Reversión 12h | −0,090 | +0,237 |
| Continuación post-apertura | −0,335 | +0,285 |
| Persistencia 12h | +0,090 | −0,237 |
| Reacción inicial de apertura | −0,181 | −0,422 |
| Barrido/recuperación | −0,033 | +0,146 |
| Tendencia multidiaria | +0,119 | +0,316 |
| Continuación de ruptura | +0,100 | −0,807 |

**E2/estadística:** 231 con mínimos de muestra, Holm FWER5% no deja ventaja positiva confirmada en ambas épocas. BH FDR 5%/10% tampoco descubre positiva ajustada; hubo **5 positivas nominales p≤0,05 DEV, 2 DIAG, 0 mismas celdas replicadas nominalmente**. XAUUSD reacción inicial mostró una detección ajustada **negativa en DEV** (≈−1,708 bps) no replicada en DIAG. GBPCHF tendencia multidiaria da delta nominal positiva (DEV +1,463/DIAG +1,645 bps, p nominal ≤0,10 ambos), pero gross DIAG ≈+0,090 bps, insuficiente frente a RT 1bp supuesto y no pasa BH.

**E3:** bootstrap conjunto semanal circular de 1,2,4 semanas y 7 hipótesis de método; todos los IC95 de delta por método en DEV atraviesan 0; no ventajas positivas replicadas; `TREND_MULTI_DAY` presenta delta +0,119/+0,316 bps pero gross DEV **−0,245bps**, DIAG +0,338bps. 21 cruces trend delta +0,440/+0,656, gross +0,049/+0,601: exploración posthoc, ni siquiera cubre 1bp RT supuesto. El E3 produce 28 estratos descriptivos y 231 puntuaciones de contracción **NO calibradas como posterior bayesiano**. Documento detallado `docs/research/QORE_NATIVE_E3_POSTHOC_MULTIBLOCK_EXECUTED_RESULTS_AND_HANDOFF_2026-10-12.md`; código `src/qore/infrastructure/trader_lab/qore_native_e3_multiblock_method_shrinkage_v1.py`.

**Disciplina:** 33 pares NO equivalen a 33 factores independientes; FX comparte EUR/GBP/JPY/USD y eventos sincronizados. Bootstrap semanal sincronizado YA implementado en GROSS04/E2; E3 controla sensibilidad serial adicional. No estimar “5–8 factores efectivos” ni “3–5k observaciones” sin análisis cuantitativo propio. FDR puede ser útil para descubrimiento, pero jamás para saltarse certificación NET o seleccionar una única celda por PnL a posteriori.

## 4. Última tarea: 3 screenshots BID/ASK y comparación 231 — COMPLETADO, alcance acotado

Archivo de transcripción 33: `docs/research/data/QORE_NATIVE_USER_BIDASK_SCREENSHOTS_33_SPOT_TRANSCRIPTION_2026-10-12.json`; procedencia `docs/research/QORE_NATIVE_33_USER_BIDASK_SCREENSHOT_PROVENANCE_AND_SPREAD_GATE_2026-10-12.md`. PNG originales **NO copiados a GitHub** (solo hashes y valores transcritos, los archivos originales están adjuntos al chat):

- `1000920175.png`: `7e261efa1364cdf8613c2996b04065d6f1a57ffa819eb9e9c9f640d020fb2897`
- `1000920174.png`: `ab1382d78ccebd3deed5aad3d61c27cf9352729f5c04b2e390951640fc15fbf0`
- `1000920173.png`: `c8794c6d6630d9f5fc0f5e5c30d2c87e139609222a20f6dbb595ac9e7d3132f3`

BID/ASK en las 3 imágenes registrados como una fotografía temporal: terminal indica horas `16:13:xx`, teléfono `10:13`, **sin fecha/zona horaria reconciliadas** ni broker/account/contract identificado. `BTCUSD` visible adicional pero EXCLUIDO de los 33. **GBPUSD** 1,32325/1,32325 spread 0 fotografiado (ANOMALÍA, nunca tratar como coste 0). **NDX100 ≠ NAS100/USTEC**, **SPX500 ≠ SP500/US500** sin homologación del contrato, BLOCKED. Ejemplos spread bps de UNA fotografía: EURUSD 0,08946; XAUUSD 0,91102; XAGUSD 9,07134; NDX100 0,51868 (alias bloqueado); SPX500 0,741932 (alias bloqueado); US30 0,383171.

Último ensayo en [Actions #38266242429](https://github.com/mezas3238-hue/qore-core/actions/runs/38266242429) **5/5 PASS**, código `src/qore/infrastructure/trader_lab/qore_native_e2_231_one_spot_spread_stress_v1.py`, workflow `.github/workflows/qore-native-231-one-screenshot-spread-stress.yml`, artefacto #11755375097. Se mantuvieron 231 celdas; **21 bloqueadas** (GBPUSD/NAS100/SP500 ×7), 210 con ilustración spot; DEV 22 gross>spread, DIAG 33, **ambas 5**. **Esto NO es backtest BID/ASK ni PnL net, no es evidencia de cinco traders ni cinco edges.** Sin costes históricos a fecha de ejecución, comisión, swap, spread variable, slippage, roll, noticia, colas ni fill.

## 5. Problemas prioritarios para el siguiente arquitecto

**P0 — antes de cualquier certificación o LIVE**
1. **Carecemos de histórico temporal BID/ASK** alineado a entradas/salidas 2016–24; tres capturas representan un instante. Obtener ticks/quotes con timestamp evento y recepción, timezone, spread de rollover/noticias, OHLC BID/ASK reconstruido desde datos reales con SHA. Si no existe, `HISTORICAL_NET_SOURCE_BLOCKED`; alternativa captura prospectiva PAPER. No inventar series ni aplicar constante actual al pasado.
2. **Homologar fuente/broker/cuenta** de 12 históricos DEMO vs 21 IC Markets DEMO vs app de pantallas. Confirmar mapping de NAS100/NDX100/USTEC y SP500/SPX500/US500, contratos, tick size, precio por punto, lot size, financiación, market hours y cuenta. Verificar GBPUSD supuesto spread cero con varias cotizaciones.
3. **Coste ejecutable**: bidask en entry/exit, comisión ida/vuelta, deslizamiento, latencia, swaps, margen, parcial fills, trading hours, holidays, gaps, stops/targets y límites del broker. No declarar NET PF/Sharpe/Sortino/DD medidos sin tal evidencia.
4. **NO-NEWS / calendario macro point-in-time**, contrato QORE #814; no filtrar eventos con noticias identificadas ex post; actuar fail-closed.
5. **Holdout verdaderamente prospectivo** distinto de datos usados DEV/DIAG; mantener embargo 2024-09-17+ hasta prereg y autorización explícita con contaminación documentada. No usar ventanas expuestas para promover “OOS virgen”.

**P1 — causalidad, estadística, seguridad de investigación**
6. No confundir Holm demasiado estricto con alpha oculta: **BH 10% y pooling E3 también 0 ganadores positivos replicados**. Cierre científico de siete reglas exactas, no universal de tendencias/reversiones. No intentar retunear sobre 231 resultados visibles (HARKing).
7. Auditar factores EUR/GBP/JPY/USD, cambios de regímenes de volatilidad y dependencia multisemanal sin nueva selección ganadora; mantener resampling semanal sincronizado de los 33 activos y métodos, revisando potencia real.
8. Contratos de sesión: NY cash open 09:30 para índices es *proxy CFD*, FX 08:00 Europe/London es transición OTC, no apertura bursátil; metales NY08:00 proxy no validado; DST/cambio estacional y horarios de broker.
9. Mantener corrección **bootstrap degenerado** E3: en series sin varianza el p-mínimo de Monte Carlo puede dar falso positivo; regla `SE <= max(1e-12,1e-10*abs(estimate))` ⇒ p=1 y test fail-closed. Se detectó por tests y quedó verde tras corrección. Mantener guardia de fuentes SHA 33/33 y 231/231 sin censura.
10. Aún falta metodología de **risk sizing, stops/targets causales, límites DD, diversificación e integración cognitiva** de tres futuros traders, solo DESPUÉS de hipótesis con alpha net reproducible y modelo de ejecución. No trasladar un retorno OHLC de horizonte fijo a orden real.

**P2 — investigación nueva justificada**
11. ADR-001 [PR #831](https://github.com/mezas3238-hue/qore-core/pull/831) propone una **clase distinta**: flujo forzado por reconstituciones de índices/ETF, con anuncios oficiales de altas/bajas, fecha/hora de publicación, fecha efectiva, constituyentes PIT, volúmenes y closing auctions. Empezar por gate **E0 factibilidad de datos**, NO backtest hasta prereg posterior; 33 CFDs son controles, NO sustituyen acciones y subastas.
12. Estudiar microestructura, mercados futuros MNQ/NQ/ES si se justifica mecanismo y costes; no trasladar directamente CFD NAS100 a MNQ; obtener tick BID/ASK, slippage y comisión reales; no usar supuestos públicos genéricos como broker fill.
13. Consultar con **DeepSeek Expert** para revisión externa de causalidad y errores, registrar cambios propuestos y prereg del siguiente ensayo antes de abrir resultados. No concederle autoridad para declarar alpha por opinión.

## 6. Arquitectura documental y archivos de código que DEBEN leer

- Fuente/meta: `src/qore/infrastructure/trader_lab/qore_native_market33_source_census_v1.py`, `src/qore/infrastructure/trader_lab/qore_native_final33_three_m5_g0_v1.py`.
- Matriz: `src/qore/infrastructure/trader_lab/qore_native_33x7_method_market_registry_v1.py`.
- Ejecución causal E1: `src/qore/infrastructure/trader_lab/qore_native_e1_33x7_seven_gross_per_market_v1.py`.
- Inferencia E2: `src/qore/infrastructure/trader_lab/qore_native_e2_33x7_holm_synchronized_weeks_v1.py`.
- BH sensitivities: `src/qore/infrastructure/trader_lab/qore_native_e2_posthoc_bh_sensitivity_v1.py`.
- E3 robustez: `src/qore/infrastructure/trader_lab/qore_native_e3_multiblock_method_shrinkage_v1.py`.
- Spot BID/ASK: `src/qore/infrastructure/trader_lab/qore_native_g1_screenshot_bidask_spot_audit_v1.py`.
- 231 gross vs ONE spot: `src/qore/infrastructure/trader_lab/qore_native_e2_231_one_spot_spread_stress_v1.py`.
- Sus tests están en `tests/infrastructure/trader_lab/test_<mismo_modulo>.py`; workflows `.github/workflows/qore-native-*.yml`. Ejecutar pruebas en GitHub y registrar run ID, HEAD SHA, artefacto y su hash.
- Planes/resultados: `docs/research/QORE_NATIVE_ADR002_33_MARKETS_7_METHODS_FACTORIAL_PLAN_2026-10-12.md`, `docs/research/QORE_NATIVE_E1_33X7_FROZEN_RULES_BEFORE_NEW_OUTCOMES_2026-10-12.md`, `docs/research/QORE_NATIVE_E2_33X7_PRE_OUTCOME_MULTIPLICITY_CLUSTER_PLAN_2026-10-12.md`, `docs/research/QORE_NATIVE_E2_POSTHOC_FDR_HOLM_COMPARISON_EXECUTED_2026-10-12.md`, `docs/research/QORE_NATIVE_E3_POSTHOC_MULTIBLOCK_EXECUTED_RESULTS_AND_HANDOFF_2026-10-12.md`, `docs/research/QORE_NATIVE_33_USER_BIDASK_SCREENSHOT_PROVENANCE_AND_SPREAD_GATE_2026-10-12.md`. Handoff histórico `docs/research/QORE_NATIVE_FULL33_GROSS04_MASTER_HANDOFF_2026-10-12.md`.
- **Cadena de PRs abiertas/draft:** #829 G0 → #830 panel Gross04 → #831 ADR001 → #832 33×7 → #834 FDR → #836 E3 → #839 BID/ASK+spot. Comprobar estado PR antes de merge, usar revisiones separadas; **no merge producción** de ramas exploratorias por accidente.

## 7. Prioridad operativa para los primeros días del siguiente arquitecto

**Día/fase 1:** recuperar este handoff y descargar/hashear artefactos exactos #11727643288 (G0), #11749739981 (E2), #11753217479 (E3), #11754836116 (33 BID/ASK), #11755375097 (231 vs spot). Confirmar que las PRs y workflows están en investigación, documentar defectos reproducidos, no repetir búsqueda global.
**Fase 2:** auditar origen/contrato/tz/cuenta de pantallas, recuperar PNG originales solo si es legalmente posible; determinar disponibilidad de quotes históricos BID/ASK 33 mercados y política NO-NEWS causal; construir **plan acotado de captura forward** si no hay histórico.
**Fase 3:** definir UNA hipótesis **nueva por mecanismo distinto** o acceso a futuros/costes justificado, con hipótesis económica, fuente PIT, potencia por eventos correlacionados, baseline pareado, embargo, falsación y regla STOP antes de ejecutar; pedir auditoría de DeepSeek si hay ambigüedades.
**Fase 4:** solo si existe ventaja económica demostrada, empezar diseño de los tres traders nativos diferenciados, computar PF/Sharpe/Sortino/MaxDD, cartera/riesgo y ejecutabilidad; PRs independientes de PAPER y posterior aprobación explícita para LIVE. Si no pasa gates, dejar 0/3 y explicar las causas.

## 8. Contrato de cierre del handoff

**Hecho:** infraestructura G0 33/33, factorial completo 231/231, FDR alternativa, E3 multibloques/agrupación, 33 BID/ASK spot registrados y prueba 231×spread puntual, con SHA/Actions y sin producción.  
**No hecho:** coste histórico auténtico, backtest net ejecutable, calendario PIT validado, independencia prospectiva genuina, acceso futuro a citas bid/ask continuo, tres traders listos.  
**Decisión científica vigente:** `G0_PASS`, `E2_E3_NO_POSITIVE_SUPPORT`, `G1_NET_BLOCKED`, `NATIVE_CERTIFIED_0_OF_3`. Nunca presentar fotografías BID/ASK como ocho años de fills; nunca esconder los NO_SUPPORT.

**SIGUIENTE ARQUITECTO: reanudar desde este documento, revisar primero las fuentes/SHAs y resolver P0 en el orden indicado.**
