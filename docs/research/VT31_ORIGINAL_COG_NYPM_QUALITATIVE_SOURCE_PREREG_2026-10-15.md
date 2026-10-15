# VT31 — PRE-REGISTRO COG ORIGINAL NY PM: decisión, memoria, abstención y método

Fecha 2026-10-15. El Owner exige certificar METODOLOGÍA Y COGNITIVA, no PF/DD ni rentabilidad. Este ensayo se preregistra ANTES de implementar cualquier test de NY PM. NO modifica el G3 COG/OPS ni autoriza trades.

## Sujeto y fuente
- Motor original `VT31CleanroomCognition.observe_closed_m1` + `.assess(SessionId.NY_PM)`; COG congelado SHA blob `d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9`; G3 OPS `0ce9707314aecb71155de8b57044b6ec028847b2`, acta `e99c70b4e018d626fb620d9a21b9314a51abc36d`.
- Identidad `ICT_GENERAL_2023_NY_PM_QORE_COG_RESEARCH`. Ventana 14:00–15:00 NY, **no es variante TTrades NY AM 10:00–11:00**. Un caso funcional ICT General solo demuestra coherencia de reglas QORE; el oráculo ICT original de DOL aún carece de homologación autoral. Verificador de sombra PR #951 `ICT_CONTEXT_WITNESS_UNDERDETERMINED`, no CLAIM_SOURCE_CERTIFIED.

## Caso sintético prescrito, sin búsqueda de mercado
1. Viernes anterior 390 M1 sesión NY cash high 150/low80. Lunes 00:00–13:59 NY M1 completos continuos; durante 09:00–09:59 hay high110 y low90 como fuente de comparación, pero NO debe aplicarse automáticamente el requisito de barrido H1 09 del TTrades AM a NY PM.
2. A las 13:57 vela M1 high104 por encima de vecinos high102; se confirma al cierre de la vela derecha de 13:58. A las 14:01 vela baja a 89, y la de 14:02 revierte con cierre LONG=105 y high106, desplazamiento que rompe nivel104. En 14:03 NY el COG ORIGINAL tiene H1/M15 frescos, swing causal, y pool confirmado `PRIOR_NY_CASH_SESSION_HIGH=150` sin barrer. Expectativa: LONG/DOL150 y fuente propia con NO TRADE.
3. Sin la vela final 14:02: WAIT por ausencia de MSS. Quitar toda la cobertura 10:00–13:59 M1 pero conservar el prior cash + NYPM: WAIT por H1/M15 desactualizados (sin inventar barras).
4. Insertar nueva vela posterior que toca DOL150 y cerrar debajo: revocar tesis/WAIT, sin reactivar pool consumido. Cambio de cierre por debajo pivote 104 también revoca tesis, aunque no toca DOL.
5. Auditar el mismo juicio auténtico bajo `ICT_GENERAL_2023`: queda `ICT_CONTEXT_WITNESS_UNDERDETERMINED`, no `CERTIFIED`; bajo `TTRADES_NY_AM_2025`: `PROFILE_SESSION_REJECTED`. No usar el COG de investigación TTrades como sustituto.
6. Rechazar solicitud `assess` retroactiva tras insertar vela futura, y comparar hora UTC con America/New_York para DST sin confundir con horario 10 NY.

## Resultado posible y prohibiciones
- Si el original COG no emite LONG, no forzar regla ni seleccionar mejor caso: registrar FAIL y diagnosticar lectura de HTF/pools/MSS. CI puede fallar; eso no permite modificar G3 sin versión nueva y autorización.
- Publicar testimonios cualitativos individuales y motivos, no N económico, PF, DD, Sharpe, OOS, trades o profits. Pasa únicamente QA de estos escenarios; no certifica método ICT ni cognición integral por sí solo.
- METODOLOGIA=PENDING, COGNITIVA=PENDING, dobles firmas G3 #897 sin inventar, NO MERGE/OMS/LIVE/VPS/FundedNext LIVE/sizing Trader.