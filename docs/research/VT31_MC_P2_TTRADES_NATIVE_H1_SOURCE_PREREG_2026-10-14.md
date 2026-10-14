# VT31 MC-P2 · Prerregistro ANTES del nuevo adaptador de contexto nativo NY AM

Fecha 2026-10-14. Continuación estricta de [PR #928 COG_EVIDENCE_V2](https://github.com/mezas3238-hue/qore-core/pull/928) (80 pruebas SUCCESS), complementa #926/#927; rama de investigación apilada, independiente de G3 #896. El propietario ordenó avanzar por **certificación metodológica y cognitiva, NO profit/lote**.

## Contrato de fuente y atribución

La fuente primaria [TTrades, The AM Silver Bullet Strategy on NQ (19 junio 2025)](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/) determina únicamente perfil NY AM 10–11 Nueva York: H1 09–10 completo; **raid** de un extremo después de 10; tras high-raid enfoque SHORT hacia low H1, tras low-raid LONG hacia high H1; confirmar regreso/desplazamiento, entrada por familia FVG/OB/Breaker/desplazamiento y stop más allá del swing que causó desplazamiento. **La fuente no define un único algoritmo universal para reconocer todas las familias ni un multiplicador de cuerpo 1,25.** El número QORE 1,25 es modelo propietario, **no** prueba de fidelidad autoral. El ICT original general 03–04/10–11/14–15 no recibe este veto H1 09 automáticamente.

## Implementación P2 única — generador de TESTIGOS, no generador de órdenes ni de decisiones COG

Entradas: fecha/hora `as_of` externa, **exactamente** 60 velas M1 previas 09–10 y prefijo M1 contiguo 10–11, todo en `America/New_York` y sólo closed_at ≤ as_of. Salidas son `TTradesAmNativeSourceEvidence` inmutable, serializable y sellada con reloj, high/low previo, primer raid side/timestamp, objetivo opuesto, candidato de dirección, primera M1 de cierre direccional estrictamente dentro del H1 tras raid (etiqueta **regreso contextual**, no certificación de displacement fuerte/MSS) y causas `AWAIT_SWEEP/AWAIT_RETURN/RETURN_INSIDE_OBSERVED/UNKNOWN/REJECTED`.

Prohibiciones de sobreinferencia:
- Barrido en una misma M1 de AMBOS extremos → `UNKNOWN_BOTH_SIDES_IN_ONE_M1`, ningún orden posible.
- Posterior raid contrario (antes de confirmación) → `REJECTED_OPPOSITE_RAID` o UNKNOWN según causalidad, nunca elegir lado por retorno.
- Mismo bar de sweep y return: no inferir precedencia intrabar, exigir **M1 cerrada posterior** para atestar regreso.
- M1 faltante, H1 incompleto, OHLC incoherentes, bar futuro, as_of no equivale al último cierre, wrong profile/session → `UNKNOWN` o `REJECTED` con razón explícita; **sin interpolación**.
- El primer sweep se conserva; nunca elegir el segundo que paga.
- Antes de 10AM o después de la ventana: `REJECTED`; el cierre 11:00 del 10:59 puede aportar solo evidencia contextual final, jamás oferta de orden en 11:00.
- Output `method_certified=false`, `cognition_certified=false`, `execution_authorized=false`; no COG DTO fabricado. Bajo cualquier estado, entrada M4 y stop M5 pendientes. No inferir edge.

## Comparación contra COG autenticado sin alterar su código

Función adicional de emparejamiento `match_native_context_to_cog`: consume `CognitiveDecision` real y serie M1 para llamar al atestador independiente `COG_EVIDENCE_V2` del PR #928. Si contexto nativo observado pero no hay decisión, `COG_NOT_PRESENT`; si DTO contradice side/target o tiempo de raid, rechazo; si coincidencia y atestación V2 M0–M3 `CONFIRMED`, solo `CONTEXT_ATTESTED_NOT_CERTIFIED`. No se integra al runtime de VT31 ni modifica G3.

## Matriz P2 frozen antes de pruebas

1. LOW raid→LONG→high target, HIGH raid→SHORT→low target; escenarios idénticos verano EDT e invierno EST.
2. 59 barras previas, gap H1, gap después 10, futuro, as_of backdate, wrong day/session.
3. Zero raid, both raid same M1, later opposite raid, sweep sin retorno, retorno en propia vela sweep que **NO cuenta**.
4. Primer raid inmutable frente a segundo barrido del mismo lado, no mirar futuro; separación de contextos Londres/PM ICT.
5. Emparejar DTO TTrades favorable de las pruebas #928 (atestación M0–M3) y DTO falseado de DOL, side, anchor; comprobar método/COG/live siempre FALSE.
6. No reusar histórico 2140 legacy como V1 y no usar profits para elegir casos.

## Gates y límites

P2 sólo intenta **M2 H1 source evidence** + inicio M3 return contextual; **NO certificación del trader ni revisión de autoría completa**. G3 par DOC `a446afa17ed6e411b8f0b6fc182b103a78959a97` + CODE `78d4cdac0e09d1a6eef37b99c505ffc5098031fc` debe quedar blob-exact, sin firmas reales #897. Prohibido MERGE/main, VPS/LIVE, nuevas órdenes, QDLE, lotaje propio, broker fills, PnL, Fresh Holdout.

**Criterio de prueba:** CI run concreto con Ruff, tests adversariales nuevos, regresiones V2+originales y SHA blob lock; no contar tests como trades ni declarar método certificado.
