# VT31 — Veredicto de auditoría cognitiva REAL TTrades NY AM
**Corte:** 14-OCT-2026 · **PR #949 DRAFT** · Fuente de mandato [PR #947](https://github.com/mezas3238-hue/qore-core/pull/947): certificar **METODOLOGÍA y COGNITIVA**, NO por PF, Sharpe, DD, sizing ni número de trades.

## Evidencia técnica obtenida
- **[CI #38671454652 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38671454652)**, versión ejecutada `258931d95975183e9bad324bdd730b0142c233cf`, **78/78 regresiones PASS**. Testigos G3 congelados verificados, fuente primaria separada por perfil. [Artifact #11943943376](https://github.com/mezas3238-hue/qore-core/actions/runs/38671454652/artifacts/11943943376), ZIP SHA256 `e0a67fb9a250ea95eb28987b59741a2bd08ba58d7e851aaac37852c4e6ce89ab`.
- Prerregistro antes del código `973ce267c9cbe00281fca717ad5a62d9eddb250c`. Emisor de COG auténtico **TTrades research #933** y censo original #934 copiados desde SHAs/blobs congelados (sin modificar el G3 general). Fuentes #926 y V2 #928 refutan el DTO cuando corresponde.
- NAS100 CFD **1.059.784 M1** con checksum original `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, datos de **desarrollo YA estudiados, NO fresh OOS**. Del censo fuente #934: **775 días de clase**, preservados TODOS sin seleccionar PnL.
- **Autor primario:** [TTrades The AM Silver Bullet Strategy on NQ, 19-JUN-2025](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/). Exige H1 09–10 NY, primer raid en hora 10–11, esperar confirmación y apuntar extremo opuesto. Menciona displacement, FVG, order block y breaker block. **No** impone en esa publicación la parametrización QORE pivot3/cuerpo 1,25×mediana5 ni la simultaneidad MSS/primer retorno en una sola vela.

## Seis casos semánticos REALMENTE emitidos/abstenidos por el COG
**Regla de elección preregistrada:** primer día cronológico de cada categoría original, NO día con resultado económico favorable. Fuente M1 y as-of exactos en artifact.

| Caso, fecha NY / UTC as-of | Qué exigía la metodología | Decisión auténtica del COG, explicación | Dictamen metodológico en alcance |
| --- | --- | --- | --- |
| **No sweep**, 31-OCT-2023 / 15:00 UTC | Sin tomar H/L 09 H1, **no trade** | `UNKNOWN` superior / `AWAIT_SWEEP` interno, sin DTO | **ABSTENCIÓN CORRECTA**, fuente no cumplida |
| **Sweep sin regreso**, 05-OCT-2023 / 15:00 UTC | Sweep solo no autoriza señal | `UNKNOWN` / `AWAIT_RETURN`, sin DTO | **ABSTENCIÓN CORRECTA** |
| **Primer regreso sin MSS proxy**, 02-OCT-2023 / 14:02 UTC | La fuente exige confirmación; MSS numérico es proxy QORE | `UNKNOWN: QORE_MSS_PROXY_NOT_CONFIRMED_ON_FIRST_RETURN`, sin DTO | **ABSTENCIÓN CONSERVADORA**; NO prueba que método TTrades original rechace setups que confirmen después |
| **Barrido, regreso y MSS proxy**, 03-OCT-2023 / 14:12 UTC | Primer barrido, sesgo en sentido opuesto, target extremo H1 09 opuesto | `CONTEXT_ATTESTED_NOT_CERTIFIED`, DTO real y #926 `CONTEXT_CONFORMANT_ONLY` / V2 `CONFIRMED` | **M2 RAÍZ H1/BIAS/DOL CORROBORADO**, NO M3 autoral ni entrada |
| **Contradicción de raid**, 05-JUN-2024 / 14:03 UTC | No reetiquetar primer sweep en lado opuesto según avance favorable | `REJECTED: OPPOSITE_H1_RAID_AFTER_FIRST_SWEEP`, sin DTO | **RECHAZO CAUSAL** del contexto contradictorio |
| **Fuente H1 incompleta**, 12-OCT-2023 / as-of ausente | Sin M1 suficientes no afirmar estructura H1 | `NOT_RUN_WITH_INCOMPLETE_REFERENCE` en este auditor; **NO equivale a prueba de rechazo del runtime** | **DESCONOCIDO FUENTE**, ningún certificado |

La tabla no fabrica decisiones en los casos incompletos. En los cinco casos completos se volvió a llamar al COG #933 **sólo con el prefijo M1 disponible as-of**. Para contexto positivo se contrastaron testigos #926 y V2 #928 con el mismo H1 y M1 posterior: no hubo desacuerdos del evento primer raid/sesgo/DOL en el corpus de decisiones propuestas. Fuente #929 es parte de la implementación #933, por lo que **no afirmar independencia total entre todos los testigos**.

## Censo de CASOS para garantizar que no se escogieron únicamente positivos
| Clase de observación | Casos diarios, NO trades | Sentido cognitivo real |
| --- | ---: | --- |
| H1 raid+return+MSS QORE contextual | 128 | DTO auténtico de contexto, H1 DOL respaldado por testigos |
| Primer regreso sin MSS proxy en la misma M1 | 483 | COG abstiene (`UNKNOWN`), posible sobre-restricción QORE frente al autor |
| Sweep sin regreso | 92 | COG espera (`UNKNOWN/AWAIT_RETURN`) |
| Sin sweep | 65 | COG espera (`UNKNOWN/AWAIT_SWEEP`) |
| H1/10 M1 incompletas | 6 | No evaluadas por este auditor; fuente insuficiente |
| Contradicción de primer barrido | 1 | COG rechaza explícitamente |
| **TOTAL** | **775** | 0 órdenes, 0 fills, 0 PF/DD |

**No usar estos recuentos como nota cuantitativa para aprobar M0–M6.** Sólo confirman integridad de cobertura del expediente y preservan negativos. En 128 decisiones reales, testigo #926 `CONTEXT_CONFORMANT_ONLY`, #928 V2 `CONFIRMED`; **0 contradicciones de esa parte H1**. El resultado es parcial, no equivalencia de toda la estrategia.

## Problemas cognitivos concretos pendientes, NO son métricas de performance
1. **M0, identidad runtime:** #933 es emisor autónomo de investigación TTrades AM. No existe aún evidencia de un **selector de perfil único y plenamente enlazado** a todas las capas VT31 COG→OPS; el G3 general no es TTrades. No sumar conclusiones de ambos como si fueran mismo productor.
2. **M1, semántica de WAIT:** la interfaz superior del COG #933 retorna `UNKNOWN` en casos donde su `native_state` específico es `AWAIT_SWEEP` o `AWAIT_RETURN`. Es funcionalmente prudente por **no emitir DTO**, pero su API **no expresa WAIT explícito**. Propuesta futura: contrato versionado `WAIT_FOR_RAID`, `WAIT_FOR_RETURN`, `UNKNOWN_SOURCE`, `REJECTED_CAUSAL` con transición comprobable, sin cambiar G3 congelado. No declarar defecto de método por vocabulario sin contrato de interfaces aprobado.
3. **M3, principal falta de fidelidad:** `_mss_proxy` de #933 exige último M1 con cierre a través de pivote3 y cuerpo ≥1,25×mediana5 **en la primera vela de regreso**. Es ingeniería de QORE, no requisito establecido por artículo autoral. Los 483 contextos de retorno sin este proxy son **abstenciones prudentes del código actual**, pero NO evidencia que TTrades prohibiría todas esas entradas. **Prioridad P0:** especificar con fuente auténtica el estado de confirmación tras regreso y desplazamiento **posterior**, sin fabricar regla/timestamp y antes de cambiar lógica.
4. **M4, setup:** prueba positiva source H1 no decide si displacement directo, FVG, OB o breaker fue el mecanismo correcto; prioridad entre alternativas y caso negativo/ambigüedad faltan. **NOT CERTIFIED**.
5. **M5, invalidación:** el artículo pide stop más allá del swing causante; G3 propone C2 full wick+tick. No asumir equivalencia; faltan tesis de cancelación, expiración y reentrada de cada familia. No hace falta fill/PnL para examinar **intención cognitiva**, pero sí hechos causales para determinar el swing.
6. **M6, frontera:** firmantes independientes reales COG/OPS todavía pendientes en [#897](https://github.com/mezas3238-hue/qore-core/issues/897). No replicar firma por una cuenta.

## Decisión de esta ronda
- **M2/TTrades H1 raid → bias → opposite DOL: EVIDENCIA DE CONFORMIDAD EN ALCANCE para los DTOs TTrades #933 realmente emitidos**; NO certificación autoral global y NO autorización de entrada.
- **Capacidad cognitiva de abstenerse y rechazar: DEMOSTRADA EN CASOS FUENTE**. El mapeo de estado superior WAIT sigue por versionar.
- **M3 displacement/MSS autoral: PENDIENTE**, porque el proxy QORE no suple definición fuente.
- **M4/M5/M6: PENDIENTES**. `VT31_METHOD_COG_CERTIFICATION_PENDING`; expediente económico Trader Lab L1–L10 separado. **No merge ni LIVE, no sizing VT31**.

## Continuación ordenada
Próximo lane P0 M3: comparar **desplazamiento de la fuente** y cronología post-return en casos positivos y `FIRST_RETURN_NO_QORE_MSS` con testigo cualitativo; demostrar explícitamente `WAIT_FOR_CONFIRMATION` sin descartar irreversiblemente en la misma vela a menos que la fuente lo imponga. Versionar cualquier cambio únicamente como candidato nuevo distinto, prereg antes de mirar PnL. Luego M4 cuatro entry families e invalidación M5, M6 firmas reales.
