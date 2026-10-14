# VT08 CRT PURE — PRE-REGISTRO DE CENSO CRT MICRO M15 DENTRO DE PARENT H4

**Congelado antes de consultar los nuevos conteos.** Fecha 14 OCT 2026 · Owner autorizó investigación + replay; PR #626 DRAFT, no merge ni broker órdenes.

## Pregunta y fuentes

¿Existen en las ventanas H4 C3 de VT08 micro-CRT M15 con su propio rango de referencia, diferentes de los 88 falsos «rearmes» bajo el C1 antiguo? **No inferir rentabilidad a partir del censo.**

- RomeoTPT (A): concepción de CRT y jerarquía H4 CRT → M15 Model #1 documentada en `VT08-CRT-PURE-MODEL1-SOURCE-CLOSURE-001.md`. El autor **NO ha adjudicado** que el detector de tres M15 siguiente sea su Model #1. Es una hipótesis de observación.
- SpeculatorFL y TraderFlameseN (B): CRT anidados/micro dentro de macro y distinción confirmacional/avanzado; dependientes entre sí. Referencias: https://threadreaderapp.com/thread/1784493604473618604.html y https://threadreaderapp.com/thread/1790141530461622525.html ; distinción de modalidades: https://threadreaderapp.com/scrolly/1794311615535518154 .
- Se congela una **operacionalización exploratoria de QORE**, no regla original de ningún autor, sin prueba de independencia económica ni de autorización de entradas.

## Diseño inalterable del primer examen: N1 micro-CRT confirmacional

**Datos:** exactos M5 históricos QORE Atlas original, AUDUSD y USDJPY, misma ventana del replay 2024-09-21 a 2026-09-17 disponible; SHA originales por año; sin APIs externas ni cTrader actual. Sólo parent H4-C1/C2/C3 **COMPLETOS** y parent TS C2 del universo anterior R2-C (287/265). No se cambian los 2 triplets NY del control para este primer estudio. Esto es una prueba **interna al parent**, no el censo de todo CRT M15 de mercado.

**Micro-fuente autónoma (3 M15 completos y contiguos dentro de C3 H4):**
1. Micro-C1 = M15 referencia propio. Micro-C2 = M15 siguiente; realiza **un único** barrido estricto (high > C1.high ó low < C1.low, pero no ambos) y **cierra dentro o en los límites** del rango C1. Si toma low ⇒ bullish, si toma high ⇒ bearish.
2. Micro-C3 = siguiente M15, completo; confirma cerrando hacia el lado coherente **más allá del punto medio de su micro-C1**: bullish `close > midpoint`; bearish `close < midpoint`. Estas relaciones no se optimizan con resultados.
3. Cualquier secuencia M15 consecutiva que cumpla forma un **candidato de micro-CRT**, se identifica por mercado + `micro_C1_utc` + `micro_C2_utc`, y por C1.high/low; no se atribuye old CRTH M15 pivote R2C ni se necesita aquel old-level.
4. Referencia/objetivo del evento micro se documentan como **su propio C1**, no el C1 de H4; el test sólo registra geometría observada y momento de confirmación. **No se simula entrada, stop, target, R o beneficio** en este censo.
5. La decisión se conoce al cierre de micro-C3; no hay permiso para operar en esa misma vela. Si no hay barra M15 posterior completa para observar que la decisión fue implementable causalmente dentro de C3 H4 ⇒ etiqueta `NO_NEXT_BAR_IN_PARENT`, no se cuenta como entrada.
6. Se registran dos clases **superpuestas por contexto, no filtros para elegir winners**: `SAME_H4_DIRECTION` vs `OPPOSITE_H4_DIRECTION`; `PARENT_FIRST_R2C_TRADED` vs `PARENT_R2C_REJECTED`; subgrupo `PARENT_WITH_OLD_C1_EXHAUSTED` cuando en el C3 antes del nuevo cierre ya se había tocado 50% del antiguo C1. El indicador no es invalidación original Romeo.
7. Dentro de un H4 C3 se aceptan **múltiples candidatos para contar hipótesis** pero ninguna se convierte en orden. Anotar `MULTIPLE_MICRO_CANDIDATES_PER_PARENT` y `EARLIEST_ONLY_POLICY` como futuras cuestiones; jamás sumar todos como trades.

**Reporte exigido**: denominadores H4 287/265, M15 completa, número total de micro-candidatos y parents únicos, n alineados/contrarios, n dentro de 88 padres antes rechazados, n con C1 viejo 50% tocado, n con siguiente M15 contiguo, n por period_1/period_2, 10 ejemplos con H4/micro timestamps y OHLC para examen humano, SHA de fuente/ledger. **No comparar PF de nuevas fuentes en esta ronda** y no promover modalidad avanzada hasta fijar reglas source-justified.

**No conjeturar ventaja ni densidad operable:** la existencia de micro-CRT distintos no demuestra que superen CIBO, gates metodológicos o fees. Gate estado siempre `RESEARCH_CANDIDATE_ONLY`. BTCUSD congelado. Sin sizing, sin MT5, sin VPS, sin merge, sin operaciones DEMO/LIVE, sin desplegar.
