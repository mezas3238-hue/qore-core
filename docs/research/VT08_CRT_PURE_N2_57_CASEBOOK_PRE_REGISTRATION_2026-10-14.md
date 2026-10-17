# VT08 CRT PURE — N2-FORENSICS: 57 contextos H4 con micro-CRT N1 (PREREG)

**Fecha: 14-OCT-2026.** Congelado ANTES del nuevo censo forense N2. Fuente de verdad: `mezas3238-hue/qore-core`, PR #626 DRAFT, sin merge.

## Pregunta y universo sin elegir por PnL
Del reporte N1 anterior [resultado](VT08_CRT_PURE_NESTED_N1_ORIGINAL_M5_REPLAY_RESULT_2026-10-14.md), 64 patrones dentro de 57 H4 contextos (30 AUDUSD, 27 USDJPY) cumplían simultáneamente condiciones descriptivas:
1. Alineación N1 con la dirección C2-H4 que R2-C llamó `TURTLE_SOUP`.
2. Una siguiente M15 contigua disponible dentro de C3 H4 después del cierre de micro-C3.
3. El 50% del antiguo H4-C1 no había sido tocado **antes de la decisión** N1.
4. R2-C no había emitido trade en el mismo H4.

Estas cuatro comprobaciones se **derivaron después de observar conteos** de N1, **no** representan estrategia preregistrada desde el inicio ni selección fuente-autorizada. Nunca llamarlas 64 entradas ni 57 oportunidades independientes.

## Examen preregistrado N2-FORENSICS — NO ECONÓMICO

**Fuente:** 148.171 AUDUSD + 148.201 USDJPY M5 originales con SHA anual QORE Atlas, no externos. Mantener 2024-09→2026-09-17 de las anteriores; no nuevo holdout. Mantener la definición N1 exactamente como está; no modificar `micro_crt_direction`, R2-C ni CIBO.

1. **Exhaustividad de 57 casos**: reconciliar exhaustivamente N1 64 filas / 57 H4 únicos, y procesar *TODOS* esos H4, no muestra seleccionada. Registrar los 16 OHLC M15 de cada H4 C3 y C1/C2 agregados; ID de cada micro candidato, con decision-time y siguiente M15 abierto (sin observar retornos posteriores).
2. **Solapamiento temporal**: representar cada micro-C1/C2/C3 como intervalo semicerrado `[micro_C1.opened_at, micro_C3.closed_at)`. Marcar si **cualquier par** comparte M15; agrupar por parent H4, dar número de filas N1 por parent, y un representante determinista *el primero por timestamp* solo como elemento de revisión, **no** orden ni evento aprobado. Si hay solapamiento, no inflar density contando los dos.
3. **Propiedad del micro-rango**: registrar `micro_C1_high/low`, `H4_C1_high/low`, si micro-rango está contenido dentro H4 C1, e identidad precio/rango coincidente con H4. Que sea distinta por timestamp **no acredita independencia macro**. Mantener sentencia `SOURCE_IDENTITY_UNADJUDICATED`.
4. **Target propio todavía disponible**: N1 exigió cerrar micro-C3 por encima/debajo del **midpoint del propio micro-C1**. Por tanto **ese midpoint ya fue alcanzado en la confirmación** y NO puede convertirse silenciosamente en TP posterior. Registrar `own_midpoint_already_closed_through=true` y si el *extremo lejano* (C1.high para bullish, C1.low para bearish) ya fue alcanzado por **cierre** de micro-C3 o por el **open** de la M15 siguiente. Estas son evaluaciones estructurales no sustitutos de DOL/target fuente-autorizado. No inventar futuro target.
5. **Contexto adversarial**: registrar si al momento de decisión el cierre micro-C3 está más allá del borde de H4-C1 que invalida la propia tesis hipotética (no afirmar que Romeo lo usa como veto). Registrar si la micro-C2 barre un high/low del H4-C1 mismo vs barrido únicamente de micro-C1.
6. **Calidad documental**: para cada caso guardar un resumen visualizable con todos los 16 OHLC M15, 1 o 2 representativos con trazabilidad SHA y estado `REQUIRES_SOURCE_REVIEW`. No emitir juicios de `CERTIFIED`, no probar PF ni calcular R, no llamar trades a micro patrones, ni seleccionar uno por beneficio.
7. **Clasificación final por contexto**: estado observacional `MULTIPLE_OVERLAPPING`, `MULTIPLE_DISJOINT` o `SINGLE_MICRO`; cruzar con distancia a nivel/objetivo propio aún disponible, pero **no seleccionar un ganador**. Si se necesitan otros conceptos de CRT o nuevas ventanas, preregistrar en experimento distinto.

**Criterio de aceptación:** reporte GitHub Action con **57 expedientes**, 64 anotaciones clasificadas, identidad por SHA y tests anti-lookahead / anti-overlap; se aceptan hallazgos negativos. **NO emitir nuevo replay económico hasta source ownership/definición de target nuevo e independencia hayan sido adjudicados.**

### Autoridad doctrinal (explícita)
RomeoTPT [Model #1 source closure](VT08-CRT-PURE-MODEL1-SOURCE-CLOSURE-001.md) es fuente primaria para Model #1, pero el micro-N1 no ha sido verificado como tal. SpeculatorFL y TraderFlameseN son apoyo secundario dependiente para contexto anidado; N1 y N2 son política de investigación **QORE_ENGINEERING**. La ausencia de un criterio específico en las fuentes no es permiso.

**Gobernanza:** no merge, no LIVE/DEMO trading, no VPS, no datos externos, no sizing/lotaje/volumen Trader, CIBO/QORE Risk soberanos, BTCUSD freeze. PR DRAFT.
