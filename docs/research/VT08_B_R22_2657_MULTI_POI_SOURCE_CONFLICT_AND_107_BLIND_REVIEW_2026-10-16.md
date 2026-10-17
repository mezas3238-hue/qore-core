# VT08 B R22 — Cruce causal de POI H1, FVG y mínimo intradía (2.657 casos), revisión ciega 107

**Fecha:** 16-oct-2026 · **Arquitecto B:** `agent/vt08-5m-cognition-replay-20261010`, PR #764 DRAFT, coordinación A #765. **Reglas Owner:** sólo VT08 TTrades + cognitiva VT08, QORE-alpha excluido, NO sizing, NO 7Y, NO trading VPS/LIVE/DEMO y NO merge.

## Verificación real en GitHub

- [Actions R22 #38975204483](https://github.com/mezas3238-hue/qore-core/actions/runs/38975204483) **SUCCESS 6/6 jobs**, Ruff + **14/14 tests adversariales** para frenar firmas sintéticas, selección retrospectiva, clocks futuros, POI supuestamente source-complete, duplicados, hashes R18/R19 falsos y manipulación de lows/contexto; cinco mercados reales comparados. HEAD del run `731c495d318a1a6f0ad5f756004a2ba1c8803299`.
- `src/qore/infrastructure/trader_lab/vt08_b_r22_multi_poi_contradiction_join_v1.py` — join **source-only**, sin importar productor A ni datos PnL. Reusa auditor independiente B R18 (M3/M15), preregistro B R19 y diagnóstico B R21, por **case_id_sha256/C2/CISD/C3 UTC**. Se verifica digest canónico R18 y R19 **fijado por mercado**, raw SHA M3 entre R18 y R21, conteos y fuente de cada low/FVG pre-CISD, `available_at<=C2.open`, `first_touch_M3.closed_at<CISD.closed_at`, distinción misma barra (intrabar D), clases de contexto NY y bloqueos Owner/economía.
- `tests/infrastructure/trader_lab/test_vt08_b_r22_multi_poi_contradiction_join_v1.py`
- `.github/workflows/vt08-b-r22-native-multi-poi-context-conflict.yml`
- Tres artifacts GitHub Actions **inmutables en la selección**:
  - R18 [#38902918264](https://github.com/mezas3238-hue/qore-core/actions/runs/38902918264), `9349cc84ee245c68291db60b4613411453061c94`;
  - R19 [#38903529731](https://github.com/mezas3238-hue/qore-core/actions/runs/38903529731), `e999e127be84a1ebb9d3e8b1d13e110cfa2cb51a`, preregistro `VT08-OWNER-R19-POI-BLIND-PRE-PNL-2026-10-16`;
  - R21 [#38903207496](https://github.com/mezas3238-hue/qore-core/actions/runs/38903207496), `8c24c425810cb960f7a3384809a1a50a2eeb6516`.
  Los SHA de los **JSON** R18/R19 son cotejados con constantes B publicadas anteriormente; no se toma HEAD mutable ni se permite rebautizar la muestra.
- Primer run R22 #38975145496 **FAIL por Ruff I001 import groups**. Corregido sin relajar pruebas, segundo run #38975204483 **6/6 SUCCESS**. No ocultar este fallo de QA.

## Resultado: concurrencias físicas por mercado

La expresión `FVG bullish pre` significa solo **zona FVG H1 de tres H1 previas cerradas (últimas 3), existente antes de C2 y tocada por M3 cerrada ANTES de la barra CISD**. No se deduce que sea el POI significativo/elección del autor. `NY low` es mínimo observado desde **00:00 Nueva York hasta C2.open** usado solo como comparación estructural QORE, NO regla universal TTrades.

| Mercado | Censo íntegro | Bull FVG pre CISD | Bull FVG + NY low barrido | Bull FVG + NY low NO barrido | Bull FVG + NY contexto gap | 2 o 3 H1 lows tocados antes CISD | Dossiers R19 |
|---|---:|---:|---:|---:|---:|---:|---:|
| EURJPY | 538 | 31 | 3 | 28 | 0 | 105 | 21 |
| USDCHF | 518 | 36 | 6 | 30 | 0 | 110 | 21 |
| NZDUSD | 550 | 33 | 2 | 29 | 2 | 123 | 21 |
| CADJPY | 516 | 33 | 3 | 30 | 0 | 117 | 21 |
| USDCAD | 535 | 32 | 3 | 29 | 0 | 119 | 23 |
| **TOTAL** | **2.657** | **165** | **17** | **146** | **2** | **574** | **107** |

Adicionalmente, **3 FVG bajistas** estuvieron tocados antes del CISD; esos tres NO barrieron el mínimo NY day-to-date en el censo físico, lo que refuerza su función como controles negativos *geométricos*, no como invalidaciones automáticas. Los **11 contextos NY incompletos** quedan desconocidos, no se imputan como barridos/no barridos.

### Número de lows H1 previos tocados antes CISD (conteos de velas, no niveles distintos)

| Candidatos H1 lows tocados | Casos |
|---|---:|
| 0 | 963 |
| 1 | 1.120 |
| 2 | 418 |
| 3 | 156 |
| **Total** | **2.657** |

**574** casos tienen **más de una vela H1 baja tocada**: una selección arbitraria de low/POI entre ellos sería una ambigüedad material. Si dos velas registran el MISMO precio, el conteo es de velas/fuentes, NO de niveles de precio distintos; por tanto tampoco demuestra exactamente 574 conflictos de niveles únicos. El perfil cualitativo importa.

Entre los 165 FVG bullish PRE-CISD, sólo **17** barren el mínimo previo NY del día, **146** no lo barren y **2** tienen contexto NY incompleto. **Esto demuestra divergencia de dos definiciones físicas posibles, no cuál POI es TTrades.** El autor [Relevant Swings](https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/) declara separación y relevancia contextuales, sin selector numérico universal; la jerarquía [Only POI that Matter](https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/) se aplica a continuación desde PS, NO automáticamente a reversión M30 C2. No usar la intersección `17` para optimizar tasa de aciertos. En cada caso, `candidate FVG touched` ≠ `important level` ≠ `author-selected POI`.

## Output materializado para actuar, no sólo documentación

Cada uno de cinco jobs produjo `vt08-b-r22-competing-poi-context-{MARKET}-{RUN_SHA}` con:
1. `entire_original_census`: **los 2.657 cases ID combinados** (nunca se pierde ninguno) con tipo FVG, phase de touch, n lows H1 candidatos tocados, grupos de source M15 IDs, clase del mínimo NY y bloqueos.
2. `blind_rater_dossiers`: **107 expedientes R19 originales, NO re-elegidos**; cada uno contiene contexto R22, metadata R18/R19 original, clocks, evidencia, y deja `human_rater_A_source_signoff=None`, `human_rater_B_independent_signoff=None`, `rater_A_verified=False`, `rater_B_verified=False`, `eligible_for_pnl=False`. Artifacts sujetos a caducidad de GitHub Actions (30 días); no subir barras del proveedor en documentos públicos.

## Próxima ruta crítica A + B

- **Arquitecto A**: anotar los 107 casos **SIN PnL** en su contexto completo, no elegir automáticamente FVG, NY-low ni low de C1. Por caso exigir 1) identificación del `important POI` concreto **antes del CISD**, 2) fuente TTrades URL/sección, 3) origen/TF/bar IDs y as-of, 4) pivot/relevant swing y valid separation cualitativa, 5) la serie causal M3 opposing closes y PS, 6) diagnóstico de duplicados/multipoi. Si el autor no especifica relevancia o desempate: `D_PENDING_SOURCE_AUTHORITY`, NO_ESPECIFICABLE.
- **B independiente**: recibir primer dictamen auténtico de A, revisar mismo source RAW original y sin PnL, documentar acuerdo/desacuerdo y resolverlos antes de certificar. Las 107 fichas pueden destapar ambigüedades, NO son una nueva subpoblación económica; siempre conservar los 2.657.
- Sólo después de tener un **conjunto metodológicamente reproducible A+B** pasar a selección causal de swing→EQ C2, breaker real LL→HH y vela(s) up-close, stop bajo EQ M30 y breaker low Example1, HTF target untouched con desempate documentado, `CandidateEvent SOURCE_COMPLETE`, 27 campos cognitivos source values/available-at, WAL, BID/ASK y Gates económicos previamente aprobados.

## Estado de certificación

`R22_SOURCE_PHYSICAL_JOIN=PASS` · `AUTHOR_POI_SELECTED=0` · `TWO_RATER_REAL_SIGNOFF=0` · `COGNITIVE_REAL_ADMISSIONS=0` · `BROKER_FILLS=0` · `ECONOMIC_GATES=NOT_EVALUABLE` · **VT08 NO CERTIFICADO**. Sin sizing, holdout 7Y sigue sellado, QORE-alpha sigue completamente excluido, cero LIVE/DEMO/VPS y cero merge.
