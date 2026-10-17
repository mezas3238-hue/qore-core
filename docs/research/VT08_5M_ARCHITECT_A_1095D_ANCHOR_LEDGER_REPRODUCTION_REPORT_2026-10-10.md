# VT08 5M — Arquitecto A: recuperación de la trazabilidad de densidad M15 en evidencia consumida

Fecha: 2026-10-10. **Nueva ejecución verificada; no certificación.**

## Autoridad y ejecución exacta

- PR A: [#765](https://github.com/mezas3238-hue/qore-core/pull/765), rama `agent/vt08-5m-methodology-source-20261010` (DRAFT).
- Issue fuente/densidad [#762](https://github.com/mezas3238-hue/qore-core/issues/762); integración pendiente con B [#763](https://github.com/mezas3238-hue/qore-core/issues/763); parent [#634](https://github.com/mezas3238-hue/qore-core/pull/634).
- **CI realmente ejecutado GREEN** [GitHub Actions 38069866898](https://github.com/mezas3238-hue/qore-core/actions/runs/38069866898), source-run commit `76491b9c184d79f55f7299665c067ffa163e6200`. Cinco jobs SUCCESS; compile+Ruff+pytest+immutable artifact download+ledger upload en cada mercado.
- Fuente de barras **consumida**: run `35934924907`, software SHA `b2d33e1b4829d8b4afc76983decca8a99131403c`; archivos `market-evidence-1095d.json` existentes, no sealed 7Y. Los cinco artifacts de origen fueron verificados `expired=false` al consultar el run.
- Nuevo módulo reproducible: `src/qore/infrastructure/trader_lab/vt08_5m_architect_a_anchor_ledger_v1.py`. Reutiliza íntegramente las funciones de admisión congeladas de B01 y el auditor previo. **No cambia metodología**, no PnL ni MFE/MAE; anota un registro por barra anchor NY observada, con `first_failure`, clasificación inicial y huella determinista.
- Tests: `tests/infrastructure/trader_lab/test_vt08_5m_architect_a_anchor_ledger_v1.py`; workflow `.github/workflows/vt08-5m-architect-a-anchor-ledger-v1.yml`.

## Resultado de reproducción REAL por mercado

| Mercado | Anclas M15 | Candidatos mecánicos | Pérdida diaria exact-one | Candidatos seleccionados antes de exits |
|---|---:|---:|---:|---:|
| EURJPY | 2.331 | 88 | 6 | 82 |
| USDCHF | 2.331 | 88 | 10 | 78 |
| NZDUSD | 2.331 | 126 | 12 | 114 |
| CADJPY | 2.331 | 88 | 2 | 86 |
| USDCAD | 2.331 | 98 | 0 | 98 |
| **Total** | **11.655** | **488** | **30** | **458** |

**Reconciliación exacta:** `11.655 = 11.167 primeras exclusiones + 488 candidatos`; `488 = 458 candidatos seleccionables + 30 excluidos por ambigüedad de cardinalidad`. **458 no son 458 trades terminales:** el informe histórico ejecutor `VT08_COGNITIVE_EXPANSION_5M_DENSITY_ROOT_CAUSE_AUDIT_V1.md` halló **1 exit incompleto USDCHF**, dando **457 operaciones terminales**. El nuevo ledger es solo admisión, no reprodujo las salidas ni PnL.

## Desglose por año NY, candidatos mecánicos previos a cardinalidad

| Mercado | 2023* | 2024 | 2025 | 2026* | Total |
|---|---:|---:|---:|---:|---:|
| EURJPY | 6 | 33 | 29 | 20 | 88 |
| USDCHF | 7 | 30 | 28 | 23 | 88 |
| NZDUSD | 12 | 47 | 36 | 31 | 126 |
| CADJPY | 6 | 36 | 31 | 15 | 88 |
| USDCAD | 10 | 33 | 33 | 22 | 98 |
| **Total** | **41** | **179** | **157** | **111** | **488** |

*2023 y 2026 son **cortes parciales del corpus**, NO anualidades enteras y NO se deben extrapolar como velocidad anual. Los archivos anuales de cada mercado incluyen desglose por causa y anchor, no solo esta tabla.

## First-failure reconciliado contra auditoría histórica

| Primer descarte (B01 estrecho) | Regenerado 1095D | Semántica honesta |
|---|---:|---|
| C2_CLOSE_NOT_INSIDE_REFERENCE | 3.987 | POSIBLE restricción estrecha; fuente primaria pendiente; no es trade recuperado |
| BIAS_UNRESOLVED | 2.071 | Bias fuente y día de QORE pendientes de adjudicación |
| C2_BOTH_SIDES_SWEPT | 1.347 | Selección direccional no resuelta; no abrir ambos lados |
| C2_SIDE_BIAS_MISMATCH | 1.317 | Confluencia requerida por subset B01 |
| C2_NO_REFERENCE_SWEEP | 1.085 | Scope de referencia narrow B01 |
| NO_PROTECTED_SWING | 769 | PS necesario para positional; no equivale a ausencia de otras familias |
| INCOMPLETE_SOURCE_H4 | 406 | Falta de barra cerrada de origen |
| MULTIPLE_PROTECTED_SWINGS | 145 | QORE selection containment, no prioridad fuente universal |
| INCOMPLETE_SOURCE_DAY | 40 | Falta dato QORE source-day |
| **Descarte total** | **11.167** | **Primera causa, no todas las causas simultáneas** |

### Artefactos producidos en GitHub

[CI 38069866898](https://github.com/mezas3238-hue/qore-core/actions/runs/38069866898) publicó cinco pares `<market>-anchor-ledger.json` + `<market>-annual-summary.json`:

- EURJPY: artifact ID `11675458468` (digest `sha256:7baa4117decf2509abb1a149e60e21f060086518aef4ae5cae060df8179ecf9a`)
- USDCHF: `11675908116` (`sha256:cb5c38d4b37a98f94586d6fc4ff845a7d035c92d95d4177e445da5d069075a4d`)
- NZDUSD: `11675939478` (`sha256:fed54449cd39274482b10f23394bdd47362ab4fae661acc35851e95a3a31654e`)
- CADJPY: `11675669782` (`sha256:c3669818f07c85ea9c9218472653773e38e0f2b2c2dbf37bad1320728c0f13b5`)
- USDCAD: `11676448977` (`sha256:9a7da313445f082e085acc3cc269143f000e9e9a197be351d2a17d249e57a4fa`)

Artifacts are retained **30 days**, not an immutable forever archive; the code/corpus-run IDs and SHA anchors provide reproduction. Preserve evidence durably before expiry.

## Interpretación y próximos bloqueos P0

- Se **resolvió reproducibilidad causal del funnel M15**, no el déficit de densidad ejecutable. C2 out-of-range es el principal grupo pendiente de adjudicación frente al autor; su cifra no es un número de nuevas operaciones.
- Seis familias fuente siguen pendientes auditoría íntegra; solo B01 positional C2 M15 es machine-complete. No convertir M3/M5 estructuras en fills.
- Falta fuente primaria vídeo/audio/framebook con hash revalidado y minuto exacto; falta ledger source-vs-QORE de **all-fail** (este entrega first-fail), y downstream matched fills/economics.
- El CandidateEvent V1 fue propuesto a Arquitecto B en #763; B debe revisar schema y acordar el golden causal fixture antes de producir un consumed replay. El reporte de esta ejecución **no** muestra nueva cognitiva gobernando trades.
- Debe aprobarse nuevo umbral numérico de trades ejecutados/2Y por el Owner antes de abrir el holdout 7Y. El `minimum_trades_per_market_2y=50` en freeze histórico está **retirado como gate**, pero aún existe en una constante legacy del contrato y precisa cambio de versión gubernamental, no edición silenciosa.
- PF raw y DD nuevos **NO MEDIDOS**. Es incorrecto declarar mejor edge, nuevos terminales o certificación basándose en este ledger.

Autoridad: GitHub research-only. PRs draft/no merge. Sin VPS/DEMO/LIVE/producción/capital. Archivo 7Y SELLADO.
