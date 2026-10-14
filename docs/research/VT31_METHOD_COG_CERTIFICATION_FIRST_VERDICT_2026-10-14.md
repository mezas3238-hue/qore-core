# VT31 — Certificación metodológica y cognitiva, dictamen inicial P0

**Fecha 2026-10-14 · Prioridad: METODOLOGÍA + COGNITIVA, no búsqueda de rentabilidad sobre histórico.**

**Veredicto de la primera fase:** `M0_M3_WITNESS_EXECUTED`; **`METHOD_CERTIFICATION_PENDING`**, **`COGNITION_CERTIFICATION_PENDING`**, **`TRADER_CERTIFICATION_PENDING`**. Los tests verifican causalidad y rechazo explícito de configuraciones incorrectas en un comprobador independiente; **no reescriben el COG, no introducen una entrada operable ni aprueban VT31**.

## Artefactos y ejecución comprobados

- [CI source + regresión real #38546461272 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38546461272), software probado commit **`0c3235b4d31880b9e0f8ac2d95b1bdc68916733e`**, **13/13 pruebas del nuevo comprobador** y **49/49 regresiones de los motores COG, OPS, M1 y G3** (62/62 en total), Ruff y compilación correctas, integridad de los blobs `cognition.py`, `operations.py` y acta G3 verificada; artefacto GitHub Actions **`11884129366`**.
- [Plan preregistrado M0–M7](https://github.com/mezas3238-hue/qore-core/blob/4477540e928dc9ec3bdbe437e2bea7a01990c9c9/docs/research/VT31_METHOD_COG_CERTIFICATION_PLAN_PREREG_2026-10-14.md), commit `4477540e928dc9ec3bdbe437e2bea7a01990c9c9`, publicado **antes** de la implementación.
- Nuevo comprobador: `scripts/vt31_ttrades_am_cognitive_fidelity_witness_20261014.py`; pruebas: `tests/infrastructure/test_vt31_methodology_cognitive_source_fidelity_20261014.py`; CI `.github/workflows/vt31-methodology-cognition-source-fidelity-p0.yml`.
- Código auténtico de COG y OPS en PR #896 **NO MODIFICADO**. Acta G3 r1.3 aún `PENDING_DUAL_SIGNATURE`, commit de documento `a446afa17ed6e411b8f0b6fc182b103a78959a97` y código `78d4cdac0e09d1a6eef37b99c505ffc5098031fc`; los bytes de Git originales siguen iguales.
- Todo es **test sintético y estudio de fuente**. Ninguna corrida M1 económica nueva, dinero, BID/ASK, órdenes, leverage, lotaje, holdout o VPS; main no modificado; ningún merge.

## Decisiones de identidad: evitar un error de certificación fundamental

| Perfil | Fuente y alcance | Certificación pretendida |
|---|---|---|
| `ICT_GENERAL_2023` | [Vídeo original ICT](https://www.youtube.com/watch?v=tRq1hyGGtl4); tres ventanas Londres 03–04, NY AM 10–11, NY PM 14–15 NY; DOL contextual. Reglas «09–10 H1» no se atribuyen por defecto a Londres/PM. | Falta testigo específico de método ICT por cada ventana, selección DOL y familias de entrada |
| `TTRADES_NY_AM_2025` | [Fuente oficial TTrades, 19-06-2025](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/): NY AM 10–11, alto/bajo anterior H1 09–10, barrido HIGH→SHORT y LOW→LONG, desplazamiento de regreso al rango, target H1 opuesto, entradas Displacement/FVG/OB/Breaker, stop más allá del swing. | **Testigo independiente de contexto M0–M3 ahora ejecutado**, aún sin integración al COG ni M4/M5 |
| `QORE_G3_MSS_CLOSE_V1_PROPOSED` | Formalización QORE: pivote de tres M1 confirmadas, cuerpo `>=1,25×median5`, DOL prior NY/Asia/Londres, primer FVG y CE, C2 stop propuesto; comparación contra fuente ya disponible en doc 12-10. | No reetiquetar «certificado ICT o TTrades» automáticamente |

**Resultado de revisión del código real:** el COG actual requiere H1/M15 causales y frescos y verifica MSS M1, pero **solo usa esos HTF como contexto disponible**; la dirección viene del cruce de un micropivote M1 y del DOL elegible, con preferencia por el objetivo más cercano. No exige directamente el barrido del 09–10 H1, ni elegir el nivel H1 opuesto como DOL NY AM de TTrades. En el comprobador, un DTO sintético con objetivo `PRIOR_NY_CASH_SESSION_HIGH=150` cuando H1 09 tiene high `110` es **REJECTED** por `DOL_NOT_OPPOSITE_9AM_H1_EXTREME`; la fuente de DTO es sintética, **NO** una nueva prueba de que todas las decisiones COG reales fallen.

## Qué se ejecutó exactamente en el comprobador

**Entrada:** `CognitiveDecision` definido en código real + **60 M1** del H1 09–10 completo + prefijo de velas M1 cerradas desde 10:00 hasta `observed_at`. El comprobador no usa outcomes ni reetiqueta señales.

1. Exige reloj local `America/New_York`, solo NY AM, M1 continuas, H1 completo y as-of exactamente la última M1. Faltantes, DST/contexto ambiguo y velas futuras = veto.
2. Registra el primer sweep del alto/bajo H1; no permite cero barridos, barrido de lado equivocado, dos lados dentro de la misma M1 (precedencia intraminuto desconocida) ni cambio de lado antes de la decisión.
3. Exige MSS observado en la M1 de 10:00–11:00 **después** del barrido, pivote confirmado antes de MSS y cierre direccional estrictamente DENTRO del H1 de 09. **No certifica con ello que 1,25×median5 o pivote-3M1 sean el MSS canónico del autor**; valida coherencia causal contextual.
4. Exige target exacto high 09 para LONG después de barrer low, o low 09 para SHORT después de barrer high. Un destino NY/Asia/London distinto es inconforme respecto a **TTrades AM específico**, no inválido universalmente para ICT.
5. Incluso en test sintético ideal, devuelve `CONTEXT_CONFORMANT_ONLY`, flags `methodology_certified=false`, `cognitive_certified=false`, `execution_authorized=false`. **No hay lógica para convertir un PASS de contexto en autorización de trading.**
6. 13 casos adversariales/testigo sintéticos PASARON, además de 49 regresiones reales COG/OPS/G3/M1; esto certifica **integridad de software respecto a sus pruebas**, no fidelidad integral ni expectativa neta positiva.

## Estado de los gates M0–M7 y soluciones concretas

| Gate | Estado comprobado | Trabajo técnico siguiente |
|---|---|---|
| **M0 fuente e identidad** | **FUENTES SEPARADAS, diseño documentado**, perfiles no implementados todavía en selector de producción | Crear contrato de perfiles explícito con fuente y versión; elegir variante por señal SIN mezclar ICT/TTrades |
| **M1 causalidad / reloj** | **62/62 QA PASS** (13 de fuente nuevos + 49 de regresión), no prueba de todas las condiciones del mercado | Añadir pruebas por sesión con DST verano/invierno, gap histórico y reinicio NY date |
| **M2 sweep/DOL TTrades** | **Comprobador independiente FUNCIONAL**, COG instalado carece del gate TTrades | Evaluar propuesta en nuevo PR COG exclusivo NY AM, no injertar en G3 signed-review |
| **M3 desplazamiento de retorno** | **Testigo causal de coherencia FUNCIONAL**, no validación autoral del pivote y umbral | Definir evidencia MSS vs BOS y revisión estructural con casos autorales antes de promover |
| **M4 cuatro entradas** | PR #906 detectores `SOURCE_ONLY`: displacement/FVG/OB/breaker proxy; **NO integrados**, no conformidad completa TTrades | Lista de ejemplos primarios de cada familia + caso negativo comparable + etiquetas `SOURCE_AMBIGUITY` |
| **M5 stop/TP** | G3 C2/wick/tick propuesto **distinto de TTrades stop swing**, no integrado; sin orden de ejecución | Una política por perfil, stop derivado causalmente del setup, orden y conflicto de fills, sin sizing propio |
| **M6 revisión dual COG/OPS** | **PENDIENTE**, issue #897, no falsificar autorizaciones | Firmantes independientes reales o cambio formal explícito de gobernanza; ninguno aprobado |
| **M7 rentabilidad / trader** | **NO CERTIFICADO**, sin BID/ASK–fills OOS | Validación económica separada y certificación Core cuando exista base real |

### Criterio de avance que no depende de resultados financieros

1. Congelar **qué método se pretende certificar** por cada ventana y quién define el nivel de entrada/SL/TP. Un VT31 puede contener más de un perfil, pero debe identificarse y auditarse cada uno sin alterar reglas por retorno histórico.
2. Definir **COG Decision Evidence** con sellos as-of de liquidez previa, barrido, MSS, desplazamiento, DOL, estado `UNKNOWN/REJECT/CONFIRMED` y fuente exacta. Actualizarlo cada nueva M1 sin adivinar datos intrabar ni reclamar confirmación con el futuro.
3. Pasar **pruebas semánticas de alta fidelidad** mediante casos reproducibles de videos/autores y sus condiciones de no-trade, más pruebas adversariales sintéticas, antes de permitir modelos de entrada. Los videos no son especificaciones deterministas de OB/Breaker; no inventar «fidelidad total».
4. Sólo con aprobación metodológica/cognitiva trazable, pasar a contrato OPS y motores de orden/economía; no confundir con `EDGE_VERIFIED`.

**Decisión P0:** seguir trabajando **sí** por metodología y cognitiva, **no** considerar al trader certificado todavía. Se han detectado diferencias doctrinales exactas y hay un nuevo comprobador operativo de contexto, pero el COG general aún no consume ese comprobador ni tiene contrato de elección de perfil. La fase prioritaria siguiente no es otro filtro cuantitativo: es integrar decisiones cognitivas con testimonios verificables en una nueva rama, revisando el MSS y DOL para la fuente escogida.
