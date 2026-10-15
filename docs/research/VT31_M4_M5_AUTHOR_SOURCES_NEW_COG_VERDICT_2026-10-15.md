# VT31 — Veredicto M4/M5 con ampliación de FUENTES AUTORALES TTrades
**15-OCT-2026** · PR #960 DRAFT child #959 · Mandato Owner: metodología+cognitiva, NO PF/DD/Sharpe/Sortino/sizing. G3 original intacto y sin MERGE/LIVE/DEMO/VPS/FundedNext.

## Resultado de QA/CI verificable
[GitHub Actions #38714295682 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38714295682); versión de código ejecutada `1b455832dbd71cd6853459639d97ff210c7ee422`, **80/80 pruebas adversariales/regresión PASS**, Ruff PASS. Fuente NAS100 1.059.784 M1 SHA256 exacto `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, desarrollo histórico ya visto (NO OOS). Artifact [#11961966060](https://github.com/mezas3238-hue/qore-core/actions/runs/38714295682/artifacts/11961966060), ZIP SHA256 `55ae649c0be0847bec9dcc82f368552f67e4670f680d246d5dd3773f07f2ffe5`. Preregistro **anterior a código** `ff27e6df536a45166c01443a300c38d844184e5a`. **No** convertir CI en nota de rendimiento/certificación.

## Corrección doctrinal material respecto al handoff R3
Se descubrieron **FUENTES ADICIONALES PRIMARIAS TTrades** (el mismo autor) que sí dan geometría semántica para subconjuntos antes tratados como enteramente indeterminados:
- [TTrades MSS vs CISD 1-JUL-2025](https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/): MSS requiere desplazamiento+cierre más allá del SWING (high/low), CISD requiere cierre más allá del OPEN de vela/serie contraria; distintas confirmaciones, no sustituir una por otra. 
- [TTrades Order Blocks 4-JUL-2025](https://ttrades.com/order-blocks-simplified/): serie últimas velas contrarias, cierre de validación, confluencia nivel; **50% CUERPO** para mean threshold e invalidación por cierre adverso. NO es midpoint FVG CE ni toque de BID/ASK.
- [TTrades Breaker Blocks 5-JUL-2025](https://ttrades.com/breaker-blocks-simplified/): breaker alcista `LOW→HIGH→LOWER LOW→HIGHER HIGH`, bajista inverso; adicionalmente vela(s) zona y retest. Cuatro piernas válidas SIN retest NO son entrada. Los [continuation breakers](https://ttrades.com/trading-breaker-blocks-for-continuations/) tienen variantes, no arrastrarlas a este perfil sin habilitarlas expresamente.
- [TTrades Advanced Market Structure 11-JUL-2025](https://ttrades.com/advanced-market-structure-simplified-from-short-term-to-long-term-trends/): **SWING SHORT TERM pivot3 geométrico descrito por autor**: máximo por encima de ambos vecinos / mínimo por debajo de ambos vecinos. Eso corrige frase demasiado amplia de R3 que decía pivot3 siempre QORE. Matiz obligatorio: elegir qué pivote **CAUSÓ** desplazamiento y poner stop en él requiere MÁS evidencia, y `cuerpo>=1,25×mediana5` continúa siendo filtro QORE propio.
- [TTrades Favorite Reversal OB 19-JUN-2025](https://ttrades.com/my-favorite-reversal-pattern-orderblocks/): sweep, serie velas opuestas, cierre sobre/desde esa serie y displacement son requisitos semánticos. No hay adjudicación automágica por OHLC.

## Testigo M4/M5 implementado y resultado en contextos REALES
Script nuevo `scripts/vt31_m4_m5_author_semantics_bridge_20261015.py`, **read-only**. Funciones con fuente/autenticidad explícita:
1. `short_term_swings`: tres M1 contiguas/cerradas, extremos estrictos y confirmación sólo después de la M1 derecha. **Source-defined short-term structure geometry**, sin atribuir causalidad de stop.
2. `source_ob_cisd`: solo una vela opuesta (aproximación QORE con prueba de cierre más allá del OPEN), fuente describe **serie**; asignar `CISD_SOURCE_COMPONENT_OBSERVED`, sin presumir MSS/displacement, OB global ni entrada.
3. `ob_body_midpoint_status`: media del **cuerpo**, distingue retest OHLC de ejecución y cierre invalidante; vela que simultáneamente toca e invalida ⇒ `AMBIGUOUS_TOUCH_AND_INVALIDATION_SAME_M1_NO_FILL`.
4. `source_breaker_four_leg`: cuatro swings de corto plazo confirmados en secuencia y relaciones HH/LL fuente; **selección consecutiva** es formalización QORE; sin zona ni retest `BREAKER_AUTHOR_ENTRY=UNVERIFIED`.
5. Solo evalúa cuando V2 #954 preserva primero H1 raid/regreso válido y ventana NY, nunca reetiqueta raid para arreglar contraejemplo; cero DTO/órdenes/ACK/fills.

Mismos **483** contextos del primer regreso congelados del #934 (NO trades):
| Componente fuente/geométrico observacional | Contextos | No es certificado autoral completo |
| --- | ---: | --- |
| Componente CISD cierre vs **una** vela opuesta QORE auditado | **478** | Falta serie OB completa, displacement/estructura y validación por fuente |
| Sin ese componente CISD | **5** | No excluye OB/Breaker/otras familias |
| Breaker **4 piernas** confirmado con swing corto fuente | **83** | Faltan zona, retest, selección causativa y convivencia |
| Sin cuatro piernas según formalización vigente | **400** | No excluye variantes del autor; selección de swings QORE |
  
Dos parejas **se solapan**, NO sumar 478+83 como oportunidades; no son fills/trades/estimación de PF ni señal de trading. Primer ejemplo lexicográfico CISD: 02-OCT-2023; Breaker 4-leg: 04-OCT-2023; sin CISD: 07-JUL-2025; sin Breaker: 02-OCT-2023. Source as-of/timestamps en artifact.

## Decisión certificar metodología/cognitiva M4/M5
- **M4 COMPONENTES semánticos**: evidencias de OB/CISD, swing geométrico y cuatro piernas Breaker **mejor respaldadas por fuente TTrades** que PR #958/#959. Se pueden etiquetar `AUTHOR_DEFINED_GEOMETRY_CONFIRMED_IN_SCOPE` para componentes con fuente explícita. **NO** etiquetar `AUTHOR_ENTRY_MODEL_CERTIFIED`: el artículo requiere más que geometría, zona/retest/estructura, displacement y concurrencia. Falta evaluación de FVG en estructura y displacement/trigger.
- **M5**: la geometría swing pivot3 como short-term swing tiene respaldo autoral, pero `CAUSATIVE_SWING_FOR_DISPLACEMENT` sigue NO ATTESTED y stop precio NO se puede emitir; los 189/88/180/26 de PR #959 documentan justamente el problema de elegir.
- **M0**: COG G3 ORIGINAL NYAM produce target previous cash en algunos casos, no DOL H1 09 del perfil TTrades (PR #950/#955). Source-first PR #956 es research separado. Un único VT31 necesita selector pre-sesión y contrato integrador source-bound antes de aprobar.
- **M6**: Issue #897 abierto, PR #896 con **0 reviews** al verificar, faltan dos firmas COG+OPS distintas; no simular.
- **CERTIFICADO_METODOLOGÍA: NO EMITIDO. CERTIFICADO_COGNITIVA: NO EMITIDO.** Ninguna mejora semántica autoriza LIVE/DEMO ni lotaje.

## Próximo trabajo sin reabrir PnL
Definir en código un enrutador de PERFIL pre-sesión que use COG fuente TTrades #956 en NY AM y G3 original *claramente QORE policy* en ICT general, con frontera sin contaminación y fallo seguro; someterlo a adversarios. Incorporar retest y serie OB/Breaker con casos fuente independentemente anotados; determinar el swing *causante* (no basta pivot3). Obtener aprobaciones reales M6 del Owner con dos revisores técnicos verificables en SHAs exactos. Mantener PR DRAFT, ninguna orden, no sizing propio.
