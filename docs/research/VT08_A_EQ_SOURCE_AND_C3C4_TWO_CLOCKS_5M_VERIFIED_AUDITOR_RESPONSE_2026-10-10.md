# QORE CORE — VT08 P0-A | Respuesta al auditor: EQ autor 2026-10-10 + DOS RELOJES C3→C4 verificados

**Fecha:** 2026-10-10. **Owner:** Architect A source methodology. [PR #765](https://github.com/mezas3238-hue/qore-core/pull/765), [issue A #762](https://github.com/mezas3238-hue/qore-core/issues/762), [issue B #763](https://github.com/mezas3238-hue/qore-core/issues/763). Todos los ensayos **GITHUB-ONLY, RESEARCH-ONLY**. No VPS, no broker, no holdout sellado de 7 años.

## 1. Respuestas a cuatro preguntas EQ del auditor — fuente primaria A

**URL/fecha/hora:** https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/ , blog TTrades **2026-10-10 11:15am**, título "How To Use Equilibrium (EQ) – TTrades Fractal Model". Secciones originales:

- **"Using EQ With Large Wicks" y "When Candle 2 Closes Against the Swing Point":** cuando existe **swing point alcista válido y C2 cierra bearish**, el autor define `(C2.close+C2.low)/2`; cuando existe **swing point bajista válido y C2 cierra bullish**, `(C2.close+C2.high)/2`. **El extremo es de la misma C2**, NO de C1. **No** lo activa un umbral universal de wick 50%, ni necesariamente `C2 close outside C1`. El autor vincula la medida con un swing point y el contexto de la mecha.
- **"When Candle 2 Closes With the Swing Point":** si C2 cierra en sentido del swing point alcista/bajista, rango completo `(C2.high+C2.low)/2`.
- **"The Mechanical Process":** primero debe existir C2/C3 closure VÁLIDA en swing point, luego asignar rango EQ. Una vela ordinary bearish/bullish aislada **no autoriza** la selección de fórmula. El helper A `source_eq_after_closure(...closure_adjudicated=True)` computa geométricamente sólo; el booleano no verifica por sí mismo autenticidad de POI y swing fuente.
- **"When Candle 2 Closes With the Swing Point", párrafo C3** y **"The Mechanical Process":** C3 siempre **full range `(C3.high+C3.low)/2`**. Fuente histórica complementaria https://ttrades.com/candle-3-closure-a-complete-guide-to-identifying-continuations-and-reversals/ , **2025-12-03**, secciones **"Using Equilibrium With Candle 3 Closures"** y **"How to Frame Trades From Candle 3 Closures"**: esperar H4 C3 cerrada, vigilar wick C4 en mitad correcta, displacement/POI/refinamiento LTF; **NO limit-fill automático en EQ**.

**Otra fuente y otro propósito:** https://ttrades.com/using-equilibrium-in-continuations/ (**2025-08-02**), sección "Fibonacci Setup" y "Step-by-Step": Daily EQ (rango diario prev. high/low wick-to-wick) es contexto de **daily continuation bias** con PD arrays y LTF CISD/closure; **no es el mismo concepto** que EQ intra-C2 para definir área de mecha. Nueva aclaración octubre 2026 ≠ cita retroactiva al vídeo de 2025.

**Autoridad:** EQ matemático A; identificación de valid swing/source POI de cada instancia histórica todavía **D/shape-only**. Auditor acepta retirar 50%-wick umbral, 8 velas CISD y 65–80% estimación; no adoptadas en código.

## 2. Reparación nueva: pruebas temporales C3 close ≠ C4 M15

**Implementación:** `src/qore/infrastructure/trader_lab/vt08_5m_c3_c4_separate_causal_snapshots_v1.py` y tests `tests/infrastructure/trader_lab/test_vt08_5m_c3_c4_separate_causal_snapshots_v1.py`.

- En `c3_closed_source_shape`: exige C1/C2/C3 H4 cronológicas, que `observed_at >= C3.closed_at`, 16 barras M15 reales dentro de C3, OHLC H4 recalculada exactamente, sin ninguna barra C4. Devuelve estado **C3_CLOSED** con `origin_id` determinístico (market, side, C2/C3 origin, family) y fingerprint H4/M15 **sin datos futuros**.
- En `c4_first_m15_closed_observation`: evento separado que solo existe después de `C4.first_m15.closed_at = C3.closed_at+15m`; valida timestamps reales y anexa nuevo snapshot hash preservando `origin_id`. La primera M15 de C4 no puede anticipar confirmación posterior de C4 H4 ni volverse una orden.
- EQ C3 viene de `source_eq_after_closure(C3)` post-close y el wick C4 cuenta solo si cae dentro de **[C3 EQ,C3.high]** para long o **[C3.low,C3 EQ]** para short, NO simplemente por estar de un lado de EQ, corrigiendo falso positivo.
- CISD/PS interno se produce exclusivamente desde las **16 M15 de C3**. Si la serie opuesta se origina antes de C3 o el PS confirma después de C3 close, se rechaza. Fuente POI todavía no atestiguada: patrón etiquetado `C3_INTERNAL_CISD_PS_PROXY`, no válida source completa.
- El shape C3→C4 exige `NOT c2_reversal_closure(C1,C2)`; test negativo y assert independente certifican **0 solapamientos** con la rama C3-after-C2-completed bajo esta partición QORE. No significa validación de prioridad TTrades.
- C2 que barrió **AMBOS** extremos de C1 se etiqueta `DUAL_SWEEP_UNADJUDICATED` (no se le atribuye dirección libre ni trade). Distinción 13NY C4 fuera Owner vs shape metodológico dentro; DST 01/05/09 local no deriva 02 NY.
- Todo `SHAPE_ONLY_NOT_SOURCE_COMPLETE`, **0 CandidateEvent autorizado, 0 órdenes, 0 fills, 0 trades, 0 PnL**.

## 3. GitHub Actions VALIDADO sobre cinco mercados

**Workflow:** `.github/workflows/vt08-a-c3c4-two-clocks-source-shape-1095d-v1.yml`.
[Run **#38095655233**](https://github.com/mezas3238-hue/qore-core/actions/runs/38095655233) **SUCCESS 5/5** · **Ruff GREEN + 12 pruebas adversariales PASSED por mercado (60 ejecuciones sin fallos)** · tested SHA `5e553747993887875cd1a35184601591ece539d6`. Evidencia fuente M15 consumida 1095D run `35934924907`, software SHA `b2d33e1b4829d8b4afc76983decca8a99131403c`. 7Y sealed no leído.

| Mercado | C3 closed shapes | C4 Owner allowed | C2 dual sweep no resuelto (shapes) | C4 Owner con C2 dual sweep | C4 Owner sin C2 dual sweep | C3 CISD/PS proxy |
|---|---:|---:|---:|---:|---:|---:|
| EURJPY | 79 | 56 | 34 | 25 | 31 | 32 |
| USDCHF | 54 | 36 | 21 | 18 | 18 | 25 |
| NZDUSD | 63 | 46 | 15 | 10 | 36 | 25 |
| CADJPY | 64 | 50 | 22 | 20 | 30 | 29 |
| USDCAD | 34 | 25 | 13 | 7 | 18 | 18 |
| **TOTAL** | **294** | **213** | **105** | **80** | **133** | **129** |

Además: **81** C4 Owner-outside contabilizadas como oportunidad de análisis fuente (NO operativa 01/05/09), **36** full-body-engulf strong proxy, y **294** snapshots C4 first M15 temporalmente posteriores, nunca fusionados con el snapshot C3. Estas dimensiones no son un funnel serial; 36/129/213 se solapan. 105 shapes con C2 dual sweep exigen adjudicación específica; no pueden ascender a SOURCE_COMPLETE. 133 shapes sin doble barrido dentro horario Owner tampoco son candidatos comerciales ni ejecutables.

### Pruebas y hashes artefactos GitHub (retención 30d)

- EURJPY artifact `11685368859`, sha256:7465bf339de903a7668ff0b38a7bcabc531d680c54a504ed0962943f65c3d11b
- USDCHF artifact `11685228815`, sha256:1b6d992eb38131e5ae2b6f7733256b302676a12c2b412e27eb3692f017073d02
- NZDUSD artifact `11684839548`, sha256:182e7102e262ed05507e818c73a37d825cf0165437c6430707fcab5a2c862ef6
- CADJPY artifact `11685213768`, sha256:c8c1b9ed17648de35b1e27432093c318e6d5dd7b787ed2502b7345025c033459
- USDCAD artifact `11685763156`, sha256:bb30a0b3d6630ddbdd9fcf4b872fd588cc5b455a41063c3edeb7e79a23f4c2f2

## 4. Bloqueantes y próximos desarrollos

**P0 A:** adjudicación POI (high/low, FVG, opposite candle / OB) y swing point fuente válido tanto para C2 como para C3; CISD M15 confirmado **después** del POI e independiente de H4 C4 futuro; C4 LTF entries con timing/SL/TP/liquidez definidos por autor, C3 continuation distinta, daily EQ bias a partir de source-day real, no forzar 2.157 UNRESOLVED a dirección arbitraria. **No fijar** 50%-wick ni 8 bar CISD como regla autor.

**P0 B:** separar `origin_id` de `snapshot_fingerprint`, stages `C3_CLOSED` / `C4_FIRST_M15_CLOSED`, verificar proyecciones de features Source C3 vs future C4 y no unir las 294 geometrías a su gate `SOURCE_COMPLETE`. Mantener `cognitive_ready=False` y `APPROVED_A_B_MANIFEST_SHA256=None` hasta que todos los `CAUSAL_FIELDS` tengan datos/horas/hashes reales y ambos arquitectos firmen.

**No son 294 operaciones**; los 488 CandidateEvent B01 y C2 intra 1514 OHLC experiment falsado son universos diferentes. Certificación necesita metodología source-complete + cognición realmente vinculada 100% en consumed historical + BID/ASK/fees + objetivos fuente + robustez WFO/MC/holdout congelado. No VPS/live.
