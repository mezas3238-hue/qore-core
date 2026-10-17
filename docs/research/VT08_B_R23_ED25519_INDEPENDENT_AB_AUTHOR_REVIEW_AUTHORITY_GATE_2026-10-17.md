# VT08 B R23 — Gate de dos dictámenes metodológicos auténticos, trazabilidad Ed25519, 107 WAIT reales

**Fecha:** 17-oct-2026 · **Proyecto:** VT08 ACTUAL (TTrades + cognitiva VT08) solamente, **QORE-alpha excluido**, B PR #764 DRAFT; A PR #765 DRAFT.

## Qué cerramos y por qué importa

R18→R22 identificaron 2.657 patrones fuente M30→M3, prepararon 107 expedientes fuente completamente ciegos al PnL y demostraron oportunidades físicas de POI, CISD, FVG, H1 lows; **ninguna** constituye un `author-selected-important-POI` por observación automática. El **R23 primer contrato complementario** [source-firstfail, GitHub Actions #39037632164](https://github.com/mezas3238-hue/qore-core/actions/runs/39037632164) unió R20+R22 y exigió ocho bloques de evidencia por dossier; **107/107 WAIT**. Ese contrato prepara fichas pero NO demuestra identidad/independencia de quienes las rellenan.

El **R23 de esta entrega** añade un mecanismo distinto y necesario, no otro censo de OHLC: **verificación real de una pareja de firmas Ed25519** sobre el JSON canónico completo del dictamen fuente *antes* de aceptar que dos evaluadores diferentes revisaron un caso. Ningún texto, boolean, SHA o label `human_signed=true` suministrado por A/B se considera una aprobación por sí solo. **No hace falta creer en dos nombres escritos en un campo**; un revisor A y un B tienen que poseer claves públicas diferentes previamente autorizadas en un registro de gobernanza inmutable. El material fuente sigue debiendo ser comprobado contra raws M3/M15 por revisión independiente.

**Dos límites intencionales:** (1) **no existen claves de revisores aprobadas** en el repositorio, de modo que el trust-root actual es `A_METHOD={}` y `B_INDEPENDENT={}` inmutable; TODOS los casos reales permanecen WAIT. Los tests emplean claves temporales sintéticas, no reviewers humanos reales. (2) incluso dos firmas auténticas y ocho afirmaciones `SUPPORTED` producen sólo `DUAL_SOURCE_REVIEW_CONSISTENT_ONLY`; **no** SourceComplete, situación cognitiva, ejecución ni Gate económico. La firma demuestra identidad/integridad del voto, NO la verdad de una interpretación de TTrades ni la validez de bar IDs no certificados por raw.

## Fuentes originales que condicionan los 8 campos

- [Relevant Swings](https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/): pivot geométrico no es swing relevante; separación cualitativa **sin fórmula numérica universal**. No inventar umbral.
- [Ideal Formation](https://ttrades.com/ttrades-ideal-formation-high-probability-swing-points/): no todo cierre C2 establece protected swing; nivel importante/POI y cierre por la serie opuesta generadora del nivel son condiciones materiales.
- [CISD Confirms Swing Points](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/): resolver el nivel real y la serie causal. La secuencia física dentro de C2 de R20 NO selecciona POI por sí sola.

Ocho entradas obligatorias, POR CASO/REVISOR: `relevant_swing_selection`, `qualitative_valid_separation`, `important_poi_selected_before_cisd`, `poi_reaction_vs_cisd_order`, `opposing_series_creates_protected_swing`, `breaker_source_sequence`, `eq_regime_and_author_stop_basis`, `untouched_htf_target_basis`. Cada una requiere estado `SUPPORTED`, `REJECTED` o `D_UNSPECIFIED`, URL `https://ttrades.com/...`, sección precisa, IDs de barra con SHA, `latest_source_available_at_utc<=C3.open` y motivo. El dictamen completo incorpora market/case ID, SHA del reporte R19 origen, rol A/B, identidad de clave, fecha y firma Ed25519 sobre JSON canónico. Dos elecciones con diferencia o D => `WAIT_DISAGREEMENT_OR_D`; rechazo de fuente => `SOURCE_REVIEW_REJECTED`; falta un firmante => WAIT. El paquete R19 sigue fijado con digest canónico por mercado, seed pre-PnL y 107 case IDs sin reelección.

## Pruebas ejecutadas

**[GitHub Actions #39037926346](https://github.com/mezas3238-hue/qore-core/actions/runs/39037926346)** — **5/5 SUCCESS**, Ruff + **24 casos adversariales por mercado = 120 pruebas exitosas** sobre firma real Ed25519 (biblioteca `cryptography` instalada sólo durante CI de esta feature).

Casos probados: ausencia de trust root, firmante no aprobado, dos firmas auténticas de claves distintas, manipulación posterior de voto/cita, identidad o SHA fuente incorrectos, plazo futuro del bar contra C3, clase/fuente desconocida, URL no TTrades, falta de evidencia o del campo, rationale insuficiente, duplicación, inyección de órdenes/authority, misma clave pública usando alias de los dos roles, 1/2 firmantes, dictámenes contradictorios y D. **Primera corrida #39037771816 falló sólo por Ruff (imports); segunda #39037828258 PASS; la final #39037926346 PASS 5/5 tras inmovilizar los mapas de claves mediante `MappingProxyType`.**

### Resultado auténtico sobre las 107 fichas sin firmas reales

| Mercado | Fichas R19 SHA anclado | `WAIT_UNREVIEWED` | Dos firmas autorizadas |
|---|---:|---:|---:|
| EURJPY | 21 | 21 | 0 |
| USDCHF | 21 | 21 | 0 |
| NZDUSD | 21 | 21 | 0 |
| CADJPY | 21 | 21 | 0 |
| USDCAD | 23 | 23 | 0 |
| **TOTAL** | **107** | **107** | **0** |

Artefactos por mercado en Actions `vt08-b-r23-dual-source-review-{MARKET}-{GIT_SHA}`, retención 30 días, guardan estados de los **107/107 casos reales** y ninguna respuesta privada de terceros. **0 firmas humanas reales; 0 source complete; 0 cognitiva; 0 fills; 0 economic Gates**.

## Implementación

- `src/qore/infrastructure/trader_lab/vt08_b_r23_signed_semantic_review_contract_v1.py` — validator fail-closed y `APPROVED_RATER_ED25519_PUBLIC_KEYS` vacío, congelado/inmutable.
- `tests/infrastructure/trader_lab/test_vt08_b_r23_signed_semantic_review_contract_v1.py` — adversarios sintéticos y firmas criptográficas efectivas; no etiquetar esos fixtures como SourceComplete.
- `.github/workflows/vt08-b-r23-signed-dual-methodology-source-review.yml` — matriz cinco mercados y artefactos originales R19 CI #38903529731 `e999e127be84a1ebb9d3e8b1d13e110cfa2cb51a`, validación sin importación de fuente mercantil PnL.
- Complemento R23 `vt08_b_r23_semantic_review_firstfail_ledger_v1.py` y [reporte físico 107 source-firstfail](VT08_B_R23_SEMANTIC_SOURCE_FIRSTFAIL_107_DOSSIERS_2026-10-17.md): comprueba los enlaces R20/R22 que este módulo de firmas NO recompone por sí solo.

## Ruta crítica de verdadera certificación

1. **A debe producir dictámenes SOURCE-PRIMARIA auténticos** de casos R23 sobre swing/POI/PS con los mismos 107 IDs, sin inventar selector numérico donde la fuente es cualitativa. B debe realizar segunda inspección independiente de barras, preferentemente sin leer el dictamen A hasta antes de firmar.
2. **Owner/arquitectura de confianza deben autorizar identidades/claves reales** (públicas únicamente) en código revisado, y cerrar el contrato de evidencia de bar IDs con RAW M3/M15. No activar `APPROVED_RATER_ED25519_PUBLIC_KEYS` por un parámetro de origen ni generar claves de revisor automáticamente en investigación.
3. **Conectar resultados A/B realmente firmados a CandidateEvent V2 y al verdadero `evaluate_provenanced`**, implementar todas las reglas de swing/POI/PS/EQ/breaker/stop/target, aportar los 27 `CAUSAL_FIELDS` con valor+SHA/available-at. **R23 no hace hoy esa integración de broker y no confiere autorización futura implícita.**
4. Sólo cuando existan señales SOURCE_COMPLETE reproducibles y auditores independientes, preregistrar y probar BID/ASK, costos, OOS, PF/DD/Sortino/Sharpe/Monte Carlo con densidad mínima. No usar 7Y sellado sin liberación explícita, no sizing.

**Estado final:** `R23_SIGNED_SOURCE_REVIEW_VALIDATOR_PASS`, `REAL_SOURCE_REVIEW_PENDING_107`, `SOURCE_COMPLETE=0`, `COGNITIVE_ADMITTED=0`, `BROKER_FILLS=0`, `GATES=NOT_EVALUABLE`, `VT08_NOT_CERTIFIED`. **Sólo VT08 actual; QORE-alpha no vuelve al programa.**
