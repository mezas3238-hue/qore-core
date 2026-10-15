# VT08 Arquitecto A — R4: A→B catálogo físico por mercado y selección segura de runner

**Fecha:** 2026-10-15 · **PR:** #765 draft · **Issue A:** #762 · **B:** PR #764, issue #763 · **Estado:** SOURCE_DATA_READY_FOR_INDEPENDENT_B_FIELD_REVIEW / NOT_CERTIFIED.

## 1. NUEVO TRABAJO REAL EN GITHUB

[GitHub Actions #38740699499](https://github.com/mezas3238-hue/qore-core/actions/runs/38740699499) finalizó con **5/5 jobs SUCCESS**, 8 tests adversariales y Ruff PASS por job (la suite se repite en cada mercado). Código de esta ronda: `src/qore/infrastructure/trader_lab/vt08_a_b_market_custody_catalog_v1.py`, tests `test_vt08_a_b_market_custody_catalog_v1.py`, workflow `.github/workflows/vt08-a-b-market-custody-catalog-v1.yml`, commit `f61b5e7a931e2c057a0660f4702f11d55ebc58af`.

El motor utiliza **Trader Lab**, lee los artefactos de datos M3 cTrader y M15 originales, verifica los hashes del censo congelado, vuelve a procesar toda la única familia bullish M30 C2→C3 y prepara un **catálogo físico de barras M3/M15 específico de cada mercado**. Se reemitieron los recibos `pre_c2_h1_m15` con perfil físico `M15` y SHA canónico de contenido — el antiguo perfil `M15_PRE_C2_H1` no era aceptable para el auditor por campo de B. No se alteran precios ni se crea trading.

Cada catálogo entrega `source_raw_market_map`, `pinned_raw_shas`, `bar_catalog` con `market`, `source_bar_id` recomputado, M3/M15, OHLC, UTC `opened/closed/available` y grupos por evento de C1, C2 y contexto H1 **cerrado PRE-C2**. Detecta barras ajenas, raw SHA erróneo, clocks futuros, fuente con cierre imposible, barras discontinuas y cualquier evento/flag que simule semántica TTrades o fills. No importa ni ejecuta la librería verificadora de B; los resultados deben ser auditados nuevamente por B de manera independiente.

| Mercado | Casos estructurales (NO señales) | Barras únicas de custodia | Artefacto Actions ID |
|---|---:|---:|---:|
| EURJPY | 538 | 17.832 | [11974837927](https://github.com/mezas3238-hue/qore-core/actions/runs/38740699499/artifacts/11974837927) |
| USDCHF | 518 | 17.206 | [11976297142](https://github.com/mezas3238-hue/qore-core/actions/runs/38740699499/artifacts/11976297142) |
| NZDUSD | 550 | 18.316 | [11976057270](https://github.com/mezas3238-hue/qore-core/actions/runs/38740699499/artifacts/11976057270) |
| CADJPY | 516 | 17.194 | [11976242012](https://github.com/mezas3238-hue/qore-core/actions/runs/38740699499/artifacts/11976242012) |
| USDCAD | 535 | 17.728 | [11975437653](https://github.com/mezas3238-hue/qore-core/actions/runs/38740699499/artifacts/11975437653) |
| **Total** | **2.657** | **88.276** | 5/5 SUCCESS |

Los `88.276` son la suma de barras únicas **dentro de cada mercado**, no número de trades, ni necesariamente 88.276 horarios distintos entre mercados. Cada barra con sello físico sigue siendo fuente OHLC, no una evaluación de relevancia del autor.

Los tests cubren manipulación de raw/bar SHA, identidad cruzada de mercado, clocks, un H1 faltante, perfiles canónicos y rechazo explícito de reclamos de `A_rule_complete` o PnL. Se preserva un caso de CADJPY con H1 incompleto: **no se rellena ni se promueve**.

## 2. Arquitecto B: tarea inmediata

B R5 halló que la lista global de raw SHA podía mezclar dos mercados. El nuevo productor A genera metadatos compatibles con el contrato `vt08_b_situation_field_source_audit_v1.py`: un `source_raw_market_map` por mercado, registros de barras con mercado explícito, IDs con SHA canónico y perfiles M3/M15 originales. **No lo tomes como prueba automática**: B debe descargar los cinco artefactos, reconstruir los hashes desde **archivos M3/M15 originales** y contrastar por su propio código antes de aceptar el catálogo.

B debe producir la matriz causal **campo por campo** (27+ Situation), usando los `source_bar_groups` de cada uno de los 2.657 contextos y registrar qué campos quedan `D_UNSPECIFIED`. No se permite llenar valores semánticos inventados solo para pasar `verify_all_situation_field_receipts`. Los atributos `reference_swing`, POI significativo, breaker low, target untouched, EQ-regime, PS/CISD de autor siguen pendientes de verificación independiente.

**Ningún SHA de mapa ni el catálogo es un manifiesto A/B firmado;** `APPROVED_A_B_MANIFEST_SHA256=None` permanece, con cero author-complete signals, cero cognitive admissions reales y cero fills.

## 3. Sobre Trader Lab y QORE Research Ultra Fast Runner

Existen los dos entornos en GitHub. **Ya se utiliza Trader Lab con los datos nativos del propio VT08** para los censos source-only y este puente A/B, por lo que no hay necesidad de recrear los datos. Se revisó el Ultra Fast Research Accelerator en la rama `research/qore-accelerator-5layers-ultrafast-20261013`, concretamente `research_accelerator/ultrafast.py`, `core.py` y su handoff.

El acelerador tiene lectura indexada, memoria experimental y simulador de órdenes **CE LIMIT/C2/DOL**, con manifests `M1 BID` y ticks BID/ASK emparejados. **NO es automáticamente equivalente** al ensayo VT08 congelado **M30 bullish C2 → M3 CISD/PS → C3.open POSITIONAL**. Ejecutarlo con señales reetiquetadas o simular fills con ticks BID/ASK parciales sería cambiar la metodología y fabricar PF. Su propio handoff indica que el benchmark ≈32× corresponde solo a un join as-of de 30 horas USTEC, no a certificación de cinco pares VT08.

**Ruta segura:** usar el motor rápido solo para operaciones de *datos* (indexado/custodia/as-of) una vez exigida paridad bit a bit frente al verificador fuente del Trader Lab. No trasladar reglas, stops, targets ni cierres del motor CE LIMIT. La certificación económica será con BID/ASK real homologado, comisiones y misma familia congelada; con datos fragmentarios `NET=NO_EVALUABLE`.

## 4. Estado de Gates

- Metodología: fuente textual y selectores swing/POI/breaker/target aún NO COMPLETA.
- Cognitiva: B posee QA creciente, pero 27+ atributos semánticos de **eventos auténticos** y firma A/B siguen faltando.
- Economía: PF net, MaxDD R, MC DD p95, Sharpe, Sortino, densidad física y OOS NO MEDIDOS. Las 2.657 geometrías NO son fills.
- Gobernanza: prohibido sizing, leverage, compounding, abrir holdout 7Y, VPS/DEMO/LIVE o fusionar PRs.

**Resultado científico correcto R4:** se cerró un bloqueo real de *formato y custodia A→B* para permitir la siguiente revisión independiente. `VT08_NOT_CERTIFIED`.
