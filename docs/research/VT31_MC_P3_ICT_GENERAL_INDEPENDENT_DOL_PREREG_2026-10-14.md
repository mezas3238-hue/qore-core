# VT31 MC-P3 — prereg certificación de origen DOL ICT general con M1 independiente

2026-10-14. El propietario autoriza continuar metodología/cognitiva, no PnL. **Registrado ANTES de construir atestador P3.** Parent PR #928 (COG_EVIDENCE_V2: 80 tests), hijo separado del perfil TTrades AM PR #929. P3 cierra un gap técnico concreto: V2 bajo ICT general devuelve `UNKNOWN:ICT_EXTERNAL_DOL_PROVENANCE_UNVERIFIED` porque no reconstruye pools desde barras externas.

**No puede acreditarse como fidelidad absoluta a ICT** sólo porque el DOL coincida con una formalización QORE. Este P3 comprueba exclusivamente fuente/tiempo de precio de pools **QORE** (prior NY cash, Asia NY y London NY), nunca que ICT obligue a elegir el pool más próximo, 10 puntos o MSS 1,25x.

## Contrato fáctico preregistrado

Input: `CognitiveDecision` G3 real/no fabricada; lista de `M1Bar` ordenadas de una fuente **independiente** de COG, timezone-aware y cerradas hasta `as_of` externo; perfil `ICT_GENERAL_2023` + sesión London 03–04, NY AM 10–11 o NY PM 14–15 Nueva York IANA. Sin construir señales.

Por `draw_family` explícito del DTO, reconstruir sin usar su precio:
- `PRIOR_NY_CASH_SESSION_HIGH/LOW`: último día anterior con cash local 09:30–16:00 **390 M1 contiguas completas**, no >5 días, fuente high/low exacta, `confirmed_at` 16:00 NY de ese día.
- `ASIA_NY_CLOCK_HIGH/LOW`: día NY actual 00–03, 180 M1 contiguas, fuente high/low exacta, `confirmed_at` 03:00 NY.
- `LONDON_NY_CLOCK_HIGH/LOW`: sólo NY AM/PM, día actual 03–05, 120 M1 contiguas, `confirmed_at` 05:00 NY.
- `draw_level_observed_at` del DTO debe coincidir exactamente con cierre último M1 de ventana; `draw_target` debe ser el máximo/minimo. La orientación high→LONG, low→SHORT debe concordar con DTO.
- Desde `confirmed_at` hasta `as_of` debe haber cobertura estrictamente contigua de barras M1; **sin imputar fines de semana, market breaks, feriados ni gaps**. Si falta un tramo, `UNKNOWN_POST_CONFIRM_MONITORING_GAP`, no asumir nivel intacto. Si existe candle posterior y su wick toca el nivel (>=high o <=low), nivel se consumió, `REJECTED_ALREADY_CONSUMED`. No resucitar sweep.
- As-of igual a último M1 cerrado; input futuro, sesión incorrecta, familia desconocida o precio/fecha falsos se rechazan, datos incompletos se marcan `UNKNOWN`; no leer historia posterior.

Salida M0–M3: `VERIFIED_QORE_DOL_PRICE_LINEAGE`, `REJECTED` o `UNKNOWN`, razón, extremos exactos y fechas de fuente; flags `method_certified=false, cognition_certified=false, execution_authorized=false`.

## Composición con V2 sin alterar V2

`compare_general_cog_v2_with_dol` llama **sin modificar** `inspect_cog_evidence(profile=ICT_GENERAL_2023)` para MSS/pivote y por separado el atestador de DOL. Solo cuando V2 esté estructuralmente íntegro y el único UNKNOWN sea `ICT_EXTERNAL_DOL_PROVENANCE_UNVERIFIED`, + DOL positivo con fuente completa, emitir `QORE_MSS_AND_DOL_SOURCE_SUPPORTED_NOT_ICT_CERTIFIED`. Cualquier UNKNOWN/rejected adicional se conserva, nunca sale permiso de operación.

## Matriz adversarial congelada

Caso positivo LONG verdadero `VT31CleanroomCognition` con Asia 00–03 high 120; 00–10+ M1 continuo, MSS LONG 107, destino Asia-high 120. Probar SHORT fuente low cuando sea representable. Falsificaciones: DTO high 121, familia inapropiada, fecha de confirmación movida, destino consumido tras ventana, lookahead, ausencia una barra en 00–03, gap monitor posterior, as_of falsificado, orientación inconsistente, fuente cash anterior incompleta, London no habilitado en sesión London; sesgo H1 09 TTrades NO obligatorio. Un "green CI" no implica que un humano haya firmado G3 ni certificado método/edge.

**Prohibiciones:** G3 Act `a446afa17ed6e411b8f0b6fc182b103a78959a97`, COG+OPS SHA `78d4cdac0e09d1a6eef37b99c505ffc5098031fc` no tocar; no nueva cohorte V1, replay económico, producción, holdout, merge, órdenes, lotaje, VPS o LIVE. Issue #897 firmas siguen pendientes.
