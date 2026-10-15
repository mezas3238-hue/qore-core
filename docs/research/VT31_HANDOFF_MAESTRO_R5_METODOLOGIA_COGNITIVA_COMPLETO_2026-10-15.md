# QORE CORE / VT31 NAS100 — HANDOFF MAESTRO R5
## Certificación por METODOLOGÍA y COGNITIVA · continuidad íntegra para el próximo arquitecto

**Corte:** 15 de octubre de 2026 (America/Asuncion).
**Repositorio fuente de verdad:** [`mezas3238-hue/qore-core`](https://github.com/mezas3238-hue/qore-core).
**Origen técnico del handoff:** [PR #971](https://github.com/mezas3238-hue/qore-core/pull/971), rama `agent/vt31-m0-predecision-profile-router-20261015`, HEAD antes de este documento `0ec466784f3047849b6b0a479c18f68bb8bc3b41`.
**Rama documental de continuidad:** `docs/vt31-handoff-maestro-r5-metodo-cog-20261015` (PR DRAFT; no merge).
**Gobernanza abierta:** [Issue #727 (comunicación interarquitectos)](https://github.com/mezas3238-hue/qore-core/issues/727), [Issue #957 (P0 metodología/cognitiva)](https://github.com/mezas3238-hue/qore-core/issues/957), [Issue #897 (G3 dos firmas COG+OPS)](https://github.com/mezas3238-hue/qore-core/issues/897).

> **DICTAMEN AL CORTE: VT31 NO ESTÁ CERTIFICADO.** Metodología = **PENDIENTE**; Cognitiva = **PENDIENTE**. Las pruebas verdes no son una firma ni demuestran fidelidad completa del autor. El objetivo prioritario del Owner es certificar POR METODOLOGÍA Y COGNITIVA, no aprobarlos a partir de Profit Factor, Drawdown, Sharpe, Sortino, win rate o sizing. Los Gates económicos oficiales pertenecen a otra fase y no deben darse por superados ni suprimidos.

---

## A. INSTRUCCIONES INNEGOCIABLES DEL OWNER

1. **Un solo VT31**, reconstruido desde cero tras abandonar el viejo VT31 defectuoso; no resucitar código/estado del trader antiguo como fuente de verdad. **M1 obligatorio** porque la operativa Silver Bullet y la lógica de origen se observan en M1; HTF M15/H1/H4 únicamente con velas cerradas.
2. **Certificar por metodología y cognitiva:** el trader debe interpretar correctamente su fuente, reconocer contexto/liquidez/sesión/estructura y discriminar LONG, SHORT, WAIT y REJECT causalmente. No convertir certificación doctrinal en búsqueda de rentabilidad, ni utilizar PnL para ajustar definiciones tras ver resultados.
3. **Trabajar rápido y encadenar pruebas** utilizando `Trader Lab`, `QORE Research`, runners existentes o `pytest-xdist`, con evidencia reproducible. No pedir permiso después de cada test; comunicar resultados por GitHub #727. Aclaración técnica: `TraderLabFastForwardSchedule(32)` comprime **tiempo SIMULADO**, NO demuestra speedup real de CPU 32×.
4. **Prohibido sizing dentro del trader.** No añadir lotaje, multiplicadores, volumen oportunista ni sizing adaptativo como salvavidas del edge. La autoridad de volumen corresponde a CIBO CMA / capa central QDLE; NO se usa para certificar VT31.
5. **No MERGE a main, no LIVE/producción/FundedNext LIVE, no VPS, no OMS ni órdenes**, no fills fabricados, no BID/ASK imaginarios, no promoción a DEMO/OOS sin Gates auténticos. DRAFT research/CI es permitido; no tocar G3 protegido en original sin versión y firmas.
6. **No fabricar revisores humanos**: el Owner tiene una cuenta autenticada; los agentes que actúan desde ella NO son dos firmas independientes COG y OPS. [Issue #897](https://github.com/mezas3238-hue/qore-core/issues/897) exige dos identidades/roles verificables.
7. **Handoff exhaustivo y permanente en GitHub** para que otro arquitecto continúe sin perder causas, datos, SHAs, contratos, pruebas y bloqueos. Preservar fechas, ramas y veredictos negativos.

## B. BASE DE CÓDIGO PROTEGIDA — NO TOCAR A CIEGAS

| Objeto G3 original | Ruta / identificación | Blob SHA1 inmutable verificado repetidamente por CI |
|---|---|---|
| COG original | `src/qore/infrastructure/traders/vt31_ict_cleanroom/cognition.py` | `d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9` |
| OPS original | `src/qore/infrastructure/traders/vt31_ict_cleanroom/operations.py` | `0ce9707314aecb71155de8b57044b6ec028847b2` |
| Acta metodológica G3 r1.3 | `docs/research/VT31_G3_DECISION_METODOLOGICA_STOP_FRAMEWORK_FVG_EXIT_V1_2026-10-12.md` | `e99c70b4e018d626fb620d9a21b9314a51abc36d` |

**Pareja G3 r1.3 pendiente de firma:** acta commit `a446afa17ed6e411b8f0b6fc182b103a78959a97`, implementación + tests + workflow commit `78d4cdac0e09d1a6eef37b99c505ffc5098031fc`, [PR #896 DRAFT](https://github.com/mezas3238-hue/qore-core/pull/896), [CI #38343414831 SUCCESS 41/41](https://github.com/mezas3238-hue/qore-core/actions/runs/38343414831). Pares anteriores son obsoletos y NO se reutilizan para atestaciones.

**Marco G3 existente, sujeto a juicio de fuente:** pivote local causal M1 confirmado 3 velas, desplazamiento cuerpo >=1.25×mediana reciente; política MSS anclada al close original, DOL no consumido y al menos `MIN_INDEX_POINTS=10` por delante; stop operativo registrado más allá de C2 full wick/ticks del contrato; FVG primero tras MSS, sin partial/BE/trailing en reglas congeladas, corte/ACK a las 15:55 NY. **Estos umbrales son ingeniería QORE**, no deben atribuirse a ICT/TTrades si el autor no los especificó. OHLC es observación de precio, NO fill.

## C. IDENTIDAD METODOLÓGICA, FUENTES PRIMARIAS Y CONFLICTOS

**No mezclar fuentes:**
- **ICT Silver Bullet general:** ventanas London NY 03:00–04:00, NY AM 10:00–11:00, NY PM 14:00–15:00. La identificación de ventanas no prueba que todo MSS/SL/DOL QORE sea la implementación ICT original.
- **TTrades AM NQ 2025:** fuente [The AM Silver Bullet Strategy on NQ](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/): rango H1 NY 09:00–10:00, primero barrer un extremo en 10:00–11:00, vuelta/desplazamiento, **objetivo lado OPUESTO del H1 de 09**, familias de entrada displacement, FVG, Order Block, Breaker; stop más allá del swing que CAUSÓ desplazamiento. Su regla 09h no debe extenderse implícitamente a London ni NY PM.
- [TTrades Order Blocks Simplified](https://ttrades.com/order-blocks-simplified/): vela o serie de velas opuestas previa a desplazamiento, contexto HTF/POI, media del cuerpo y cierre de invalidación; #906 seleccionar solo `opposing[-1]` es una aproximación QORE insuficiente si no demuestra causalidad, confluencia y zona.
- [TTrades Breaker Blocks Simplified](https://ttrades.com/breaker-blocks-simplified/): estructura bull LOW→HIGH→LOWER LOW→HIGHER HIGH y bear HIGH→LOW→HIGHER HIGH→LOWER LOW; zona de candle(s) + retest posterior. El pivote aislado de #906 NO certifica las cuatro piernas.
- [TTrades Protected Swings](https://ttrades.com/protected-swings-understanding-trends-and-invalidations/) y [Stop Loss Mastery](https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/): el swing protegido requiere barrido/contexto y cierre más allá de velas opuestas; es un testigo útil, NO identifica sin más el swing exacto causante del desplazamiento del artículo AM ni lo equipara al G3 C2.

**Conflicto comprobado:** G3 original NY AM LONG DOL cash anterior 150 vs autor TTrades H1 09 HIGH 110; G3 original SHORT DOL cash 80 vs TTrades H1 09 LOW 90. No es cuestión de spread ni PF; es un conflicto de IDENTIDAD DEL MÉTODO. [PR #950](https://github.com/mezas3238-hue/qore-core/pull/950), [#955](https://github.com/mezas3238-hue/qore-core/pull/955).
**Conflicto QORE G3 MIN10 vs objetivo autoral:** si M1 MSS close LONG105→autor H1 HIGH110 (5 puntos) o SHORT94→autor H1 LOW90 (4 puntos), ambos criterios son incompatibles: módulo #956 devuelve **WAIT**, preserva destino del autor y no reduce 10 buscando rentabilidad. Casos compatibles LONG 105→120 (15 puntos) y SHORT 94→80 (14 puntos) generan DTO **nueva versión de investigación** validado por V2, no salida nativa de G3.

## D. INVENTARIO DE TRABAJOS, PRs Y RESULTADOS — CRONOLOGÍA REAL

### D1. Evidencia original de mercado y métodos (octubre 2026)

| PR / rama | Trabajo realizado | Resultado demostrable | Frontera pendiente |
|---|---|---|---|
| [#901](https://github.com/mezas3238-hue/qore-core/pull/901) USTEC cTrader | 483,103 quotes BID/ASK DEMO en ~30 horas; mediana spread 0.8, p95 1.4 (instrumento USTEC, no serie 3Y NAS100 equivalente) | Existe evidencia microestructura BROKER de muestra corta; issues datos #857/#900 | No extrapolar costes reales a los 775 días NAS100 |
| [#906](https://github.com/mezas3238-hue/qore-core/pull/906) cuatro familias | Reconstrucción source-only displacement/FVG/OB/Breaker, proxies de OB última vela y Breaker pivote | Familias de investigación 212/205/116/84 contextos; **cohortes solapadas**, NO sumables como trades; medias brutas exploratorias 15m NO rentabilidad certificada | Familia OB/Breaker NO author literal, zonas/ticks/ejecución inciertos |
| [#934](https://github.com/mezas3238-hue/qore-core/pull/934) M2/M3 | Censo causal TTrades primer raid y MSS en NAS100 1,059,784 M1 / 775 días NY | 128 contextos raid+MSS, 483 rechazados sin MSS, otros sin retorno; source-only | No calificación G3/autoral integral ni PnL neto |
| [#935](https://github.com/mezas3238-hue/qore-core/pull/935) M4/M5 | Primer FVG post MSS, C3, CE y stop wick C2 sobre M1 real | 119 FVG elegibles; 61 retests M1 observados, 31 intraminuto ambiguos, 27 expiran; sin fills | No convertir toque M1 en orden ejecutada, stop autoral no verificado |
| [#938](https://github.com/mezas3238-hue/qore-core/pull/938) M4-P1 | Anticipación causal sobre primeros FVG M1 y prefijos | 5,155 prefijos M1 examinados anti-lookahead | No mide edge ni ejecuta broker |
| [#937](https://github.com/mezas3238-hue/qore-core/pull/937) L3 PREP | Reproducción 1×/32× de 92,280 M1 NY 09–11 contra fuente real | Paridad SOURCE-ONLY | No `qualify_trader_lab_fast_forward` nativo de candidato VT31 real, NO L3 |
| [#939](https://github.com/mezas3238-hue/qore-core/pull/939) L1 PREP | 120 casos fuente M1 reales y congelación research para Trader Lab | Tests 247 PASS en ronda reportada | No objeto oficial `EvaluationFreezeEvidence`, no sello L1 |
| [#943](https://github.com/mezas3238-hue/qore-core/pull/943) M5 | C2 wick G3 vs extremos raid/path en 119 contextos FVG | Diferencias observadas; NO identifica swing autoral que CAUSÓ displacement | Resolver swing con ejemplos reales etiquetados, no por proxy |
| [#945](https://github.com/mezas3238-hue/qore-core/pull/945) Breaker 4 legs | Auditoría M1 real 3Y de cuatro piernas, confirmaciones previas, zona research | 149 testigos estructurales de 775 días NY; **no compararlos con los 84 #906** (cohortes distintas). CI 228 PASS | Testigos source research, no zonas/retest autoral aprobados |

**Fuente de M1 histórico:** artifact original de NAS100 #11459859004, JSON `NAS100/market-evidence.json`, SHA256 **`0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`**; 1,059,784 M1 cerradas, 775 días NY, 769 completos conforme al censo citado. Datos de desarrollo utilizados repetidamente, **no denominarlos holdout virgen**. El precio NAS100 OHLC de esa fuente NO es por sí solo ticks/bid-ask reales del contrato/cuenta.

### D2. Arquitectura G3 y certificación formal

| PR | Resultado y función | Estado real |
|---|---|---|
| [#896](https://github.com/mezas3238-hue/qore-core/pull/896) | G3 r1.3 COG/OPS/acta congela MSS y reglas; CI 41 PASS | DRAFT; faltan 2 firmas reales COG/OPS [#897](https://github.com/mezas3238-hue/qore-core/issues/897) |
| [#936](https://github.com/mezas3238-hue/qore-core/pull/936) | Matriz de contrato oficial Trader Lab Gates L1–L10 y dependencias M0–M7 | Análisis preparatorio, NO certifica etapas |
| [#940](https://github.com/mezas3238-hue/qore-core/pull/940) | Handoff maestro R2 con 18 problemas y plan, [documento](https://github.com/mezas3238-hue/qore-core/blob/63aa56ce9db4355106eee793b85ccb07ea171180/docs/research/VT31_HANDOFF_MAESTRO_CERTIFICACION_METODOLOGIA_COGNITIVA_R2_2026-10-14.md) | Predecesor histórico, NO incorporar decisiones obsoletas automáticamente |

### D3. COG REAL, fuente autoral y juicio cognitivo (14–15 OCT)

| PR y CI SUCCESS | Ingeniería entregada | Resultado con interpretación estricta |
|---|---|---|
| [#948](https://github.com/mezas3238-hue/qore-core/pull/948) · CI [#38671368366](https://github.com/mezas3238-hue/qore-core/actions/runs/38671368366) · 66 PASS | Ejecutó `VT31CleanroomCognition` ORIGINAL Londres LONG/WAIT/REJECT, memoria, invalidación y contrafactual | Original COG juicio causal en sintéticos, no homologación de fuente |
| [#950](https://github.com/mezas3238-hue/qore-core/pull/950) · CI [#38671726622](https://github.com/mezas3238-hue/qore-core/actions/runs/38671726622) · 73 PASS | Caso COG ORIGINAL NY AM LONG vs TTrades autor DOL | Fallo de fidelidad al perfil TTrades, cash HIGH150 ≠ 09h HIGH110 |
| [#951](https://github.com/mezas3238-hue/qore-core/pull/951) · CI [#38706697043](https://github.com/mezas3238-hue/qore-core/actions/runs/38706697043) · 80 PASS | Auditor M0 sombra: TTrades NY AM REJECTED; ICT_GENERAL UNKNOWN | Nunca promover UNKNOWN a PASS; no selector oficial nativo |
| [#953](https://github.com/mezas3238-hue/qore-core/pull/953) · CI [#38707397529](https://github.com/mezas3238-hue/qore-core/actions/runs/38707397529) · 41 PASS | NY PM ORIGINAL LONG/WAIT/invalidación/future as-of | COG real, en escenarios definidos; fuente ICT_general aún indeterminada |
| [#955](https://github.com/mezas3238-hue/qore-core/pull/955) · CI [#38708707140](https://github.com/mezas3238-hue/qore-core/actions/runs/38708707140) · 46 PASS | SHORT ORIGINAL 3 ventanas EST y EDT, 6 positivos + WAIT/contrafactual | DOL cash80 vs TTrades 09 LOW90, fallo fuente específico a NY AM |
| [#956](https://github.com/mezas3238-hue/qore-core/pull/956) · CI [#38709608789](https://github.com/mezas3238-hue/qore-core/actions/runs/38709608789) · 58 PASS | Fuente-primero TTrades + MSS G3 real, nuevo DTO versión `RESEARCH`, V2 independiente | 4 contextos compatibles + 4 WAIT por MIN10; NO cambia COG/OPS originales |
| [#961](https://github.com/mezas3238-hue/qore-core/pull/961) · CI [#38714144265](https://github.com/mezas3238-hue/qore-core/actions/runs/38714144265) · 65 PASS | Gate independiente OB candles/HTF/mean50 y Breaker cuatro piernas/zona/retest, rejects | Solo estructura fuente parcial; no ejemplos autoralmente etiquetados |
| [#962](https://github.com/mezas3238-hue/qore-core/pull/962) · CI [#38714817522](https://github.com/mezas3238-hue/qore-core/actions/runs/38714817522) · 69 PASS | Testigo protected swing, LONG low89 vs wick93 y SHORT high111 vs wick109, contextos WAIT | Confirmación de serie/close, NO stop broker y NO swing único causante |

### D4. Tribunal final de evidencias, Trader Lab ultra-fast y M0 reciente

| PR y CI SUCCESS | Trabajo realizado | Alcance / límite |
|---|---|---|
| [#964](https://github.com/mezas3238-hue/qore-core/pull/964) · CI [#38715458476](https://github.com/mezas3238-hue/qore-core/actions/runs/38715458476), 73 PASS | Tribunal metodológico+cognitivo con **8 artifact ZIP SHA256** auténticos, revisiones GitHub PR#896 e issue#897; JSON condición por condición | METODOLOGÍA PENDIENTE, COGNITIVA PENDIENTE; no PnL |
| [#965](https://github.com/mezas3238-hue/qore-core/pull/965) · CI [#38741786681](https://github.com/mezas3238-hue/qore-core/actions/runs/38741786681), 55 PASS | `TraderLabFastForwardSchedule(32)` **NATIVO**; COG original 12 SHORT/WAIT 1×/32×; `qualify_trader_lab_fast_forward` con 3 carriers **SINTÉTICOS** y candidato genérico | Igualdad causal de traza; NO L3 real ni 32× CPU medido |
| [#967](https://github.com/mezas3238-hue/qore-core/pull/967) · CI [#38747782153](https://github.com/mezas3238-hue/qore-core/actions/runs/38747782153), 69 PASS | 24 casos G3 original LONG/SHORT/WAIT, 3 sesiones×EST/EDT×dos lados×MSS/WAIT, 1×/32× | LONG espejo geométrico M1 `p'=230-p` sintético; TODAS trazas/hashes iguales |
| [#969](https://github.com/mezas3238-hue/qore-core/pull/969) · CI [#38748834633](https://github.com/mezas3238-hue/qore-core/actions/runs/38748834633), 92 PASS | Tribunal ampliado **10 ZIP auténticos**, manifest+hashes internos, CGI real G3, revisión humana consultada | Flag nuevo `COG_original_native_traderlab_1x_32x_full_semantic_parity=true`; ninguno de los bloqueos de cert removido |
| **[#971](https://github.com/mezas3238-hue/qore-core/pull/971)** · **CI [#38762670233](https://github.com/mezas3238-hue/qore-core/actions/runs/38762670233), 78 PASS** | **ÚLTIMO trabajo:** Router research M0 `FrozenMethodProfilePolicy` PRE-M1; 16 casos LONG/SHORT EST/EDT | 4 TTrades context compatibles, 4 TTrades WAIT por MIN10, 8 ICT_GENERAL UNKNOWN; NO firmado ni conectado a OPS |

**Rondas CI:** Cada cifra de pytest pertenece a **una ejecución y su propia suite (con regresiones solapadas)**; NO sumar 66+73+... como miles de pruebas independientes, ni contar sintéticos como trades. Las últimas CI verificaron originales G3 sin alterarlos.

## E. ÍNDICE DE ARTIFACTS Y HASHES — FUENTE DE EVIDENCIA, NO PROMESAS

| PR / CI | GitHub Actions artifact ID | SHA256 del ZIP | Qué contiene |
|---|---|---|---|
| #948 | `11944328096` | `05710d9ab11c598fbfc57718f6e5a7fe18ebcc02564443cd4831c0eef925a272` | Tribunal COG ORIGINAL London |
| #950 | `11943793928` | `bb5aef53f1db40f89683da9cb982ac51f4689abbd3a23ce044f958ff2527833f` | NY AM LONG divergencia TTrades |
| #951 | `11958388150` | `78ad2ba7c53790a6c9119f4e831c6683f3f502aee10aa729dc800dd16784ca0e` | M0 shadow perfil |
| #953 | `11959135942` | `f9ccfa7a62e467db595992819024d8b02f8b4d44b7e1dc4c41dd874020e47bfe` | NY PM COG ORIGINAL |
| #955 | `11960185549` | `0b32d306a86e50e924ab3a29d2f6b5dffe1242d383aff3970728b45552acafde` | SHORT COG original seis casos |
| #956 | `11959393863` | `05b834475801822e339d21665736f3f78a4e4dbf4c266f50be7ece3f8662dcbf` | Fuente TTrades + MIN10 |
| #961 | `11961174983` | `115047d9f83fcc56f725fe8e47659148a5d69a7d160c8f399c2f0d9b94643ce4` | OB/Breaker regla source |
| #962 | `11962555846` | `a01bcd191e8f379f4cbc39a3621ab40b58f0635316f0669473b18cd88cd7ee95` | Protected swings |
| #965 | `11976412423` | `e52de6f442238be555eb739d8d46082cb83a2132f49e6bcf3d748de462d3fd4e` | Fast Forward 12 casos |
| #967 | `11979797382` | `a77be5d7c66a767a4f0724f2b981571f3972fc0eee992a2b9b2ea70c7ccad25b` | Fast Forward 24 casos |
| **#969** | **[`11980475570`](https://github.com/mezas3238-hue/qore-core/actions/runs/38748834633/artifacts/11980475570)** | **`258bba6d0b39cccfc6b8469c7c23ecb3934eecdd970c3b422f44e4a53abddda5`** | **Tribunal final diez ZIP** |
| **#971** | **[`11987016022`](https://github.com/mezas3238-hue/qore-core/actions/runs/38762670233/artifacts/11987016022)** | **`692798ab1efcef5dbb67feacbeeb42a1f622a272fec98708837ddd6dca11fdba`** | **16 casos router M0** |

**Importante:** artifacts GitHub Actions tienen retención; si caducan, recuperarlos antes de plazo o regenerarlos ejecutando el mismo SHA/código+dataset, documentando NUEVOS hashes. No reemplazar un hash con otro silenciosamente. El PR #971 es POSTERIOR al tribunal #969, por lo que **NO está dentro de sus diez ZIP**. Siguiente tribunal será 11 fuentes si se agrega su artifact y se validan hashes + testigos.

## F. CÓDIGO EXACTO QUE DEBE ABRIR EL PRÓXIMO ARQUITECTO

**COG real protegido:**
- `src/qore/infrastructure/traders/vt31_ict_cleanroom/contracts.py`: `M1Bar`, `CognitiveDecision`, `SessionId`, `G3_MSS_FRAMEWORK_POLICY`, `MIN_INDEX_POINTS`, ventanas NY, validación de fuente.
- `src/qore/infrastructure/traders/vt31_ict_cleanroom/cognition.py`: `VT31CleanroomCognition.observe_closed_m1()`, `assess()` y `_OnlineCausalIndex`, memoria de un solo trader; políticas MSS/pools y revocaciones. **NO modificar blob protegido.**
- `src/qore/infrastructure/traders/vt31_ict_cleanroom/operations.py`: original OPS protegido; no ejecutar órdenes.

**Nuevos adjudicadores y reproducciones de investigación:**
- `scripts/vt31_m0_predecision_method_router_20261015.py` + `tests/infrastructure/test_vt31_m0_predecision_method_router_20261015.py` — **PR #971: punto exacto de continuación**; perfiles explícitos y 16 casos.
- `scripts/vt31_m0_profile_shadow_attestation_20261015.py` — sentencia ICT_UNKNOWN vs TTrades_REJECTED para mismo COG ORIGINAL.
- `scripts/vt31_ttrades_source_first_g3_cognitive_proposal_20261015.py` — usa MSS G3 REAL y construye únicamente DTO **RESEARCH** DOL H1 TTrades; caso mínimo 10pt ⇒ WAIT.
- `scripts/vt31_mc_p2_ttrades_native_h1_evidence_20261014.py` — detector causal del H1 09, first sweep, retorno, sin lookahead; UNKNOWN cuando ambos lados barridos en la misma vela.
- `scripts/vt31_m4_ob_breaker_author_evidence_gate_20261015.py` — rechaza zona OB/Breaker insuficiente; no produce fill/trades.
- `scripts/vt31_m5_ttrades_protected_swing_source_20261015.py` — contexto de swing protegido, NO identifica el stop broker ni swing causante definitivo.
- `scripts/vt31_original_g3_cog_short_sessions_qualitative_20261015.py` y `scripts/vt31_original_cog_traderlab_32x_long_short_20261015.py` — escenarios auténtico COG vs reloj simulado.
- `scripts/vt31_original_cog_trader_lab_fast_forward_20261015.py` y `src/qore/infrastructure/trader_lab/fast_forward.py` — API de fast-forward **nativa**; prueba #965 con eventos tipados sintéticos no broker.
- `scripts/vt31_qualitative_method_cog_certificate_decision_20261015.py` — tribunal original ocho sources y revisión real.
- `scripts/vt31_cert_ledger_10_artifacts_traderlab_20261015.py` — tribunal ampliado a diez ZIP; no actualiza automáticamente con #971.

**Workflows CI verificadas:**
- `.github/workflows/vt31-m0-predecision-method-profile-router.yml` — 78 PASS, última CI.
- `.github/workflows/vt31-cert-ledger-traderlab-10artifacts.yml` — 92 PASS, tribunal diez ZIP.
- `.github/workflows/vt31-traderlab-32x-bidirectional-cog.yml` — 69 PASS, dos direcciones.
- `.github/workflows/vt31-trader-lab-32x-cognitive-parity.yml` — 55 PASS, 12 casos y contrato nativo.
- `.github/workflows/vt31-m4-ob-breaker-source-lineage.yml` — reglas metodológicas source.
- `.github/workflows/vt31-m5-protected-swing-source.yml` — contexto protected swing.

## G. INVENTARIO DE PROBLEMAS ENCONTRADOS Y SOLUCIÓN PARA EL SIGUIENTE ARQUITECTO

| ID / prioridad | Problema confirmado | Causa raíz / riesgo | Solución verificable / criterio de cierre |
|---|---|---|---|
| **B01 P0** | Identidad de VT31 mezclada entre ICT_GENERAL y TTrades AM | G3 original selecciona DOL cash, TTrades exige 09 H1; autoetiquetar como TTrades falsearía fidelidad | Aprobar mapa de perfiles *antes de M1* y versión del contrato de método. #971 prueba solo mapa **RESEARCH**, no Owner sign-off ni productor nativo |
| **B02 P0** | COG productivo sigue fuente TTrades no conforme | Adaptador #956 externaliza DOL y reversiona DTO, pero COG/OPS G3 congelados no lo conocen | Implementar NUEVA versión gobernada de COG con preselección y *source-first*; inspección V2 en todas las decisiones; no mutar #896 sin nuevo SHA/aprobación |
| **B03 P0** | QORE MIN10 vs TTrades H1 objetivo | Objetivo autoral puede quedar a 4–5 pts, por lo que no satisface marco QORE aunque sea válido para autor | Decisión metodológica explícita: mantener abstención `WAIT` cuando ambos contratos no son compatibles; formalizar en la política aprobada; NO modificar objetivo del autor ni optimizar MIN10 por PnL |
| **B04 P0** | MSS numérico 3bar/1.25×median5 no acreditado como literal ICT/TTrades | Ingeniería QORE usada como proxy de desplazamiento y cambio de estructura | Matriz de ejemplos originales anotados por tercero con M1/HTF y casos falsadores; distinguir `QORE_PIVOT_PROXY` de `AUTHOR_MSS_CONFIRMED`; cerrar M3 |
| **B05 P0** | Order Block #906 `opposing[-1]` simplista | Puede omitir vela-serie, HTF/POI y selección/invalidation de zona | Obtener ejemplos primarios autor positivo/negativo, zona por candles, media/close/invalidation causal; registrar ambigüedad multicandle como UNKNOWN; homologar familia M4 |
| **B06 P0** | Breaker #906 usa pivote único | No acredita Low–High–LowerLow–HigherHigh / espejo SHORT, zone ni retest | Aprovechar gate #961 + censo real #945 sin equiparar 149 a 84. Definir selección de 4 swings causales y zona anotada por fuente; testear LONG/SHORT M1 |
| **B07 P0** | Protected swing de #962 no identifica swing que CAUSÓ displacement | Artículos TTrades protected ≠ definición única de stop AM y G3 C2; alto riesgo de invalidación no fiel | Dos/tres ejemplos primarios de swing causante, validación causal tick/price source, política del stop versionada, estudio de divergencia C2 vs swing; sin broker fills inventados |
| **B08 P0** | No existen dos firmas G3 r1.3 | [PR #896](https://github.com/mezas3238-hue/qore-core/pull/896) `reviews=[]`, `requested_reviewers=[]` y [Issue #897](https://github.com/mezas3238-hue/qore-core/issues/897) abierto al último chequeo; solo 1 identidad visible con autoridad | Owner designa COG y OPS humanos/identidades GitHub distintas, autoriza permisos, ellos auditan y `APPROVED` sobre SHA + acta exactos; verificar API. No simular |
| **B09 P0** | COG autónomo no demuestra selection de las 4 familias/stop | Testigos research externos #961/#962 no son decisiones del productor verdadero | Extender productor NUEVA versión source-reviewed, reproducir trazas LONG/SHORT/WAIT/REJECT, razones y timestamps en casos ciegos positivos/negativos de cada familia; auditor humano |
| **B10 P1** | Entradas FVG, CE y stop proxy no prueban ejecución | M1 OHLC y toque CE pueden ocultar secuencia intraminuto | Si llega fase DEMO/economía, usar ticks BID/ASK canónicos broker, bid/ask con metadata/hashes, spreads slippage; no declarar fills por wick |
| **B11 P1** | Datos BID/ASK real muy cortos y USTEC≠NAS100 3Y | #901 demo ~30h USTEC; desarrollo NAS100 OHLC 3Y, feeds distintos | Identificar mismo instrumento/broker/timezone/contrato y descarga auditable, [#857](https://github.com/mezas3238-hue/qore-core/issues/857)/[#900](https://github.com/mezas3238-hue/qore-core/issues/900); no mezclar feeds |
| **B12 P1** | 3Y NAS100 ya se exploró con muchas hipótesis | Reutilización repetida = riesgo de contaminación/OOS; backtest estadístico distinto del método | Congelar dev; distinguir blind holdout independiente y su custodia; no vender 3Y como OOS virgen; metodología primero |
| **B13 P1** | Trader Lab 32× podría interpretarse como 32× CPU | `TraderLabFastForwardSchedule` contrae tiempo **simulado**, no acelera cálculo automático 32× | Medir CPU de forma separada si hace falta; usar `pytest-xdist` y Ultra Fast Runner real donde corresponda, preserving as_of; jamás reclamar L3 por carrier sintético |
| **B14 P1** | `qualify_trader_lab_fast_forward` en #965 usa candidato genérico/quote sintética | Carrier NAS100 BID100/ASK101 tipeado no procede de mercado/broker, fixture EURUSD de tests | Si calificar L3, registrar candidate VT31 real y cronología retenida real, hashes, events exactos, test anti-lookahead, firma y Gate oficial |
| **B15 P1** | Censo four-leg #945 vs #906 parece contradictorio | 149 vs 84 cuentan hipótesis, cohortes y filtros distintos; no son trades | Etiquetar cada cohorte, comparar por `source_id`/timestamps/definición común antes de cualquier conclusión |
| **B16 P1** | Existen numerosos PRs DRAFT con dependencias apiladas + otra rama #906/#943 | Riesgo de merge/copy de viejos proxies, conflictos o perder preregs por salto de SHA | Seguir la tabla de dependencias H, revisar `git merge-base`, cherry-pick por contenido y tests si autorizado; no hacer merge automáticamente |
| **B17 P1** | Cierres de CI por problemas de tooling/formato | #945 test SHORT sintetizó color erróneo; #955 E501/B023; #956 E501; #961 tests; #962 I001; #965 `Instrument.value` inexistente; #967 YAML `:` sin comillas + Ruff E741; #969 validaba prereg extension como el original; #971 I001/F401 | Se corrigieron esos casos (solo infraestructura/tests o fixture explícito), conservar logs y diferencia CI fallido→SUCCESS; ningún error Ruff equivale a fallo de método, nunca ocultar fallo de fuente |
| **B18 P1** | CI verde confunde evidencia con certificado | El tribunal devuelve algunos flags parciales true, pero carece de reglas/firma humanas | Conservar conjunción estricta M0–M6 y adjudicación separada COG, JSON con lista de blockers, source references y atestaciones humanas; **PENDIENTE** hasta evidencia real |
| **B19 P2** | Artifacts GitHub Actions expirarán | Período de retención, SHA pierde ruta descargable aunque informe persista | Crear manifest preservado en repo con digest, metadata, versiones y almacenamiento autorizado; regenerar solo como nueva evidencia con SHA nuevo documentado |
| **B20 P2** | Coste/recursos datos futuros y dependencia QORE Research | Mercado tick NQ futuros puede requerir pago no disponible, proceso lento manual | Priorizar pruebas M1 ya disponibles para doctrina, usar Trader Lab/QORE Research workflows; definir presupuesto/plan de datos antes de exigir futuros/OOS |

## H. DEPENDENCIAS DE BRANCH/PR: NO MEZCLAR FAMILIAS

**Cadena apilada actual (simplificada):** `#948 → #950 → #951 → #953 → #955 → #956 → #961 → #962 → #964 → #965 → #967 → #969 → #971 → ESTE HANDOFF R5`. Cada PR compara contra la rama anterior y muchos cambios están solo en ramas de investigación. **No afirmar que main contiene estas funciones.**
**Cadenas independientes:** `#906` four-family QORE proxies en `agent/vt31-ttrades-all-entry-models-20261013` y `#934 → #935 → #938 / #936→#937→#939→#943→#945` de censo/Gates; #940 R2 documental también es otra rama. Tomar solo evidencia explícita/paths y preservar `PREREG`/SHAs; no asumir que el stack de R5 contiene todos esos scripts de otra rama.
**Exacto inicio de continuidad:** branch `agent/vt31-m0-predecision-profile-router-20261015` commit `0ec466784f3047849b6b0a479c18f68bb8bc3b41`; para trabajar sobre código + handoff use este nuevo branch documental y cree un branch nuevo de trabajo desde su HEAD, sin hacer merge sobre `main`.

## I. CERTIFICACIONES: QUÉ SIGUE FALTANDO Y CRITERIOS DE ACEPTACIÓN

### METODOLOGÍA (M0–M7) — NO CERTIFICADA

| Gate | Evidencia actual | Requisito concreto de aceptación |
|---|---|---|
| **M0 identidad doctrinal** | #951 shadow + #971 16 casos con mapa fijo research | Versión formal de perfil aprobada y aplicada **por el COG nativo** antes del primer dato, política documentada, fuente trazable, revisión |
| **M1 temporalidad y mercados** | M1 causal, DST EST/EDT, escenarios Londres/NYAM/NYPM; #934 data dev | Auditor independiente comprueba fuente NY/timezones/sesión y exactitud ventanas; sin anticipación de H1 |
| **M2 liquidez, raid, DOL** | #950/#955 descubrieron conflicto; #956 WAIT correcto y 4 contextos research conforme | Objetivo de fuente seleccionado nativamente según perfil; casos ciegos de raid/no raid/sides same M1; DOL origen y frescura probadas |
| **M3 MSS/desplazamiento** | Original G3 MSS se comporta coherente en tests, es proxy 3bar/1.25× | Fidelidad a criterio autor con ejemplos positivos/negativos, causa fechada y fail-closed incertidumbre |
| **M4 entradas (displacement/FVG/OB/Breaker)** | #906 research proxies, #935 FVG, #945 4legs, #961 veto source | 4 familias definidas íntegramente, prioridad/selector y FVG CE/OB zone/Breaker zone retest causales sobre M1 con ejemplos etiquetados y contraejemplos |
| **M5 stop/salida** | G3 C2 wick framework + #943 auditoría y #962 protected swing contexto | Auténtico swing que causó displacement y regla de invalidación; sin equivalencia inventada C2; versión source-reviewed y exacta |
| **M6 gobierno/independencia** | #896 DRAFT, #897 sin firmas; tribunales prueban autenticidad faltante | Dos revisores reales independientes COG/OPS y auditor metodológico validan fuente+código SHA exactos, acta, criterios |
| **M7 cierre documental/certificado** | #964/#969 JSON auditado, #971 aún fuera del tribunal | Agregar evidence #971 al siguiente ledger + fuentes autorales; con TODOS los gates anteriores cerrados emitir documento certificado firmado **sin usar PnL** |

### COGNITIVA — NO CERTIFICADA

| Dimensión | Verificado | Falta para firmar |
|---|---|---|
| Entrada/razonamiento causal M1 | Original LONG/SHORT/WAIT/REJECT en #948/#953/#955/#967, estabilidad 1×/32× | Casos ciegos fuera de fixtures de diseño, razonamiento en cada familia y sesión y prueba independiente |
| Fidelidad perfil elegido | Shadow #951 y router research #971 separan perfiles | COG **productivo nativo** con selector aprobado, TTrades 09h / ICT source evidence según sesión |
| Selección de familias | Gate externo #961, original G3 no emite explicación de 4 familia autoral completa | Telemetría de productor: por qué FVG vs OB vs Breaker vs directo, y cuándo WAIT; casos fuente |
| Swing/invalidación | #962 solo testigo protected, G3 C2 protegido | COG identifica swing responsable de displacement con evidencia fuente; invalidación y timestamps |
| Gobernanza/firma | Ninguna review APPROVED #896 | Auditor COG independiente + OPS independiente sobre versión exacta, decisiones justificadas |

**Gates Trader Lab oficiales L1–L10** ([#936](https://github.com/mezas3238-hue/qore-core/pull/936)): L1 metodología/freeze auténtica, L2 execution replay, L3 fast-forward nativo con candidato y eventos reales, L4 OOS intacto, L5 estrés, L6 Monte Carlo, L7 economía neta (PF/DD/Sharpe/Sortino), L8 Risk, L9 CIBO, L10 independiente. El Owner **no desea basar los certificados M/COG en PF/DD**; eso NO autoriza marcar L1–L10 como PASS o afirmar DEMO_ELIGIBLE. Deben mantenerse como expedientes distintos para futuras promociones.

## J. PLAN EJECUTABLE PARA EL PRÓXIMO ARQUITECTO — POR IMPACTO

**P0 — acción 1: especificar y adjudicar fuente con exactitud.** Tomar [PR #971](https://github.com/mezas3238-hue/qore-core/pull/971) y la CI 78 PASS. Hacer documento `VT31_METHOD_PROFILE_CONTRACT_V1` con mapa sesión→fuente aprobado por Owner (si Owner aprueba), reglas WAIT en conflictos y versionado. Incluir M1 blind examples para NYAM TTrades e ICT GENERAL independientes. No cambiar el código G3 congelado.

**P0 — acción 2: resolver fuente author M3/M4/M5.** Compilar casos TTrades de sweep→displacement/MSS→OB/Breaker/FVG→stop con capturas/URL y referencias por timestamp, distinguir `AUTHOR_EXPLICIT` vs `QORE_PROXY` vs `UNDERDETERMINED`; otra persona adjudica sin ver retorno/PnL. Extender verificador y fuzz de cronología. El hecho de que #961 tenga dos positivos estructurales NO equivale a familias certificadas.

**P0 — acción 3: construir el COG candidato NUEVA versión.** Crear módulo independiente versionado que use un `FrozenMethodProfilePolicy` **formal** (no el de prueba) dentro del proceso cognitivo real; cada `CognitiveAssessment` incluye fuente, decisión, DOL, familia, MSS, stop CAUSANTE, razones WAIT/REJECT y causal source hashes. Si falta doctrina/source: WAIT y emitir `UNKNOWN`; no trades. Mantener `src/.../cognition.py` protegido sin tocar; versión nueva con tests y review de roles.

**P0 — acción 4: auditoría cruzada de perfiles.** TEST LONG/SHORT y WAIT para tres ventanas EST+EDT, side first raid, sweep same M1 high/low UNKNOWN, H1 incompleto, DOL ya consumido, MSS falso sin cierre, C2 vs protected swing, invalidación temporal, future-M1, discrepancias de fuentes. Ejecutar `pytest-xdist -n 4` o runner QORE Research real con hashes y prereg; no repetir únicamente 24 sintéticos ya pasados.

**P0 — acción 5: designar y obtener revisores [#897](https://github.com/mezas3238-hue/qore-core/issues/897).** Owner debe registrar identidad GitHub de COG y OPS, permisos y responsabilidad; enviarles acta exacta r1.3 o la nueva versión si procede. **Dos reviews APPROVED autenticadas**, no comments del mismo login. Revisar `/pulls/896/reviews`, `/requested_reviewers`, commits y blob SHA. Abrir Issue separado si formalmente renueva r1.3 para candidato nuevo.

**P1 — acción 6: ampliar tribunal a 11+ fuentes.** A partir de `scripts/vt31_cert_ledger_10_artifacts_traderlab_20261015.py`, incorporar artifact verificado #971 `11987016022` ZIP SHA256 `692798...fdba`, registrar nuevo prereg, CI que compruebe SHA256 ZIP + `SHA256SUMS` interno, delta de condiciones, y NO remueva falsamente M0 nativo. Adicionar futuras pruebas fuente/COG y firmas. No restar bloqueos porque aumentan casos sintéticos.

**P1 — acción 7: emitir certificados separados SOLO si cumplieron todo:** documento independiente `VT31_METHOD_CERTIFICATE_<version>` con criterios M0–M7, hashes, testigos y revisores; `VT31_COGNITION_CERTIFICATE_<version>` con juicios originales y auditorías; ambos con firmas verificadas, link CI y prohibición de operación hasta otros Gates. Si faltan ejemplos fuente/identidades, el dictamen sigue `PENDIENTE` con causa.

**P2 — preparar fase económica DEMO después de método, sin sizing propio:** levantar same-feed NAS100 cTrader bid/ask si presupuesto/datos permiten, freezes de dev vs holdout, fills verificables en bróker y Gates L1–L10 reales. **NUNCA** confundir este paso con certificación de fuente/cognición ni asumir rentabilidad actual.

## K. COMANDOS PARA RETOMAR Y VALIDAR (SIN MERGE NI LIVE)

```bash
# En clon autorizado de mezas3238-hue/qore-core
git fetch origin 'agent/vt31-m0-predecision-profile-router-20261015'
git checkout -b agent/vt31-next-source-cog origin/agent/vt31-m0-predecision-profile-router-20261015
git rev-parse HEAD  # checkpoint 0ec466784f3047849b6b0a479c18f68bb8bc3b41
git hash-object src/qore/infrastructure/traders/vt31_ict_cleanroom/cognition.py
git hash-object src/qore/infrastructure/traders/vt31_ict_cleanroom/operations.py
git hash-object docs/research/VT31_G3_DECISION_METODOLOGICA_STOP_FRAMEWORK_FVG_EXIT_V1_2026-10-12.md
python -m pip install -e '.[dev]' pytest-xdist
PYTHONPATH=src:. pytest -q -n 4 -o addopts='' tests/infrastructure/test_vt31_m0_predecision_method_router_20261015.py tests/infrastructure/test_vt31_m0_profile_shadow_attestation_20261015.py tests/infrastructure/test_vt31_ttrades_source_first_g3_cognitive_proposal_20261015.py tests/infrastructure/test_vt31_ict_cleanroom_cognition.py
PYTHONPATH=src:. python scripts/vt31_m0_predecision_method_router_20261015.py --out /tmp/VT31_M0_PREDECISION_RESEARCH.json
python -m json.tool /tmp/VT31_M0_PREDECISION_RESEARCH.json >/dev/null
```

**Nota:** por diseño este comando crea una nueva rama DE CÓDIGO sobre #971; el handoff documental R5 está en una rama distinta y debe consultarse por URL. Si en lugar de #971 se usa HEAD de R5, hacer `git checkout -b ... origin/docs/vt31-handoff-maestro-r5-metodo-cog-20261015` después de publicar el handoff. No usar `git merge origin/main` automáticamente.

## L. MATRIZ DE CRITERIOS PARA NO PERDER CONTEXTO

| Afirmación | Estado al corte | ¿Se puede reclamar? |
|---|---|---|
| COG ORIGINAL funciona causalmente LONG/SHORT/WAIT/REJECT en fixtures definidos | **EVIDENCIADO parcialmente** | Sí, con scope sintético y SHA |
| Cronología 1× y TraderLab 32× preservan los mismos estados en 12+24 casos | **PASS de paridad** | Sí, sin afirmar 32× CPU ni L3 |
| TTrades NY AM H1 opuesto DOL y WAIT MIN10 resueltos en una propuesta source-first | **RESEARCH PASS** | Sí, pero NO producto nativo G3 |
| M0 política sesión→método seleccionada causalmente antes de M1 | **RESEARCH PASS** #971 | Sí, NO política Owner firmada |
| COG nativo implementa fielmente TTrades NY AM completo | **NO** | No |
| ICT General London/NYPM está homologado contra autor | **UNDERDETERMINED** | No |
| Cuatro familias de entrada y stop autoral están homologados | **PENDIENTE** | No |
| Swing protegido TTrades = swing causante de desplazamiento = C2 G3 | **NO DEMOSTRADO** | No |
| Dos firmas independientes sobre acta y código G3 r1.3 | **AUSENTES al chequeo** | No |
| Certificado de METODOLOGÍA y COGNITIVA | **PENDIENTE / PENDIENTE** | **NO DECLARAR CERTIFICADO** |
| PF/DD/Sortino favorables, TraderLab L3 oficial, OOS limpio, DEMO_ELIGIBLE | **NO CALIFICADOS por esta cadena** | No |

## M. EVIDENCIA DE GOBERNANZA COMPROBADA EN ESTE HANDOFF

Consulta al crear R5: [PR #896 reviews](https://github.com/mezas3238-hue/qore-core/pull/896) (`GET /pulls/896/reviews`) devolvió **lista vacía** y `/requested_reviewers` también vacío; [Issue #897](https://github.com/mezas3238-hue/qore-core/issues/897) **OPEN**. Esto NO demuestra que nunca existan colaboradores, solo que **no hay firmas verificadas** en el expediente observado. El Owner no puede quedar bloqueado por tests adicionales, pero tampoco se puede declarar firmado por una misma identidad.

### NOTA DE CONTINUIDAD FINAL PARA OTRO ARQUITECTO

**No volver a empezar de cero:** los COG originales y el router de investigación ya están codificados, probados y publicados. El problema principal ha dejado de ser 'hacer otra prueba de 32×' o 'conseguir un Profit Factor'; es **congelar una metodología de fuente inequívoca, incorporarla nativamente a la cognitiva en versión gobernada, cerrar M3/M4/M5 con testigos de autor y conseguir revisiones humanas reales**. Trabajar en GitHub con prereg anterior a código, CI reproducible y notas #727. Sin merge, LIVE ni sizing del trader hasta permisos/contratos posteriores.

**Este archivo es DOCUMENTACIÓN de traspaso, no un certificado ni una modificación del software G3.**