# VT08 CRT — QORE tres fuentes V3, confirmación tercera vela
**Pre-registro antes de generar señales, outcomes o resúmenes V3:** 15-OCT-2026. **NUEVA identidad** `VT08_CRT_THREE_SOURCE_QORE_V3_CSD_THIRD_CANDLE`. No modificar retrospectivamente V1 ni V2.

## Motivación científica y fuentes originales examinadas

- RomeoTPT, [video Model 1](https://www.youtube.com/watch?v=UUq_wKQ61Wo&t=2332s): vela fuente que atraviesa old-high/old-low y **cierre de cuerpo** de vela posterior en el sentido contrario. Esta descripción inspira una confirmación de cierre real, no un simple wick.
- SpeculatorFL, [How to Select a CRT Correctly (25-MAY-2024)](https://threadreaderapp.com/scrolly/1794311615535518154), distingue **Advanced CRT** (sin esperar confirmación) de **Conformational CRT** (espera cerrar la segunda vela y considera la tercera), además de HTF/LTF anidados, PD array, timing y inside bars. No asumir que «más protocolos incrementa X%» sea una tasa científicamente demostrada.
- SpeculatorFL [CRT detailed thread (28-APR-2024)](https://threadreaderapp.com/thread/1784493604473618604.html), jerarquía HTF/LTF, CSD y destino 50%/opuesto.
- TraderFlameseN [Choose the best CRT candle (13-MAY-2024)](https://threadreaderapp.com/thread/1790141530461622525.html), tercer pilar de corpus con protocolos análogos pero parecido sustancial a SpeculatorFL: **NO cuenta como validación de rentabilidad independiente**.

**Advertencia esencial:** Las fuentes describen arquitectura CRT, no un algoritmo universal exacto de 3 barras consecutivas M15. La siguiente micro-regla es **`QORE_ENGINEERING_SOURCE_INSPIRED_V3`** y no se atribuye a ninguno de los 3. El Owner autorizó sintetizar de las 3 fuentes, no aprobó cada umbral operativo ni otorgó G-M PASS.

## V3: reglas fijas antes de ver resultados

1. Misma base H4 estructural que V2, con H4 de UTC 00/04/08/12/16/20, **C1 y C2 ambas completas, contiguas y anteriores al C3**. C2 ha de barrer exactamente un lado de C1 y **cerrar dentro** de C1; el rango de C1 define `target_twice = C1.high + C1.low` (midpoint). Si H4 C2 barre ambos lados o cierra fuera, ABSTAIN.
2. En el H4 C3, las M15 reales completas se inspeccionan **secuencialmente**. Para cada triple M15 contiguo `M15_REF, M15_SOURCE, M15_CONFIRM` (índices 0–2 hasta 13–15):
   - Fuente M15 bullish: `M15_SOURCE.low < M15_REF.low`, `M15_SOURCE.high <= M15_REF.high`, source.close dentro de ref, y **source CLOSE < source OPEN**. Bearish inverso `SOURCE.high > REF.high`, `SOURCE.low >= REF.low`, source.close dentro de ref y **source CLOSE > source OPEN**.
   - **CONFIRM** debe estar cerrada, M15 bullish `CONFIRM.close > SOURCE.open` (bearish `CONFIRM.close < SOURCE.open`). Este umbral se denomina `QORE_V3_BODY_CLOSE_PROXY`, *NO* certificación de CSD auténtico de todos los autores.
   - La tesis M15 ha de ser la **misma** que la tesis H4. Primera triple cronológicamente elegible únicamente, máximo UN caso por padre H4.
3. Desde apertura H4 C3 hasta cerrar `M15_CONFIRM`, verificar que el **midpoint H4 C1 jamás se alcanzó por wick M15** y que a la confirmación el target está delante del `CONFIRM.close` (bullish midpoint mayor, bearish menor). Primer toque agota ese destino y **no rearmar**; M15 pérdida no puede transformar una hipótesis en otra rentable.
4. Invalidación estructural (solamente para hipótesis de trayectoria posterior): **extremo barrido de M15_SOURCE**. Si la confirmación cruzó ese extremo en sentido invalidante, ABSTAIN, no corregir el stop ex post. La invalidez no es un stop de broker ni sizing.
5. Decisión conceptual ocurre **al cierre de M15_CONFIRM** (nunca dentro de la vela), verificando que sigue DENTRO del H4 C3; triple final que cierra exactamente H4 C3 recibe `EXPIRED_AT_H4_C3_CLOSE`, **no** autoriza mirar el próximo H4.
6. No se impone PD array/horario histórico arbitrario o inside-bars artificiales como filtros **hasta disponer de política y datos verificables**. Guardar esos protocolos como **`CONTEXT_NOT_ADJUDICATED`** y excluirlos del certificado, no fingir evidencia. EURUSD/BTCUSD no introducidos: este estudio conserva AUDUSD/USDJPY originales.
7. Falla de una M5 anterior al cierre de confirmación: **WAIT_DATA_GAP**; ninguna vela «rellenada». No usar M5 posteriores al reloj de decisión ni prices de C3 H4 completa para crear la señal.
8. Censo sobre todos los pares H4 cerrados de los dos mercados, salidas exhaustivas `ABSTAIN_H4`, `WAIT_M15`, `CONCEPTUAL_CANDIDATE_V3`, `EXPIRED_AT_H4_C3_CLOSE`, `WAIT_DATA_GAP`, `ABSTAIN_TARGET_CONSUMED`. Registros case_id y UTC, conteos mercado/año/causa, **NO sizing, dinero, riesgo patrimonial, Profit Factor, Sharpe, Sortino, Drawdown ni PnL**.
9. Este censo es **DESARROLLO con Atlas M5 ya consumido, NO OOS**, incluso si las señales parecen prometedoras. Nada se convierte automáticamente en una operación ni G-M1..G-M5 PASS.

## VALIDACIÓN ADVERSARIAL antes de datos

- Test bull/bear con tercera vela real cerrada.
- Test oposición H4/LTF, source sin cierre direccional, confirm wick sin cierre de cuerpo, doble sweep, dato M5 incompleto.
- **Metamorphic no-lookahead:** cambio arbitrario en M5 posteriores al cierre de la tercera vela NO cambia case_id, dirección ni reloj de decisión.
- **C3 close:** última confirmación expira sin consumir barra de H4 posterior.
- **Censorship accounting:** todos los padres elegibles contados, no solo señales elegidas.
- Antes de cualquier investigación económica, congelar más adelante costos BID/ASK broker originales, OOS nuevo, PF/DD/Sharpe/Sortino y revisión Risk/CIBO externa. **VT08 no hace sizing**.

## Comparabilidad y NO optimización
- V1 = 54, V2 = 745 candidatos conceptuales. V2 después tuvo evidencia adversa de precio: 115 destino vs 538 invalidez; esto **fue visto antes de redactar V3**. Por ello V3 está CONTAMINADA a nivel de hipótesis por conocimiento previo de desarrollo, aunque su código sea causal. No ocultarlo ni presentar su validación interna como confirmación independiente de edge.
- El foco V3 es reparar una **especificación de confirmación respaldada por los textos**, no elegir el parámetro con mejor PnL. Si falla, registrar NO_SUPPORT V3 sin adaptar tests al resultado.

**No sizing, no merge, no DEMO/LIVE/VPS/orders; CIBO soberano.**
