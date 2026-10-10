# QORE Scalper — Arquitecto 2: auditoría de fidelidad metodológica

**Fecha:** 2026-10-10  
**Base auditada:** `535a2054d43c259e09b9a7e8eb3d54d21a503b4c`  
**Rama:** `agent/scalper-architect-b-methodology-20261010`  
**PR madre:** #623 (DRAFT/UNMERGED). **Issue metodología:** #757. **Cross-review:** #756.  
**Ámbito:** fuentes primarias del autor y contrato/código de Scalper. Sin cambio de estrategia ni uso VPS/LIVE.

## 1. Principio de atribución y frontera de evidencia

- Autor/publisher de la fuente "TTrades Scalping Model": **TTrades**, según su publicación de 2026-02-07. No se ha verificado identidad civil de la marca; no atribuir persona inventada.
- Autor ICT: **Michael J. Huddleston**; documentar a ICT por separado. Usar sólo fuente ICT primaria para reglas atribuidas a ICT. Los timestamps exactos del vídeo ICT 2022 Episode 2 **siguen PENDIENTES**.
- Esta auditoría inicial incluye verificación de **texto de los artículos TTrades** con secciones identificables; PDF/video/timestamps, pruebas de rutas y todo el codebase **aún requieren cierre**.
- **Fuente explicita para una ruta NO significa obligatoriedad universal en otras rutas**.
- Regla TTrades vs ingeniería QORE pueden coexistir como "specialization" documentada, pero NO llamarse replicación íntegra del autor si existen conflictos.
- Separar fidelidad de PF/DD/winner-preservation: ninguno prueba al otro.

### Fuente primaria indexada

