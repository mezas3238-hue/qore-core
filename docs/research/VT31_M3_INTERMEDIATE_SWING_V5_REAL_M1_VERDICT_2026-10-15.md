# VT31 — V5: jerarquía de swing INTERMEDIO de TTrades, 318 casos ambiguos originales
**Fecha 15-OCT-2026** · Owner certifica por METODOLOGÍA Y COGNITIVA, nunca por PF/DD/Sharpe/Sortino, frecuencia de operaciones ni sizing. [PR #973](https://github.com/mezas3238-hue/qore-core/pull/973) DRAFT, hijo del COG V4 [#972](https://github.com/mezas3238-hue/qore-core/pull/972). G3 OPS/COG inmutables, NO MERGE/DEMO/LIVE/FundedNext/VPS.

## 1. Fuente del autor y su interpretación limitada
- [TTrades — Advanced Market Structure 11-JUL-2025](https://ttrades.com/advanced-market-structure-simplified-from-short-term-to-long-term-trends/): *short-term swing* tiene extremos vecinos M1; un *intermediate-term swing* está formado por un swing corto del mismo tipo flanqueado por otros swings cortos de su tipo. Relación centro HIGH mayor que sus short-term vecinos (LOW menor que vecinos) constituye una **formalización QORE conservadora** de esa descripción. La fuente NO afirma que cualquier intermediate geometría sea necesariamente el swing PROTEGIDO que causa displacement/stop.
- [TTrades MSS vs CISD Jul1](https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/): MSS requiere **displacement y cierre beyond swing**, mientras FIRST_OPEN CISD es diferente. Ningún pivot short/intermediate por sí solo certifica MSS. La metodología usa jerarquías, no selección retrospectiva del nivel favorable.
- V4 [#972](https://github.com/mezas3238-hue/qore-core/pull/972) confirmó **96** cierres de swing short-term con referencia única, **318** con múltiples swings short-term y **69** sin componente acreditado en los 483 contextos; V5 no altera esa clasificación ni sus hashes.

## 2. Evidencia histórica autocomprobable en GitHub
**[CI GitHub Actions #38764379725 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38764379725)**, código tested commit `4aa6b2cbac233275806205b590816443e30d1619`, **Ruff PASS + 35/35 pytest PASS**, original **1.059.784 M1 NAS100** SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa` verificada, 775 NY días y 483 casos fuente congela dos años plus, corpus desarrollo ya explorado (**NO OOS**).

**[Artifact #11986218764](https://github.com/mezas3238-hue/qore-core/actions/runs/38764379725/artifacts/11986218764)**, ZIP SHA256 `4fcd5acd421beb0a47f7b5313b956c9f0850a33142c0859ac13501cd5545dece`. Registro completo de **483/483 fechas**, primer V4 ambiguous as_of, clase previa, candidatos intermedios, timestamp de vecino corto DERECHO confirmado, clase nueva, sin stop/operaciones/lotaje/PnL. Casebook JSON SHA256 `0999c3d1bb1332645150f613d8bc2cf347c7ac3eb067b53c45c3e38ef94d879b`, idéntico scalar vs 2 procesos fork Ultra Fast.

| Universo de prueba sin selección posterior | Casos | Interpretación |
| --- | ---: | --- |
| Ya no ambiguo en V4 (96 con 1 short-term + 69 sin ruptura) | **165** | Sin nueva adjudicación, V4 sigue soberano |
| De 318 V4 ambiguos, **1** geometría intermedia previamente confirmada y recién cruzada | **24** | `SINGLE_SOURCE_INTERMEDIATE_GEOMETRY_COMPONENT_ONLY`; NO MSS sin displacement ni swing protegido |
| De 318 V4 ambiguos, **ningún** intermediate confirmado y recién cruzado antes del instante | **294** | `NO_INTERMEDIATE_CONFIRMED_AT_CAUSAL_ASOF`; WAIT/UNKNOWN bajo criterio conservador |
| De 318 V4 ambiguos, múltiples intermedios | **0** | Este censo no produjo solapamiento intermedio bajo el contrato, pero adversarial con 2 sigue siendo UNKNOWN |
| **TOTAL** | **483** | NO son trades ni éxitos/errores económicos |

**La contribución cognitiva real:** antes había 318 referencias short-term múltiples; jerarquía source intermedia explica 24 situaciones estructurales sin inventar prioridad por cercanía/PnL, y deja **294** en abstención. La cantidad no certifica ninguna: el proceso reconoce la diferencia entre evidencia observacional y legitimidad de la decisión. El V5 no modifica los 318 casos ni el COG V4; es testigo de investigación.

## 3. Causalidad y aceleración probadas
- **Pre-registro antes del código** commit `54f5985ce174d3bcf8614d15ac33bc5201c882c0`, ruta `docs/research/VT31_M3_INTERMEDIATE_SWING_SOURCE_PREREG_2026-10-15.md`.
- `intermediate_swing_source_geometry()` consume prefijo real M1 ya cerrado hasta **primer instante ambiguo**; todos los short-term de 3 M1 contiguas, pivot central con vecino SHORT-TERM a izquierda y **derecha completamente confirmado ANTES de as_of**. No crea vecinos con datos futuros. Romper la referencia exige cruce nuevo del CLOSE y no wick. Dos referencias igualmente válidas ⇒ `MULTIPLE_INTERMEDIATE_PIVOTS_UNKNOWN`. Incompleta/gapped M1 ⇒ error, sin interpolación.
- Fuentes original V3 #970 FIRST_OPEN H1 y V4 #972 causales verificadas; testigo V5 pide sesgo LONG/SHORT a V3 REAL justo en instante ambiguo. G3 COG/OPS originales no se mutan.
- Shared source+censo 14,467469 segundos, scalar 25,68708 s, fork Ultra Fast 13,213514 s; velocidad auditorías ~**1,94×** excluyendo carga común, paridad de JSON COMPLETO `0999c3d1bb...`.

## 4. Qué falta realmente certificar
1. **M3 desplazamiento:** construir testigo source VELAS del displacement, con ejemplos positivos/negativos author-annotated de expansión/estructura (sin inventar body >= 1,25×mediana5 como autor); confirmar coexistencia con cierre swing y FIRST_OPEN. El PR #973 NO emite `MSS_AUTHOR_CERTIFIED`.
2. **M3 hierarchy protected/causation**: distinguir intermediate, protected HTF and long-term swing; la geometría de 24 casos no permite decir cuál swing **causó** la ruptura o define SL. Resolver 294 con evidencia doctrinal/HTF, no alejar umbrales o usar sizing.
3. **M4** entrada autoral completa de displacement/FVG/OB/Breaker con zona, retest, timeframe, precedencia, invalidación y `WAIT` causal. Research PRs #960/#961 no son trader runtime.
4. **M5** swing específico que **causó** displacement, no seleccionar automáticamente el swing intermedio de V5 para poner stop.
5. **M0** integrar selector metodológico research [#963](https://github.com/mezas3238-hue/qore-core/pull/963) y COG V3–V5 a un único contrato gobernado, sin modificar G3 original sin aprobación.
6. **M6** [issue #897](https://github.com/mezas3238-hue/qore-core/issues/897) continúa exigiendo dos revisores independientes COG/OPS y firmas comprobables; la única cuenta Owner no representa ambas firmas.

**Dictamen:** `V5_INTERMEDIATE_SOURCE_GEOMETRY_ENGINEERING_PASS`, `METHOD_CERTIFIED=false`, `COGNITION_RUNTIME_CERTIFIED=false`, `TRADER_CERTIFIED=false`; la suite certifica comportamiento de testigo, NO autorización operativa ni edge económico. Sin merge, LIVE, DEMO, FundedNext, VPS o lotaje VT31.
