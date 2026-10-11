# QORE CORE — VT08 | RESOLUCIÓN P0 AL AUDITOR: SWING POINT AS-OF / CISD-PS POR FAMILIA / DOBLE SWEEP D

**Fecha:** 2026-10-10. **Arquitecto:** A método fuente. **PR #765**, issue A #762 / B #763, parent #634. Investigación 1095D M15 consumida, 5 pares FX, Owner NY 01/05/09, **sin VPS, sin órdenes ni 7Y sealed**.

## 1. Hallazgo decisivo: definición ejecutable del swing point válido

**Fuente original de autor 2026-01-10**, URL https://ttrades.com/how-change-in-the-state-of-delivery-confirms-swing-points/ , secciones **"How I Use CISD With Swing Points"**, **"Valid Candle 2 Closure With CISD"**, **"Candle 3 Closure With CISD"** y **"CISD Without a Higher Time Frame Closure Means Nothing"**:

1. El sweep (alto/bajo) es un **punto observado, no swing validado**.
2. Una C2 reversal closure necesita tomar un extremo de C1 y **cerrar dentro de C1**, no ambos extremos, y aparecer en POI HTF relevante; fuente de 2025-11-15 https://ttrades.com/understanding-candle-2-closures-within-the-fractal-model/ , sección **"Candle 2 Closures Need a Point of Interest"**.
3. El CISD de una serie de velas opuestas debe cerrar atravesando dicha serie y **confirmarse dentro de la misma C2 o C3 HTF** que se pretende validar.
4. El instante de swing validado `max(HTF_C2_or_C3.closed_at, LTF_CISD.confirmed_at, POI.evidence_asof)`. No asignar al comienzo del sweep ni a una barra M15 que se confirma **antes** de que HTF C2/C3 cierre.
5. Para la C3 Continuation **intrac3** existe **C2 H4 validada previamente**; el CISD posterior de C3 puede observarse durante C3 para evaluar una entrada intracycle **sin leer el futuro close H4 de C3**. La clasificación "C3 ideal" necesitaría nueva closure source adjudicada; NO está certificada automáticamente.
6. C3 Closure→C4: el swing C3 **requiere CISD dentro de C3**. C4 puede generar **su propio** CISD después, pero **no puede retro-confirmar** un swing C3 ausente al terminar C3. Corregido en commit `a5f7581e`, y test anti-retro `5ea7d4ff`. Una C3 shape sin CISD previo continúa D, aunque C4 forme una geometría de PS.

**A** para requisitos cualitativos del autor: HTF closure + LTF CISD + POI. **C** para el contrato mecánico de cuál FVG activo M15 y la correspondencia exacta de `protected_swings_in_candle2` con el POI (p.ej. criterio distal de invalidación): pendientes auditoría mediante velas originales de TTrades. **D** para relevancia de swing/POI cuando varios candidatos y regla C2 con sweep múltiple. NO afirmar que hay `A` completa por pasar geometría.

## 2. POI: fuente y límites

TTrades 2026-07-18 **The Only Points of Interest That Actually Matter**, https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/ , secciones **"Fair Value Gaps Come First"**, **"If There Isn't a Fair Value Gap, Look for Swing Highs or Lows"** y **"CISD Is the Final Point of Interest"**:

**Prioridad literal A: FVG → structural swing high/low → CISD retest.** La regla depende del **rango desde el protected swing hasta el rango actual**. Nuestra prueba V1 admite solo FVG M15 reconstruido desde TRES velas cerradas, y si hay >1 FVG plausible NO elige arbitrariamente un 'ganador'. No existe todavía adjudicación de relevancia del POI HTF ni selector completo de varios FVG, highs/lows u OB. El `fvg_proven_at` verifica barra fuente y timestamps, pero no sustituye la validación independiente desde fichero por B.

**EQ separados:** EQ diario de previous source day (context bias, aún sin confirmar 2157 old UNRESOLVED), EQ intra-C2 `full|close-to-wick` del artículo 2026-10-10 (requiere swing validado), EQ C3 full `high↔low` (C4 espera wick en mitad interior rango). NINGÚN EQ por sí mismo habilita orden. https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/ . 50% wick cutoff y timeout CISD 8 M15 **no reglas fuente**.

## 3. Reglas temporales implementadas en CÓDIGO