| Clave | Publicación TTrades | Identificación del pasaje |
|---|---|---|
| T-GEN | [TTrades Scalping Model](https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/) (2026-02-07) | "The Core Concept"; "Establishing Hourly Bias"; "Finding The Fifteen Minute Swing Point"; "Entry" |
| T-ASIA | [How to Trade Asia](https://ttrades.com/how-to-trade-asia-using-the-ttrades-fractal-model/) (2026-08-15) | "Option One: Positional Entries in Asia"; "Option Two: The 4-Hour and 15-Minute Fractal Model" |
| T-LON | [How to Trade London](https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/) (2026-09-12) | "Start With A Daily Bias"; "Use The 4 Hour Candle"; "Confirm The Swing On The 15 Minute"; "How To Trade The Model" |
| T-NYM | [New York Manipulation](https://ttrades.com/daily-profile-understanding-the-new-york-manipulation/) (2025-07-24) | "What is the New York Manipulation Profile"; "How to Recognize It"; "Adding Confluences" |
| T-FTM | [Failure To Manipulate](https://ttrades.com/how-to-trade-breakouts-failure-to-manipulate/) (2026-09-05) | "The Reversal Has To Actually Form"; "Trade The Continuation"; "Pair It With Higher Time Frame Bias" |
| I-2022 | [ICT Mentorship 2022 Episode 2](https://www.youtube.com/watch?v=tmeCWULSTHc) | **UNRESOLVED: transcripción / timecodes por regla** |

## 2. Ledger de reglas — baseline de auditoría (NO cerrado)

Valores permitidos:
- **Tipo:** `SOURCE_EXPLICIT`, `SOURCE_STRONGLY_IMPLIED`, `INTERPRETATION`, `QORE_ENGINEERING_RULE`, `UNRESOLVED`.
- **Veredicto:** `MATCH`, `PARTIAL`, `CONFLICT`, `UNRESOLVED`.
- **Alcance:** `MANDATORY_FOR_ROUTE`, `ALTERNATIVE`, `CONTEXTUAL`, `QORE_ONLY`, `UNKNOWN`.

| ID | Ruta/sesión | Código / regla QORE | Fuente / pasaje | Tipo / alcance | Veredicto / obligación del A2 |
|---|---|---|---|---|---|
| SRC-001 | Generic scalp | `capitalizer_high_frequency_identity_v49.py`: H1 bias -> M15 setup -> M1 trigger | T-GEN, "The Core Concept", "Entry" | SOURCE_EXPLICIT / MANDATORY_FOR_ROUTE | **MATCH** estructura principal H1/M15/M1 |
| SRC-002 | Generic scalp | Daily/H4 prohibido como capa de decisión | T-GEN, "The Core Concept": Daily = contexto más amplio | QORE_ENGINEERING_RULE / QORE_ONLY | **PARTIAL**: la prohibición QORE no es la descripción completa del autor |
| SRC-003 | Generic scalp | H1 estado persistente, múltiples M15 por H1 | T-GEN, "Establishing Hourly Bias" | INTERPRETATION / QORE_ONLY | **UNRESOLVED**: persistencia reusable no explícitamente definida con frecuencia MAX3 |
| SRC-004 | Generic scalp | M15 CISD/protected swing como setup | T-GEN, "Finding The Fifteen Minute Swing Point" | SOURCE_STRONGLY_IMPLIED / MANDATORY_FOR_ROUTE | **PARTIAL**: revisar precisión de la detección y vela de confirmación |
| SRC-005 | Generic scalp | M1 no inventa bias; ejecuta tesis | T-GEN, "Entry" | SOURCE_EXPLICIT / MANDATORY_FOR_ROUTE | **MATCH** en graph V49; verificar wiring real |
| SRC-006 | Generic scalp | `LIQUIDITY_SWEEP_CISD` vs `FVG_RETRACE_CISD` como alternativas | T-GEN, "Entry" (FVG interaction, CISD, protected swing); T-NYM "How to Recognize It" (FVG/OB/modelo a elección) | INTERPRETATION / ALTERNATIVE | **PARTIAL**: combinación exacta FVG+retrace+CISD debe probarse por ruta; no super-AND universal |
| SRC-007 | All | M15 stop de tesis y M1 stop de ejecución diferentes | T-GEN "Entry" / T-ASIA "Protected Swings Define Risk" | QORE_ENGINEERING_RULE / QORE_ONLY | **UNRESOLVED**: TTrades apoya protected-swing invalidation, no prueba separación universal M1/M15 ni ratio 4–8 |
| SRC-008 | Generic | target causal H1 y protected swing como invalidation | T-GEN "Entry" | SOURCE_STRONGLY_IMPLIED / CONTEXTUAL | **PARTIAL**: HTF objective soportado, selección de ladder H1 QORE |
| SRC-009 | Asia TTrades | Universal H1/M15/M1 en Asia | T-ASIA "Option One" y "Option Two" | SOURCE_EXPLICIT / ALTERNATIVE | **CONFLICT si se anuncia como la ruta Asia del autor**: fuente ofrece positional y H4/M15; QORE specialize |
| SRC-010 | London TTrades | Universal H1/M15/M1 en London | T-LON "How To Trade The Model" | SOURCE_EXPLICIT / MANDATORY_FOR_ROUTE | **CONFLICT si se anuncia como modelo London TTrades**: fuente Daily/H4/M15 |
| SRC-011 | NY manipulation | Simple H1/M15/M1 sin sweep London-range | T-NYM "What is the New York Manipulation Profile" | SOURCE_EXPLICIT / MANDATORY_FOR_ROUTE | **UNRESOLVED**: determinar si QORE implementa la ruta NYM o un scalp genérico dentro de NY |
| SRC-012 | NY manipulation | Requerir simultáneamente OB+FVG y MSS | T-NYM "How to Recognize It", "Entry Models" | SOURCE_EXPLICIT / ALTERNATIVE | **CONFLICT si se exige super-AND**: artículo presenta refinamientos alternativos; V49 graph lo prohíbe |
| SRC-013 | FTM continuation | Continuación ante ausencia de reversión confirmada | T-FTM "Trade The Continuation", "Pair It With Higher Time Frame Bias" | SOURCE_EXPLICIT / CONTEXTUAL | **PARTIAL**: no hacer FTM requisito de toda entrada; ruta y detector requieren prueba |
| SRC-014 | All | Broad research sessions NY 20–02 / 02–08:30 / 08:30–16 con DST | `capitalizer_session_clock.py` | QORE_ENGINEERING_RULE / QORE_ONLY | **MATCH ingeniería**, NO prueba de killzones autorales |
| SRC-015 | All | 9 mercados segmentados y MAX3 portfolio por sesión | `capitalizer_contract.py`; `_portfolio_max3` | QORE_ENGINEERING_RULE / QORE_ONLY | **PARTIAL**: controles propios QORE; no atribuir al autor |
| SRC-016 | All | Cierre dentro de sesión, sin overnight | `CapitalizerStrategyIdentity` | QORE_ENGINEERING_RULE / QORE_ONLY | **PARTIAL**: T-ASIA "Overnight Trades Should Not Be Overmanaged" muestra diferencia con algunas rutas del autor |
| SRC-017 | V50-G | stop M1 pivot confirmado, intacto, dentro de tesis M15 | `capitalizer_v50_target_stop_intelligence.py:build_dual_invalidation` | QORE_ENGINEERING_RULE / QORE_ONLY | **UNRESOLVED** para fidelidad exacta, pero causalidad interna verificable |
| SRC-018 | V50-G | ruido 4–8x y target mínimo 1R | `capitalizer_v50_cognitive_geometry_specialist.py` | QORE_ENGINEERING_RULE / QORE_ONLY | **UNRESOLVED** económicamente; NO es mandato de TTrades |
| SRC-019 | V50-R/V53 | re-arm M1 posterior bajo mismo parent M15 | `capitalizer_v50_m1_rearm_capacity.py`; `capitalizer_v53_winner_preserving_rearm_economics.py` | QORE_ENGINEERING_RULE / QORE_ONLY | **UNRESOLVED**: sólo con event/time guard y preservación económica |
| SRC-020 | V54-B | parcial 50%, runner H1, BE luego T1 | `capitalizer_v54_structural_partial_runner.py` | QORE_ENGINEERING_RULE / QORE_ONLY | **UNRESOLVED**: lifecycle ingeniería, requiere A/B causal |
| SRC-021 | ICT lineage | Raid/MSS/displacement/PD-array atribuidos a ICT | I-2022, **timecodes no cerrados** | UNRESOLVED / UNKNOWN | **UNRESOLVED**: nunca promover como universal sin fuente ICT primaria y minuto/página exacto |

**El ledger es inicial, no exhaustivo ni apto para reclamar SOURCE_FAITHFUL.** Debe expandirse a cada `if`, guard, selector, stop, target, tiempo y ruta efectivamente usada antes de certificación.

## 3. Grafo diferencial de rutas — primera revisión

### Generic scalping
`T-GEN: Daily contextual → H1 bias → M15 swing → M1 execution → protected stop / HTF draw`  
`QORE V49: H1 persistent → multiple M15 setup → M1 [sweep+CISD | FVG-retrace+CISD] → stop M15 or V50 M1 → H1 ladder → MAX3`

Resultado: núcleo H1/M15/M1 **alineado parcialmente**, no identidad total; Daily prohibido por Owner y stop/noise/target policy añadido por ingeniería. Una arquitectura QORE puede especializarse, pero debe identificarse correctamente.

### Asia
`T-ASIA: [positional con HTF protected swing] OR [4H Candle 2 → M15 fractal / protected swing]`.  
`QORE: H1 persistent → M15 → M1, close same session`.  
Veredicto: **CONFLICT** si QORE declara implementar el modelo Asia de TTrades; es una estrategia QORE especializada distinta. No introducir Daily/H4 hard gate sin autorización del Owner.

### London
`T-LON: Daily bias → daily wick → 4H swing/wick → M15 CISD/protected swing → expansion`.  
`QORE: H1 persistent → M15 → M1`.  
Veredicto: **CONFLICT** si QORE declara identidad exacta de ruta Londres del autor. La rentabilidad de 90 trades no demuestra fidelidad a Londres.

### New York
`T-NYM: London range context → liquidity sweep NY → CISD → expansion, FVG/OB or other model alternatives`.  
`QORE: generic H1/M15/M1 in NY; sweep+CISD or FVG-retrace+CISD candidates`.  
Veredicto: **UNRESOLVED** hasta probar si la intención es NY manipulation profile o simple generic scalp durante horario NY. El nombre de sesión no implica automáticamente modelo de manipulación.

### FTM
`T-FTM: high/low taken → expected reversal fails to confirm → continuation + protected swing, under HTF bias`.  
`QORE: must identify explicit FTM route/detector or declare FTM contextual`.  
Veredicto: **UNRESOLVED**. No usar FTM como gate universal sin fuente.

## 4. Invariantes de certificación metodológica

1. Una alternativa documentada no se convierte en superintersección por conveniencia.
2. Estructura H1/M15/M1 congelada por QORE; toda fidelidad de rutas del autor fuera de esta gramática debe declararse como excepción/conflicto, no esconderse.
3. Observaciones confirmadas por cierre; ninguna vela futura ni target/stop hindsight.
4. H1 debe conservar su contexto, M15 su tesis y M1 sólo disparar ejecución.
5. El stop elegido sigue vigente hasta entrada y no supera la invalidación de tesis.
6. Mercado y sesión son etiquetas de segmentación, no prueba causal negativa automática.
7. MAX3 y control de riesgo son límites QORE (no declarar mandatos TTrades/ICT).
8. El autor puede proponer runners o overnight donde el contrato QORE cierra en sesión; indicar diferencia, no fusionar sin revisión.
9. La evidencia histórica consumida sirve para construir; certificación final sólo proveedor independiente o ensayo prospectivo congelado.
10. Sin ledger completo y todos CONFLICT/UNRESOLVED resueltos o declarados formalmente como *QORE-specialized*, está prohibido etiquetar al sistema como "fiel al autor".

## 5. Próximos trabajos A2: tareas verificables y tests

- Resolver fuentes PDF/video original y timestamps para cada afirmación ICT. Conservar URL, versión, fecha y ubicación de cada cita.
- Expandir ledger al conjunto **completo** de condiciones de `capitalizer_high_frequency_capacity_census_v49.py`, H1 context, M15 detectors, M1 CISD/FVG, dual invalidation, V50-G, rearm, lifecycle.
- Por cada ruta, generar casos sintéticos long/short y contraejemplos: no H1 bias, setup M15 no confirmado, M1 antes de M15, FVG/CISD alternativos, swing roto, target tocado, H1 invalidado, cruces de sesión/DST y MAX3.
- Separar claramente source-aligned generic scalping / perfiles especiales Asia London NY / especializaciones QORE. Proponer corrección documentada, **no** introducir H4/Daily en código congelado sin acuerdo explícito de propietario.
- A2 debe solicitar a A1 (#756) análisis causal / económico del cambio propuesto, con preservación ganadores y densidad. A1 debe remitir a A2 todo nuevo gate/trigger para cotejo con autor.
- Publicar reporte firmado en #757 y #623; aprobación metodológica no significa aprobación estadística.

**Estado: DIFERENCIAL INICIAL REPRODUCIBLE / LEDGER INCOMPLETO / FIDELITY NOT CERTIFIED / NO LIVE.**
