# QORE CORE — VT31 · HANDOFF MAESTRO DE CONTINUIDAD R2
## Certificación de METODOLOGÍA y COGNITIVA · corte 14-OCT-2026

**Repositorio soberano:** https://github.com/mezas3238-hue/qore-core  
**Misión impartida por Owner:** terminar la certificación metodológica y cognitiva de VT31; no perseguir PF mediante optimización retrospectiva. Registrar todo lo hecho, todo lo pendiente y todos los problemas para que el próximo arquitecto continúe exactamente donde quedó.  
**Handoff anterior (R1):** [PR #931](https://github.com/mezas3238-hue/qore-core/pull/931), documento en commit 778e419d005951c0efb435256cb0859b4d042946. **R2 amplía R1**, no lo borra.  
**Rama R2:** docs/vt31-master-handoff-cert-method-cog-20261014-r2, derivada exactamente del HEAD verificado PR #938: 888e048edeff7899fb086e526bd5b0af9c44140a. El handoff R2 es documentación, no cambia el trader.  
**Veredicto a este corte:** **VT31_METHOD_CERTIFICATION_PENDING; VT31_COGNITIVE_CERTIFICATION_PENDING; TRADER_NOT_CERTIFIED; ECONOMIC_EDGE_NOT_DEMONSTRATED; G3_PENDING_DUAL_SIGNATURE; NO_GO_LIVE.** 150/150 pruebas del último ensayo M4-P1, NO equivale a certificación M4 completa ni L1–L10.

> **LEER ANTES DE HACER CAMBIOS:** GitHub constituye la fuente de verdad. Diferenciar pruebas de implementación (software), fidelidad al método original, evidencia de decisiones del COG REAL y certificación económica. Ninguna puede sustituir a otra. Mantener la misión vigente en metodología/cognitiva. No falsificar dos aprobaciones usando la única cuenta del Owner; si se necesita cambiar gobernanza, versionarla explícitamente.

---

## 0. Mandatos absolutos y límites de autoridad

1. **NO MERGE** a main sin orden expresa del Owner; todo cambio en rama research y PR DRAFT con preregistro, hash, CI y acta. No modificar por conveniencia los SHA frozen del G3 #896; no desplegar a producción/VPS; **NO LIVE / FundedNext LIVE**; no crear órdenes reales ni promover LAB/DEMO por este handoff.
2. **Trader VT31 sin sizing propio**. CIBO CMA tiene autoridad de volumen; QDLE es motor de factibilidad cuando corresponda. Certificar cognición, geometría y fuente no requiere dimensionamiento monetario.
3. **Fresh Holdout sellado**. Los 1.059.784 M1 de 2023-10 a 2026-10 ya fueron estudiados y son desarrollo exploratorio; resultados en ese corpus no se convierten en OOS por preregistrar una nueva implementación.
4. NO recuperar el viejo VT31 defectuoso ni reinterpretar el antiguo ledger B (51 stops B no probados, 619 conflictos históricos); nuevo proyecto metodológico M1 desde cero. No reciclar 2.140 fuentes A/B OLD como cohorte nueva G3.
5. Toda cognición consumirá **M1 cerradas y disponibles as-of**, zona America/New_York con DST, eventos independientes COG/OPS. Imposible conocer orden high→low de una M1 sólo por OHLC: conservar UNKNOWN; un CE touch sin broker ACK es NOT_FILL.
6. Tres identidades estrictamente diferenciadas: **ICT_GENERAL_2023** (LONDON 03–04 NY, NY AM 10–11 NY, NY PM 14–15 NY), **TTRADES_NY_AM_2025** (variante sólo AM con rango H1 09–10) y **QORE_G3_PROPUESTA** (reglas de ingeniería propias). No trasladar regla H1 09 de TTrades a London/NYPM universalmente; no atribuir umbral cuerpo 1,25×mediana5, stop C2 o selección DOL más cercano al autor ICT.
7. No retocar reglas para que los 128 contextos, 119 FVG o 61 touches parezcan más rentables. Si cambia la metodología, nueva versión, prereg y nuevo holdout; no reetiquetar PASS de versiones anteriores.

## 1. Fuente de doctrina y arquitectura del trader

**Un único VT31 NAS100**, con perfiles de investigación de Silver Bullet. No confundir NAS100 CFD y futuros NQ ni homologar nombres de broker sin contrato. Velas M1 obligatorias para estructura, MSS y FVG. H1/M15 sirven de contexto cuando el perfil lo prescribe, sin futuro.

**ICT GENERAL 2023.** Fuente principal: [ICT Silver Bullet Time-Based Trading Model, vídeo](https://www.youtube.com/watch?v=tRq1hyGGtl4), con contraste específico en docs/research/VT31_2023_PRIMARY_VIDEO_DOCTRINE_DELTA_2026-10-12.md. Silver Bullet temporal 03–04, 10–11, 14–15 NY; desplazamiento, FVG y draw on liquidity. No asumir que el vídeo impone por igual H1 09 previo, C2 stop, primer FVG elegible siempre, lotaje, parcial/BE/trailing o ratio fijo.

**TTrades NY AM 2025.** Fuente [The AM Silver Bullet Strategy on NQ](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/). Rango HIGH/LOW del H1 09–10 NY completo; primer barrido tras 10:00; HIGH raid → sesgo SHORT hacia LOW 09, LOW raid → LONG hacia HIGH 09; regreso/desplazamiento dentro de rango; menciona familias direct displacement, FVG, order block, breaker block. Stop descrito más allá del swing de desplazamiento; no se desprenden algoritmos unívocos para OB/Breaker, FVG preferido, simultaneidad MSS/regreso ni multiplicador de cuerpo. Tratar implementación restante como QORE_PROXY, con revisión autoral pendiente.

**QORE G3 r1.3 propuesta NO FIRMADA:** [PR #896](https://github.com/mezas3238-hue/qore-core/pull/896); acta commit a446afa17ed6e411b8f0b6fc182b103a78959a97 (blob e99c70b4e018d626fb620d9a21b9314a51abc36d), código/CI commit 78d4cdac0e09d1a6eef37b99c505ffc5098031fc. Pivote M1 estricto, confirmación MSS por cierre desplazado >=1,25×mediana de cinco cuerpos previos, ancla MSS.close y potencial al DOL >=10 puntos, primer FVG causal de C1-C2-C3 cerrado, CE 50%, referencia SL mecha COMPLETA C2 ± un tick oficial con al menos dos ticks riesgo, TP DOL fijo, cancelación pendientes al fin de ventana, salida de posición no resuelta antes de 15:55 NY, sin parciales/BE/trailing. Estas son **decisiones QORE de investigación**, no toda doctrina ICT. Faltan firmas COG+OPS, broker tick exacto, OMS/ACK y validación económica.

## 2. MAPA MAESTRO de avances y SHA — cronología comprobada

Los recuentos de regresiones **se solapan entre PR**. Nunca sumarlos como muestras independientes ni como trades.

| PR | Producto y frontera | CI/veredicto |
|---|---|---|
| [#896](https://github.com/mezas3238-hue/qore-core/pull/896) | Acta G3 r1.3, falsificación real MSS COG→OPS; DRAFT unsigned | [CI #38343414831](https://github.com/mezas3238-hue/qore-core/actions/runs/38343414831) **41/41**. Ver #897 |
| [#926](https://github.com/mezas3238-hue/qore-core/pull/926) | Prereg M0–M7, fuentes ICT/TTrades/QORE, testigo M0–M3 NY AM no runtime | [CI #38546753088](https://github.com/mezas3238-hue/qore-core/actions/runs/38546753088), **62/62**; HEAD 82ea1ab802ede75d7fbd965ee42cce23e7ce1487 |
| [#927](https://github.com/mezas3238-hue/qore-core/pull/927) | COG **auténtico** (clase original) en M1 sintéticas emitió LONG MSS 107→prior cash 150 sin raid 09 H1 ni DOL opuesto; TTrades testigo REJECTS | [CI #38579110581](https://github.com/mezas3238-hue/qore-core/actions/runs/38579110581), **69/69**. Discrepancia doctrinal real de código, no falsación de ICT general |
| [#928](https://github.com/mezas3238-hue/qore-core/pull/928) | COG_EVIDENCE_V2 independiente: pivote3, MSS close, displacement y contexto H1 por perfil; devuelve REJECTED/UNKNOWN/CONFIRMED limitado | [CI #38594178014](https://github.com/mezas3238-hue/qore-core/actions/runs/38594178014), **80/80**. HEAD 90f2ce2a957823389fc5d999eedd198c3f20d55a |
| [#929](https://github.com/mezas3238-hue/qore-core/pull/929) | MC-P2 atestador nativo TTrades H1 09, primer raid, regreso M1 POSTERIOR, DOL opuesto y comparación V2 | [CI #38607626630](https://github.com/mezas3238-hue/qore-core/actions/runs/38607626630), **101/101**. HEAD 54ed47d35db25df5c47115cac6888da4c58801d7 |
| [#930](https://github.com/mezas3238-hue/qore-core/pull/930) | MC-P3 **rama hermana**: testigo independiente DOL QORE prior cash, Asia y London para tres sesiones ICT general; verdadero COG con input M1 sintético | [CI #38608745246](https://github.com/mezas3238-hue/qore-core/actions/runs/38608745246), **103/103**. HEAD 1c820086339323f79d4ec1cb5954fb53841064b2 |
| [#931](https://github.com/mezas3238-hue/qore-core/pull/931) | Primer handoff maestro R1 (corte anterior a los censos reales) | Doc SHA 778e419d005951c0efb435256cb0859b4d042946, no sustituir por R2 |
| [#932](https://github.com/mezas3238-hue/qore-core/pull/932) | Otro testigo independiente ICT DOL (cash 390 / Asia 180 / London 120). Base #929; **alternativa/solapado con #930** | HEAD e3f65b34599cc868d6cf1867dcc3df480e1e66d4. Reconciliar ANTES de adoptar uno |
| [#933](https://github.com/mezas3238-hue/qore-core/pull/933) | Productor de COG research TTrades AM separado de COG G3; no sustituye runtime general; MSS proxy QORE después del primer retorno | [CI #38621919251](https://github.com/mezas3238-hue/qore-core/actions/runs/38621919251), **154/154** referido por #934; HEAD 1556766c1831190b5459bf93404081412200ba7d |
| [#934](https://github.com/mezas3238-hue/qore-core/pull/934) | Censo causal real M1 de TTrades 3Y development, sólo primer regreso y MSS proxy, sin PnL | [CI #38622553350](https://github.com/mezas3238-hue/qore-core/actions/runs/38622553350), **159/159**. 775 días, **128 contextos**. HEAD 35bd317ddfed60e09523287de51347683d98e613 |
| [#935](https://github.com/mezas3238-hue/qore-core/pull/935) | M4 primer FVG 3 M1, CE 50%, referencia C2 full wick, M5 precio M1 NOT_FILL/AMBIGUOUS/EXPIRED | [CI #38634407465](https://github.com/mezas3238-hue/qore-core/actions/runs/38634407465) **179/179**; 119 FVG, 8 sin FVG, 1 tardío. HEAD 6d8bd9bae747707659e8a850a625aef7437b68a1 |
| [#936](https://github.com/mezas3238-hue/qore-core/pull/936) | Auditoría de **Gates oficiales Trader Lab L1–L10** (capa obligatoria adicional, no sustituto de M0–M7) | Matriz en docs/research/VT31_GATES_CANONICOS_TRADER_LAB_L1_L10_MATRIZ_CERTIFICACION_2026-10-14.md. HEAD 91571de79a17cab7556d15ea2bc209700a60a611 |
| [#937](https://github.com/mezas3238-hue/qore-core/pull/937) | **Preparación L3**, paridad de reloj streaming M1 ×1/×32; no confundir con habilitación L3 | Investigación de equivalencia propuesta; **no declarar L1/L2/L3 QUALIFIED** sin candidato freeze+replay y evidencia promocional. HEAD e504b46dd17f5859d95eba614c9e3faa7db9d524 |
| [#938](https://github.com/mezas3238-hue/qore-core/pull/938) | **ÚLTIMA VERIFICACIÓN REAL DE ESTE HANDOFF:** 128 contextos y **5.155 prefijos M1** → primer FVG, CE y C2 sin anticipación/cambio por velas futuras; M5 primer evento terminal inmutable | [CI #38639069852](https://github.com/mezas3238-hue/qore-core/actions/runs/38639069852), código ejecutado ea50262dc1327a793168f35aaef8746d7a8cc897, **150/150**. Doc HEAD 888e048edeff7899fb086e526bd5b0af9c44140a; artifact #11929562855, ZIP SHA256 91e0b923b311fa77233dd123cd29551e84ceb31f2b1869b328507a0b894fb09a |

**Evidencia de la versión anterior y rutas:** archivo del #938: [auditoría detallada](https://github.com/mezas3238-hue/qore-core/blob/888e048edeff7899fb086e526bd5b0af9c44140a/docs/research/VT31_M4_P1_128_REAL_M1_FIRST_FVG_CAUSAL_PREFIX_VERDICT_2026-10-14.md). Los HEAD documentales pueden tener commits posteriores a los ejecutados; siempre vincular CI con su **run.head_sha**, no inferir que prueba cada commit posterior.

**No integrar sin reconciliar:** rama paralela de Evidence V2 no canónica agent/vt31-cog-evidence-v2-p0-20261014 tuvo CI FAIL #38607867244 y #38607963276 (Ruff / serialización y expectativas incoherentes). Canónica de investigación es #928. El productor TTrades #933 es otra cosa que la COG G3 original; no combinar sin selector de perfil y testigos.

## 3. Dato REAL NAS100 y distribución de estados cognitivos

**Fuente original**: GitHub Actions [artifact #11459859004](https://github.com/mezas3238-hue/qore-core/actions/runs/38018856150), miembro NAS100/market-evidence.json, **1.059.784 M1** entre 2023-10-01 y 2026-10-01, SHA256 **0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa**. Confirmado repetidamente por los CI. Son velas desarrollo ya vistas, **no test confirmatorio OOS**.

**Censo #934** (775 días NY AM con H1 09 y 10):
- **128** primer regreso + MSS QORE corroborados como CONTEXTO;
- **483** primer regreso sin MSS QORE EN ESA MISMA M1;
- **92** sweep sin regreso;
- **65** sin sweep;
- **6** horas incompletas;
- **1** caso REJECTED_SOURCE; investigar reason code en artifact #11921659492, no inventar causa.
Todos suman **775**. En 769 días completos, 128/769 = 16,64% fueron contextos. No son trades ni WR. La acumulación de 483 muestra la **condición más restrictiva de este proxy**, pero no prueba que deba eliminarse ni que autor TTrades la exija.

**M4/M5 #935 y paridad independiente #938**, mismos 128 contextos:
- **119** con primera geometría FVG elegible de QORE; **8** no FVG; **1** primer FVG justo a 11:00 sin entrada nueva;
- dentro de los 119: **61 TOUCH_NOT_FILL**, **31 AMBIGUOUS_M1_SEQUENCE_NO_FILL**, **27 EXPIRED_NO_ORDER_OR_ACK**;
- **5.155** prefijos evaluados por #938, **0 mutaciones detectadas** de primer C3 / side / FVG / CE / C2 FULL WICK / DOL / MSS anchor después de su formación; primer estado terminal M5 estable. Prueba **ingeniería causal** de ese proxy FVG sobre desarrollo, NO prueba de stop broker, ejecución, ni fuente autoral completa.
- **0 órdenes enviadas / 0 broker ACK / 0 fills / 0 PF / 0 DD / no Sharpe**. Nunca dividir 61/119 como fill rate, 119/128 como win rate o convertir 128 contextos en PnL.

**QORE Native BID/ASK cTrader como contexto (NO certificación del método):**
- [PR #899](https://github.com/mezas3238-hue/qore-core/pull/899) primera captura real USTEC 6h + [PR #901](https://github.com/mezas3238-hue/qore-core/pull/901) 24h adicionales: **483.103 ticks-side** (241.538 BID + 241.565 ASK), **30 horas** de Silver Bullet en **10 días** desarrollo.
- En los 1.800 M1 coincidentes con esos tramos: HIGH/LOW/CLOSE M1 = extremos/último BID en **1.800/1.800**; OPEN **1.789/1.800**, **11** discrepancias. **Dos** instantes ASK<BID quedaron en cuarentena; fuente presenta timestamps sides muy sincronizados y spreads históricos potencialmente reconstruidos. No atribuir quote a fill.
- **Bloqueadores:** NAS100↔USTEC/NDX100 contrato no homologado; faltan tick_size, valor punto, stops/freeze levels, comisiones y cobertura **desde entrada hasta SL/TP o 15:55 NY**, no sólo tres horas fuente. Artifacts de Actions de 90 días no son almacenamiento duradero (issue #837).
- La prueba direccional antigua 2.140 fuentes OLD a horizonte 15m fue desfavorable (aprox. **−1,92 puntos brutos** por candidato); NO corresponde al nuevo perfil MSS+CE de V1. Informe P0 [PR #903](https://github.com/mezas3238-hue/qore-core/pull/903) concluye NO GO económico actual, **NO demostración matemática de pérdida para nueva V1**.

## 4. Dictamen de los GATES METODOLÓGICOS y COGNITIVOS M0–M7

| Gate | Qué exige para CERTIFICAR (no sólo ingeniería) | Hechos obtenidos | VEREDICTO HONESTO |
|---|---|---|---|
| **M0 PERFIL/IDENTIDAD** | fuente primaria, reglas originales vs QORE, versión única por perfil y selector sin contaminación | #926/#928/#929; perfiles ICT_GENERAL, TTRADES_AM y QORE separados en investigación | **PARCIAL**: perfiles descritos; candidato runtime unido no congelado |
| **M1 CAUSALIDAD M1/TIEMPO** | DST real, 09H1 TTrades completo, only closed M1, sin lookahead, cash/Asia/London fuente as-of | testigos #927–#930, censo #934, prefix #938 **5.155 PASS** para FVG | **ENGINEERING_PASS EN ALCANCE**, no M1 universal de las cuatro familias |
| **M2 LIQUIDEZ/DOL** | TTrades: primer raid del H1 09, sesgo y DOL opuesto; ICT GENERAL: origen DOL independiente sin imponer H1 09 | #929 H1, #930 y #932 dos verificadores DOL independientes; primero puede reconciliar fuente, no doctrine | **PARCIAL**: #930/#932 contrato sin reconciliar, no universo real ICT completo |
| **M3 MSS/DESPLAZAMIENTO** | pivote, cierre de ruptura, desplazamiento, as-of, retorno tras sweep por perfil, evidencia COG genuina | #927 incompatible TTrades AM cuando usa COG general; #933 emisor perfil separado, #934 128 contextos reales del **proxy QORE** | **PARCIAL**: aún no fidelidad universal, 483 primeros regresos sin MSS proxy |
| **M4 ENTRADAS** | displacement directo, FVG, OB y breaker, geometría específica fuente, prioridades entre varios patrones y pruebas causales por familia | #906 proxies 4 familias; #935 y #938 **FVG QORE 119 casos** y estabilidad causal | **NO CERTIFIED**: OB/Breaker autorales no especificados; FVG proxy solo |
| **M5 STOP/TP/INVALIDACIÓN** | por perfil stop del swing causante o política QORE explícita C2, tick oficial, DOL, cancelación y secuencia temporal sin falsos fills | C2 full wick + CE M1 fuente, 61 touch, 31 ambiguous, 27 expired, inmutable #938 | **NO CERTIFIED**: sin broker spec/ACK ni orden real de eventos intrabar |
| **M6 DOBLE FRONTERA COG/OPS** | separación de responsabilidades, testigos contra DTO falso, dos aprobadores independientes o enmienda formal de gobernanza | #896 41 adversariales PASS, [issue #897](https://github.com/mezas3238-hue/qore-core/issues/897) abierto; Owner indica que posee una sola cuenta | **PENDING_DUAL_SIGNATURE**: una cuenta no son dos aprobaciones |
| **M7 CIERRE** | convergencia real M0–M6 + certificación separada economía/OOS/riesgo antes de promover trader | ninguna curva neta ejecutable ni aprobación del candidato completo | **NOT_CERTIFIED; NO_GO** |

**Condición de éxito del mandato inmediato:** certificar por fuentes y pruebas adversariales **M0–M6** por perfil (sin disfrazar UNKNOWN) y congelar esa versión. Certificación del **trader integral** exige además M7 y los Gates oficiales. Esta distinción impide «certificación metodológica» falsa aunque existan 150 tests.

## 5. Los Gates oficiales QORE Trader Lab L1–L10 — NO OMITIR

Autoridad: [Issue #473](https://github.com/mezas3238-hue/qore-core/issues/473), [QORE-TRADER-LAB-001.md](https://github.com/mezas3238-hue/qore-core/blob/main/docs/architecture/QORE-TRADER-LAB-001.md), [matriz completa #936](https://github.com/mezas3238-hue/qore-core/pull/936); código lifecycle.py, stage_evidence.py, promotion.py. El código enumera 9 etapas lifecycle, pero la promoción exige además **L7 ECONOMIC_EVALUATION**; por eso el contrato completo del Issue #473 contiene diez puertas.

| Gate | Estado actual | Bloqueador |
|---|---|---|
| L1 METHOD FREEZE | INCOMPLETE | una versión completa y fuente autorizada, selector y firmas M6 faltan |
| L2 REPLAY | INCOMPLETE | censo fuente 0 operaciones/ACK no es replay de candidato completo |
| L3 FAST-FORWARD | NOT QUALIFIED | #937 es preparación, no paridad promocional de L1+L2 exactos |
| L4 FRESH OOS | BLOCKED | corpus 3Y ya estudiado, nuevo holdout requiere freeze y protección |
| L5 STRESS | PARTIAL | adversariales causales no sustituyen spread/slippage y fallos operacional/económicos |
| L6 MONTE CARLO | BLOCKED | no hay ledger de fills netos para remuestrear |
| L7 ECONOMIC EVALUATION | BLOCKED | 0 fills, sin contrato/ticks completos/costes, PF/DD sin identidad |
| L8 RISK REVIEW | PENDING | autorización externa autenticada y riesgo del mismo candidato |
| L9 CIBO REVIEW | PENDING | evaluación autoridad CIBO con riesgos/volumen externo; no sizing trader |
| L10 INDEPENDENT VALIDATION | PENDING | un auditor autorizado valida paquete único completo; no sustituir firmas #897 |

Ninguna de L1–L10 está homologada como conjunto, ni se declara DEMO_ELIGIBLE. No inventar umbrales universales PF/Sharpe/Sortino: preregistrar criterios aprobados por QORE antes de medir desempeño. La certificación profunda requiere operating/non-operating envelope, competencia por régimen, autopsia de pérdidas y consistencia; el programa QORE distingue LAB_CERTIFIED, DEMO_CERTIFIED y LIVE_AUTHORIZED. El Owner no autorizó LIVE en ningún caso.

---

## 6. REGISTRO P0/P1 DE PROBLEMAS — causas, solución y criterio de cierre

### B01 P0 — No existe todavía una sola especificación metodológica firmada para cada perfil
**Evidencia:** ICT general, TTrades AM y QORE G3 se usan en distintos testigos; PR #896 sigue unsigned.  
**Resolver:** tabla normativa regla→fuente minuto/pasaje→interpretación→perfil→prohibiciones→DTO y archivo SHA. Obtener decisión explícita de qué perfil se desea certificar y NO mezclar reglas de autores.  
**Cierre:** M0 pasa pruebas negativas cruzadas y selector runtime versionado; sin doctinas no soportadas.

### B02 P0 — COG genérico no es el COG TTrades AM
**Evidencia:** [#927/#928](https://github.com/mezas3238-hue/qore-core/pull/927) productor real emitió LONG DOL previous cash=150 cuando TTrades requería high H1 09=110, sin raid.  
**Resolver:** mantener emisor TTrades research por perfil de #933, certificar sobre fuente y **comparar contra COG auténtico en NAS100 real**; NO reemplazar COG G3 sin nuevo protocolo y revisión.  
**Cierre:** toda decisión TTrades requiere primer raid, dirección, MSS/shift y opuesto H1 atestiguados; cero conversiones ficticias de estado.

### B03 P0 — Dos testigos DOL ICT GENERAL alternativos, sin contrato único
**Evidencia:** #930 rama hermana de #928; #932 rama descendiente de #929. Ambos reconstruyen pools, pero pueden diferir en calendario, gaps, disponibilidad de cash anterior, as-of y semántica de UNKNOWN.  
**Resolver:** correr **ambos sobre una lista inmutable de source M1 real**, registrar matriz concordante/discordante con razones y testigos extremos. Elegir uno sólo por precedencia de fuente y seguridad causal, **no** por cantidad de señales ni profit. Si las discrepancias no se resuelven, NO certificar M2 general.  
**Cierre:** reporte de equivalencia y fuente de verdad claramente versionados, diff revisado; conservar la rama no elegida sin mezclar sin control.

### B04 P0 — Desplazamiento/retorno TTrades no tiene definición autoral algorítmica completa
**Evidencia:** #933 exige MSS proxy QORE en la misma M1 del primer regreso; **483** primeros regresos sin MSS de 775 días.  
**Resolver:** identificar testigo audiovisual de displacement, confirmar distinción regreso vs MSS y secuencias válidas; si falta pasaje, etiquetar SOURCE_UNDERDETERMINED y certificar únicamente como formalización QORE separada.  
**Cierre:** testigos positivos/negativos por perfil antes de cambiar el emisor; jamás recuperar esos 483 por optimización de retorno.

### B05 P0 — M4 completo sigue sin validar las cuatro familias
**Evidencia:** #938 valida sólo primer FVG QORE; #906 contiene proxies de displacement/OB/Breaker, no identidad fuente.  
**Resolver:** ficha por familia (definición del autor, causalidad M1, invalidación, primera oportunidad, prioridad cuando coexisten, conflictos, zona, mínimo contexto), prueba independiente con casos adversariales, rechazo de inferencia cuando source es imprecisa.  
**Cierre:** matriz M4 por familia/version, pruebas en fuente M1 de desarrollo sin hindsight, abstención por faltantes; no certificar las 4 por contar 119 FVG.

### B06 P0 — STOP TTrades swing vs stop G3 C2 FULL WICK NO son equivalentes
**Evidencia:** texto TTrades pide beyond swing causante; G3 congelado-para-revisión propone C2±tick como QORE ingeniería.  
**Resolver:** dos contratos separados por perfil con regla de origen M1, timestamp, invalidación, y evidencia de valor tick broker. Ninguna conversión silenciosa.  
**Cierre:** testigos M5 LONG/SHORT/DST, diferencia de ambos modelos explícita, bloqueos por symbol spec.

### B07 P0 — Intrabar y ejecución: 31 casos ambiguos + 0 ACK
**Evidencia:** 61 CE touches y 31 touch/invalidación misma M1, 27 expiración; no se conoce secuencia.  
**Resolver:** motor source-only de transición LIMIT_pending→order ACK→fill/reject/cancel ACK→stop/TP/time exit, con tiempo causal, eventual quotes y adversarios same-ms y delay. No declarar fills sin prueba; M5 source UNKNOWN puede permanecer cuando datos no resuelvan precedencia.  
**Cierre:** ninguna ruta M5 etiquetada filled desde solo OHLC; auditoría de todas las carreras/latencia.

### B08 P0 — M6 firmas originales COG/OPS inviables con una cuenta personal
**Evidencia:** [Issue #897](https://github.com/mezas3238-hue/qore-core/issues/897), PR #896 DRAFT sin dos approvals genuinos.  
**Resolver:** el Owner puede **modificar formalmente** el proceso de gobernanza para contexto de un solo usuario con revisión técnica independiente documentada, sin fingir cuentas/firmas; o designar verdaderos revisores con permisos. Aprobación de Owner para revisar YA permite investigación, **no** equivale a cumplimiento de una regla dual escrita sin enmienda.  
**Cierre:** documento de gobernanza aprobado con identities/procedure y hashes, acto de revisión auténtico sobre mismo SHA.

### B09 P0 — Broker NAS100/USTEC contrato y quotes económicas no homologadas
**Evidencia:** fuente 30h cTrader real, matches 1.800 HIGH/LOW/CLOSE con BID, pero no prueba tick size, lot point value, fees/stops/freeze ni fill. 11 aperturas distintas, 2 quotes crossed, timestamps laterales sincronizados.  
**Resolver:** [issues #857](https://github.com/mezas3238-hue/qore-core/issues/857) y [#900](https://github.com/mezas3238-hue/qore-core/issues/900): certificación símbolo exacto/account/source, event-time/receipt-time, BID/ASK hasta 15:55/SL/TP, OMS/ACK. Mantener G5 artifacts fuera de repo público y proteger su retención.  
**Cierre:** source/contract witness, quotes de trayectoria íntegra, anomalías con motivo reproducible; solo después es lícito un replay económico VERSIONADO.

### B10 P1 — Reconciliar errores/lagunas del 3Y real antes de declarar tasa causal global
**Evidencia:** 6 días 09/10 incompletos; 1 REJECTED_SOURCE en #934; 11 divergencias M1 OPEN en fuente G5.  
**Resolver:** inspeccionar códigos por día en artifact #11921659492 y conciliar M1 con tick BID/ASK ya descargados; NO rellenar huecos para fabricar PASS ni elegir días por PnL.  
**Cierre:** reporte por fecha y razón, estado UNKNOWN conservado y recuentos de 775 sin cambios no autorizados.

### B11 P1 — Fuente original ICT/TTrades incompleta para OB/Breaker
**Evidencia:** pasaje escrito menciona familias, no algoritmos universales.  
**Resolver:** investigación audiovisual/citación precisa de geometría y condiciones, clasificar ORIGINAL_EXPLICIT/ORIGINAL_AMBIGUOUS/QORE_FORMALIZATION. Si no es identificable, no prometer certificación autoral.  
**Cierre:** acta de identidad reproducible con juez negativo de confluencias.

### B12 P1 — Dependencias GitHub DRAFT y genealogías divergentes
**Evidencia:** #927 rama hermana de #928, #930 rama hermana #932; #933→#934→#935→#938 encadenados; #937 surge de matriz #936; #931 handoff antiguo.  
**Resolver:** crear grafo de dependencias, comparar sha/archivos tocados, CI exacta y preregs; incorporar sólo piezas adicionales aprobadas tras reconciliar fuentes. **No merge main ni cherry-pick ciego**.  
**Cierre:** candidato único research con interfaces coherentes, sin perder pruebas #927 ni mutar G3.

### B13 P1 — Rama V2 alternativa roja
**Evidencia:** CI #38607867244 y #38607963276 FAIL de una implementación distinta a #928.  
**Resolver:** no promover esa implementación; estudiar logs/declaraciones y decidir descartar o portar solo testigos nuevos con prereg sobre la rama canónica.  
**Cierre:** cero alias y nombres colisionados; QA verde de implementación elegida.

### B14 P1 — Resultados económicos antiguos no identifican V1
**Evidencia:** directional screen OLD ~−1,92 pts, antigua B 619 UNKNOWN/51 stops fail, ledger 2.140 elegidos por DOL-C3 en vez de MSS.close; V1 nueva no tiene órdenes/ACK.  
**Resolver:** mantener documentos separados por cohorte. No reciclar 2.140 ni usar esos retornos para seleccionar el FVG actual; metodología/cognitiva primero.  
**Cierre:** reporte NO_GO económico responsable, sin PF falso.

### B15 P1 — Sin evidencia de Trader Lab L1–L10 ni independencia promocional
**Evidencia:** #936 constata L1 incompleto, no L2 ni L4 y L7 0 fills; #937 acelera reloj virtual pero no acredita candidato oficial.  
**Resolver:** después de M0–M6 de una versión congelada, construir paquete formal L1, L2 normal/fast, L3, fresh OOS L4, stress L5, MC L6, economía L7, Risk L8, CIBO L9 e independiente L10.  
**Cierre:** todas las evidencias al mismo candidate hash y autoridad verificable, nunca simple CI verde.

### B16 P1 — Custodia de artefactos y licencia
**Evidencia:** GitHub Actions artifacts históricos expiran (G5 y QA nuevos ~12 enero 2027); precios provider no deben incorporarse al Git público; data vault #837 pendiente.  
**Resolver:** guardar SHA, licencia/autorización y manifest de retención, respaldos duraderos sólo en vault permitido y prueba de restauración.  
**Cierre:** data reproducible antes de caducidad sin leakage.

### B17 P1 — Sesiones/salidas e interrupciones
**Evidencia:** Silver Bullet entrada 03–04/10–11/14–15 pero posición puede sobrevivir; 15:55 NY time-exit QORE. Pausas de mercado o cambio DST no pueden rellenarse con OHLC inventadas.  
**Resolver:** certificación temporal de condiciones de mercado cerrado, sesión, expiración order, DOL ya barrido, stale quote, time-exit y no falsa liquidación; adversarios lunes/feriados/short session.  
**Cierre:** cronología source y reglas M5 exactas y conservadoras.

### B18 P2 — Tasa de aprobación aparente distinta de conformidad real
**Evidencia:** 150/150 pytest #938, 119/128 geometría, 128/775 contexto; se podrían confundir con certificación autoral, densidad final, win rate o rentabilidad.  
**Resolver:** publicar por perfil counters CONTEXT / COG_DTO / ENTRY_SOURCE / ORDER_OFFER / BROKER_ACK / FILL / CLOSED_TRADE; gates con bandera independiente source/method/cognition/economic.  
**Cierre:** ningún artifact con “CERTIFIED” sin firma, fuente y transición correspondiente.

## 7. CHECKLIST DE EJECUCIÓN para el PRÓXIMO ARQUITECTO — orden y criterios de parada

**Prioridad P0-00: custodiar.** Partir de branch exacta #938 (888e048edeff7899fb086e526bd5b0af9c44140a) SOLO para investigación fuente M4 si aporta la cadena #933–#935. Leer #926 plan, #931 R1, #936 matriz y **este R2**. Confirmar G3 #896 SHA doc+code y todos los PR DRAFT. NO modificar G3.

**P0-01: fuente y contrato únicos por perfil.** Crear tabla rule_id/version/profile, ICT clip/page o TTrades URL, source fact/proxy, DTO/CausalEvidence, UNKNOWN/REJECTED, tests positivos/negativos. Auditar el fallo B02. Congelar una especificación de evaluación **metodológica**, no un resultado monetario. M0 debe ser falsable.

**P0-02: reconciliar DOL #930 vs #932 sobre historial real**. Hacer PR SOLO lectura que ejecute ambos desde las MISMAS M1 e instantes as-of, compare estados/reasons sin futuros, sin dinero. Guardar divergencias exactas y decidir por causalidad, no por número de señales. No mezclar ramas hasta aprobar la reconciliación. M2 ICT no aprobado si las contradicciones siguen.

**P0-03: seguir emisor perfil TTrades real #933 y divergencia #927**. Muestrear los 775 días ya fijados y todas las categorías de #934, especialmente 483 FIRST_RETURN_NO_QORE_MSS, 1 REJECTED_SOURCE, 6 incomplete, sin usar retornos. Verificar que cada DTO lleva pruebas fuente sweep→return→MSS→DOL y no un objeto sintético sustituido por COG auténtico. Si la variante no es fiel a fuente, dejar QORE_PROXY.

**P0-04: terminar M4 doctrinal**. Conservar PASS QORE_FVG_PREFIX_PARITY #938; construir PRs separados source DISPLACEMENT_DIRECT, OB_RETEST, BREAKER_RETEST con preregs sobre historia que ya es development. Primero citar definición primaria o declarar ambigüedad, luego tests adversariales y una única política causal de prioridad. No convertir tres setups coexistentes en tres trades. Si la fuente autoral no permite validar una familia, marcar FAIL/UNKNOWN de esa familia, **no** introducir proxy como fuente original.

**P0-05: M5 stop/exit por perfil sin OMS**. Especificar TTrades swing vs QORE C2; crear testigos de geometría, invalidación, expiry y 15:55, casos M1 ambigüos. Usar FVG evidenciado desde C3; CE touch marcado NOT_FILL. Homologar contrato real y orden/ACK solo para futura fase económica. Ningún sizing dentro VT31.

**P0-06: M6 gobernanza**. Registrar solicitud del Owner de revisión urgente con única cuenta; preparar procedimiento permitido que no simule dos cuentas independientes. No asumir firma dual de comentarios o tests. Emitir dictamen PENDING si no se puede cumplir sin nueva gobernanza.

**P1-07: paquete de CERTIFICACIÓN M0–M6**. Evidence manifest con perfil, fuentes, SHA del COG/OPS/tests, sello de tiempo as-of, número de ejemplos reales vs sintéticos, conteos REJECTED/UNKNOWN/CONFIRMED, adversarios y revisiones independientes; un gate por acta. No permitir aumento automático a L1/L7.

**P2-08: trader integral** (posterior y separado del mandato inmediato). Resolver los gates L1–L10 según #936, datos/ACK/quotes hasta salidas, OOS realmente intacto, estrés/Monte Carlo/economía con criterios preregistrados y autoridad Risk/CIBO/Independiente, sin tamaño propio ni live. Solo cuando pruebas sean suficientes considerar autorización DEMO por protocolo distinto. Nunca promover por presión de tiempo.

**Criterios STOP obligatorios:** cambio no prerregistrado basado en PnL; datos futuros en prefijo; entrada sin fuente y as-of; OB/Breaker “original” sin regla de fuente; retorno same M1 marcado con precedencia inventada; dos firmas falsas; divergencia entre testigos DOL no resuelta; source de quotes incorrecto; alta de LIVE/merge/sizing sin Owner.

## 8. CÓMO REPRODUCIR EL ÚLTIMO PASS (sin desplegar nada)

Repositorio: mezas3238-hue/qore-core, rama research de PR #938, commit de CI **ea50262dc1327a793168f35aaef8746d7a8cc897**. El archivo normativo para el ensayo y el resultado están en docs/research/VT31_M4_P1_REAL_M1_PREFIX_PARITY_PREREG_2026-10-14.md y docs/research/VT31_M4_P1_128_REAL_M1_FIRST_FVG_CAUSAL_PREFIX_VERDICT_2026-10-14.md.

1. Instalar proyecto y herramientas de test en entorno aislado: python -m pip install -e '.[dev]' 'ijson>=3.3,<4'.
2. Ejecutar tests: PYTHONPATH=src:. pytest -q -o addopts='' tests/infrastructure/test_vt31_m4_first_fvg_prefix_audit_20261014.py tests/infrastructure/test_vt31_m4_m5_ttrades_fvg_path_20261014.py ; CI completo usa también suite M0–M3 y COG/OPS, 150/150.
3. Descargar **sólo de GitHub Actions autorizado** artifact 11459859004 (gh api /repos/mezas3238-hue/qore-core/actions/artifacts/11459859004/zip) y extraer miembro NAS100/market-evidence.json; verificar primero sha256sum igual a 0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa.
4. Ejecución source-only: PYTHONPATH=src:. python scripts/vt31_m4_first_fvg_prefix_audit_20261014.py --market <path_to_authorized_verified_market-evidence.json> --out <out.json>.
5. Exigir en JSON: days_source=775, m2m3_candidate_days=128, total_closed_m1_prefixes_replayed=5155, m4_counts=119/8/1, m5_counts=61/31/27, causal_first_fvg_geometry_parity=true, fills_or_ack=0, method_certified=false, cognition_certified=false, trading_authorized=false. Ante divergencias: FAIL y documentar, no ajustar reglas.
6. Evidencia del run verde de reproducción: [CI #38639069852](https://github.com/mezas3238-hue/qore-core/actions/runs/38639069852) y [artifact #11929562855](https://github.com/mezas3238-hue/qore-core/actions/runs/38639069852/artifacts/11929562855), SHA256 ZIP 91e0b923b311fa77233dd123cd29551e84ceb31f2b1869b328507a0b894fb09a. Intento anterior #38638973823 falló Ruff sólo en tests; quedó registrado, no es un negativo del algoritmo.

Nota: las ejecuciones son reproducibles si la licencia, disponibilidad y retención de artifacts lo permiten; **no** inventar acceso a fuentes si el artifact caducó.

## 9. Dependencias/casos que el siguiente arquitecto NO debe confundir

- R1 #931 (documenta hasta #929) vs **R2 (incluye hasta #938)**.
- COG auténtico G3 (contrato COG/OPS) vs emisor TTrades research #933.
- ICT DOL testigo P3 #930 vs ICT_DOL_SOURCE_V1 #932; ambos potencialmente útiles, pero no se verificó una sustitución semánticamente idéntica.
- FVG QORE causal #938 vs cuatro familias originales TTrades (no todas certificadas).
- Sesión de oportunidad 10–11 y continuación abierta hasta 15:55; no limitar validación económica a horas 10–11.
- 150 tests verdes, 128 contextos y 119 FVG **NO SON** Sharpe, PF, WR o cantidades de trades.
- Datos históricos de Nasdaq con BID/ASK cTrader existen; no afirmar ausencia total. Tampoco afirmar 3Y BID/ASK ejecutable.
- Issue #897 dual approval **no se resuelve fingiendo firmas**; owner puede autorizar revisión metodológica ya, pero cambiar formalmente el mecanismo dual es una decisión aparte.
- PR #903 NO_GO económico aplica a falta de evidencia y parte de OLD; no convierte nueva V1 en “matemáticamente imposible”.
- Trader LAB sólo puede avanzar cuando las pruebas metodológicas sean correctas y *su propia* versión esté congelada. No merge ni LIVE implícitos.

## 10. ÍNDICE de recursos/custodia para continuidad directa

- [Muro de coordinación entre arquitectos #727](https://github.com/mezas3238-hue/qore-core/issues/727)
- [Prerregistro de certificación M0–M7 #926](https://github.com/mezas3238-hue/qore-core/pull/926)
- [Testigos V2 #928](https://github.com/mezas3238-hue/qore-core/pull/928)
- [TTrades AM perfil #929](https://github.com/mezas3238-hue/qore-core/pull/929)
- [ICT general DOL #930](https://github.com/mezas3238-hue/qore-core/pull/930) y [#932](https://github.com/mezas3238-hue/qore-core/pull/932)
- [COG TTrades nativo #933](https://github.com/mezas3238-hue/qore-core/pull/933)
- [Censo cognitivo 3Y #934](https://github.com/mezas3238-hue/qore-core/pull/934)
- [M4/M5 source-only #935](https://github.com/mezas3238-hue/qore-core/pull/935)
- [Gates oficiales L1–L10 #936](https://github.com/mezas3238-hue/qore-core/pull/936)
- [L3 preparatorio #937](https://github.com/mezas3238-hue/qore-core/pull/937)
- [Último M4-P1 prefix pass #938](https://github.com/mezas3238-hue/qore-core/pull/938)
- [G3 doc/code #896](https://github.com/mezas3238-hue/qore-core/pull/896) y [firmas #897](https://github.com/mezas3238-hue/qore-core/issues/897)
- [Fuente BID/ASK y contratos #901](https://github.com/mezas3238-hue/qore-core/pull/901), [#857](https://github.com/mezas3238-hue/qore-core/issues/857), [#900](https://github.com/mezas3238-hue/qore-core/issues/900), [custodia #837](https://github.com/mezas3238-hue/qore-core/issues/837)
- [NO GO económico de evidencia antigua #903](https://github.com/mezas3238-hue/qore-core/pull/903)

---

## 11. DECLARACIÓN DE CUSTODIA Y MISIÓN AL SUCESOR

**Último punto técnico concluido:** 5.155 prefijos M1 reales en 128 contextos, primer FVG y referencia C2 **sin mutación por futuro**, [CI #38639069852 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38639069852) en SHA ea50262dc1327a793168f35aaef8746d7a8cc897; informe head #938 888e048edeff7899fb086e526bd5b0af9c44140a. Este PASS mejora evidencia de causalidad de **FVG QORE**, no la certificación total.

**Instrucción exacta al próximo arquitecto:** proteger SHA, reconciliar los testigos DOL #930/#932 con NAS100 M1 real, cerrar identidad doctrinal M0 y el productor cognitivo TTrades #933, desarrollar testigos faltantes M4 y políticas M5 sin fills ficticios, resolver autoridad de M6 sin doble firma falsa, documentar resultado de M0–M6 por perfil, luego y sólo entonces presentar candidato congelable para Gates oficiales L1–L10. Evitar optimizar PnL, no confundir metodología certificada con edge, y no declarar VT31 certificado hasta pruebas y autoridad válidas.

**Estado final del handoff:** DOCUMENTED_FOR_CONTINUITY, **METHODOLOGY_PENDING + COGNITION_PENDING + TRADER_NOT_CERTIFIED + NO_LIVE**. Este documento no concede autorización de merge, producción, trader sizing, fundeo real, VPS, paper OMS, ni consumo del Fresh Holdout.


## 12. ACTUALIZACIÓN CONCURRENTE detectada al publicar R2 — PR #939, L1 research (sin promoción)

Durante la verificación del PR de este handoff se abrió [PR #939](https://github.com/mezas3238-hue/qore-core/pull/939), HEAD **666eb3d581ec3494dc7f6a5193c35c2fe04c46b8**, base **agent/vt31-l3-fastforward-source-parity-20261014** (#937), DRAFT. Esta rama paralela parte de la línea de canonical Trader Lab, **NO** de #938; su objetivo declarado es construir una vinculación de candidato de investigación mediante contratos oficiales QORE sobre **120 M1 reales** del primer día NY 09+10 completo, con huella digital de datos, código y configuración. Prereg commit **f5db95eac6cd275add0ed8dafc814932f742b4b5**. El PR **expresamente NO reclama** METHOD_FREEZE aprobado, RESEARCH_READY, L1/L2/L3 cualificados, Replay/fast-forward homologado, DEMO, fills, PnL ni edge. A fecha de esta adenda **no se verificó un run verde de #939**: no tomar su intención declarada por CI ejecutado.

**Encargo al sucesor:** documentar #939 como trabajo **L1 de infraestructura/identidad candidato POST_DISCOVERY_RESEARCH_DRAFT**, separado de la misión inmediata de fidelidad fuente M0–M6. Evitar prometer L1 METHOD_FREEZE por generar un CandidateBinding sin fuente OB/Breaker, firma G3, identidad doctrinal y evidencia autoral. Revisar el CI de #939 cuando exista y coordinarse en #727; si hay cambios posteriores al SHA auditado aquí, emitir nueva adenda con SHA y pruebas, no alterar retroactivamente los números del #938.

Esta actualización fue incorporada **antes del cierre de la custodia R2** para que el próximo arquitecto no pierda la nueva rama concurrente. Estado final sigue **METHODOLOGY_PENDING / COGNITION_PENDING / TRADER_NOT_CERTIFIED / NO_LIVE**.
