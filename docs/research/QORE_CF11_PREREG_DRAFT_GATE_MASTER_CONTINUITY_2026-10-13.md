# QORE RESEARCH — CONTINUIDAD PREREG DRAFT / CF-11 / TRADER LAB

**Checkpoint:** 13-OCT-2026. **Repositorio:** `mezas3238-hue/qore-core`.
**Nueva PR:** [#918](https://github.com/mezas3238-hue/qore-core/pull/918), DRAFT, no merge.
**Rama:** `research/qore-cf11-prereg-draft-causal-gate-20261013`.
**PR madre:** [#916](https://github.com/mezas3238-hue/qore-core/pull/916) → #915 → #914 → #913 → #895.
**Presupuesto datos:** USD0. **Capital real/LIVE:** no autorizado.

## 1. Resultado realmente ejecutado

Se implementó un contrato **versionado de preregistro DRAFT (v1)** y un CI source-first read-only para las propuestas nuevas de QORE Research. Es un paso técnico de la misión, no un hallazgo predictivo de mercado.

**[Actions #38478999803](https://github.com/mezas3238-hue/qore-core/actions/runs/38478999803): SUCCESS**, código HEAD validado `108b83e4f92927d97bcdf506b4a392bc31d42c74`.
Resultados del log: **40/40 tests**, Ruff PASS, Mypy PASS, fuente original EIA autenticada, cola CF-11 reconstruida del artefacto histórico, **0 borradores**, receipt SHA256 `174e823fbd97aa816367ba4d9537a243a161e29868dea3164be1041316b56479`. Los datos referenciales EIA no se redistribuyen en el nuevo artifact.

**Permanecen:**
- `research.eia.futures-a-f1f2-closure = closed_no_support`;
- `research.futures-a.native-6roots-d1 = source_blocked`;
- 0 nuevas hipótesis de mercado corridas, 0 traders nuevos certificados en esta línea;
- EIA holdout 2022-01 a 2024-04 sin puntuar; FX Native holdout desde 2024-09-17 intacto;
- 0 USD de gasto en datos, 0 órdenes, 0 capital real.

## 2. Entregables de esta PR

- `src/qore/infrastructure/trader_lab/qore_research_prereg_draft_gate_v1.py`: validación fuerte de manifest v1; misma identidad que cola autenticada; SHA256 canónico.
- `tests/infrastructure/trader_lab/test_qore_research_prereg_draft_gate_v1.py`: **16 nuevos tests** sintéticos (24 heredados de #916 = 40 total) que revisan falsos permisos, fuente, duplicaciones, family-wise alpha, split temporal, ventanas, fake Git chronology, tampering.
- `.github/scripts/qore_research_prereg_draft_receipt_v1.py`: une manifests DRAFT con ledger autentificado por pipeline anterior y emite sólo receipt; nunca PnL.
- `.github/workflows/qore-cf11-prereg-draft-causal-gate.yml`: CI que descarga el mismo artifact original EIA, verifica run/digest y antecedencia prereg de aquel experimento, recrea CF-11, construye ledger y procesa **manifest nuevo vacío**.
- `docs/research/QORE_RESEARCH_PREREG_DRAFTS_2026-10-13.json`: manifiesto deliberadamente vacío; no reciclar resultados ni fabricar una hipótesis.

## 3. Restricciones científicas codificadas

Un borrador completo debe declarar antes de mirar outcomes:
1. Identidad de propuesta, pregunta, hipótesis y versión; mecanismo falsable.
2. Root/venue esperado con raíces reconocidas `CL, NG, GC, HG, ZC, ZS`, registro 2/6 consistente con fuente del ledger.
3. Resultado primario, exposición, control/comparación, dirección y unidad muestral.
4. Inferencia preelegida (Fisher o permutación por bloques como etiqueta contractual), alfa en partes por millón, tamaño de familia, Bonferroni, efecto mínimo y mínimo de eventos por grupo.
5. Ventanas TRAIN, DIAG y HOLDOUT no superpuestas, declaradas explícitamente; no abrirlas en esta fase.
6. Fuente no certificada, sin timestamp as-of autorizado, sin snapshot falsificado, sin inspección de outcomes, sin posibilidad de ejecución y con gasto USD0.

El ledger también obliga a **correspondencia uno a uno** de una propuesta con un draft, rechaza SHA alterados y duplicaciones de código/hipótesis. Recibo `scientific_prereg_frozen=false`, `can_execute=false`, `can_open_holdout=false`, `provenance_git_ancestor_attested=false`, `data_rights_certified=false`.

## 4. Orden causal Git — implementación vs autoridad

`verify_prereg_before_outcome_git` es una utilidad de verificación de secuencia para uso futuro: exige commits SHA distintos, `git merge-base --is-ancestor PREREG RESULT`, hace `git show PREREG:manifest` y compara el digest de la especificación original.

**Limitación clave:** los tests de esta utilidad usan commits/outputs simulados y no constituyen evidencia de que exista una nueva hipótesis preregistrada de verdad. Ni siquiera un `merge-base` verde demuestra que nadie haya consultado outcomes históricos antes. Faltan identidad de run confiable, hash del dataset/first-publication-as-of, emisor independiente de fuente y comprobación humana de ausencia de post-selection.

El contrato fuerza `version=1` en esta fase; la política de enmiendas posteriores todavía NO se ha aprobado. No confiar en un “nuevo nombre” para relanzar backwardation de EIA: los hashes e identidades sólo impiden equivalencia literal, no equivalencia semántica sin auditoría.

## 5. CI y correcciones durante la intervención

Primera implementación CI red por orden de imports, luego por tipos `Any | None`, luego lint `E501/I001` y un patch mock con signature errada. Se corrigió sin cambiar la interpretación científica. La única CI válida para certificar **esta implementación del contrato** es la ejecución **SUCCESS #38478999803** y su SHA HEAD de código citado arriba; no citar los workflows RED como evidencias económicas.

Artefacto producido: `qore-research-prereg-draft-zero-budget-receipt` (retención GitHub temporal, sin market prices). Hash lógico publicado arriba. Conservar custodia en GitHub del acta + hash.

## 6. Pendientes para siguiente arquitecto

**P0 mercado/datos:** fuente CME contract-native 6×2 con derechos legales US$0, OHLCV/settlement/OI, contrato de expiración, first publication as-of y política de roll + bid/ask y costes. Mientras no exista, mantener `SOURCE_BLOCKED`. No usar EIA reference-only close como sustituto y no consumir reservas. No inventar Sharpe/Profit Factor/Drawdown.

**P1 científico:** si aparece una hipótesis genuinamente independiente, registrar primero una propuesta `PROPOSAL_ONLY` y su DRAFT con mecanismo y umbrales, someter independencia semántica y revisión humana; congelar contenido en un commit anterior a ejecutar cualquier outcome. La herramienta actual NO produce sellado científico autorizado. Necesita política de versiones/enmiendas, definición completa de prueba/permutaciones (bloques y semillas), test de potencia, fuente y autoridad as-of.

**P1 cadena de custodia:** introducir fuente/licencia verificada por emisor independiente, comprobación del SHA del commit y blob de prereg por Actions en trabajo separado, frontera de independencia fuente/resultados y registro de revocaciones. Cambios históricos al prereg deben fallar cerrados.

**P1 orquestación:** diseñar y ensayar sin despliegue una cola idempotente `source→prereg→run→receipt→decision`. GitHub workflow por push/dispatch NO es Research Director autónomo siempre activo.

**P2 certificación económica:** únicamente con datos suficientes y autoridad: replay contract-native causal, holdout fresco sellado, stress, costes, Risk soberano, CIBO soberano y Trader Lab. Nunca añadir sizing al Trader ni habilitar LIVE.

## 7. Reanudación y gobernanza

Abrir [PR #918](https://github.com/mezas3238-hue/qore-core/pull/918) y [Actions SUCCESS #38478999803](https://github.com/mezas3238-hue/qore-core/actions/runs/38478999803), inspeccionar commit/receipt; continuar **sin merge**. Handoff maestro padre:
`docs/research/QORE_FUTURES_A_QORE_RESEARCH_CF11_TRADER_LAB_MASTER_HANDOFF_INTEGRAL_2026-10-13.md` en la rama #916. No cambiar el significado de `NO_SUPPORT` ni `BLOCKED_DATA_OR_LICENSE`.

**Veredicto:** infraestructura de prereg DRAFT comprobada técnicamente. **Ninguna rentabilidad ni edge descubierto/certificado.**
