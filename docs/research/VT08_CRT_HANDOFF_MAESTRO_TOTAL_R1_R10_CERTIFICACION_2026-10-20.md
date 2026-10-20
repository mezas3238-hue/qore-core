# VT08 CRT PURE / QORE CORE — HANDOFF MAESTRO TOTAL R1–R10

**Fecha de corte: 20 de octubre de 2026. Documento maestro autónomo para el siguiente arquitecto.**
**Naturaleza:** transferencia técnica, histórica, metodológica, cognitiva, forense, operativa, custodia y riesgos de certificación. **NO es un certificado del trader.**

> **DIRECTIVA SOBERANA DEL OWNER (NO REINTERPRETAR):** Certificar VT08 CRT usando una metodología QORE coherente formada con tres fuentes — RomeoTPT, SpeculatorFL, TraderFlameseN —; **no exigir fidelidad exclusiva a RomeoTPT**; investigar metodología/cognitiva y *también* rentabilidad económica GLOBAL con todos los Gates; **PROHIBICIÓN ABSOLUTA DE SIZING dentro de VT08**, incluyendo lotes ficticios, tamaño fijo, capital supuesto, 1R nominal o ratios dependientes de posición. Toda autoridad patrimonial, DD de cuenta y capital es de CIBO / QORE Risk. **No órdenes, broker, demo, live, VPS, despliegue o merge** en este PR.

---

## 0. IDENTIDAD, POSICIÓN REAL DEL PROYECTO Y URLS PARA RETOMAR

