# VT08 5M — DOS VALIDACIONES NUEVAS: BIAS AS-OF REAL Y C3 FVG SHAPE (SIN FILLS)

**Fecha:** 2026-10-10. Methodology Architect A, [PR #765](https://github.com/mezas3238-hue/qore-core/pull/765), issues #762 / #763, coordinación #634. Investigación only; Owner 01/05/09 NY; cinco mercados; evidencia histórica ya CONSUMIDA 1095D y SHA `b2d33e1b4829d8b4afc76983decca8a99131403c` del run 35934924907. 7Y sealed: NO consultado.

## A. Prueba temporal del sesgo diario B01 original

[GitHub Actions run **38078585235**](https://github.com/mezas3238-hue/qore-core/actions/runs/38078585235): **SUCCESS 5/5**, code SHA `d254370f76e978d90194bb48b0363fd88e08e1b5`. Hermetic tests + lint + 5 REAL M15 source-day reconstructions.

| Mercado | Ventanas NY | Bias completo, resuelto, hash M15 | Bias completo, no resoluble | 2 source days faltantes |
|---|---:|---:|---:|---:|
| EURJPY | 2331 | 1851 | 471 | 9 |
| USDCHF | 2331 | 1854 | 468 | 9 |
| NZDUSD | 2331 | 1929 | 393 | 9 |
| CADJPY | 2331 | 1884 | 438 | 9 |
| USDCAD | 2331 | 1935 | 387 | 9 |
| **TOTAL** | **11655** | **9453** | **2157** | **45** |

El código `src/qore/infrastructure/trader_lab/vt08_5m_source_bias_asof_attestation_v1.py` crea por anchor:
- Las 2 velas fuente de 17:00 NY a 17:00 NY en su orden exacto y **sus M15 constituyentes**; fecha/cierre originales.
- `SHA256(M15 OHLC closed sequence)` independiente por día y comparación del agregado H/L/O/C.
- `bias_feature_cutoff = current_source_day.closed_at`, siempre **<= decision_at**, no rellenado artificialmente con H4 open.
- `bias_side` resuelto/UNRESOLVED por `resolve_bias` B01 congelado; no fuente universal TTrades certificada.
- Tests adversariales: fuga de dato futuro nula, mutación de vela cambia hash, día incompleto fail closed, DST/source clock robustez pendiente un caso más.

**Distinción para B #763:** Este aporte soluciona **únicamente el bloqueador de causal source-day bias por valor, cierre y hashes**. NO produce los valores y timestamps del resto de Situation (POI, liquidity, journey, risk, etc.), ni firma A/B. Por tanto **todavía NO transforma CandidateEvent V1 en cognitive_ready** y B debe mantener `APPROVED_A_B_MANIFEST_SHA256=None`.

### Auditoría reproducible de archivos

Run con JSON de **cada ventana** y razones, artifacts (30d):
- EURJPY 11679673601 sha256:16bdc50e9f786817ced9602f93815e5ccf9d317f2f2359b9868699f169c31e41
- USDCHF 11679770051 sha256:ebf4c401c6bee69b74c73e2fd4e3a79a42eb169609fb71f534ad5b541d14d66b
- NZDUSD 11678723313 sha256:52923d36d8bb27c70ba63d44e8c4c81950e1276432489e373869c1a45c38e639
- CADJPY 11679024762 sha256:5ec25afd3e81a9b3464d9a03640a5982e79e310ddaa9423ca9ba2b6c9dee88eb
- USDCAD 11678558686 sha256:f355dc67dc7864266f4d101f081e70065a030d95083aa3982f1765b20c64b16d

## B. Auditoría de geometría C3 separada de trading

**Pre-registro ANTES de la ejecución** [VT08_5M_A_C3_FVG_POI_CISD_PS_SHAPE_PREREG_2026-10-10.md](VT08_5M_A_C3_FVG_POI_CISD_PS_SHAPE_PREREG_2026-10-10.md), commit `7806a11f87dae1e183825c578081a79bef43685c`.

[GitHub Actions run **38078899345**](https://github.com/mezas3238-hue/qore-core/actions/runs/38078899345): **SUCCESS 5/5**, exact tested code SHA `9270a2b300d8c0ed10d30dda6d58358f0c110bb9`.

`src/qore/infrastructure/trader_lab/vt08_5m_c3_fvg_poi_cisd_ps_shape_census_v1.py` verifica C1+C2 H4; bias QORE as-of; C2 sweep/close-inside contra C1 alineado; FVG 3-bar del lado bias **confirmado y no invalidado ANTES de C3**; POI retest durante C3; CISD y swing protegido confirmado *después del primer touch*; siguiente M15 open y orientación de stop meramente geométrica.

| Mercado | C2 alineadas H4 | C3 POI + CISD + PS shapes | de ellas C2 también PS confirmado | además next-M15-open stop orientado |
|---|---:|---:|---:|---:|
| EURJPY | 271 | 45 | 20 | 17 |
| USDCHF | 273 | 51 | 31 | 31 |
| NZDUSD | 311 | 54 | 27 | 24 |
| CADJPY | 287 | 48 | 23 | 20 |
| USDCAD | 260 | 54 | 21 | 18 |
| **TOTAL** | **1402** | **252** | **122** | **110** |

**Lectura exacta:**
- 252 geometrías **SHAPE_ONLY_NOT_SOURCE_COMPLETE**, potenciales POIs que cumplen este subtipo C3 de FVG preexistente; **0 trade y 0 PnL**.
- 122 conservan confirmación PS también en C2; 110 son esa intersección con precio de entrada next-M15 y riesgo orientado, pero **no son fills broker**.
- Esta FVG-only + prior C2 reversal/bias es una subfamilia **estrecha, no toda la C3 de TTrades**. No extrapolar 252 como techo real C3 ni sumar 252 a los 488/1514 baseline/C2 experiments.
- El autor NO entregó en artículos consultados umbral numérico universal "large wick"; no existe regla congelada de POI-priority, TP, stop-offset ni lifecycle. Habilitar estas 110 como entradas produciría **falsos SOURCE_COMPLETE**.
- En cada uno de estos estados no se ha ejecutado backtest financiero, ni cognitiva B, ni BID/ASK, ni OPEN/LIVE.

### Evidencia de artefactos por símbolo

Run 38078899345, outputs JSON shape/time/fingerprint, 30d:
- EURJPY 11679740588 sha256:7ece47b133c2521095661b0b7c919468821a3e0baf9ffaf17807bc851ee7ea94
- USDCHF 11680085008 sha256:06b16b914aae7580e9b271d3590b8552bc4cdc1f17f764d2b777581cdcf9114e
- NZDUSD 11679589626 sha256:c68598cbc72b51758f7bfefdf71f192e4df11d5352a9e5ad4d74d204acebe350
- CADJPY 11679790503 sha256:c5496e15c596f1c16a48a51d6cf4ca72134d96591f69aac390d107b0914d17da
- USDCAD 11678938762 sha256:22c85cffc8eaf7c51a2b1a00897b66993fb3f387742eb39e4ffb939b58645487

## C. Auditoría fuente posterior: dos C3 NO equivalentes

[VT08_5M_A_TTRADES_TWO_C3_IDENTITIES_AND_DAILY_EQ_FIDELITY_GAPS_2026-10-10.md](VT08_5M_A_TTRADES_TWO_C3_IDENTITIES_AND_DAILY_EQ_FIDELITY_GAPS_2026-10-10.md).

1. `C3_AFTER_C2_REVERSAL_CONTINUATION` (TTrades Sep 2025): C2 deep wick y close inside, entra en C3 tras POI/CISD/PS; último censo estima 110 SHAPE narrow con C2 PS/next open (NO trades).
2. `C3_CLOSURE_TO_C4` (TTrades Dec 2025): si C2 NO completó cierre, C3 body-engulf closure puede habilitar **C4** posterior, nunca llamar entrada a vela C3 pre-close. Es family diferente y todavía no censada.
3. `DAILY_EQ_CONTINUATION` (TTrades Dec 2025): sesgo original `resolve_bias` NO contempla todas las continuaciones del autor por EQ de previous day y posterior LTF confirmation; nueva familia de fuente requiere diseño causal y datos. No suprimir `BIAS_UNRESOLVED` unilateralmente.

## Veredicto / acciones prioritarias

P0: Full video/framebook fuente primaria original y jerarquía POI/target/wick; productor real A→B as-of para estados Situation restantes; separar C3 closure-to-C4/EQ continuation sin asignarles PnL; decidir números Owner para densidad real **ejecutable** pre-7Y. El experimental C2 intracycle 1514 fills / PF 0.712–1.139 / max DD 11.25–53.10R sigue **REJECTED**; no reutilizar sus trades como evidencia de edge ni optimizar sus resultados.

**No hay un trader certificado ni full-cognition real replay en este trabajo.** Research solo GitHub. No VPS, no cambios producción, no abrir archive sealed 7Y.
