# VT08 A→B NARROW CANDIDATE REAL SOURCE LINEAGE — 488/458 REPRODUCIDO

2026-10-10, Architect A, PR [#765](https://github.com/mezas3238-hue/qore-core/pull/765), issues #762/#763, research-only. **No cognitive PnL replay and no promotion.**

## Prueba ejecutada

[GitHub Actions run 38079270152](https://github.com/mezas3238-hue/qore-core/actions/runs/38079270152) `SUCCESS` 5/5, exact tested SHA `b4c7b2df356e1df81bfcf66c810ee1cc794d61e4`, `src/qore/infrastructure/trader_lab/vt08_5m_a_b_narrow_source_lineage_v1.py`. Su inputs: artefactos históricos consumidos 1095D run 35934924907 código `b2d33e1b4829d8b4afc76983decca8a99131403c`; sealed 7Y NO leído.

Por cada candidato B01 original evaluado en cada Owner anchor:
1. `evaluate_expansion_at_entry_indexed` sin reescribir el método decide el candidato.
2. `attest_bias` real reconstruye source days 17NY→17NY con exacta OHLC y SHA256 de cada M15, comprueba lado y cutoff source-day cerrado.
3. Se rehacen C1 y C2 desde sus 16 M15 reales, se verifica OHLC coincidente, `cisd_confirmed_at` pertenece a cierre de una de esas velas y no es futuro.
4. `from_narrow_b01_candidate` REAL de A crea el `Vt08CandidateEventV1` y `source_event_id` estructural estable. Se añade en **envelope extended research** un `bias_feature_cutoff` derivado del último cierre source day real (ya no el placeholder), ambos SHA source-day, ambos SHA H4, cierre CISD y hash `source_lineage_sha256` vinculado con `event_id`.
5. Se declaran explícitamente `cognitive_feature_provenance_complete=False`, `joint_a_b_contract_signed=False`, sin `cognitive_feature_cutoffs` inventados, `trades_executed=0` y `pnl_evaluated=False`. Este anexo NO muta/firma CandidateEvent V1. B debe volver a verificar desde archivo bruto antes de usarlo.

## Resultado 5/5 (exacto)

| Mercado | Owner H4 observados | CandidateEvent con bias+C1+C2+PS lineage | Conflictos one/NY-day | Candidatos únicos antes de salida |
|---|---:|---:|---:|---:|
| EURJPY | 2331 | 88 | 6 | 82 |
| USDCHF | 2331 | 88 | 10 | 78 |
| NZDUSD | 2331 | 126 | 12 | 114 |
| CADJPY | 2331 | 88 | 2 | 86 |
| USDCAD | 2331 | 98 | 0 | 98 |
| **TOTAL** | **11655** | **488** | **30** | **458** |

**Reconciliación** exacta con el histórico first-failure B01: 488 mechanical, 30 ambiguous, 458 selected. 457 terminal históricos de fuente vieja **NO** se reproducen aquí ni se debe llamar a 458 nuevos fills. Tampoco suma 1514 fills simulados de experimento C2 intracycle falsado (no mezclar identidades).

### Artifact archive (30d)

[Run 38079270152](https://github.com/mezas3238-hue/qore-core/actions/runs/38079270152) contiene en cada zip el JSON **completo** con cada CandidateEvent envelope + SHA/closed-bar provenance y resumen:
- EURJPY ID 11680255365, sha256:e34206e644ab31dcacfb9f6bcd2c1021a1b24ecfc38793e0f5ebd9007e0f8653
- USDCHF ID 11678499595, sha256:41d363ca456d8ee99518da1c1eda7b6cbfd69709c7c21d674678ac121d064b89
- NZDUSD ID 11680230479, sha256:d28c03abf4e97a788f702aa3739a6825871ffcad3035014e6e885f235e94a71a
- CADJPY ID 11678924049, sha256:41940a7208f46943b49d2f6b83b2e9d4d4ead7dd7ec0a3b4c43b7e26b436644f
- USDCAD ID 11680235353, sha256:a1b0c8f8d6777b3b1ea8943bf3a8d78a8299f99fe5e877162b8ecd63a9f1d066

## Interface challenge to Architect B #763

1. Comprueba que la extensión de A `bias_feature_cutoff` es **exacta** contra M15 + source-day OHLC (no sólo ISO string). Eso elimina el código de bloqueador `A_B:DAILY_BIAS_SOURCE_TIME_UNATTESTED` sólo después de verificación independiente, **NO** el de situación completa ni firma.
2. `cognitive_feature_cutoffs` todavía no está provisto y la puerta B debe continuar fail-closed: Cognitive V1 todavía **0 eventos ejecutados en datos reales**.
3. No permitir `joint_contract_manifest_sha256` arbitrario; no hay SHA bilateral. `source_event_id` para WAIT/KILLED; `event_id` para traza snapshot; `source_lineage_sha256` de anexo es evidencia, no firma A/B.
4. Los 488 son C2_COMPLETED positional-entry narrow B01; no están validados todas las reglas originales TTrades, con PF histórico fallido. El 7Y sigue sellado y el trader no está certificado.

## Dependencias P0 próximas

A: source POI/liquidity/EQ/daily bias alternativo + valores/sellados as-of por feature, source-author target/lifecycle/familias; 3.987 early B01 close-not-inside no son trades C3. B: integrar los 488 documentos al auditor de readiness con verificación de data lineage y `cognitive_ready=False` explícito, después formular manifest conjunto solo cuando situación completa. CIBO, QDLE, VPS, capital, LIVE no se tocan.
