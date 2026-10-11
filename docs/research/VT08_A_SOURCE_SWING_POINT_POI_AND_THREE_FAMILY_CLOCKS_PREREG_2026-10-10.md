# P0 VT08 — PRERREGISTRO ANTES DE RESULTADOS: SWING-AS-OF / POI PRIORIDAD / CISD-PS R3

**Fecha 2026-10-10.** Arquitecto A; PR #765; tareas #762/#763. ÚNICAMENTE GitHub research, consumido 1095d fuente M15 #35934924907. **NO** 7Y sealed, paper orders ni VPS.

## Fuentes con autoridad explícita A

1. [TTrades: How Change in the State of Delivery Confirms Swing Points (2026-01-10)](https://ttrades.com/how-change-in-the-state-of-delivery-confirms-swing-points/): `C2 or C3 HTF closure` + `lower timeframe CISD inside that HTF candle` son ambos necesarios para validar swing. Un sweep antes de CISD = swing pendiente. El HTF completed confirmation **no** existe hasta su H4 close.
2. [TTrades: Understanding Candle 2 Closures Within the Fractal Model (2025-11-15)](https://ttrades.com/understanding-candle-2-closures-within-the-fractal-model/): **C2 reversal closure** exige sweep C1 y cierre C2 de vuelta dentro rango C1, POI HTF significativo. Confirma C3 continuation; la C2 que no cumple no se puede pasar por C2 closure.
3. [TTrades: The Only Points of Interest That Actually Matter (2026-07-18)](https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/): POI prioridad **FVG → structural swing high/low → CISD retest** desde PS y hacia current range; la primera categoría existente se considera y no se continúa buscando después de FVG. *Formalización C pendiente:* definir numéricamente `first in range` en situaciones de varios POI e invalidaciones.
4. [TTrades: EQ C2/C3 (2026-10-10)](https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/): EQ intra C2 contra swing `(C2.close + C2.wick_extreme)/2`, a favor swing C2 full, C3 full. **Requires valid swing point/closure**.
5. [TTrades: Ideal Formation (2026-06-27)](https://ttrades.com/ttrades-ideal-formation-high-probability-swing-points/): ideal = closure coincides con valid PS y POI; no reclasificar automáticamente un closure ordinary como IDEAL.
6. [TTrades C3 Closure→C4 (2025-12-03)](https://ttrades.com/candle-3-closure-a-complete-guide-to-identifying-continuations-and-reversals/): C3 cierre completo confirma para C4, EQ full C3; no C4 H4 future usado.

## Hipótesis preregistradas sin umbrales ni predicción de densidad

**A.** Diseñar `swing_point_confirmation_asof`: al momento de decisión incluye (a) nivel HTF/POI conocido y fecha fuente antes del touch, (b) HTF closure válida **al cierre H4**, (c) CISD/PS calculado con barras LTF M15 cerradas del timeframe aplicable **con evidencia de serie opuesta y cierre por encima/debajo de su OPEN**, (d) side coherente con sweep, (e) no doble sweep. Retorna `PENDING_HTF`, `PENDING_CISD`, `SOURCE_POI_UNVERIFIED`, `MULTIPLE_PS_D`, `DUAL_SWEEP_D`, `CANDIDATE_VALIDATED_STRUCTURE_ONLY`. **Nunca ordenar** ni entregar candidato aprobado.

**B.** Separar tres familias y tiempos de forma literal:
- `C2_CLOSURE_TO_C3`: sweep único y C2 H4 close, CISD PS en C2 antes de su close, confirmación no antes de H4 C2 close; señal futura en C3.
- `C3_CONTINUATION`: H4 C2 validada **antes de C3 start**; POI touch + LTF CISD/PS **dentro C3** antes de cualquier hipotético entry. NO usar H4 C3 close para una entrada dentro C3.
- `C3_CLOSURE_TO_C4`: C2 incompleta; H4 C3 validada a su close; LTF CISD confirmado dentro C3, o un **nuevo CISD** dentro C4 anterior a su entrada, jamás H4 C4 futuro. Cada caso se etiqueta distinto, no decidir caducidad de CISD en 8 velas.

**C.** `POI`: demostrar al menos FVG con triple M15 source y momento formación M15-3 CLOSED anterior al touch. Para HIGH/LOW o CISD_RETEST habilitar tipo en schema pero dejar D hasta pivote y su propia confirmación as-of verificables. No simular un POI arbitrario ni source-validarlo mediante bool.

**D.** `DUAL_SWEEP_UNADJUDICATED`: los 105 C3→C4 shapes previos constituyen D y se mantienen en bucket con 80 C4 Owner permitidas según censo anterior, jamás se elige lado por último CISD, y excluidos de `SOURCE_COMPLETE`. Números previos son hechos congelados, **no outcome nuevos**.

**E.** Todos los ensayos sin equity/PF/DD, 7Y untouched, no predictions de +200 o 65–80%, no thresholds wick 50%, no expiración 8 M15, no selector PS nearest. Probar M15 falsificados, timestamps fin de velas, futuro, POI posterior a touch, cambios DST, C3 ficticiamente cerrada, C4 H4 futura, doble sweep, PS ambiguos, event IDs estables, EQ no activa entradas por sí sola.

## Condiciones antes de promocionar A→B

La prueba de temporalidad y estructura **NO** prueba que POI es significativo fuente, jerarquía entre varios FVG, órdenes físicas, SL/TP, cardinalidad, ni situación cognitiva completa. No emitir CandidateEvent source-approved sin productor/independent verifier y manifest A+B firmado. **B cognitive_ready=False** permanece.