**Contrato** `src/qore/infrastructure/trader_lab/vt08_5m_ttrades_source_swing_asof_contract_v1.py`.
- `PoiReceipt` admite `FVG` con 3 M15 contiguous cerradas, `formed_at` exacto, `lower/upper` verificados; otros tipos existen en schema pero se devuelve `POI_NOT_ATTESTED` hasta reconstruir POI source.
- `SourceSwingReceipt` conserva `origin_id` desde market+family+side+C1/C2 origen, lado, POI formed/touched, opposing-series start, CISD confirmed_at, PS price, earliest `swing_point_confirmed_at` y estados explícitos, **cognitive_ready=False`, `orders_authorized=False` siempre**.
- `C2_CLOSURE_TO_C3`: C2 valid completed, M15 CISD inside C2, no swing as-of antes C2 HTF.close.
- `C3_CONTINUATION_INTRAC3`: C2 valid completed, C3 M15 prefix as-of, FVG ya existente de C2, CISD M15 confirmado antes de cualquier entrada; contrato **rechaza suministro de objeto H4 C3 completado** para esta decisión.
- `C3_CLOSURE_TO_C4`: strict C3 body closure and unambiguous C2 prior sweep, C3 HTF.close; C4 M15 CISD no puede retro-confirmar C3 CISD ausente. `C3_HTF_CISD_NOT_ATTESTED` bloquea si falla.
- `DUAL_SWEEP_UNADJUDICATED`: ningún selector latest CISD, sin adivinanza, estado D. Previamente **105/294** shapes C3→C4 contenían doble barrido, de ellas 80 C4 Owner. En este censo más amplio los dobles barridos se excluyen antes de evaluar la familia; **no comparar directamente 105 con este nuevo conteo universo**.
- `MULTIPLE_PS_UNADJUDICATED`: no elegir PS cercano por mejor RR o resultado futuro; todo source C, no A.

## 4. Replay causal real CINCO FX, primera medición independiente de rendimientos

Prerregistro anterior a salidas [VT08_A_THREE_FAMILY_REAL_FVG_SOURCE_SWING_1095D_CENSUS_PREREG_2026-10-10.md](VT08_A_THREE_FAMILY_REAL_FVG_SOURCE_SWING_1095D_CENSUS_PREREG_2026-10-10.md), commit `cb7ef851b540a88452d570c96a0b6fc446905770`.

[GitHub Actions run #38098839670](https://github.com/mezas3238-hue/qore-core/actions/runs/38098839670) — **SUCCESS 5/5**, exact code SHA `5ea7d4ff2104200e99328bf57f6ee1aed447e028`; **18 pruebas adversariales por mercado (90 aprobadas)**, Ruff GREEN, estudio real 1095 días desde 11.655 Owner H4 (2331 por mercado). Fuente immutable workflow run `35934924907`, software `b2d33e1b4829d8b4afc76983decca8a99131403c`.

| Mercado | C2: prior FVG C1 → touch/PS LTF C2 at HTF close | C3 intracycle: prior FVG C2 → touch/PS LTF C3 | C3 closure→C4 misma cadena FUENTE FVG → CISD/PS (requires proof C3) | C3 closure shape aligned with prior single C2 sweep |
|---|---:|---:|---:|---:|
| EURJPY | 48 | 49 | 0 | 8 |
| USDCHF | 52 | 44 | 0 | 4 |
| NZDUSD | 48 | 49 | 0 | 18 |
| CADJPY | 42 | 63 | 0 | 5 |
| USDCAD | 47 | 53 | 0 | 2 |
| **TOTAL** | **237** | **258** | **0** | **37** |

**LEER CORRECTAMENTE**: `237` y `258` son **source M15 FVG provenance + CISD/PS mecánico + temporalidad superadas para SHAPE_ONLY**, no trades, no fuente POI relevancia completamente adjudicada, no A+B readiness; se solapan potencialmente con 488 B01 originales, 252 C3 FVG shape anteriores y otras 3 familias. **No sumar 495 a 488, NO PnL**. El resultado `0` en C3 closure→C4 es característica **del filtro estrecho 1 FVG seleccionado / CISD dentro HTF**, no refutación de la familia. De las 294 geometrías iniciales, solo 37 respetaron adicionalmente una asociación direccional conservadora con el sweep C2 único; otras diferencias de cuenta parten de fuentes/casos aún no adjudicados. NO afirmar 37 candidatas ejecutables.

**Persistencia y artifact ZIP por mercado (30d):**
- EURJPY artifact ID `11687038505`, SHA256 `484aa2cfd17d587e29bbeae6a325614628c3f44a529e56e9320bf12b6d7840bf`
- USDCHF `11687068452`, `c6fe498a35c9c1556bdceb16656fea83d8bf02521fc8608be2c03f0f3908a777`
- NZDUSD `11686163087` no, **ver listado RUN FINAL**: artifact USDCHF=11687068452, EURJPY=11687038505, CADJPY=11686778966, USDCAD=11686439306, NZDUSD=11686163087.
- CADJPY artifact ID `11686778966`, SHA256 `9efd5536156187d6f1e46495f6604d47b8fc430a655be081075e9bb6540f40bb`
- USDCAD artifact ID `11686439306`, SHA256 `d596019de8f9d3dbae8a1e880c9dab673f48f89e5fab03536d1179858f1bda71`
- NZDUSD artifact ID `11686163087`, SHA256 `06cbaba8a504fa2779a136663d8597d46b6222d3c759b4fccbe75bb24d3b4b12`

## 5. Requerimientos para arquitecto cognitivo B

B debe revisar y **reproducir sin confiar en declarados por A** los triples FVG source M15, timestamp `formation<=touch_open<PS_confirm`, que `swing_valid_asof` usa `max(HTF_close,CISD_close)` y NO backdate. Para C3 continuation check **C3 H4 full NO pasa** a productor; solo barras M15 prefix. Para C3 closure C4 check **C3 CISD interno** requerido antes de atribuirle un swing validado; C4 CISD no puede prestar confirmación retroactiva.

Todos los recibos `source_status=STRUCTURE_RESEARCH_NOT_SOURCE_COMPLETE`, `cognitive_ready=False`. **No** modificar `APPROVED_A_B_MANIFEST_SHA256=None` ni activar Cognitive B full replay hasta que POI source High/Low/CISD_RETEST, significant range, no multiple-FVG ambiguity, C3 source closures, risk/entry/exit and complete Situation `CAUSAL_FIELDS` tengan procedencia y firma bilateral. No tocar VPS/live ni holdout final.

## 6. Estado exacto de certificación

**0** órdenes, **0** fills, **0** trades terminales y **0** PnL generados por este nuevo censo. El experimento C2 intracycle con 1514 OHLC fills previo resultó PF/DD insuficiente y NO se reautoriza por recuperar estructuras. Siguiente fase: más POI legítimos con fuente y chronology → CandidateEvent real A→B → cognición 100% operativa → replay broker bid/ask/commission/slippage → certificar solo después de controles independientes.