| Identificador | Estado verificado 20-OCT-2026 |
|---|---|
| Repositorio | [mezas3238-hue/qore-core](https://github.com/mezas3238-hue/qore-core) |
| Rama de ESTE método, no confundir con otros traders | `agent/vt08-crt-pure-source-identity-001` |
| [PR #626 — VT08 CRT PURE](https://github.com/mezas3238-hue/qore-core/pull/626) | **OPEN, DRAFT, UNMERGED; 0 reviews nativas GitHub** |
| Base del PR | `agent/vt08-crt-cognitive-architecture-freeze-001`; NO asumir `main` |
| Último HEAD ANTES de publicar este handoff | `6185abdada44f6c0c6af35c089381977fd83c330` |
| CI en ese HEAD | [QORE VT08 CRT PURE Cognitive Gate #39097058762](https://github.com/mezas3238-hue/qore-core/actions/runs/39097058762), **SUCCESS**, Ruff / mypy / **159 pytest PASS** |
| Último CI específico Atlas G2/G7/R10 | [Actions #39096884947](https://github.com/mezas3238-hue/qore-core/actions/runs/39096884947), **SUCCESS 3/3**, Ruff / mypy / **77 tests PASS** + AUDUSD/USDJPY originales |
| G-M1 / G-M2 / G-M3 / G-M4 | **PARTIAL / PARTIAL / PARTIAL / PARTIAL** |
| G-M5 metodología/cognitiva | **NOT ISSUED** |
| GLOBAL económico | **NOT CERTIFIED** |
| Capital/ejecución | **NOT AUTHORIZED**, 0 sizing VT08, sin operaciones |

**Lectura obligatoria en este orden:**
1. **Este handoff R1–R10** y [handoff histórico con anexos profundos](VT08_CRT_HANDOFF_MAESTRO_TRANSFERENCIA_INTEGRAL_2026-10-15.md), que contiene ~68 KB de investigación detallada.
2. [Orden tri-fuente del Owner](VT08_CRT_OWNER_TRES_FUENTES_CAMBIO_MANDATO_2026-10-15.md) y [dossier G1–G7](VT08_CRT_GM1_SEVEN_RULES_REVIEW_DOSSIER_2026-10-15.md).
3. [Informe técnico R9 — los 36 casos y política G7](VT08_CRT_R9_G2_G7_ADJUDICATION_READY_36_BLIND_REAL_ATLAS_2026-10-17.md) y [R10 — guardias SHA y revisiones humanas](VT08_CRT_R10_36_BLIND_REVIEW_GUARD_REAL_ATLAS_VERIFIED_2026-10-18.md).
4. [R5–R6 raíz de 108 WAIT y cinco UNKNOWN](VT08_CRT_R5_R6_ROOT_CAUSE_REAL_ATLAS_AND_CERTIFICATION_BLOCKERS_2026-10-15.md), [R7 calendario NY-DST](VT08_CRT_R7_FX_WEEKLY_CLOSE_REAL_ATLAS_VERIFIED_2026-10-16.md) y [R8 custodia productor original](VT08_CRT_R8_ORIGINAL_PRODUCER_SHA_QUALITY_GAPS_VERIFIED_2026-10-16.md).
5. Actas anteriores [13-OCT](VT08-CRT-PURE-MASTER-HANDOFF-2026-10-13.md), [14-OCT](VT08_CRT_PURE_HANDOFF_MAESTRO_INTEGRAL_DOBLE_CERTIFICACION_2026-10-14.md) para evitar repetir investigaciones históricas R1/R2/N.

**Advertencia esencial:** hay otra línea VT08 de TTrades/5M y trabajos de VT31 en el mismo repositorio, además de otras ramas de VT08. **NO fusionar métricas, umbrales, reglas ni certificaciones entre traders.** Este handoff concierne exclusivamente a **VT08 CRT PURE de tres fuentes, PR #626**.

---

## 1. LA MISIÓN ORIGINAL, CAMBIO DEL OWNER Y LÍMITES DEL MÉTODO

- Diseñar un CRT QORE de tres fuentes, formalizado de forma **causal / point-in-time (PIT)**: identificar contexto H4, elegir referencia, confirmar en M15, vetar contradicciones, registrar destino/invalidación, memoria y nueva hipótesis sin mirar la vela futura.
- Fuentes autorizadas: **RomeoTPT**, [Model #1](https://www.youtube.com/watch?v=UUq_wKQ61Wo) y [old CRTH](https://t.me/s/officialRomeotpt/6615); **SpeculatorFL**, [CRT](https://threadreaderapp.com/thread/1784493604473618604.html) y [confirmaciones](https://threadreaderapp.com/scrolly/1794311615535518154); **TraderFlameseN**, [CRT best candle](https://threadreaderapp.com/thread/1790141530461622525.html).
- Lo textual del autor se etiqueta **SOURCE_SUPPORTED** con localizador preciso. Los detalles formales propuestos por QORE se etiquetan **QORE_ENGINEERING**, hasta validación real. Textos SpeculatorFL/TraderFlameseN comparten similitudes y NO equivalen a dos validaciones económicas independientes.
- No imponer a toda familia CRT un veto Romeo-only de old CRTH, pero **tampoco** otorgar automáticamente legitimidad a niveles H4 inventados. G-M1 exige los siete artículos, revisión independiente y acta Owner.
- Certificación dual: **G-M1…G-M5** metodología/cognitiva y **E0…E11** GLOBAL económico; ambos, no únicamente uno. Un pipeline CI exitoso significa ingeniería reproducible, no metodología aprobada, capacidad predictiva ni rentabilidad.

### Siete contratos de G-M1 (QORE ENGINEERING DRAFT, sin aprobación)

| Gate | Norma pendiente de adopción | Prueba falsadora |
|---|---|---|
| **G1: elegibilidad referencia** | Dos H4 C1/C2 completas; sweep unilateral de C1 en C2 y cierre interior, identidad SHA/reloj | sweep doble, cierre fuera, M5 incompleta, vela futura: ABSTAIN/UNKNOWN |
| **G2: prioridad multirreferencia** | Identificar viejos CRTH/CRTL elegibles PIT; C1 adyacente es *comparador V3*, no regla autoral universal; conflicto sin prioridad: WAIT/ABSTAIN | 36 casos con C0/C1 candidatos, inventario no exhaustivo |
| **G3: H4→M15 temporalidad** | H4 parent vs M15 hija con 3 M5 por M15 cerradas antes de decidir; no reversal oportunista | mutar M15 futuras no cambia decisión pasada |
| **G4: confirmación entrada conceptual** | Proxy V3 triple M15 REF/SOURCE/CONFIRM; sweep y reclaim de SOURCE, body CONFIRM cruzando SOURCE.open | wick insuficiente, tercera vela no cerrada o contradicción: no-confirm |
| **G5: invalidación/expiración** | Wick extremo M15 SOURCE como estructura congelada; invalidación antes de señal: ABSTAIN; después: KILLED; expiry delimitado sin precio inventado | entrada ya invalidada, evento intrabar ambiguo, sesión cerrada, falta M5 |
| **G6: destino/lifecycle** | Midpoint H4 C1 disponible al reloj y no consumido antes; primer toque de wick ≠ ejecución/fill | DOL anterior ya tocado o por detrás: no reutilizar |
| **G7: conflicto, memoria y rearm** | Un evento/hipótesis por H4; nueva fuente/cadena causal para rearm; veto a mismo parent/source por conveniencia | cinco UNKNOWN, 108 WAIT; política ALL-PRIOR vs lineage sin resolver |

**Pendencia transversal:** zona horaria de H4 UTC `00/04/08/12/16/20` es convención de QORE de investigación, no norma inmutable del autor ni calendario autenticado del broker.

---

## 2. DATOS, UNIVERSO, CUSTODIA, LIMITACIONES NO NEGOCIABLES

### Source y población verdaderamente comprobados

- Productor fuente **CIBO Atlas 10Y windowed** commit `ab782b8e9f890f86a2b6500070f0556b4b685e3d`; [run original #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458). Adaptador fail-closed `src/qore/infrastructure/trader_lab/vt08_crt_pure_original_atlas_reader.py` comprueba simbolización, UTC, manifests anuales, hashes y continuidad; no es una fuente BID/ASK.
- AUDUSD **148.171 M5** + USDJPY **148.201 M5** = **296.372 M5** originales. Ventana vista ~septiembre 2024–septiembre 2026. **Totalmente CONSUMIDA** para investigación, desarrollo y falsación; NUNCA nueva OOS virgen.
- Censo H4 C1/C2 completas **5.524** = AUDUSD **2.738** y USDJPY **2.786**; `1.734` cumplen barrido/reclaim parent estructural; 1.109 descartados en el análisis V3 por destino ya consumido.
- BTCUSD continúa **FROZEN**. Otros 33 activos/periodos M1/M5 del QORE Native/Trader Lab no son automáticamente validación VT08 ni precio ejecutable del broker. La certificación GLOBAL general heredada exige BTCUSD / tres mercados: necesita decisión **explícita** de alcance Owner+Risk, sin cambiar flags falsos.
- M5 OHLC relativo puede diagnosticar trayectoria y wick touch, **no** precisión intrabar tick, BID/ASK, comisiones, spread, slippage, fill, profit factor neto ni DD de cuenta. Los huecos no se rellenan.

### DATA VAULT P0 — Originales no están custodiados de forma permanente

**Verificado por GitHub API 20-OCT-2026:**
- AUDUSD artifact **#10475697610**, run `35166210458`, ZIP SHA256 `ac72aaf438c164cd79691a7cf1f3f0a68f4c65aa6a91a921a721c7a04ebdc2f0`.
- USDJPY artifact **#10475389415**, mismo run, ZIP SHA256 `e3ac9a45f3000c3e3bd93e50c730c952ddd08f77f1c857b5c4b3a67679fcaa51`.
- Ambos `expired=false` a la consulta; **expiran 16-DIC-2026 00:21:18 UTC**. NO confiar en este vencimiento para otros datasets M15/M3/M1; [issue #837](https://github.com/mezas3238-hue/qore-core/issues/837) abarca más conjuntos y riesgos independientes.
- **No se ha verificado backup privado duradero ni restore**. Hacer inventario completo de 33xM5/33xM1 y demás fuentes si pertenecen al alcance QORE, licencia y permisos; alojar solo en storage privado aprobado, manifest SHA/size/run/artifact/source/UTC/broker y probar restore independiente, marcar propietario/caducidad y credenciales de acceso. **No subir raw licenciados al Git, no VPS, no pagos automáticos.**

---

## 3. HISTORIA COMPLETA REALIZADA: TRABAJO LEGACY, V1–V3, G-M3 Y G-M4

### Programa anterior 13–14 OCT / R1–R2 / familia N (CONSERVAR, NO RECICLAR EDGE)

- Reconstruidos contextos CRT H4/M15/M5, R1/R2 y variantes AO/BE/BM/CC/CD con investigación de densidad y fallos de percepción. Los números exploratorios de estas familias **no son comparables** a V1/V2/V3 ni certifican CRT tri-fuente.
- Hallazgo **grave R2-BM**: ante TP y SL tocados en la misma M15 se aplicó en una implementación TP_FIRST, inflando PF bruto (~**1,119** frente a ~**1,019** bajo corrección conservadora; con coste hipotético 0,02R ~**0,976**). Corrección: **STOP_FIRST** si no puede reconstruirse orden intrabar; preferir ticks reales. **No usar esos 1R/costes legacy ni introducir sizing en VT08 actual**; se citan como advertencia histórica de falsación, NO técnica de certificación.
- R2-CC AUDUSD PF exploratorio ~1,074 y R2-CD USDJPY ~1,012; costes hipotéticos/otras identidades, edge no confirmado. No sumarlos a resultados CRT PURE.
- Forenses N1/N2/N3: 939 geometrías anidadas y 2.634 diagnósticos N3; NO trades ejecutables y temas abiertos en duración de fuente, oposición HTF/LTF, confirmación, PD arrays.
- G-M2 baseline **48 first-look** (24+24), **96 SVG**, H4 C1/C2 + M15 prefijo, sin desenlace; [run #38706589343](https://github.com/mezas3238-hue/qore-core/actions/runs/38706589343). No hay dictámenes humanos. 48/48 WAIT/ABSTAIN en pruebas de seguridad **no** es 48 predicciones correctas. Caso "blind" separado por archivo NO garantiza embargo del futuro a quien tenga acceso GitHub.

### Experimentos de tres fuentes PRE-REGISTRADOS, CONGELADOS, mismo histórico DEV

| Versión | Metodología QORE propuesta | Fuente conceptual | Resultado de precio postdecisión | Veredicto real |
|---|---|---:|---|---|
| **V1** | H4 C1/C2 sweep/reclaim + primera pareja M15 de C3 + DOL midpoint | **54** (31 AUDUSD / 23 USDJPY) | principalmente censo/densidad | Demasiado restrictiva, NO edge |
| **V2** | Nested micro CRT a lo largo de C3, primer evento por padre, midpoint no consumido | **745** (353 / 392) | **115 DOL primero, 538 invalidez primero, 2 simultáneos misma M5, 57 expiry, 6 expiry de cierre, 27 UNKNOWN** | Diagnóstico de trayectoria ADVERSO; no support económico |
| **V3** | Tercera M15 CONFIRM cerrada; body-cross SOURCE.open; invalidación extrema wick SOURCE; midpoint | **139** (61 / 78) | **23 DOL primero, 69 invalidez primero, 42 expired, 5 UNKNOWN** | Trayectoria ADVERSA; no PF ni fills, V3 NO rentable demostrada |

**Nunca** retunear V2/V3 sobre las mismas velas y luego llamar el resultado OOS. V2 se propuso con V1 ya visto; V3 con V2 ya visto; cada preregistro precedía su PROPIO replay, pero TODOS son desarrollo sobre el histórico ya consumido.

**Runs y archivos:**
- V1 [#38710923324](https://github.com/mezas3238-hue/qore-core/actions/runs/38710923324); prereg `docs/research/VT08_CRT_3_FUENTES_QORE_V1_PREREG_2026-10-15.md`; código `src/qore/infrastructure/trader_lab/vt08_crt_three_source_candidate_v1.py` y `vt08_crt_three_source_v1_full_h4_census.py`.
- V2 censo [#38711787794](https://github.com/mezas3238-hue/qore-core/actions/runs/38711787794), lifecycle [#38713036976](https://github.com/mezas3238-hue/qore-core/actions/runs/38713036976); `vt08_crt_three_source_v2_full_h4_census.py`, `vt08_crt_three_source_v2_price_lifecycle.py`; informe `VT08_CRT_THREE_SOURCE_V2_PRICE_LIFECYCLE_FALSATION_2026-10-15.md`.
- V3 censo [#38749028744](https://github.com/mezas3238-hue/qore-core/actions/runs/38749028744), trayectoria [#38749761117](https://github.com/mezas3238-hue/qore-core/actions/runs/38749761117); `vt08_crt_three_source_v3_confirmed_h4_census.py`, `vt08_crt_three_source_v3_price_lifecycle.py`; informe `VT08_CRT_THREE_SOURCE_V3_CONFIRMED_139_CAUSAL_FALSATION_2026-10-15.md`.

### G-M3: cognición causal en casos originales

- Módulos `src/qore/infrastructure/traders/crt_pure_cognitive_state.py`, `crt_pure_cognitive_contract.py` y `src/qore/infrastructure/trader_lab/vt08_crt_three_source_v3_gm3_cognitive_replay.py`.
- [CI #38750815066](https://github.com/mezas3238-hue/qore-core/actions/runs/38750815066), original 139/139 señales geométricas V3 **RECONOCIDAS**. `reason()` devuelve 139/139 **ABSTAIN** por fuente/metodología todavía abierta, 0 EXECUTE. Positivo para integridad/no futuro y veto; NO demuestra precisión real, excelencia cognitiva ni edge.
- G-M3 PARTIAL: faltan juicio humano independiente, errores bajo incertidumbre, contratesis, causalidad entre eventos, memoria G7 y razones contrastadas.

### G-M4: pipeline fuente→cognición→router→lifecycle, SOLO investigación

- Implementación `src/qore/infrastructure/trader_lab/vt08_crt_three_source_v3_gm4_lifecycle.py` y tests homónimos; [CI #38763192649](https://github.com/mezas3238-hue/qore-core/actions/runs/38763192649) 3/3 SUCCESS.
- 139/139 identidad/clock/market/dirección source→cognition→router; 139/139 ABSTAIN en router, NO operaciones. **134 terminales observados (59 AUDUSD / 75 USDJPY)** y **5 UNKNOWN** (2 AUDUSD / 3 USDJPY). Outcome conceptual: **23 DOL primero, 69 invalidación primero, 42 expiración**, 5 censurados.
- Estados `OBSERVED_EVENT→HYPOTHESIS_FORMING→AWAITING_CONFIRMATION→CONFIRMED`, después invalidación/consumo/expiración causal. **UNKNOWN no se transforma en KILLED automático ni en trade vivo**. Falta integración/atestado conceptual externo de Risk/CIBO, resolución metodológica de censura y aprobación humana. G-M4 PARTIAL.

---

## 4. RELEVOS TÉCNICOS R3–R10 (HECHOS, EVIDENCIA CI, CAMBIOS)

| Etapa | Trabajo realizado y evidencia | Qué quedó abierto |
|---|---|---|
| **R3 (15-OCT)** | Auditoría de cobertura CI y contratos de fuente G2/G7: `src/qore/infrastructure/traders/crt_pure_gm1_g2_g7_causal_audit.py`; censura PIT de fuentes y veto a rearm; suite enfocada amplia, [quality #38802896904](https://github.com/mezas3238-hue/qore-core/actions/runs/38802896904) 159 tests PASS (baseline de esa rama). | Referencias old-CRT no exhaustivas, G7 ledger runtime no autenticado; verdicts PROVISIONAL/WAIT NO son permisos. |
| **R4 (15-OCT)** | Pre-registro y puente **Atlas real** `vt08_crt_g2_g7_real_atlas_pit_bridge.py`, workflow dedicado, 16 adversariales, [#38802320161](https://github.com/mezas3238-hue/qore-core/actions/runs/38802320161) 3/3 SUCCESS, 139 V3; C0 rival **36** (AUD 16, JPY 20), 14 opuestos/22 iguales; G2 139 WAIT por inventario incompleto; G7 31 PROVISIONAL/108 WAIT. | Otras referencias H4 aparte de C0/C1; G2 no adjudicado; 31 PROVISIONAL **no autorización**. |
| **R5 (15-OCT)** | Diagnóstico estrictamente ex-post de G7: **108/108 WAIT asociados a UNKNOWN previos**, 0 explicables solo por terminal futuro finalmente observado; 184 menciones UNKNOWN censurados repetidas, **no 184 casos diferentes**. [#38819759238](https://github.com/mezas3238-hue/qore-core/actions/runs/38819759238) SUCCESS, 20 tests. Caso G2 C0/C1/C2 causal sin C3 futuro. | Política `GLOBAL_ALL_PRIOR_TERMINAL` propaga unos pocos UNKNOWN a todas las fuentes posteriores. No se puede cambiar con hindsight. |
| **R6 (15-OCT)** | Forense `vt08_crt_gm4_unknown_root_forensics.py` clasifica cinco UNKNOWN, reproduce entradas incompatibles con invalidación y huecos M5. [#38820419577](https://github.com/mezas3238-hue/qore-core/actions/runs/38820419577) 28 PASS + 2 markets. R6-B identifica clocks/source IDs [#38820840827](https://github.com/mezas3238-hue/qore-core/actions/runs/38820840827) SUCCESS. | **2 open M5 ya más allá de invalidación, 3 huecos M5**. NO cambiar G-M4, NO inventar terminal. |
| **R7 (16-OCT)** | Auditor NY-DST `vt08_crt_original_fx_weekly_close_forensics.py`: en ambos viernes conflictivos **17/17** semanas vecinas siguen 17:00 ET cutoff en M5. USDJPY miércoles 22:30Z es un hueco aislado. [#38902464494](https://github.com/mezas3238-hue/qore-core/actions/runs/38902464494) 35 PASS + 2 markets. | Patrón de horario NO certifica schedule histórico del broker/cuenta/símbolo; G-M4 queda UNKNOWN. |
| **R8 (16-OCT)** | Auditor `vt08_crt_original_atlas_quality_gap_custody.py`: tres huecos figuran EXACTAMENTE en `DATA_QUALITY_LEDGER/{year}.jsonl` original SHA-backed del productor, no introducidos por replay. [#38975246782](https://github.com/mezas3238-hue/qore-core/actions/runs/38975246782) 43 PASS + 2 markets. | Dos weekends 576 M5 calendario cada uno; una M5 aislada sin OHLC; producer `market_open_expected=null`; falta broker source/custodia. |
| **R9 (17-OCT)** | `vt08_crt_g2_independent_blind_review.py`: arregla fuga de etiquetas del motor en antiguo "blind pack". Emite **36 reviewer-only** sin engine directions/source IDs y **sealed engine labels** por separado, IDs+SHA y 36 plantillas NULL. [#39037416479](https://github.com/mezas3238-hue/qore-core/actions/runs/39037416479), 56 PASS + original 2 markets. | Dos ZIP distintos comparten acceso GitHub (NO un embargo real); 0 reviewers / dictámenes. |
| **R10 (18-OCT)** | `vt08_crt_g2_human_response_guard.py` valida 36 respuestas SHA-bound, identidad del caso, cinco opciones, localizador fuente/QORE_ENGINEERING/SOURCE_GAP, razón causal, counterexample y denegación de flags de aprobación falsos; [#39096884947](https://github.com/mezas3238-hue/qore-core/actions/runs/39096884947) 77 PASS + original ambos. **36/36 respuestas auténticas siguen vacías**. [CI focused HEAD #39097058762](https://github.com/mezas3238-hue/qore-core/actions/runs/39097058762) 159 PASS. | Validación estructural NO autentica personas ni confirma contenido metodológico. Verificador GitHub R1 existente debe usarse desde entorno protegido, PR 0 reviews. |

**Por qué CI verde ≠ certificado:** Ruff/mypy/pytest confirman ciertas invariantes de fuente, timestamps y reglas de seguridad; no confirman autoría metodológica, reviewer genuino, orden de fill, rentabilidad ni validez estadística de datos nuevos. No usar `159 PASS` como `G-M5 PASS`.

---

## 5. CINCO UNKNOWN EXACTOS: UNA RUTA DE REPARACIÓN POR CASO

Todos son source V3, NO trades. IDs/clocks registrados en [forense R5–R6](VT08_CRT_R5_R6_ROOT_CAUSE_REAL_ATLAS_AND_CERTIFICATION_BLOCKERS_2026-10-15.md), [R7](VT08_CRT_R7_FX_WEEKLY_CLOSE_REAL_ATLAS_VERIFIED_2026-10-16.md) y [R8](VT08_CRT_R8_ORIGINAL_PRODUCER_SHA_QUALITY_GAPS_VERIFIED_2026-10-16.md).

| Mercado | Source event ID | Decisión UTC | Diagnóstico forense INMUTABLE | Resolución EXIGIBLE |
|---|---|---|---|---|
| **AUDUSD** | `bfc66b2457f3e3ec93ae` | 2025-04-25 20:45 | Primera falta viernes **2025-04-25 21:00Z**; 576 M5 slots hasta domingo 2025-04-27 21:00Z; R7 **17/17** viernes similares; productor SHA confirmado. | Verificar schedule histórico broker/símbolo y adjudicar política expiración fin de semana, sin inventar precio ni reetiquetar pasado. |
| **AUDUSD** | `fa3965fd21bc149c2ce8` | 2026-08-06 21:00 | M5 open ALREADY_BEYOND_INVALIDATION (no viable desde inicio). | Regla cognitiva de no-viabilidad `ABSTAIN` fundada y revisada por Owner/auditor; nunca modelar fill ni terminal ex-post. |
| **USDJPY** | `9572d855b2dedc8fecb2` | 2024-12-26 23:00 | M5 open ALREADY_BEYOND_INVALIDATION. | Igual que anterior, una abstención conceptual requiere versión/acta PRE-OOS. |
| **USDJPY** | `11a7c3cdb30a9eabdbbe` | 2025-02-12 21:30 | ÚNICA M5 faltante **miércoles 2025-02-12 22:30Z**; 22:25 y 22:35 existen, ledger productor SHA identifica **1 slot**. | Recuperar OHLC **mismo origen y provenance verificables** o **permanecer censurado**. Registro de calidad no contiene OHLC; no interpolar ni copiar otro feed. |
| **USDJPY** | `a63b7073af8d33e8963a` | 2026-06-19 20:45 | Primera falta viernes **2026-06-19 21:00Z**; 576 slots hasta domingo 2026-06-21 21:00Z; R7 17/17; calidad productor original. | Schedule broker autenticado + regla expiry/adjudicación G5/G7. |

**R8 evidencia de origen en SHA:** anual calidad AUDUSD 2025 `48ffebed4c26cc420dd1d56d75d03e6debd7d586ed03ef5d16e7f0e198b1895e`; USDJPY 2025 `b3d1eba7c9a4a2cdee29bc7514169c6d5b65d1c42c379c1433fe891b779d671f`; USDJPY 2026 `5a44d978efbc7c8d7e258b611b6770c997ea87637e709e4ae3db3b0b3dcbce0e`. El productor etiquetó los 3 gaps `UNRESOLVED_CLOSURE_OR_MISSING_DATA` y `market_open_expected=null`, NO opening o cierre certificado del broker.

**Consecuencia G7:** 5 UNKNOWN originales no terminados provocan **108 G7 WAIT** posteriores bajo regla research `GLOBAL_ALL_PRIOR_TERMINAL` (AUDUSD 43 y USDJPY 65), **31 `PROVISIONAL`** sin autoridad. No desbloquear esos 108 con un `terminal=true` ficticio; tampoco tratar como 108 errores independientes. Fallo semántico profundo: política de memoria de TODO EL MERCADO puede no corresponder al concepto de REARM de una misma fuente/lineage. Resolver artículo G7 sin consultar quién tuvo ganancias.

---

## 6. G2 Y G-M2: EJECUCIÓN REAL DE REVISIÓN CIEGA PENDIENTE

### G2 paquete de 36 contradicciones H4, R9/R10

- C0 competidor vs C1 principal: **36** (AUDUSD **16**, USDJPY **20**), **14 OPPOSITE**, **22 SAME**. Estos son solo rivales *observados* C0/C1, **NO un inventario exhaustivo** de old CRTH/CRTL. En 139 V3 G2 permanece **WAIT** con `inventory_complete=false`.
- **Enviar SOLO** `g2-reviewer-only-no-engine-labels.jsonl` y `g2-blank-human-review-responses.jsonl` + `g2-independent-human-response-readiness-R10.json`. Cada caso tiene C0/C1/C2 H4 ya cerrados, reloj, ID SHA, 5 opciones: `C0`, `C1`, `BOTH_AMBIGUOUS`, `NEITHER_VALID`, `INSUFFICIENT_SOURCE`. Revisor debe poner localizador de fuente, explicación causal y contraejemplo, sin observar C3/outcomes/engine label.
- Paquetes REVIEWER ONLY del último R10:
  - **AUDUSD:** [artifact #12125231326](https://github.com/mezas3238-hue/qore-core/actions/runs/39096884947/artifacts/12125231326), SHA ZIP `c3bef18cc39479ec87f18fc03facd3aa317b013d7078c23f6500c5b627ccdc31`.
  - **USDJPY:** [artifact #12124797767](https://github.com/mezas3238-hue/qore-core/actions/runs/39096884947/artifacts/12124797767), SHA ZIP `583bdd6c11e94cd167535421ca5c537bd7c64b550c591c094d12ab249e5f4948`.
- **NO ENTREGAR AL REVIEWER:** artifact SEALED engine AUDUSD `12125385879`, USDJPY `12125101905`; los full research ledgers también revelan engine labels. Todos los ZIP R10 expiran nominalmente **2027-01-16 04:22:50 UTC**. **Separación de ZIP ≠ aislamiento de accesos GitHub**; hace falta proceso/personas con control de no exposición real, idealmente storage segregado.
- **VERDAD VERIFICADA:** no hay ninguna respuesta humana auténtica en R10; **16/16 y 20/20 NOT READY**. Aun 36 respuestas sintéticas "completas" no prueban método ni autorizan gate.

### G-M2 48 first-look

- Paquetes neutros previos: **48 casos (24 AUDUSD+24 USDJPY)**, 96 SVG; [CI #38706589343](https://github.com/mezas3238-hue/qore-core/actions/runs/38706589343); sin revisor humano (0). Mantener futuro sellado y C3 oculto hasta dictámenes independientes; reviewer informa tesis/contratesis, WAIT/ABSTAIN/confirmación, niveles, justificación. Controlar independencia e historial de acceso.
- G2 36 H4 conflictos **≠** G-M2 48 first-look. Se requieren AMBOS; tampoco los 139 eventos V3 son 139 dictámenes independientes.

---

## 7. G7 Y REGISTRO DE IDENTIDAD: QUÉ DEBE DECIDIR LA AUTORIDAD DE FUENTE

**A. `GLOBAL_ALL_PRIOR_TERMINAL` (vigente solo en audit research):** exige que TODAS las hipótesis anteriores del mismo mercado terminen antes de nueva fuente; por eso cinco UNKNOWN bloquean posteriores. Conveniente para seguridad conservadora pero causa veto permanente de eventos causalmente distintos.

**B. `LINEAGE_SCOPED_CAUSAL_REARM` (alternativa SOLO PROPOSAL):** reinicio únicamente de la familia/parent realmente relacionado; exige cerrar hipótesis del MISMO lineage y prueba positiva de fuente nueva e independiente. No es fuente homologada ni autorizada por código actual.

**C. `ABSTAIN_UNKNOWN_UNTIL_SOURCE`:** default WAIT para historia dudosa sin política firmada, sin cierre/fill artificioso.

**Decisión obligatoria ANTES de nuevo OOS:** Owner y revisor independiente examinan fuentes y casos adversariales, registran artículo G7 exacto versionado, delimitan parent_id, source_event_id, hypothesis_id, event_generation, clocks y terminal observado; determinan cuándo nace un NUEVO parent H4 y cuándo es rearm de la MISMA tesis. Prohibir rehash artificial de event ID y repetir misma triple tras una pérdida. Ejecutar comparadores metodológicos en datos no dependientes de PnL y congelar criterios antes de la muestra económica.

**NO** ejecutar backtest selectivo de B sobre Atlas consumido y elegirlo porque aumenta densidad o PF. Reglas G5 invalidación por inicio fuera de barrera y cierre semanal deben resolverse junto a G7.

---

## 8. SEGURIDAD DE APROBACIÓN G-M1, REVISIÓN REAL Y NO SELF-ATTESTATION

**Existe verificador nativo GitHub R1, NO sustituir:**
- `src/qore/infrastructure/traders/crt_pure_gm1_external_review.py` y tests `tests/infrastructure/traders/test_crt_pure_gm1_external_review.py`; [dossier de funcionamiento](VT08_CRT_GM1_EXTERNAL_GITHUB_REVIEW_VERIFIER_R1_2026-10-15.md).
- Requiere **GITHUB_TOKEN, VT08_TRUSTED_OWNER_ID, VT08_TRUSTED_REVIEWER_ID** desde entorno protegido FUERA del PR. Hace GET live a PR #626, GitHub reviews, comments, commits y SHA exacto del dossier; comprueba independencia de reviewer respecto Owner/PR author/commits, cronología, head SHA, digest, última review APPROVED, texto exacto y comentario posterior Owner, ausencia de CHANGES_REQUESTED tardío, head no movido.
- Patrón nativo de firma ya propuesto: `VT08-GM1-REVIEW-V1 HEAD=<40hex> DOC_SHA256=<64hex>` y `VT08-GM1-OWNER-V1 HEAD=<40hex> DOC_SHA256=<64hex>`. **No fabricar firmas ni ejecutar código PR no confiable con secrets de cuentas protegidas**. Auditor debe ser persona distinta, idónea y no implementadora.
- Incluso `authenticated_witness=true` solo atestigua *procedencia de la revisión*; el verificador R1 deliberadamente devuelve `gm1_pass=false`, `gm5_issued=false`, `capital_authorized=false`. **Siete reglas deben ser adjudicadas individualmente**, con contenido verificable y propiedad de riesgo independiente.
- Campos heredados `independent_adjudicator`, `owner_approval_id`, booleanos `no_future_leak_attested` o `G_Mx_PASS=true` **no constituyen firmas**. Tests con fixtures de reviews sintéticos NO acreditan acciones GitHub reales.
- PR #626: verificación **20-OCT-2026: 0 reviews GitHub**. No dar por aprobada G-M1 en esta rama. Issue [#976](https://github.com/mezas3238-hue/qore-core/issues/976).

---

## 9. GATES PENDIENTES CON PRUEBA DE CIERRE Y RESPONSABLE

| Gate | ESTADO | Responsabilidad y Definition of Done REAL |
|---|---|---|
| **G-M1** | PARTIAL | Owner + metodólogo externo revisan G1…G7 con fuentes triad/localizadores, positivos/negativos/contraejemplos, SHA de regla y revisor GitHub auténtico; resolver G2/G7/expiración, no solo checklist. |
| **G-M2** | PARTIAL | 48 first-look adjudicados antes de abrir futuro + casos R9 G2 si aplica, reviewer independiente, contradicción y error por categoría, custodia de blind verdadera. |
| **G-M3** | PARTIAL | Cognición predice decisiones razonadas frente a truth humana ciega, con WHY/WAIT/ABSTAIN, falsaciones, metacognición, eventos y clocks; 139/139 reconocimiento autoetiquetado insuficiente. |
| **G-M4** | PARTIAL | Reconciliación fuente→cognition→router→lifecycle con 5 UNKNOWN preservados hasta resolución válida o censura explícita, política aprobada, pruebas adversariales e interfaz conceptual Risk/CIBO autenticada. No órdenes. |
| **G-M5** | NOT ISSUED | Solo tras G-M1..G-M4 **PASS reales con evidencia firmada** y gating que no acepte flags autoemitidos. G-M5 solo método, sin capital. |
| **E0** Identidad económica | OPEN | Owner/Risk congelan versión/familia, mercados y reglas causales, calendario y cumplimiento de muestra nueva. |
| **E1** Fuente ejecutable/costes | OPEN | BID/ASK broker PIT/ticks/quotes, spread, comisión, swap/fees, slippage, reglas fill intrabar sin sesgo, mapeo instrumentos. |
| **E2** PF net / expectancy | NOT EVALUATED | Ledger económicamente ejecutable con muestra e incertidumbre por par/año; no wick touch→fill. |
| **E3** DD patrimonial | NOT EVALUATED | CIBO/QORE Risk exclusivamente; VT08 no calcula sizing ni notional/1R fijo. |
| **E4** Sharpe / Sortino | NOT EVALUATED | Series netas realizables, horizonte/frecuencia/MAR y significancia definidos PRE-OOS por Risk. |
| **E5** OOS nuevo virgen | OPEN | Fuente y ventana con acceso sellado, fuera 2024–26 consumido; embargo y certificación de no exposición. |
| **E6** WFO / embargo | OPEN | Folds temporales, purging y prevención leakage/no refit. |
| **E7** Stress | OPEN | Costes, gaps, DST, news/regímenes, spreads, asincronía, same-bar uncertainty. |
| **E8** Monte Carlo | OPEN | Block/bootstrap por dependencia/regímenes con criterios previos. |
| **E9** Base/multiplicidad | OPEN | Baselines, sesgo de selección y múltiples ensayos V1→V3, incertidumbre. |
| **E10** Risk/revisor global | OPEN | Informe independiente Risk/CIBO de resultados y autoridad de alcance BTCUSD. |
| **E11** Certificación GLOBAL | NOT CERTIFIED | Todos E0–E10 + G-M5 reales bajo identidad y controles antifalsificación. |
| Operativa | NO AUTORIZADA | No merge, broker/demo/live/VPS ni órdenes; VT08 sin sizing. |

**Umbrales PF/DD/Sharpe/Sortino no están firmados en este dossier**; no importar umbrales de otro VT08 (TTrades 5M) o QORE Alpha2. Selección y umbrales **antes** de nuevo OOS. La historia V2/V3 de trayectorias adversas supone un riesgo real de falta de edge; si no hay edge bajo reglas aprobadas, la respuesta correcta es **NO_SUPPORT**.

---

## 10. INVENTARIO DE PROBLEMAS/ERRORES Y RESOLUCIÓN CONCRETA PARA EL PRÓXIMO ARQUITECTO

| ID / severidad | Causa raíz comprobada o riesgo | Estado/acción exacta |
|---|---|---|
| **P01 histórico** | Romeo-only exigido indebidamente pese a tri-fuente autorizada | **CORREGIDO EN CONTRATO**; no reintroducir veto Romeo-only. Mantener origen textual incierto. |
| **P02 P0** | 7 artículos G1…G7 sin firma/semántica homologada | **ABIERTO #976**: acta Owner+auditor, SHA, pruebas + source attribution. |
| **P03 evidencia adversa** | V1 densidad conceptual 54 | Congelada; NO forzar densidad a posteriori. |
| **P04 falsación** | V2 115 DOL vs 538 invalidez; simultáneos M5 | Congelar; no declarar rentable ni cambiar SL/TP in-sample. |
| **P05 falsación** | V3 23 DOL vs 69 invalidez + 42 expiry | Congelar; estudiar nueva identidad PRE-OOS, no curve-fit. |
| **P06 P0** | 139 cogniciones repiten propio generador con `ABSTAIN`, no truth externa | G-M3 validar contra revisor realmente ciego y contratesis. |
| **P07 P0** | G-M4 5 UNKNOWN con 2 entradas no viables, 2 weekends, 1 M5 interno | **ABIERTO #988**; no inventar terminal; analizar item `5`. |
| **P08 P0** | G7 global all-prior-terminal propaga 5 UNKNOWN a 108 WAIT | **ABIERTO #985**; scope lineage vs global, resolver causalmente pre-OOS. |
| **P09 P0** | G2 C0/C1 sólo 36 de 139, no inventario PIT completo de old levels | **ABIERTO #985**; ampliar elegibilidad old-CRTH sin decidir por retorno. |
| **P10 P0** | 36 G2 human responses = NULL; 0 GitHub reviews | **ABIERTO #976**; revisor externo y Owner, R9/R10 SHA + firmas. |
| **P11 P0** | Falsa independencia: reviewer-only vs SEALED mismo GitHub ACL | Custodia real independiente; evidence of no sealed access, scope perms y revisión PRE-UNSEAL. |
| **P12 P0** | G-M2 48 casos / 96 SVG sin aprobación externa | Entregar FIRST-LOOK, recabar respuestas antes de abrir futuros. |
| **P13 corregido legacy** | R2-BM TP_FIRST same M15 infló PF exploratorio | Corrigió STOP_FIRST/reconocer ticks; nunca usar números iniciales para cert. |
| **P14 P0** | API de método acepta strings/flags de self-attestation sin identidad | Guardar firma live fuera PR; código legacy solo no basta. |
| **P15 P0** | M5 OHLC ≠ quote BID/ASK/broker ejecutable | Buscar fuente ejecutable licita y costes/fills reales, comparador neutral a sizing. |
| **P16 P0** | Atlas 2024–2026 consumido como DEV, V1→V3 vistos | Nuevo OOS realmente virgen con embargo, sin múltiples reformulaciones en test final. |
| **P17 P0** | Original artifacts caducan y no hay restore probado | **ABIERTO #837**: vault autorizado y restore SHA ANTES 2026-12-16, otros M1/M3 pueden expirar antes. |
| **P18 P0** | BTCUSD frozen pero readiness GLOBAL solicita 3 markets | Owner/Risk definen alcance, no falsificar `btcusd_history_verified`. |
| **P19 P1** | H4 UTC QORE, NY DST, sessions/PD arrays no homologados | Fuente broker histórica y semantics PIT, investigar sin usar futuro. |
| **P20 P1** | Mercado semanal: viernes 17 ET 17/17 pero quality `market_open_expected=null` | Firmar politica de sesión/expiración G5/G7 y probar calendario real, NO asumir broker certificado. |
| **P21 P1** | USDJPY 2025-02-12 22:30 falta en original ledger | Recuperar misma fuente/provenance con OHLC o censurar; NO interpolar. |
| **P22 P1** | Familias reaction/journey/confirmation y jerarquía no cerradas | Separar mecanismos causalmente y preregistrar IDENTIDAD NUEVA antes nuevo OOS. |
| **P23 P0** | CI PASS autointerpretado como certificación | Mantener G-M1..4 PARTIAL y economic OPEN, no promocionar verdicts por pipeline verde. |
| **P24 permanente** | Sizing o DD de VT08 compromete mandato Owner | **PROHIBICIÓN PERMANENTE**; CIBO Risk owner único. |
| **P25 frontera seguridad** | Derivaciones R9 reviewer packet muestran mercado/reloj y pueden cotejarse externamente | Ofuscación SHA no es anonimato perfecto; exigir independencia humana/acta no exposición. |

---

## 11. PLAN DE TAKEOVER PRIORIZADO — QUÉ HACER SIN PEDIR CONTEXTO AL OWNER O REPETIR LO YA HECHO

### P0 inmediato: custodia, revisión y la verdad contractual

**Paso 1.** Abrir PR #626 y su HEAD REAL; distinguir este repo/branch del VT08 TTrades y de VT31. Verificar que siga DRAFT, 0 merges, revisar últimos workflows y comentarios/issues. **No fusionar**.

**Paso 2.** [#837](https://github.com/mezas3238-hue/qore-core/issues/837): confirmar fecha expiry de cada artifact M5/M1/M3; aprobación para bóveda privada; backup SHA + restore en entorno separado. **No copiar raw por comodidad a repo público, ni decir “backed up” sin bytes restaurados y hash verificado**.

**Paso 3.** [#976](https://github.com/mezas3238-hue/qore-core/issues/976): entregar al metodólogo externo genuino los **36 reviewer-only** R10 sin sealed labels. Solicitar respuestas `C0/C1/BOTH_AMBIGUOUS/NEITHER_VALID/INSUFFICIENT_SOURCE`, localizador de fuente, WHY causal y contraejemplo; registrar independencia/permisos y cumplir validador R10. Este es un verdadero **BLOQUEO HUMANO EXTERNO** que ningún unit test puede saltar.

**Paso 4.** En paralelo, auditor+Owner adjudican siete contratos G1..G7 y sus casos adversariales, especialmente `G2` referencias old CRT y `G7` genealogía/terminal. Registrar por artículo SOURCE_SUPPORTED vs QORE_ENGINEERING, identidad de personas y hash de versión; firma nativa en GitHub vía verifier R1 protegido, **después** de congelar doc final. No instalar secretos en CI de rama no revisada.

**Paso 5.** [#988](https://github.com/mezas3238-hue/qore-core/issues/988): dos NO-VIABLE al open requieren política abstenerse; dos weekend necesitan schedule broker/expiry versionado; USDJPY miércoles exige mismo feed/hashes o censura. **Sin alterar 5 UNKNOWN originales V3/G-M4 ni inventar expiraciones.** Aceptar un método nuevo con nueva versión si se justifica antes OOS.

### P1 cognitiva y prueba de concepto científica

**Paso 6.** Revisiones independientes de 48 FIRST-LOOK G-M2 por un evaluador realmente sin acceso a sealed; registrar decisiones/conflictos y acta. No comparar con futuro hasta congelar respuestas.

**Paso 7.** Integrar método aprobado en G-M3, probar WHY, contratesis, conflicto HTF/LTF, event_generation/lineage y real-world WAIT/ABSTAIN, sin uso de resultado del futuro. Implementar **solo** política G7 legítima; adversariales para mismo parent, duplicate source, terminal no observado, C3 futuro, calendario, race/late update, older hypothesis.

**Paso 8.** Completar G-M4 fuente→cognitiva→router→Risk-boundary bajo contrato sin orders ni sizing, con trazas PIT y 5 casos censurados/evidencia recuperada. La transferencia a Risk es interfaz segura, no ejecución.

**Paso 9.** Revalidar G-M1..G-M4 contra reviewer independiente y hashes, emitir G-M5 **si y solo si** cuatro PASS auténticos; caso contrario mantener NOT ISSUED.

### P2 cert GLOBAL (obligatorio; sin ello no proclamar trader certificado)

**Paso 10.** Owner+Risk fijan alcance económico AUDUSD/USDJPY vs BTCUSD y umbrales previa muestra, nueva identidad CRT, ventanas OOS nunca consultadas, fuente BID/ASK PIT+costos/fills. NO usar 2024–2026 como nuevo holdout.

**Paso 11.** CIBO/Trader Lab ejecuta evaluación económica con PF neto, Sharpe/Sortino, WFO, stress, MC, comparadores/multiplicidad y revisión intermercado, **DD patrimonial y sizing exclusivamente CIBO Risk**. VT08 no modela volumen ni exposición ficticia. Si no supera: FAIL/NO_SUPPORT trazable y no tuning del mismo holdout.

**Paso 12.** Solo si G-M5 y E0…E11 PASS reales e independientes, pasar por proceso externo de autorización (fuera de este PR); no activar órdenes por mera CI.

### Cierre de cualquier ronda futura
Actualizar **este handoff + el original de anexos**, comentarios en [PR #626](https://github.com/mezas3238-hue/qore-core/pull/626), issues #976/#985/#988/#837, registrar HEAD exacto, run URL y conclusión, diferencias de fuente/versionado, artifacts ID/hash/expiry, casos/mercados, unknowns, reviewers y matriz Gates. La revisión humana sigue sin auto-sustitución.

---

## 12. REPRODUCIR SIN REESCRIBIR INVESTIGACIÓN

**Código central (en repo):**

| Función | Ruta |
|---|---|
| M5 original SHA loader | `src/qore/infrastructure/trader_lab/vt08_crt_pure_original_atlas_reader.py` |
| H4 V1 / sweep | `src/qore/infrastructure/trader_lab/vt08_crt_three_source_v1_full_h4_census.py` |
| V2 / path | `src/qore/infrastructure/trader_lab/vt08_crt_three_source_v2_full_h4_census.py`, `vt08_crt_three_source_v2_price_lifecycle.py` |
| V3 / price path | `src/qore/infrastructure/trader_lab/vt08_crt_three_source_v3_confirmed_h4_census.py`, `vt08_crt_three_source_v3_price_lifecycle.py` |
| G-M3 / G-M4 causal | `src/qore/infrastructure/trader_lab/vt08_crt_three_source_v3_gm3_cognitive_replay.py`, `vt08_crt_three_source_v3_gm4_lifecycle.py` |
| G2 G7 PIT real | `src/qore/infrastructure/trader_lab/vt08_crt_g2_g7_real_atlas_pit_bridge.py` |
| G7 pure verdicts | `src/qore/infrastructure/traders/crt_pure_gm1_g2_g7_causal_audit.py` |
| R6 causa UNKNOWN | `src/qore/infrastructure/trader_lab/vt08_crt_gm4_unknown_root_forensics.py` |
| R7 DST-weekly | `src/qore/infrastructure/trader_lab/vt08_crt_original_fx_weekly_close_forensics.py` |
| R8 hashes quality ledger | `src/qore/infrastructure/trader_lab/vt08_crt_original_atlas_quality_gap_custody.py` |
| R9 G2 reviewer-only/sealed | `src/qore/infrastructure/trader_lab/vt08_crt_g2_independent_blind_review.py` |
| R10 human response guard | `src/qore/infrastructure/trader_lab/vt08_crt_g2_human_response_guard.py` |
| Reviewer GitHub native R1 | `src/qore/infrastructure/traders/crt_pure_gm1_external_review.py` |
| Dossier G1–G7 | `docs/research/VT08_CRT_GM1_SEVEN_RULES_REVIEW_DOSSIER_2026-10-15.md` |
| Focused gate CI | `.github/workflows/vt08-crt-pure-cognitive-gate.yml` |
| Repro M5 G2/G7+R4…R10 | `.github/workflows/vt08-crt-g2-g7-real-atlas-pit-audit.yml` |
| G-M4 workflow | `.github/workflows/vt08-crt-three-source-v3-gm4-lifecycle.yml` |

**CI preferida sin descargar/cambiar fuentes:** ejecutar GitHub Actions workflow `vt08-crt-g2-g7-real-atlas-pit-audit.yml` en rama del PR con permisos read-only; `actions/download-artifact@v4` usa run original `35166210458` y matriz `AUDUSD, USDJPY`, comprueba manifests e identidad, imprime sumarios R4…R10, exporta SHA256SUMS por artifact. El workflow cognitivo gate ejecuta Ruff/mypy y 159 tests. **No modificar artifacts fuente ni checksums para pasar CI.**

En entorno autorizado si los originales ya están descargados de GitHub, solo ejemplo de lectura/diagnóstico sin crear órdenes:

```bash
python -m pip install -e '.[dev]'
python -m qore.infrastructure.trader_lab.vt08_crt_g2_g7_real_atlas_pit_bridge AUDUSD /ruta/atlas-original-sha-verified /ruta/salida-audusd
python -m qore.infrastructure.trader_lab.vt08_crt_g2_g7_real_atlas_pit_bridge USDJPY /ruta/atlas-original-sha-verified /ruta/salida-usdjpy
pytest -q --no-cov tests/infrastructure/trader_lab/test_vt08_crt_g2_human_response_guard.py tests/infrastructure/trader_lab/test_vt08_crt_g2_independent_blind_review.py
```

**Cuidado:** el script solo debe admitir el directorio original correcto del símbolo, previamente validado con SHA; no reutilizar una misma ruta para ambos sin el contenido correspondiente. Preferir Actions ya probado, nunca cargar código de rama no revisada con tokens privilegiados. Cualquier artifact `ENGINE SEALED` debe permanecer oculto del auditor hasta dictamen.

---

## 13. MATRIZ DE EVIDENCIA Y ENLACES DE CORTE / NO PERDER CONTEXTO

| Evidencia | URL Run |
|---|---|
| Original M5 10Y productores | [#35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458) |
| G-M2 first-look 48 | [#38706589343](https://github.com/mezas3238-hue/qore-core/actions/runs/38706589343) |
| V1 original 54 | [#38710923324](https://github.com/mezas3238-hue/qore-core/actions/runs/38710923324) |
| V2 745 + price | [#38711787794](https://github.com/mezas3238-hue/qore-core/actions/runs/38711787794), [#38713036976](https://github.com/mezas3238-hue/qore-core/actions/runs/38713036976) |
| V3 139 + price | [#38749028744](https://github.com/mezas3238-hue/qore-core/actions/runs/38749028744), [#38749761117](https://github.com/mezas3238-hue/qore-core/actions/runs/38749761117) |
| G-M3 recognition 139/139 | [#38750815066](https://github.com/mezas3238-hue/qore-core/actions/runs/38750815066) |
| G-M4 observed terminal 134 / UNKNOWN 5 | [#38763192649](https://github.com/mezas3238-hue/qore-core/actions/runs/38763192649) |
| R3 source audit/gate | [#38802896904](https://github.com/mezas3238-hue/qore-core/actions/runs/38802896904) |
| R4 G2/G7 PIT | [#38802320161](https://github.com/mezas3238-hue/qore-core/actions/runs/38802320161) |
| R5 G7 WAIT root | [#38819759238](https://github.com/mezas3238-hue/qore-core/actions/runs/38819759238) |
| R6 / exact unknowns | [#38820419577](https://github.com/mezas3238-hue/qore-core/actions/runs/38820419577), [#38820840827](https://github.com/mezas3238-hue/qore-core/actions/runs/38820840827) |
| R7 DST FX (17/17) | [#38902464494](https://github.com/mezas3238-hue/qore-core/actions/runs/38902464494) |
| R8 producer SHA ledger | [#38975246782](https://github.com/mezas3238-hue/qore-core/actions/runs/38975246782) |
| R9 36 reviewer-only blind | [#39037416479](https://github.com/mezas3238-hue/qore-core/actions/runs/39037416479) |
| R10 36 unanswered + guard | [#39096884947](https://github.com/mezas3238-hue/qore-core/actions/runs/39096884947) |
| Último CI previo a handoff (159 green) | [#39097058762](https://github.com/mezas3238-hue/qore-core/actions/runs/39097058762) |

**Issues prioritarios revisados OPEN 20-OCT:** [#976 revisión auténtica](https://github.com/mezas3238-hue/qore-core/issues/976), [#985 G2/G7 PIT](https://github.com/mezas3238-hue/qore-core/issues/985), [#988 cinco UNKNOWN](https://github.com/mezas3238-hue/qore-core/issues/988), [#837 Data Vault](https://github.com/mezas3238-hue/qore-core/issues/837). PR #626 **0 GitHub reviews** al corte. La presencia de comments del bot/arquitecto NO equivale a review aprobatorio.

---

## 14. ACTA DE TRASPASO Y STOP CONDITIONS

**TRABAJOS REALIZADOS:** reconstrucción CRT original y defectos legacy; directiva triad implementada; V1/V2/V3 congeladas con source+price path; 48 first-look; G-M3 139 reconocimiento/ABSTAIN; G-M4 139 E2E conceptual/5 UNKNOWN; R3–R10 auditorías causales, G2/G7, causa de 108 WAIT, hashes/censura R6–R8, 36 G2 verdaderamente sin etiquetas/SEALED R9 y guardia SHA de dictámenes R10; CI real 159 passing. Documentación técnica/hashes/links/PR/issues arriba.

**TRABAJOS AÚN FALTANTES:** custodiar originales, revisar 36 G2 y 48 G-M2 con humanos independientes; inventario old-CRT; 7 contratos/firmas Owner+auditor externo; adjudicar G7 scope y cinco casos UNKNOWN sin fabricar terminales, G-M3 externas, G-M4 Risk boundary y G-M5; después **una hipótesis legítima con OOS virgen + BID/ASK/fees/fills + todos los E0–E11** y DD/capital por Risk. No trivializar las falsaciones V2/V3 por urgencia.

**STOP / ABSTAIN obligatorio si:** falta custodia/provenance, la firma es string/booleano editable, hay C3 future en packet blind, historia pendiente sin policy G7, gaps M5 censurados, fills imposibles sin datos, datos OOS ya vistos, resultado de PF retuneado, falta Risk DD, intento de introducir sizing o de autorizar órdenes antes del certificado real.

**ESTADO QUE DEBE RECIBIR EL NUEVO ARQUITECTO: `G-M1 PARTIAL · G-M2 PARTIAL · G-M3 PARTIAL · G-M4 PARTIAL · G-M5 NOT ISSUED · GLOBAL NOT CERTIFIED · EXECUTION NOT AUTHORIZED`.**

**Firma documental:** compilación de evidencia GitHub; **NO** firma del Owner ni dictamen de auditor; no sustituye identidades. Todos los cambios a este documento generan nuevo HEAD y cualquier futura firma nativa referida a HEAD anterior deberá revalidarse.
