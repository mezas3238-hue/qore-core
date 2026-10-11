# SCALPER — Issue #772 P0: Gate A/B fuente-as-of EJECUTADO; Gate C sigue abierto

**Fecha 2026-10-11. Dictamen:** `SOURCE_TIMESTAMP_PASS_NOT_AUTHOR_CERTIFIED`, `H1_INHERITED_STATE_HIGH_PREVALENCE`, `FIRST_ONLINE_NOT_YET_INDEPENDENTLY_RECONSTRUCTED`, **NO LIVE / NO VPS / NO MERGE / NO CERTIFIED**.

## Evidencia exacta y reproductibilidad

- Prerregistro previo al análisis: commit **`e467f31f7d291838447bb3145cb27adaebc3db1f`**, [protocolo P0](QORE_SCALPER_P0_H1_M15_M1_DIRECTION_CAUSAL_FORENSIC_PREREG_2026-10-11.md).
- Fuente original V49: run **38053946695**, SHA **`e356e7a52541e99533b25ecfef0ab9c4e9ce03c0`**.
- M1 proveedor nativo: run **35548099334**, SHA **`18c338aedd5013ce65a6cb6408ffbc2e904a6217`**.
- GitHub Actions Gate A/B **[38112995741, 11/11 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38112995741)**, código SHA **`962c24cf94b34e06e64c6bcb208686885bc6dd93`**.
- [Artefacto consolidado con las 20 trazas, 2020 filas y censo](https://github.com/mezas3238-hue/qore-core/actions/runs/38112995741/artifacts/11692516499), además nueve artefactos por mercado con los 2876 testimonios fuente.
- [PR Draft de investigación #773](https://github.com/mezas3238-hue/qore-core/pull/773), [Issue #772](https://github.com/mezas3238-hue/qore-core/issues/772).
- No cargó `realized_R`, operaciones ganadoras/perdedoras, costes ni payoffs 1:1. No modificó V49, DCVC ni producción.

## Gate A — 20 trazas SHA256 outcome-blind

Resultado: **20/20 identidades A seleccionadas de forma determinística**, 5 por grupo familia-de-trigger × H1 inherited/fresh donde hay muestras, resto por menor SHA256 global, usando literalmente el prefijo de hash del protocolo original. Cada caso expone mercado/sesión/día, H1 original estado/basis, origen recuperado desde eventos originales, última ventana H1 completa de proveedor, última ventana M15 original y últimos M1 cerrados, precio, stop y target fuente, timestamp, demora M15→M1, errores de geometría/price, y hash nativo. El origen POI/C2/C3 **procede del mismo observador histórico V48 para conciliación**, NO se presenta como evidencia de un detector independiente. El pivot-right M15 y la secuencia independiente sweep/CISD siguen **UNRESOLVED**.

La publicación pública de las 20 trazas/manifest y el resumen íntegro de 2020 se realiza dentro de esta rama de investigación; los artefactos de GitHub Actions también contienen las versiones inmutables que produjeron el censo.

## Gate B — censo 2876 y A 2020, sin resultados económicos

| Control source-as-of | Total fuente 2876 | A 2020 |
|---|---:|---:|
| Estado H1 fresco | 1.272 | 755 |
| Estado H1 inherited | 1.604 | **1.265** |
| H1 evento original recuperado por observador V48 (mismo algoritmo) | 2.876 | **2.020** |
| Validación estricta de campos almacenados: H1-from <= M15 setup <= entrada, cierre M1/precio y geometría | 2.876 | **2.020** |
| Comparación H1 pendiente 4-cierres (referencia NO autoral): MATCH | 1.468 | 1.017 |
| Comparación H1 pendiente 4-cierres: OPPOSE | 1.403 | 999 |
| Comparación H1 pendiente 4-cierres: FLAT | 5 | 4 |

Cálculo de pendiente H1 **independiente del detector de sesgo V49**: se forma cada barra H1 exclusivamente si el proveedor suministra **60 M1 continuas completas**, y se compara el cambio entre cierre actual y cuatro cierres previos. No se admiten velas H1 sintéticas ni parciales. La concordancia ~50/50 es un **benchmark descriptivo de tendencia**, NO una regla TTrades ni evidencia de que la dirección fuente esté invertida: una metodología de reversión puede oponerse justificadamente al precio reciente.

**Edad real recuperada de evento H1 para las 2020 A:** mínimo **50 minutos**, mediana **234**, P95 **710**, máximo **4.061** (67 h 41 min). En 1.265/2.020 casos inherited (62,62%), `h1_state_from` se resetea al comienzo de sesión en `build_h1_context_states`; por eso NO refleja la edad del evento. El evento original real se recupera hacia atrás del observador V48, con el riesgo metodológico de que es side-comparison, no motor first-online independiente.

**Retardo desde confirmación M15 registrada hasta confirmación M1 de entrada:** mínimo **5 minutos**, mediana **17**, P95 **50**, máximo **237**. Estas demoras **NO** demuestran entrada tardía económica ni infracción autoral; miden retraso causal de la cadena original, con necesaria futura validación de exactitud del timestamp de confirmación M15.

No se detectaron fallos de las invariantes fuente/timestamp/entry price disponibles: **0 de 2.876**. ***No interpretar 0/2876 como 0 causal bugs***, porque faltan testigos independientes de: vela derecha del swing, primera aparición as-of del POI/C2/C3, secuencia M1 CISD y reconciliación del detector limpio. Si una sola de esas precondiciones muestra futuro, registrar fallo grave sin requerir umbral del 70%.

## Gate C — NO APROBADO: reconstrucción first-online independiente

**No ejecutado como un motor íntegro nuevo.** El hallazgo A/B NO autoriza dar por testado first-online con reutilización de `_build_h1_bias_events`, `build_h1_context_states`, `_all_m15_setups`, `observe_first_structural_cisd` ni `observe_first_m1_cisd`. Estos permanecen referentes V49 de lado comparado, nunca oráculos en Gate C.

**Hitos mínimos restantes** (antes de atribuir causa económica):
1. Reconstruir Candle2/Candle3 H1 y POIs desde prefijos M1 independientemente, con regla autoral exacta/ambigüedades anotadas; impedir `_aggregate` de H1 incompleta (45/60 M1) sin tratamiento causal justificado.
2. Confirmar pivot M15 solo al cierre de su vela derecha; reconstruir serie contraria y cruce CISD; emitir versiones `available_at`.
3. Ejecutar M1 sweep, FVG retrace y CISD en orden causal **sin** V49Opportunity como generador de eventos del nuevo motor; comparar exhaustivamente `EXACT_MATCH`, signo, `TIME_DRIFT`, trigger family, swing, `MISSING/NEW`, con 2876 source y cualquier first-online adicional.
4. Adjudicar si sesgo H1 inherited con edad de hasta 67.7 h tiene límite/regla autoral; no introducir TTL empírico por el resultado 1:1.
5. Validación por invariancia de prefijo y test mínimo que falsaría cualquier uso de velas futuras. Sin eso **NO_CERTIFIED**, no abrir H2/edge económico.

Los resultados 1:1 del Issue #770 sobre el histórico consultado quedan separados; **ninguna cifra de PF/DD se recalcula** en el Gate #772. M30→M3 autoral de [Issue #768](https://github.com/mezas3238-hue/qore-core/issues/768) permanece independiente. Si hay ambigüedad autoral DeepSeek puede servir de crítico externo con citas, nunca reemplaza la fuente primaria.
