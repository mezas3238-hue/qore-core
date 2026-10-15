# VT31 — PREREG COG ORIGINAL SHORT espejos de London/NY AM/NY PM, EST/EDT

**2026-10-15. ANTES DEL CÓDIGO.** Directiva owner: certificar metodología y cognitiva, NO por PF/DD/rentabilidad. Auditoría de conducta SHORT real de `VT31CleanroomCognition`, no proxy ni motor cuantitativo. Conservar G3 original (cognition blob `d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9`, OPS `0ce9707314aecb71155de8b57044b6ec028847b2`, acta `e99c70b4e018d626fb620d9a21b9314a51abc36d`).

## Hipótesis de comportamiento (QORE G3, no regla autoral certificada)
- Dos días NY: invierno 2026-01-05 (EST) con viernes anterior 2026-01-02 y verano 2026-07-13 (EDT) con viernes anterior 2026-07-10. Un día sintético por DST, sin seleccionar mercado por retorno. Cada fuente cash del viernes completo 09:30–16:00 NY, 390 M1 con HIGH150/LOW80 válidos, visible antes del lunes. Fuente lunes H1/M15 cerrada y fresca en cada sesión.
- LONDON NY 03:00–03:06: contexto 00:00–03:00 M1 completo; pivote mínimo estricto M1 de 03:02 LOW96 confirmado a las 03:04 (barra derecha de 03:03), 03:05 M1 cierra SHORT=94 bajo 96, con cuerpo >1.25×mediana5; próximo DOL QORE elegible prior NY cash LOW80 (14 puntos), siempre antes del target.
- NY AM NY 10:00–10:03: 00:00–10:00 M1 completo, rango 09–10 HIGH110/LOW90, 09:57 LOW96 confirmado al 09:59; primera M1 de 10:01 barre HIGH111, 10:02 cierre SHORT94/MSS pivote96; COG original debe emitir SHORT DOL80 por liquidez cash anterior, mientras **TTrades AM fuente** exige opposite 09h LOW90. Clasificar **NONCONFORMANT** para TTrades, no confundir el perfil ICT General con este criterio.
- NY PM NY 14:00–14:03: 00:00–14:00 M1 completo, 13:57 LOW96 confirmado 13:59; 14:02 MSS SHORT94, DOL cash80. No trasladar regla TTrades AM de H1 09h a NY PM, aunque el 09h haya existido.
- Para las seis parejas sesión×DST correr COG ORIGINAL por `observe_closed_m1` en orden real y `assess(session, as_of=last.closed_at)`. Verificar side SHORT, familia `PRIOR_NY_CASH_SESSION_LOW`, DOL80, pivot96, NSS asof; no órdenes.

## Contrafactuales por situación (NO economía)
- Variar SOLO `close` de la vela de MSS final 94→97, dejando wick, la primera estructura y el resto de las M1 igual. COG debe abstenerse (NO MSS SHORT) porque no cierra bajo pivot96. Es un contrafactual estructural, no probabilidad ni rentabilidad.
- Evaluar `assess` del instante previo a MSS: WAIT, sin señales retroactivas.
- Al escenario positivo añadir vela siguiente que barre LOW80 (wick79) y cierra bajo pivot96 con cuerpo neutro: COG debe revocar su DOL (no persistir SHORT objetivo consumido); añadir alternativa cierre97 sobre pivote96: COG debe revocar tesis SHORT. No exigir que nunca aparezca otra tesis válida con una señal nueva; el chequeo es sobre persistencia original.
- Probar `as_of` retroactivo luego de añadir M1 posterior: error de causalidad, no re-etiquetar.
- Someter el DTO original SHORT a testigo fuente nativo AM y `inspect_cog_evidence(TTRADES_NY_AM_2025)`; debe rechazar por DOL80 vs 09h LOW90, no por auto-certificar o cambiar el COG.
- Registrar todos los juicios per-case, UTC/NY/DST, evidencia original, razones WAIT/REJECT, `certified=false` y SHA. Evidencia limita a escenarios sintéticos positivos/negativos y no certifica original ICT/TTrades autoral entero.

## Scope
Sin 3Y NAS100 market scan, backtest, PnL, PF/DD/Sharpe/Sortino, buy/sell orders, CIBO/QDLE, lotaje propio, OMS, OOS, LIVE, FundedNext LIVE, VPS, merge o firmas COG/OPS falsas. Metodología/Cognitiva siguen PENDIENTES hasta M0–M6 y revisión humana #897. Si alguna hipótesis falla, documentar y no cambiarla silenciosamente.