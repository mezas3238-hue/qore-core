# VT31 — M3 V6 · RESULTADO REAL: triple literal TTrades vs criterio QORE estricto

**Fecha:** 15-OCT-2026. **Estado:** `V6_DIAGNOSTICO_GEOMETRIA_INGENIERIA_PASS`, **NO** `M3_MSS_CERTIFIED`, **NO** `METHODOLOGY_CERTIFIED`, **NO** `COGNITION_CERTIFIED`, **NO** `TRADER_CERTIFIED`.

**Fuente de verdad:** [PR #977 DRAFT](https://github.com/mezas3238-hue/qore-core/pull/977), hijo del [handoff R4 PR #974](https://github.com/mezas3238-hue/qore-core/pull/974), baseline R4 `037ae728ed2d7990998d837574099cb1d7e2f116`. **Código probado** commit `51e09eb2dd529dcf5b440b72c23c875a9ca6e0f8`. [CI #38788005339 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38788005339). El flujo corre sobre Linux python3.12, Ruff PASS, **46/46 pytest**, original NAS100 1.059.784 velas M1 SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa` comprobada por `sha256sum -c`, censo 775 días / 483 contextos fuente sin alterar, paridad de JSON completo scalar/Ultra Fast fork = TRUE.

**Artefacto:** [GitHub Actions artifact #11998603310](https://github.com/mezas3238-hue/qore-core/actions/runs/38788005339/artifacts/11998603310), ZIP SHA256 `dd9ec21428b9fc246d28c992085e017aa66a952beb152c861f05b8933ff4a29d`. SHA256 **casebook JSON completo 483/483:** `3f50950a82eda409808844fe1e1ef735e4604f685ec6b1942322ded5b54d5834`. Archivo `evidence/VT31_M3_LITERAL_INTERMEDIATE_V6_483_REAL_M1.json` dentro del artefacto. Referenciar siempre el código probado y esta fuente; ZIP puede expirar.

## 1. Hipótesis preregistrada y fuente

El [prerregistro V6](https://github.com/mezas3238-hue/qore-core/blob/03db7f1ff0377bdfabaa058165e866bd7b55f267/docs/research/VT31_M3_V6_LITERAL_INTERMEDIATE_VS_QORE_STRICT_PREREG_2026-10-15.md) está en el commit `03db7f1ff0377bdfabaa058165e866bd7b55f267` **ANTES del código**. Las reglas V4/V5 y el censo de datos quedaron congelados.

[TTrades — Advanced Market Structure, 11-JUL-2025](https://ttrades.com/advanced-market-structure-simplified-from-short-term-to-long-term-trends/) describe un intermediate basic por tres short-term swings del mismo tipo con vecinos izquierdo/derecho; V5 agregaba una desigualdad de extremo central `center.high > left.high/right.high` (o LOW inverso), una política QORE más estricta no formulada literalmente por el autor. Para falsarla sin PnL, V6 conserva confirmación del vecino DERECHO estrictamente anterior al instante de ruptura, primer retorno causal, M1 contiguas realmente cerradas, y requiere `CLOSE` atravesando nivel (no mecha). La geometría literal puede arrojar 0, 1 o 2+ referencias; jamás decide por cercanía, stop o rentabilidad.

[TTrades — MSS vs CISD, 01-JUL-2025](https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/): MSS necesita displacement y cierre más allá de un swing. **Ningún triple de esta prueba confirma displacement ni swing protegido/causante.**

## 2. Resultado con los mismos denominadores (no trades)

| Universo / clasificación | N | Interpretación |
| --- | ---: | --- |
| **V4 único 96 + V4 sin cierre 69** | **165** | No examinados por V6, preservados como fuera de 318 |
| **V4 múltiple (única cohorte V6)** | **318** | Pregunta fijada ANTES del código |
| V6 `ONE_LITERAL_INTERMEDIATE_COMPONENT_ONLY` | **113** | Exactamente una geometría literal recién cruzada; **componente, NO MSS** |
| V6 `MULTIPLE_LITERAL_INTERMEDIATES_UNKNOWN` | **44** | Referencias concurrentes, **WAIT/UNKNOWN** |
| V6 `NO_LITERAL_INTERMEDIATE_BREAK` | **161** | Ningún triple literal recién roto bajo esta política M1 causal; NO prueba ausencia de otro tipo de intermedio/HTF |
| **Cohorte fuente total** | **483** | 165 fuera de V6 + 318 examinados; no es censo de fills |

### Tabla cruzada V5 strict vs V6 literal (todos los 318)

| Clase V5 congelada | V6 único | V6 múltiple | V6 sin ruptura | Total |
| --- | ---: | ---: | ---: | ---: |
| V5 strict **NO** intermediate | **99** | **34** | **161** | **294** |
| V5 strict **SINGLE** intermediate | **14** | **10** | **0** | **24** |
| **TOTAL** | **113** | **44** | **161** | **318** |

**Hallazgo 1:** En **99/294** casos previamente sin intermedio estricto, el modelo literal obtiene **un candidato geométrico**, y en otros **34/294** obtiene varios. Los 294 no eran 294 rechazos autoriales: el filtro QORE excluía geometrías literales.

**Hallazgo 2 (contradicción de unicidad relevante):** De los **24** casos V5 estrictos, **10** incluyen otros triples literales que la desigualdad QORE descartaba. Si el perfil certificado aplicara únicamente la descripción literal sin política extra aprobada, esos 10 **NO** pueden tratarse como unívocos. Los otros **14** son únicos bajo ambos testigos, pero siguen sin displacement ni protected causation.

**Hallazgo 3:** Los **161** contextos sin triple básico recién atravesado pueden incluir intermediate **rebalanced/FVG**, reacción HTF, swing long-term u otras estructuras no modeladas. No trasladar `NO_LITERAL...` a `NO_VALID_MSS`.

**Cifras no aditivas:** 96, 318, 69 son la partición V4 de 483; 24/294 la partición V5 dentro de 318; 113/44/161 la partición V6 del mismo subconjunto 318. Ningún resultado significa entrada, oportunidad rentable, orden o sesión aprobada.

## 3. Garantías efectivamente comprobadas

- `Ruff PASS`, `pytest 46 passed in 1.16s`, incluidos adversariales LONG/SHORT, triple no estricto, empate estricto, dos referencias y abstención, wick-only, no re-disparar con cierre ya cruzado, vecino derecho no confirmado al mismo as_of, gaps M1, reloj naive/futuro y rechazo de `side` string.
- Pin de SHAs G3 COG/OPS originales, V2/V3/V4/V5 fuente, versión de preregistro y fuente real NAS100; ninguna de esas piezas fue modificada para obtener resultado.
- 483/483 casebook con fecha y primer instante ambiguo, todos los contadores V4 `96/318/69` y V5 `165/24/294` conservados. `full_casebook_sha256=3f50950a...` idéntico scalar vs 2 procesos fork. El workflow llegó a `SUCCESS` y publicó artefacto.
- No `CognitiveDecision` operativo, no `OMS`, `broker ACK`, lotaje, dinero, drawdown, PF, optimización, OOS o deployment. **El indicador de éxito sólo atesta reproducibilidad geométrica.**

## 4. Qué cambia en el plan de certificación M0–M7

**M3 P0-04: diagnóstico de causa mejorado, aún NO cerrado.** La elección metodológica es explícita y anterior a cualquier certificado: a) **perfil fuente literal**, donde 44 casos son multireferencia y 161 no tienen triple básico; b) **perfil QORE estricto** como regla propia, documentada, si Owner acepta formalmente ese perfil. No permitir que la cognitiva cambie entre ambas reglas en mitad de la sesión ni por resultados económicos. Hasta aprobación, **WAIT** en toda comparación controvertida.

**M3 P0-03 displacement:** sigue sin testigo fuente de expansión/velas revisado; *no* sustituir por `body >= 1.25 * median5` atribuido a TTrades, ni promover triple a MSS.

**M5 P0-09:** pivot intermedio geométrico **no** acredita cuál swing causó la expansión, ni qué nivel protege la invalidación. Al menos dos candidatos válidos ⇒ no inventar stop; los 113 literales únicos tampoco prueban causalidad.

**M4:** FVG, OB, Breaker y displacement directo requieren setup completo (zona/retest/invalidation/POI/timeframe), sin sumar componentes independientes como operaciones.

**M0/M1/M2:** integrar un solo perfil pre-sesión y reloj/CFD PIT; mantener congelado G3. **M6** firmas independientes #897 no resueltas; no fingir dos aprobadores usando un login. **M7** aún no emitido.

## 5. Secuencia concreta para el siguiente arquitecto

1. Revisar caso a caso **los 10** V5 strict-single → V6 literal-multiple y **los 99** V5 no-strict → V6 literal-single; documentar triples exactos, marcas de tiempo, evolución posterior y si el perfil necesita fuente/doctrina adicional. NO seleccionar por PnL.
2. Buscar evidencia TTrades específica sobre **basic vs rebalanced intermediate/FVG**, jerarquía LONG-TERM y swing protected; crear oracle positivo/negativo fuente antes de modificar otra clasificación. El video/pdf es evidencia complementaria, no licencia para convertir intuición en umbrales.
3. Crear suite M3 **displacement/cierre/causal swing separados** a partir de ejemplos autorales y confrontarla con los 113 componentes únicos, 44 múltiples y 161 sin triple. Cuando no hay evidencia, `UNKNOWN`.
4. M4/M5 completos, luego M0 runtime real y M6 firmas humanas sobre SHAs exactos; nunca autofirmar ni transferir certificados de scripts read-only al trader.

**Veredicto V6:** `LITERAL_INTERMEDIATE_RESEARCH_PASS`, `M3_AUTHOR_MSS=UNVERIFIED`, `M3_PROTECTED_SWING=UNVERIFIED`, `M4_M5=BLOCKED`, `M6=G3_PENDING_DUAL_SIGNATURE`, `CERTIFICADO_METODOLOGIA=NO_EMITIDO`, `CERTIFICADO_COGNITIVA=NO_EMITIDO`, `VT31_TRADER_CERTIFICADO=FALSE`. **NO MERGE**, NO DEMO/LIVE/VPS/FundedNext, NO SIZING.
