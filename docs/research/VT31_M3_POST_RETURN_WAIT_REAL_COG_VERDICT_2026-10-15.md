# VT31 M3 — COG real no conserva WAIT tras retorno · veredicto causal en M1
**Corte de evidencia 15-OCT-2026; metodología y cognitiva, NO economía.** PR #952 DRAFT de investigación child #949, NO MERGE. M3 **PENDIENTE DE CERTIFICACIÓN AUTORAL**.

## Hallazgo confirmado reproducible
**[CI SUCCESS #38707327204](https://github.com/mezas3238-hue/qore-core/actions/runs/38707327204)**, commit ejecutado `210872a5c0ea8dec336cde8e0673a64d3f1ad934`. **79/79 pytest PASS**, Ruff PASS, hashes G3/OPS/testigos originales verificados. Evidence [artifact #11959160949](https://github.com/mezas3238-hue/qore-core/actions/runs/38707327204/artifacts/11959160949), ZIP SHA256 `2dcf24261146167a9dd79282fd5f75979f1b2934bb8c1550c8eb49c6fbda7067`; contiene JSON completo de decisiones con tiempos y sumas de integridad. Prerregistro **anterior al código** `eeb0aefff638e39805c6dff1e39128e76dbdcdb5`.

Datos reales NAS100 M1 **1.059.784** SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, desarrollo visto del #934, **NO fresh OOS**. No se volvió a elegir metodología por resultados monetarios, ni se calcularon PF/DD/Sharpe/expectancy, ni se construyeron DTOs sintéticos dentro de la auditoría real.

### Qué se le preguntó al COG
En los **483 casos** del censo #934 con primer regreso al interior del H1 09 NY pero sin MSS *QORE* en la M1 exacta del regreso, el emisor real #933 respondía `UNKNOWN:QORE_MSS_PROXY_NOT_CONFIRMED_ON_FIRST_RETURN`. En cada **M1 POSTERIOR** antes de las 11:00 NY se volvieron a invocar el testigo autoral de contexto #929 y el **emisor REAL** #933, junto con su función congelada `_mss_proxy`, exclusivamente sobre barras cerradas disponibles as-of. Fuentes y código pinneados a hashes, sin cambiar el emisor, el stop ni las entradas.

| Estado terminal del testigo read-only | Casos contextuales | Afirmación exacta |
| --- | ---: | --- |
| **LATE_QORE_PROXY_ONLY_NOT_AUTHOR_CERTIFIED** | **449** | Posteriormente apareció una ruptura MSS del **proxy de QORE** cuando el contexto source H1 primer raid/return seguía válido; el COG original respondió `UNKNOWN:RETURN_M1_NOT_FRESH_AT_ASOF` y no produjo nueva intención |
| **EXPIRED_WITHOUT_LATE_PROXY** | **34** | Llegaron las 11:00 NY sin ruptura válida posterior del proxy según el observador |
| **TOTAL** | **483** | Son días/casos de COG, NO entradas ni operaciones, no rendimiento, no certificado TTrades |

No se observaron en este ensayo estados terminales `SOURCE_REJECTED`, `SOURCE_AMBIGUOUS`, objetivo tocado, ni candidato con target y proxy en una misma M1 ANTES del primer proxy encontrado; ese es **solo un resultado del conjunto auditado y orden causal**, NO la prueba de que esos eventos no ocurren en el mercado. Los adversariales sintéticos cubren rechazo del barrido opuesto, ambigüedad high/low same-M1, fuente incompleta y caducidad.

## Ejemplos REALES y trazabilidad por as-of
- **02-OCT-2023, short (NY):** primer raid `14:01 UTC`, regreso `14:02 UTC`; `_mss_proxy` QORE no confirma en la vela del retorno, pero una M1 posterior cierra con confirmación: `14:11 UTC` (pivote preconfirmado `14:09 UTC`). **El emisor congelado sigue en UNKNOWN; no hay DTO/orden.** Son timestamps, no precios ni performance.
- **13-NOV-2023, short (NY):** primer raid `15:47 UTC`, regreso `15:49 UTC`; COG WAIT implícito / `UNKNOWN`; no se observa confirmación proxy admisible antes de `16:00 UTC` = fin 11:00 NY. Correcto **no inventar intención**.

Estos ejemplos fueron elegidos por **primera fecha lexicográfica por estado** fijada en el preregistro, no por rentabilidad. El JSON incluye todos los casos.

## Dictamen semántico / doctrinal
- **M0/M2 contexto TTrades NY AM:** primer raid, sesgo opuesto y DOL H1 de 09:00 ya corroborados en #949. La continuidad del primer raid y regreso se mantuvo en 449 casos hasta la aparición posterior de un MSS **QORE proxy**, sin fuente cambiada.
- **M3 LIMITACIÓN COG CONCRETA:** la API actual de investigación #933 exige retorno y `_mss_proxy` en **la misma M1** para emitir `CONTEXT_ATTESTED_NOT_CERTIFIED`; después del retorno responde `UNKNOWN:RETURN_M1_NOT_FRESH_AT_ASOF` aunque se verifique un proxy posterior. El COG actual **no dispone de un estado explícito `WAIT_FOR_CONFIRMATION` persistente**. Se documenta necesidad de retener contexto y observar confirmaciones posteriores causales.
- **Límite doctrinal importante:** la [fuente primaria TTrades AM](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/) exige confirmación tras barrido (desplazamiento, FVG, OB, breaker), **no consagra umbral de cuerpo QORE 1,25×mediana5 ni pivote3 en M1**. Por eso los **449 NO son trade setups certificados del autor** y los 34 NO prueban ausencia de entradas válidas con FVG/OB/Breaker/displacement cualitativo. No perseguir convertir 449 en señales sin fuente.
- **M4 aún no certificado:** formalización autoral de displacement/FVG/OB/breaker, prioridad, retesteos y caducidad. **M5** invalidación swing causante del movimiento vs stop C2 de QORE pendientes. **M6** firmas independientes en [#897](https://github.com/mezas3238-hue/qore-core/issues/897) pendientes.
- **Economía y Trader Lab L1–L10:** expediente integral separado. Sin orden/ACK/fills, ningún PF/DD/Sharpe ni lotaje del trader.

## Acción concreta siguiente P0 — diseño de estado cognitivo, NO estrategia económica
1. Nuevo **candidato de COG TTrades de investigación V2**, archivo separado, sin editar el emisor #933 ni G3: estados `AWAIT_SWEEP`, `AWAIT_RETURN`, `WAIT_FOR_CONFIRMATION`, `CONTEXT_READY_PENDING_ENTRY_FAMILY`, `SOURCE_REJECTED`, `UNKNOWN_INTRABAR`, `EXPIRED`; reloj de sesión y primer raid sellados. La evolución de estado debe ser determinista bajo streaming 1× y xN usando siempre closed M1, sin first-return one-minute expiration no respaldada por el artículo.
2. En V2, el evento `_mss_proxy` sigue **testigo diagnóstico opcional QORE**, NO prueba suficiente para `CONTEXT_READY` autoral. Para lograr `READY` exigir al menos una familia M4 con evidencia de fuente, aún pendiente. Hasta entonces no emitir `CognitiveDecision` con autoridad de entrada.
3. Testigos negativos: nuevo barrido opuesto invalida o vuelve desconocido según observabilidad; dos extremos en M1 UNKNOWN; target DOL tocado antes del evento bloquea; no recomponer orden intrabar OHLC; no volver al barrido segundo por conveniencia.
4. Evaluar casos manuales positivos/negativos contra material primario (incluidas cuatro familias) y testigo independiente, registrar `AUTHOR_AMBIGUITY` donde TTrades no prescribe algoritmo determinista.
5. Contrato COG→OPS versión/hashes y sign-off real M6; **ninguna modificación a G3 congelado, merge, LIVE, VPS, FundedNext ni sizing propio.**

**ESTADO:** avance cognitivo REAL M3 demostrado como limitación estructural del diseño actual; `VT31_METHOD_COG_CERTIFICATION_PENDING`; no certificado global.
