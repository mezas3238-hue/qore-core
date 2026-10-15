# VT31 M3 · PRE-REGISTRO COG COGNITIVA V2 WAIT TTrades (SIN EMITIR TRADE)
**15-OCT-2026 ANTES DE NUEVO CÓDIGO.** Misión actual Owner: certificar por METODOLOGÍA + COGNITIVA, no por performance, PF, sizing, nº de trades. PR #952 demostró LIMITACIÓN actual #933: 449/483 primeras vueltas sin MSS QORE en la primera M1 tienen MSS proxy tardío, pero el COG original ignora confirmación tardía. Es evidencia diagnóstica de metodología, NO 449 entradas autorales.

## Doctrina y límites
TTrades [AM Silver Bullet 2025](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/): H1 09–10 completo; primer raid en NY 10–11; high raid ⇒ SHORT hacia low H1 09, low raid ⇒ LONG hacia high H1 09; barrido sin confirmación no es entrada; displacement/FVG/OB/Breaker posibles. Fuente NO prescribe pivote3/1,25×mediana5 y NO obliga coincidencia regreso+MSS en una sola M1.

Nuevo componente `TTradesAmWaitCognitionV2` estrictamente **READ-ONLY** separado, NO reemplaza G3 congelado o el emisor TTrades #933. Tiene estados semánticos explícitos sin construir `CognitiveDecision`:
- `UNKNOWN_INCOMPLETE_H1` cuando no hay 60 M1 cerradas 09h;
- `WAIT_FOR_SWEEP` antes de raid;
- `WAIT_FOR_RETURN` tras primer raid;
- `WAIT_FOR_CONFIRMATION` tras primer regreso cuando faltan requisitos semánticos;
- `QORE_PROXY_OBSERVED_AUTHOR_DISPLACEMENT_UNVERIFIED` si QORE `_mss_proxy` se confirma ahora o posteriormente, **SIN EMITIR INTENCIÓN**;
- `INVALIDATED_OPPOSITE_RAID` o `UNKNOWN_INTRABAR_OR_SOURCE` si fuente contradice o no permite causalidad;
- `EXPIRED` al fin del horario 11 NY si no existe evento pendiente; no atestiguar la entrada.

## Algoritmo y criterios falsables
1. Consumir exclusivamente M1 CERRADAS, input `observe_closed_m1` 09–11 NY con as-of y DST; exigir orden estricto y coherencia `opened_at/closed_at`, no rellenar M1. Cada día ejecuta instancia fresca y fuente H1 09 de M1 originales NAS100.
2. En cada cierre 10h llamar a la **función testigo externa original** `native_ttrades_am_context` PR #929, blob `3cf076810b1e6dcec0ba2f1571609577ceac6d50`, usando SOLO los prefijos 09+10 disponibles. Primer barrido/retorno/target son del testigo independiente, NO de `CognitiveDecision`.
3. Antes del primer regreso, NO observar `_mss_proxy` como legitimación de intención. Tras primer regreso, se puede examinar el **proxy propio QORE** de #933 exclusivamente como diagnóstico. No se declara SOURCE-AUTHOR CONFIRMED ni se genera DTO, orden, riesgo, stop, fill, PF o score.
4. Mantener identidad causal de primer raid y primer regreso: sellar side, `first_sweep_at`, `return_inside_at`, objetivo H1 opuesto, sin reorientar por second raid. Si el testigo fuente pasa a REJECTED/UNKNOWN, prioridad de invalidación/abstención por sobre cualquier proxy.
5. Observar temporalidad del proxy: registrar `proxy_first_confirmed_at` en una M1 cerrada y mantener estado identificado (no parpadear en M1 siguientes); si existe target touch intrabar que permite interpretaciones alternativas, **no promover**. No se asume que el autor apruebe ese proxy.
6. `snapshot(as_of)` y `observe_closed_m1` producen estados auditables idénticos al ejecutarse streaming normal, sin recrear m1 ni mirar M1 futuras. Una repetición `snapshot` no muta estado. Eventos fuera de ventana y fuente gapped deben quedar UNKNOWN/EXPIRED, no borrar fuente.
7. **Test adversarial**: primeros dos lados en una M1 UNKNOWN, opuesto posterior INVALIDATED, H1 incompleta UNKNOWN, no sweep WAIT, tras raid WAIT, post-regreso WAIT, proxy tardío V2 lo RECONOCE pero #933 lo ignora, retorno + proxy temprano etiquetado QORE, caducidad 11, invierno/verano NY, futuro M1/duplicado ERROR, estado terminal no revivable. Son casos **sintéticos de ingeniería**, no prueba autoral.
8. **Datos reales**: corpus exacto #934 con 775 días y sha fuente NAS100 #11459859004 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, 1.059.784 velas M1 ya vistas, **NO OOS**. Para los **483 días FIRST_RETURN_NO_QORE_MSS** (sin outcomes), verificar caso por caso que V2 se mantiene en WAIT explícito tras primer regreso y encuentra los mismos **449 contextos de proxy tardío** del testigo #952, manteniendo 34 expiraciones. El mismo universo y algoritmo congelados, no usarlo para ajustar método.
9. CI GitHub sobre repositorio, G3/Cog/OPS SHA congelados, fuente #929 y #933 pin, Ruff+pytest, artifact JSON evidencia e identidad, PR DRAFT separado.

## Gate de aceptación de esta ronda
CI PASS significa **estado cognitivo WAIT V2 implementado en investigación**, sin certificar M3 original: faltan fuente de displacement cualitativa TTrades, prioridad de FVG/OB/Breaker M4, invalidación swing y cancelaciones M5, 2 firmas reales M6. El V2 sólo intenta resolver la capacidad de ESPERA, no la entrada. Prohibido MERGE/LIVE/DEMO/FundedNext/VPS/sizing VT31; Traders sin lotaje propio, CIBO CMA es autoridad de volumen.
