# VT08 P0 DENSIDAD — ROOT CAUSE / PRERREGISTRO POSITIONAL ENTRY Y MATRIZ DE RECHAZOS

**Fecha 2026-10-10, antes del nuevo censo.** GitHub exclusivamente, PR #765, issues A #762, B #763, 1095 días consumidos 5 pares reales M15, artefactos #35934924907. Todos los ensayos OUTCOME-BLIND, sin órdenes/PnL/holdout 7Y, sin VPS. Rechazo del usuario: **la densidad del trader continúa inaceptablemente baja; 237/258 SHAPES no son una solución**.

## NUEVA FUENTE PRIMARIA (ERROR MATERIAL DE ANTERIOR DEEPSEEK)

- [TTrades **Positional Entries – Enter Before The Expansion**, publicado 2026-08-08](https://ttrades.com/positional-entries-enter-before-the-expansion/): entrada al **OPEN de nueva vela HTF**, siempre **después** de cierre HTF C2 o C3 **válido** + CISD LTF previo + protected swing previo + contexto/EQ adecuados. **NO exige un nuevo CISD en la vela HTF que acaba de abrir**. También es técnica alterna, no duplicar trades por ambas técnicas. DeepSeek había clasificado "Positional Entry" como NO fuente; queda formalmente invalidado.
- [TTrades **Time Frame Alignment**, 2025](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/): par de timeframes **30M→3M** aparece explícito (M3 pasa D→A para ESE par). 4H→15M y 1H→5M son emparejamientos distintos, no poner M3 arbitrariamente en H4. La fuente original C2 validada necesita H4 cierre y lower-CISD.
- [TTrades **Understanding Candle 2 Closures**, 2025-11-15](https://ttrades.com/understanding-candle-2-closures-within-the-fractal-model/): HTF sweep+close inside C1, POI higher-TF (swing high/low, FVG, o contrario si faltan), LTF CISD; la fuente **NO exige FVG único**.
- [TTrades **C3 Closure**, 2025-12-03](https://ttrades.com/candle-3-closure-a-complete-guide-to-identifying-continuations-and-reversals/): C3 cierre en cuerpo C2 si C2 falló, entonces C4 potencial; POI + CISD requeridos. Doble sweep permanece D.
- [TTrades **Positional Entries Asia**, 2026](https://ttrades.com/how-to-trade-asia-using-the-ttrades-fractal-model/): apertura HTF sin *otra confirmación*, con PS validado anterior.

## Objetivo y variables de investigación

**NO fijar un target ficticio de candidatos**, no usar el PF para decidir filtros. Contar causalmente cómo el filtro estrecho `FVG_C1_UNICO` reduce C2, cómo `FVG_C2_UNICO` reduce C3, y oportunidades geométricas posicionales AL ABRIR vela HTF que hoy pueden perderse por esperar otro CISD en la vela de expansión. Usar `protected_swings_in_candle2` del código congelado como proxy y buscar autorización de POI independientemente; NO etiquetar PS como autor validado si no hay source POI.

Denominadores en la misma población `11.655` anchors (5*2331). Por cada ancla C1,C2 completas:
1. C2 sweeps ONE extreme and closes inside C1 (reversal-closure geométrica);
2. C2 CISD/PS M15 contra extremo barrido, exactamente confirmado antes de C2 close (0 /1 /many);
3. C2 PS **independiente de FVG** de C1 (source POI pendiente);
4. C1 has exactly 0/1/>1 FVG aún activo, y con FVG al tocarlo; medir pérdida atribuible a `EXACTLY_ONE_FVG` no llamar todos salvables;
5. preexisting C2 PS y H4-open en C3 (Owner allowed), riesgo geométrico PS vs open (stop < entry long, > entry short), y PS/EQ respecto a expected half, sin imponer wick%-threshold;
6. distinguir 0/1/many PS (no elegir el más cercano por R:R), overlap con antiguas 488 B01 *solo geometría* y 237 C2 source FVG receipts; NO sumar conteos;
7. C3 closure→C4: C3 closed (body beyond C2, no sweep C2 H/L), prior C2 failed closure and prior POI/PS candidate within C3, H4-open next C4; bucket Owner allowed, outside Owner, double-sweep D; C3 PS confirmed exclusively before C3 close. Reportar upper bound estructural, no trades.
8. Como diagnóstico secundario: owner 01/05/09 local vs unautorizado 13/17/21; no ampliar horario por backtest, no duplicar entrada bajo one-trade/day.

**Dos capas obligatorias en reporte:** `MECHANICAL_UPPER_BOUND_NO_POI_ADJUDICATION` y `SOURCE_POI_AUTHORITY_PENDING`. Nada a B como CandidateEvent source completo antes de POI validado/SL/target y 27+ CAUSAL_FIELDS.

**Éxito científico:** identificar el verdadero gate que ha suprimido frecuencia y conmensurar el efecto potencial de entrada posicional (captura de expansión inmediata). Éxito COMERCIAL requiere un replay A→B cognitivo con costes y PF/DD, todavía NO disponible. La capa estructural no justifica comprar/vender.
