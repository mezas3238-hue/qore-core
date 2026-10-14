# VT08 CRT PURE — N3B PRE-REG: evento M5 realmente nuevo tras C2-close

**Fecha 14-OCT-2026.** Pre-registro previo a la ejecución nueva N3B, pero creado DESPUÉS de ver resultados agregados de N3 (2.634 C2, 1.109 M5 tempranos, 540 C2 ya beyond-midpoint). **Resultado N3B será diagnóstico exploratorio de continuación, jamás holdout nuevo ni modelo pre-elegido antes de observar N3.**

## Hipótesis concreta

N3 cuenta cualquier cierre M5 en C3 del lado del midpoint, incluyendo casos donde **C2 YA había cerrado** más allá del midpoint. Por ello llamar al primer M5 `crossing` puede inducir a error: puede ser persistencia, no información nueva. N3B separa estrictamente:
- `C2_ALREADY_BEYOND`: M15-C2 cerrado del lado del midpoint al confirmarse, conocido antes de C3;
- `NEW_M5_EVIDENCE`: C2 no estaba beyond y el primer cierre M5 de C3 del lado del midpoint se registra en M5 slot1/2 (antes del final de C3).
- `FAR_BOUNDARY_SPENT_AT_EVIDENCE`: mecha extrema se produjo en cualquier M5 anterior O EN el mismo M5 cuyo cierre aporta evidencia, sin poder establecer secuencia intrabar.
- `FAR_BOUNDARY_UNTOUCHED_AT_M5_CLOSE`: ninguna M5 hasta ese cierre tocó extremo lejano de micro-C1 (un DOL posible, NO autorizado doctrinalmente).
- `CONTEXT_H4_ALIGNED_AND_TARGET_PRISTINE_AT_C2_CLOSE`: dirección igual H4 y midpoint H4 C1 no tocado en C3 hasta cierre C2.
- **Intersección fija de diagnóstico:** `NEW_M5_EVIDENCE` + `FAR_BOUNDARY_UNTOUCHED_AT_M5_CLOSE` + `CONTEXT_H4_ALIGNED_AND_TARGET_PRISTINE_AT_C2_CLOSE`. Reportar N de eventos, H4 distintos, períodos, conteos de exclusiones, aun si cero. **No es una entrada; no hay garantía de que el extremo sea target auténtico ni de que HTF confirme después.**

## Identidad y seguridad

- Mantener **todas** las 2.634 filas de C2 del N3 y método de barrido C1/C2 congelado; no alterar `c2_purge_return` ni `first_m5_observation`.
- Agregar contadores N3B, claves booleanas de origen temporal y H4 únicos; falla cerrada si N1 no reconcilia a 521/418.
- Usar los mismos AUDUSD y USDJPY, los **296.372 M5 QORE originales SHA** y la misma época 2024–2026; no otros proveedores, no otros mercados ni búsquedas por PF.
- `NEW_M5_EVIDENCE` mira exactamente M5-C3 slots 1/2 cerrados. Nunca mirar M15-C3 final para dar elegibilidad a un evento ocurrido antes. La auditoría puede etiquetar el desenlace N1 final para comparación, pero no puede usarlo en el subconjunto C2/M5.
- NO PnL, NO trades, no stops/targets/lotes, no entrada, no test de performance, no cambio R2-C/CIBO.
- G-M1/3/4 permanecen OPEN si faltan confirmación C2 auténtica, propiedad del micro C1, HTF PD array, trigger M5 original, DOL y cancelación por contradicción.
- La instrucción fuente B se refiere a la tercera vela tras confirmar la segunda; la condición micro midpoint es operacionalización QORE, NO Model #1 original RomeoTPT.

**Gobernanza:** PR #626 DRAFT sin merge, no LIVE/DEMO, no VPS, no FundedNext LIVE, BTCUSD frozen, no sizing/lotaje Trader, soberanía CIBO.
