# VT08 CRT R9 — 36 G2 casos cegados listos; resolución de G7 pendiente del auditor y Owner

**17 OCT 2026.** Evidencia nueva REAL publicada, no certificación. Congelados V1/V2/V3, G-M4, 139 casos y las 5 UNKNOWN. Sizing en VT08 estrictamente prohibido, incluso 1R/volúmenes ficticios. Sin órdenes, demo, live, VPS, merge, capital o PF simulado.

## Evidencia verificada
- **PREREG ANTES** de replay: [R9 protocolo de independencia G2](VT08_CRT_R9_G2_INDEPENDENT_BLIND_36_REVIEW_PROTOCOL_PREREG_2026-10-17.md), commit `1e47a99143ed2a3e29d7f141dcc036b95e3cbdcc`.
- [**GitHub Actions #39037416479**](https://github.com/mezas3238-hue/qore-core/actions/runs/39037416479), código exacto **`7e304bddf9721de62f838927e99f04d1edd8b5cd`** — **3/3 jobs SUCCESS**: Ruff/mypy 5 módulos, 56 tests unitarios/adversariales PASS, original Atlas AUDUSD y USDJPY completados; no feed externo, se conserva SHA original.
- Implementación `src/qore/infrastructure/trader_lab/vt08_crt_g2_independent_blind_review.py`, tests `tests/infrastructure/trader_lab/test_vt08_crt_g2_independent_blind_review.py`, integrado en `vt08_crt_g2_g7_real_atlas_pit_bridge.py` y matriz de workflow `.github/workflows/vt08-crt-g2-g7-real-atlas-pit-audit.yml`.

## Resultados G2 y evidencias SHA separadas

| Campo | AUDUSD | USDJPY | Total |
|---|---:|---:|---:|
| Casos reviewer-only H4 C0/C1/C2 | **16** | **20** | **36** |
| Diagnóstico ENGINE SEALED `OPPOSITE` | 4 | 10 | **14** |
| Diagnóstico ENGINE SEALED `SAME` | 12 | 10 | **22** |
| Revisión firmada independiente real | 0 | 0 | **0** |

**Solo enviar al revisor los dos artefactos `independent-reviewer-only`**. Cada fuente contiene únicamente H4 C0/C1/C2 OHLC originales y cerrados al reloj, caso ofuscado por SHA, mensaje de adjudicación y opciones `C0`, `C1`, `BOTH_AMBIGUOUS`, `NEITHER_VALID`, `INSUFFICIENT_SOURCE`. No se entregan source_event_id, parent_id, direcciones, etiquetas de conflicto, G-M4 terminal o resultados económicos. Se incluye `g2-blank-human-review-responses.jsonl` con respuestas NULL, sha de cada case y flags de aprobación FALSE. Nada se autodeclara revisado.

**Archivos ENGINE SEALED separados:** constan `engine_c0_direction`, `engine_c1_direction`, `engine_conflict_kind`, mapa de identidad y hashes de payload. No exhibirlos antes de que el revisor emita decisión. Los scripts no pueden forzar control de acceso en GitHub: aunque los artefactos están separados, **cualquier persona con acceso al repositorio/Actions podría consultar ambos**, por lo que el cegamiento real requiere permisos procedimentales, revisor no expuesto a sealed y prueba externa de independencia. Cualquier exposición prematura invalida el carácter blind del protocolo y requiere nueva custodia.

**Artifactual addresses con SHA ZIP de GitHub, vencen 2027-01-15T13:38:50Z:**

- AUDUSD **REVIEWER ONLY** [artifact #12102807181](https://github.com/mezas3238-hue/qore-core/actions/runs/39037416479/artifacts/12102807181), sha256 `afbd44369558e6b169c9b5599868c96b2407f1b2625632c03467cfba65b81fc8`.
- USDJPY **REVIEWER ONLY** [artifact #12103140816](https://github.com/mezas3238-hue/qore-core/actions/runs/39037416479/artifacts/12103140816), sha256 `89646f07a159c8e3284fb20521c207bd4f836bae3c1d17ada7f3aa92ee9d5130`.
- AUDUSD **SEALED — DO NOT RELEASE** #12102657747 sha256 `6fddeb478dee6b0e5dbae96fe224245f9df9539b9aad10017b049d472237eb20`.
- USDJPY **SEALED — DO NOT RELEASE** #12103245345 sha256 `4e53cdd210b79ba3cf292fe814b2d3ad9d47fa165afcb024b206dbb99f5b4d31`.
- Atlas research R9 full ledger AUDUSD #12102870863 sha256 `544e73486038dacfcff2775e6a408712e7a5c4ff31748670c4b7db1d87c4c37e`; USDJPY #12103105829 sha256 `47c7195210404cdf1b69b2d22f5048cffbc9ea64839cc3cbafa1150bd98c4699`. Full ledgers ALSO have labels: **no entregar al revisor blind**.

## Formato de adjudicación G2 que realmente cerraría G-M1

Por cada uno de los 36:
1. Completar `human_choice` con una de las cinco decisiones, sin mirar ENGINE sealed o replay de C3. Si C0/C1/BOTH/NEITHER explicar regla de *relevancia de referencia* preexistente, no solo elegir alto/bajo. Un H4 extremo no equivale de por sí a old CRTH/CRTL autor-certificado.
2. Dar `source_quote_locator` exacto a corpus tri-fuente, o indicar explícitamente `QORE_ENGINEERING` cuando regla no está respaldada; documentar qué pasaría ante niveles contradictorios, incertidumbre y abstención. Añadir `counterexample_if_any` y razón de no entrada si no hay autoridad.
3. El evaluator independiente emite review de GitHub sobre **el commit exacto que contendrá la política G1–G7 final**, no el paquete histórico separado. Owner, como identidad GitHub independiente del implementador y reviewer, valida la misma versión y acepta/rechaza. Sin autenticación externa de **ambas firmas, SHA y roles**, la plantilla no concede G-M1 PASS. Revisar issue #976.
4. Primero congelar la nueva política metodológica de cualquier modificación; después validar con *datos realmente vírgenes*. Nunca escoger respuestas retrospectivas para inflar PF o trades. CIBO Risk debe evaluar Gates patrimoniales independientemente, jamás hacer sizing desde VT08.

## G7: decisión semántica crítica separada de G2

El dossier G1–G7 de QORE define “no rearm del mismo padre/same hypothesis, nueva identidad de evento con ciclo causal”. Sin embargo, el código research actual `audit_g7_rearm` exige **que todos los eventos de todo el mercado anteriores tengan terminal verificable**. Eso es una **precondición adicional global ENGINEERING**, no identificada como cita universal de los autores. Los 5 UNKNOWN hacen `WAIT` en 108 fuentes posteriores; no 108 eventos no válidos independientes.

El auditor debe resolver normativamente ANTES de mirar nuevos outcomes:

| Alternativa de política | Precondición | Ventaja metodológica | Prueba negativa imprescindible |
|---|---|---|---|
| A: `GLOBAL_ALL_PRIOR_TERMINAL` vigente en puente R8/R9 | Toda fuente previa de ese mercado termina causalmente antes de aceptar nueva fuente | Conservadurismo extremo; NINGUNA hipótesis histórica previa ignorada | Si un UNKNOWN previo nunca es terminal, nueva fuente independiente queda permanentemente WAIT |
| B: `LINEAGE_SCOPED_CAUSAL_REARM` **PROPUESTA NO AUTORIZADA** | Cerrar/invalidar **solo la genealogía de hipótesis a la que pertenece un rearm**; una nueva identidad independiente requiere evidencia positiva autónoma; nunca reusar parent/source/hyp | Distinción cognitiva entre verdadera tesis nueva y reciclaje de tesis fallida | No se puede rearm padre/tesis ya usados; un nuevo hash artificial sin fuente positiva no da autorización; un UNKNOWN del MISMO lineage bloquea |
| C: `ABSTAIN_UNKNOWN_UNTIL_SOURCE` | Sin adjudicación de genealogía, seguir WAIT para casos dudosos | No inventa permiso | NO expandir supuestos EXIT por calendario inferido |

**R9 no calcula un PF de B, no cambia G7 a B y no lo etiqueta “autor supported”.** Owner + auditor deben seleccionar con evidencia tri-fuente/casos adversariales; firmar scope de línea causal, asociación de source a parent, ciclo de expiración al cierre de mercado (R7/R8), 2 no viabilidades open post-invalidation y 1 miércoles sin M5 original. Solo después implementarlo sin hindsight.

## Qué falta realmente para certificar (no esconderlo)

G2 conserva 139 WAIT por inventario old-CRT incompleto y decisión humana pendiente; G7 108 WAIT por política aún propuesta; G-M4 **5 UNKNOWN** sin false closure. G-M2 **48 FIRST-LOOK** sin firmas independientes, G-M3 truth externa, G-M1 siete artículos y dos revisiones GitHub distintas. G-M5 no emitido. Sin OOS virgen, BID/ASK/fills reales, edge económico, PF/Sharpe/Sortino/WFO/Monte Carlo, DD patrimonial (CIBO/Risk only), GLOBAL NOT CERTIFIED. Atlas bruto original caduca 2026-12-16 (issue #837). **No sizing VT08 ni demo/live/VPS ni merge del PR #626**.
