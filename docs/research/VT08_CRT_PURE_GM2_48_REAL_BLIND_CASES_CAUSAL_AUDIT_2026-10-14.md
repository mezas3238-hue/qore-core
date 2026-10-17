# VT08 CRT PURE — Auditoría ciega de 48 casos reales G-M2: prefijos causales

**14-OCT-2026. PR #626 DRAFT; SIN MERGE. Certificación NO EMITIDA.**

## Alcance, fuentes y verificación

Se examinaron los 48 registros de `gm2-blind-cases.jsonl`, sin abrir `gm2-sealed-c3-witness.jsonl` como input de clasificación, procedentes de GitHub Actions [#38617425240](https://github.com/mezas3238-hue/qore-core/actions/runs/38617425240), código `1dbac0d7cde881288c4969f2d9d19a299e6496d8`. AUDUSD artifact **11920048252**, USDJPY artifact **11921035427**. Para cada ZIP se verificaron los cinco hashes internos declarados en `SHA256SUMS.txt`; cada mercado contiene 24 registros, sin ID duplicado. En los 48 casos se comprobó que todos los M15 observados son consecutivos y su último cierre coincide exactamente con `decision_clock_utc` (ninguna M15 futura en el prefijo).

Origen previo de M5 QORE/CIBO Atlas: [Actions #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), AUDUSD **148.171 M5**, USDJPY **148.201 M5**; 296.372 M5 en total. Cohorte previa R2-C, no holdout virgen. Los 48 NO son operaciones, NO son Model #1 autenticados ni demuestran edge.

## Resultados verificables, solo geometría M15-C2

| Estado observable al cierre C2 | AUDUSD | USDJPY | Total |
|---|---:|---:|---:|
| HIGH_RETURN: barrido unilateral alto + cierre dentro C1 | 7 | 7 | 14 |
| LOW_RETURN: barrido unilateral bajo + cierre dentro C1 | 5 | 5 | 10 |
| OUTSIDE_RANGE: un lado barrido pero cierre externo | 4 | 4 | 8 |
| TWO_SIDED: ambos extremos C1 penetrados | 4 | 4 | 8 |
| NO_SWEEP: ningún extremo C1 penetrado | 4 | 4 | 8 |
| **TOTAL** | **24** | **24** | **48** |

Estos estados son **QORE RESEARCH OBSERVATIONS** de dos M15 locales, no sentencias canónicas del autor. Las 24 geometrías HIGH_RETURN/LOW_RETURN son candidatas C2 observacionales, no entradas ni 24 éxitos. Ninguno de los 48 expedientes incorpora selección original inequívoca de old CRTH/CRTL ni constancia source-authorized de confirmación Model #1 y DOL. Por lo tanto el veredicto de **certificación de entrada** para los 48 es `NOT_ADJUDICATED; NO_CONCEPTUAL_EXECUTE_AUTHORIZED`, no un resultado de cognitiva ejecutada caso por caso.

**Seguridad metodológica:** cuando no hay un Model #1 canónico adjudicado, mantener `WAIT / UNRESOLVED` en la ruta de certificación, pero nunca presentar `WAIT` como predicción acertada. Cuando una hipótesis completa resulta contradictoria y confirmada, `ABSTAIN` debe tener precedencia. Esto NO supone atribuir al autor los buckets C2.

## Registro individual cronológico; lectura SOLO del prefijo

| Mercado | Case ID | Cierre causal | Contexto H4 | Geometría M15 C2 |
|---|---|---|---|---|
| AUDUSD | `6d49076d495cecf59476` | 2024-09-26 01:30 UTC | BEARISH | OUTSIDE_RANGE |
| AUDUSD | `c82d29eba20a76f4f9f7` | 2024-09-26 01:45 UTC | BEARISH | HIGH_RETURN |
| AUDUSD | `5230c1567075f6b3d3ec` | 2024-09-26 02:15 UTC | BEARISH | NO_SWEEP |
| AUDUSD | `0bcabf815803e1a713c6` | 2024-09-26 02:30 UTC | BEARISH | TWO_SIDED |
| AUDUSD | `1dd103b4d58c0bede7d0` | 2024-09-27 01:30 UTC | BULLISH | LOW_RETURN |
| AUDUSD | `2311a3da997c6381c3e0` | 2024-09-27 01:45 UTC | BULLISH | OUTSIDE_RANGE |
| AUDUSD | `27271e200a4228893f06` | 2024-09-27 02:15 UTC | BULLISH | NO_SWEEP |
| AUDUSD | `e042f891641587d0016b` | 2024-09-27 03:15 UTC | BULLISH | HIGH_RETURN |
| AUDUSD | `3b5d0d3fb75c91505da9` | 2024-09-30 14:00 UTC | BULLISH | TWO_SIDED |
| AUDUSD | `dad7381c63f01b65a5a2` | 2024-09-30 15:00 UTC | BULLISH | HIGH_RETURN |
| AUDUSD | `f8518e96f9e8f829e7aa` | 2024-09-30 15:15 UTC | BULLISH | LOW_RETURN |
| AUDUSD | `092c03af89a49cc2f8f0` | 2024-10-07 14:00 UTC | BULLISH | HIGH_RETURN |
| AUDUSD | `040945b4e3fb6dd4b2ef` | 2025-09-23 01:30 UTC | BULLISH | LOW_RETURN |
| AUDUSD | `f1e95e9ed3b79f0012bb` | 2025-09-23 01:45 UTC | BULLISH | TWO_SIDED |
| AUDUSD | `713c5d874eb6a08b5346` | 2025-09-23 02:00 UTC | BULLISH | HIGH_RETURN |
| AUDUSD | `27494e5327fc6d7429f4` | 2025-09-23 02:15 UTC | BULLISH | OUTSIDE_RANGE |
| AUDUSD | `140955fe5365d73ea789` | 2025-09-23 03:00 UTC | BULLISH | NO_SWEEP |
| AUDUSD | `318035b9fc0aeb80fc3e` | 2025-09-24 01:30 UTC | BULLISH | LOW_RETURN |
| AUDUSD | `47d200bcc6c42c0e4962` | 2025-09-24 01:45 UTC | BULLISH | OUTSIDE_RANGE |
| AUDUSD | `12cbbbdc25faf34dade6` | 2025-09-24 02:00 UTC | BULLISH | HIGH_RETURN |
| AUDUSD | `67daf927bd42c72c475a` | 2025-09-24 04:15 UTC | BULLISH | TWO_SIDED |
| AUDUSD | `3dac3e0546ef1ad23a6e` | 2025-09-26 16:00 UTC | BULLISH | NO_SWEEP |
| AUDUSD | `f275bab49c8a3cc7eaaf` | 2025-10-01 14:00 UTC | BEARISH | LOW_RETURN |
| AUDUSD | `f60980956de383e4c11d` | 2025-10-20 14:00 UTC | BULLISH | HIGH_RETURN |
| USDJPY | `bfad075c584c3fdb122a` | 2024-09-23 13:30 UTC | BULLISH | TWO_SIDED |
| USDJPY | `88cf2b52f693a091dc72` | 2024-09-23 13:45 UTC | BULLISH | HIGH_RETURN |
| USDJPY | `d147f2d6e6fda7428d34` | 2024-09-23 14:15 UTC | BULLISH | OUTSIDE_RANGE |
| USDJPY | `834f934739a776f801ab` | 2024-09-23 15:00 UTC | BULLISH | LOW_RETURN |
| USDJPY | `6ea683c401e0e2df0146` | 2024-09-23 15:30 UTC | BULLISH | NO_SWEEP |
| USDJPY | `0722af53179fa0338b92` | 2024-09-24 01:30 UTC | BEARISH | HIGH_RETURN |
| USDJPY | `4783156f976713cad8be` | 2024-09-24 01:45 UTC | BEARISH | OUTSIDE_RANGE |
| USDJPY | `a9de8b91f32b01e78d4c` | 2024-09-24 02:00 UTC | BEARISH | LOW_RETURN |
| USDJPY | `0bd0871b248de26eb424` | 2024-09-24 02:30 UTC | BEARISH | NO_SWEEP |
| USDJPY | `f90b2d6cc92fea40ebae` | 2024-09-24 03:30 UTC | BEARISH | TWO_SIDED |
| USDJPY | `3821acbcc39bc5f789f9` | 2024-09-24 13:30 UTC | BULLISH | HIGH_RETURN |
| USDJPY | `0f8719f24223b4d4dc52` | 2024-09-25 01:30 UTC | BULLISH | LOW_RETURN |
| USDJPY | `84ec4940d8bf0e8b38fd` | 2025-09-22 13:30 UTC | BULLISH | LOW_RETURN |
| USDJPY | `5e97dace044662797696` | 2025-09-22 13:45 UTC | BULLISH | OUTSIDE_RANGE |
| USDJPY | `afbab96247ce354d490c` | 2025-09-22 14:00 UTC | BULLISH | HIGH_RETURN |
| USDJPY | `e34df3c5a92944b92924` | 2025-09-22 14:15 UTC | BULLISH | NO_SWEEP |
| USDJPY | `c6c6afc0fdfcc2c48055` | 2025-09-22 15:30 UTC | BULLISH | TWO_SIDED |
| USDJPY | `187a212a31f072009d44` | 2025-09-30 13:30 UTC | BULLISH | HIGH_RETURN |
| USDJPY | `c2a8c2e7985361241c87` | 2025-09-30 13:45 UTC | BULLISH | OUTSIDE_RANGE |
| USDJPY | `60535deefbb230b30c01` | 2025-09-30 14:15 UTC | BULLISH | TWO_SIDED |
| USDJPY | `a6ab68db66d65226e343` | 2025-09-30 14:30 UTC | BULLISH | NO_SWEEP |
| USDJPY | `63ccde965a248a65d714` | 2025-10-02 13:30 UTC | BULLISH | HIGH_RETURN |
| USDJPY | `dd1c4017ce160744596b` | 2025-10-08 13:45 UTC | BEARISH | HIGH_RETURN |
| USDJPY | `6bbae0b218a4b958c8da` | 2025-10-08 15:00 UTC | BEARISH | LOW_RETURN |

## Análisis de fallos frente a G-M1..G-M5

1. **G-M1 PARTIAL**: `MODEL_1_REFERENCE_SELECTION` figura `AMBIGUOUS` en `crt_pure_source_registry.py` a pesar de `strategy_identity_ready()==True` para la identidad CRT general. También falta DOL, caducidad exacta y arbitraje multifuente. Ninguna geometría C2 soluciona esto.
2. **G-M2 PARTIAL**: expediente real causal auditado y positivo/negativo/ambiguo cubierto; faltan gráficos ciegos valorados contra la **fuente original** y la adjudicación específica de old-level, elección independiente por un auditor de método. No declarar PASS.
3. **G-M3 PARTIAL**: no hay salida `reason()` de la cognitiva contrastada con dictámenes fuente originales de estos 48; la validación local de no-leakage/no sizing NO equivale a entender el CRT.
4. **G-M4 PARTIAL**: código reforzado por `model1_source_ready()`, `unresolved_model1_source_concepts()` y `assess_model1_certification_entry_family()`; evita promover el `EXECUTE` de la ruta de laboratorio heredada cuando falta el selector fuente. Aún falta prueba end-to-end sobre pipeline completo real.
5. **G-M5 NOT_CERTIFIED**: se prohíbe emitir certificado si hay `PARTIAL` u `OPEN`.

## Restricciones de trabajo y siguiente reparación

- Lo siguiente es contrastar con RomeoTPT los localizadores originales y resolver **old-high/old-low ownership**, confirmación y destino antes de declarar modelo auténtico. Si la fuente no lo define, preparar una **propuesta explícita de ingeniería para aprobación del Owner**, sin calibrarla por retorno histórico.
- Tras cerrar G-M1, procesar el mismo corpus a través de `CrtPureSituationModel -> reason() -> certification-specific R2 router`, persistiendo hipótesis, contradicciones y decisión; confrontar cegado con auditor humano (G-M3).
- G-M4 necesita probar expiración C3, hipótesis terminal, no fallback, frontera de autoridad y aislamiento de mercados en una cadena completa, no solo pruebas unitarias.
- Ni sizing, ni lotes, ni capital, ni volumen, ni apalancamiento, ni riesgo por operación son parte de certificación. Solo CIBO administra lotaje/capital. NO DEMO, LIVE, VPS, produccion, órdenes, ni merge sin orden.
- Conservar SHA/ZIP de artifacts y atender Issue #837 por vencimiento.

**DICTAMEN AUDITORÍA:** prefijos y geometría QORE revisados, NINGÚN Model #1 certificado; G-M1 PARTIAL / G-M2 PARTIAL / G-M3 PARTIAL / G-M4 PARTIAL / G-M5 NOT_CERTIFIED.