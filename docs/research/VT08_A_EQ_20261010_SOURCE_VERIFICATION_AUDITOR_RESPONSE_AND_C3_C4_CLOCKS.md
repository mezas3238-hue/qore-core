# VT08 P0-A — Respuesta verificable a la auditoría EQ y alcance real de C3→C4

**10-oct-2026.** [Issue #762](https://github.com/mezas3238-hue/qore-core/issues/762); [B #763](https://github.com/mezas3238-hue/qore-core/issues/763). Metodología source authority A, no permisología de broker. El auditor retira correctamente 50%-wick, 8 barras de caducidad y estimación 65–80%; siguen D. No promoverlos.

## FUENTE PRIMARIA NUEVA VERIFICADA (A)

Enlace: **https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/**, publicada 2026-10-10 11:15, texto escrito accesible. Secciones EXACTAS:

- **`When Candle 2 Closes Against the Swing Point`**: en bullish swing, C2 cierra bearish ⇒ tomar **el cierre de la propia C2 y su low**. EQ=(C2.close+C2.low)/2. En bearish swing, C2 cierra bullish ⇒ **el cierre de la propia C2 y su high**. EQ=(C2.close+C2.high)/2. Referencia C1 NO entra en este cálculo.
- **`When Candle 2 Closes With the Swing Point`**: C2 cierra con la dirección del swing ⇒ EQ del **rango íntegro high↔low de la propia C2**. No hay un umbral numérico publicado de wick para cambiar automáticamente de régimen.
- **`The Mechanical Process`**: identificar **closure válida en swing point C2/C3** ANTES de marcar EQ, no usar la fórmula basada solo en una vela bajista/alcista aislada. Hay que confirmar POI y swing point causalmente por separado.
- **`When Candle 2 Closes With the Swing Point`**, párrafo final, y **`The Mechanical Process`**: para **C3** usar **rango completo de C3, high↔low**, luego evaluar vela siguiente. En artículo C3 Closure del **3-dic-2025**, https://ttrades.com/candle-3-closure-a-complete-guide-to-identifying-continuations-and-reversals/, secciones **`Using Equilibrium With Candle 3 Closures`** y **`How to Frame Trades From Candle 3 Closures`**: C4 debe formar mecha en mitad correcta de C3, luego displacement + refinamiento LTF. C3 EQ **contextual/potencial POI**, NO limit-fill automático al 50%, no autorización de trade.
- Importante: aclaración 2026-10-10 NO se atribuye retroactivamente al vídeo original 2025. Distinta fuente https://ttrades.com/using-equilibrium-in-continuations/ (2025-08-02), **`Fibonacci Setup`**, usa wick high↔low de una vela/rango escogido y EQ como divisor de contexto. **NO confundir DAILY EQ previo para bias con C2/C3 intra-fractal EQ para POI/continuación**.

**Grado:** Fuente A para fórmulas y sus contextos escritos; **D** para qué velas históricas concretas tienen POI/swing source-validado hasta reconstrucción upstream. El argumento booleano `closure_adjudicated` del helper de A no prueba por sí mismo POI ni swing: código de geometría `source_eq_after_closure` sigue **research-only**, `source_complete_entry=False`.

## CORRECCIONES AL INFORME DEL AUDITOR

1. No existe un funnel serial `294→213→36→129→45`. **294** geometrías C3 strict body-close/no C2 sweep; **213** C4 starts en Owner 01/05/09, **81** C4 fuera; **36** body engulf estricto y **129** internal M15 CISD/PS **son subconjuntos parcialmente superpuestos**, no escalones secuenciales; **45** intersección de owner + old B01 bias alineado + internal PS proxy. Distinguir intersecciones.
2. Los **294** no son setups completados y por tanto **VT08 no implementa todavía una segunda familia ejecutable**; A sí implementó su detector SHAPE_ONLY. No añadir a los 488 B01, 252 otros C3 shapes, 1514 replays C2 intracycle PF/DD falsificados.
3. Solapamiento del subconjunto **36** con `C3_AFTER_COMPLETED_C2_REVERSAL` no debe asumirse nulo por nombre. Nuestra definición C3→C4 incluye `C2_FAILED_REVERSAL_CLOSURE`, la otra C3 after completed C2 exige `C2 reversal closure` (sweep único/return-inside). Por la **partition formalizada** son excluyentes dentro del mismo `(market,C1,C2,C3)`, pero falta probarlo con fuente histórica. Caso C2 con doble sweep debe quedar **DUAL_SWEEP_UNADJUDICATED**, no ser convertido en "failed reversal" fuente-completo.
4. El primer PS intrace3 se detecta con M15 **de C3 exclusivamente**, nunca por lectura de C2. Es **proxy usando el low/high de primera M15 C3**, no prueba de POI. Para C4 aún NO hay productor POI+CISD+PS real, por tanto 0 órdenes. Un CISD C4 requerirá `confirmed_at<=now`, sin leer H4 C4 final.
5. `source_event_id` estable y `snapshot_fingerprint` separado: hay que emitir snapshots `C3_CLOSED_ASOF` sin ningún dato posterior de C4, y `C4_M15_CLOSED_OBSERVATION` solo después de first M15 close, sin utilizar C4 para crear el C3 ID ni para decidir al inicio de C4.
6. La etiqueta `BIAS_UNRESOLVED` no es prohibición universal autor, pero es salida honesta del **antiguo helper B01**. No forzar EQ diario→LONG/SHORT sin POI + closure + CISD temporalmente confirmados.

## Próximas obligaciones

- Productor POI source adjudicado (FVG/high/low/OB) con barras y cierres, y CISD/PS post POI causal; owner HTF 01/05/09 no alterar por DST.
- Separar formalmente daily EQ contextual de C2/C3 EQ intra-fractal en payload B; nunca usar un nivel EQ de C3 antes de cerrar C3.
- Manifest bilateral A/B y todos los CAUSAL_FIELDS; B debe devolver `cognitive_ready=False` para shapes.
- Certificación económica: solo source-complete signals → paper BID/ASK/fees → paired full cognition; 7Y sealed sin tocar.
