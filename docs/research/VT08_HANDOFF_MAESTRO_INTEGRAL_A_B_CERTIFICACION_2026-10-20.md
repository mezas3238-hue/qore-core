# VT08 ACTUAL — HANDOFF MAESTRO INTEGRAL A/B Y PLAN DE CERTIFICACIÓN
## Corte técnico 20 de octubre de 2026 · Transferencia al próximo arquitecto sin pérdida de contexto

> **INSTRUCCIÓN DEL OWNER / PRIORIDAD ABSOLUTA:** «Qore alpha quedó excluido del programa por ende no puede mezclarse con el vt08 actual». **QORE-alpha está EXCLUIDO DE TODO EL PROGRAMA VT08 ACTUAL.** No hay un track alpha, fork, híbrido, alternativa ni fuente de reglas o cognitiva alpha. Que una herramienta de ejecución sea genérica y resida en el repo QORE CORE no la convierte en estrategia QORE-alpha. Si un documento histórico propuso `VT08-QORE-ALPHA`, dicha propuesta fue **ANULADA**. Contrato canónico: [VT08_OWNER_SCOPE_CURRENT_ONLY_NO_QORE_ALPHA_2026-10-15.md](VT08_OWNER_SCOPE_CURRENT_ONLY_NO_QORE_ALPHA_2026-10-15.md).

**Veredicto real a este corte: `VT08_NOT_CERTIFIED`.** `AUTHOR_TTRADES_SOURCE_COMPLETE=0`; `REAL_COGNITIVE_ADMISSIONS=0`; `AUTHENTIC_INDEPENDENT_AB_SIGNOFFS=0`; `BROKER_FILLS=0` para la nueva familia auditada; `PF_NET, MaxDD, Sortino, Sharpe, MonteCarlo, OOS=NOT_EVALUABLE`. **GitHub Actions PASS valida software/custodia y hechos físicos, NO certifica trader, metodología ni profitabilidad.**

**Cómo usar este handoff:** es el punto de entrada resumido e integral, no reemplaza los informes fuente detallados A R3–R8, B R1–R25 ni los handoffs anteriores. Incluye el trabajo terminado, evidencias Actions comprobadas, conflictos de interpretación, problemas, riesgos, soluciones y una lista ordenada de acciones ejecutables. Al reanudar, leer primero secciones **0, 1, 8, 9, 12–16**, verificar HEAD/PR/retención de artifacts, y **NO** recrear desde cero el censo geométrico.

---

## 0. Control de versiones, responsables y límites de esta transferencia

- **Repositorio:** [mezas3238-hue/qore-core](https://github.com/mezas3238-hue/qore-core), privado y accesible por GitHub conectado.
- **Rama A (metodología):** `agent/vt08-5m-methodology-source-20261010`, [PR #765](https://github.com/mezas3238-hue/qore-core/pull/765), **DRAFT**, HEAD verificado **ANTES de emitir este handoff** `d7d9b5dd4dea10f2f82fe731d3e6698dde33ae9e` (17-oct-2026); si aparece un nuevo commit, revisar diff. Arquitecto A: interpreta fuente TTrades y produce evidencia autónoma de cada candidato; NO es revisor B.
- **Rama B (cognitiva, custodia y revisor independiente):** `agent/vt08-5m-cognition-replay-20261010`, [PR #764](https://github.com/mezas3238-hue/qore-core/pull/764), **DRAFT**, HEAD verificado **ANTES de emitir este handoff** `e69d0f0fb3c028a178b809926573ede49b13a9a4` (19-oct-2026); este mismo documento introducirá nuevos commits al escribirse.
- **Coordinación metodológica:** [issue #762](https://github.com/mezas3238-hue/qore-core/issues/762). **Revisión B:** [issue #763](https://github.com/mezas3238-hue/qore-core/issues/763).
- **Histórico de continuidad:** [A R8 15-oct](VT08_HANDOFF_MAESTRO_ARQUITECTO_A_CONTINUIDAD_CERTIFICACION_R8_2026-10-15.md) (en rama A), [B maestro extendido 15–19-oct](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_HANDOFF_MAESTRO_ARQUITECTO_B_CONTINUIDAD_CERTIFICACION_2026-10-15.md), [master 14-oct](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_HANDOFF_MAESTRO_CERTIFICACION_METODOLOGICA_COGNITIVA_GATES_2026-10-14.md). Los informes específicos contienen SHA de cada artifact / caso.
- **No confundir esta rama** con experimentos CRT H4 ni `QORE-alpha` ni antiguos PR #634/#787 u otras familias C3/C4. Este handoff certifica el trabajo en **una familia M30 bullish C2 → M3 CISD/PS → C3 OPEN posicional**; otras familias sólo pueden entrar mediante delimitación y evidencias de TTrades genuinas, sin alterar la identidad que ya está congelada.
- **Restricciones:** no sizing adaptativo, lotaje dinámico, leverage/compounding, pesos de portfolio o ajuste de riesgo para superar PF/DD. No ejecutar LIVE/DEMO/VPS, ni fusionar ramas, ni tocar el **holdout 7Y sellado** sin autorización expresa y preregistro. No consultar PnL para seleccionar variantes de swing/POI. No subir archivos brutos cTrader licenciados a GitHub público. Mantener estrategia única VT08.

## 1. Misión y condiciones para llamar «certificado» al trader

La certificación es acumulativa y **no se puede saltar ninguna puerta**:

1. **G-MET / metodología TTrades real:** reglas originales con cita sección/URL y familia exacta; relevantes swing/POI/Protected Swing/cierre CISD/choosen EQ/breaker/stop/target con identificadores físicos, tiempos disponibles `as-of`, resolución de casos múltiples y datos verdaderos; `D` por falta de selector => `WAIT/ABSTAIN`. No convertir interpretación externa C en afirmación del autor.
2. **G-SRC / revisión cruzada A y B independientes:** productor A aporta contrato de evidencia por caso y original raw bar IDs/available_at; B reconstruye autónomamente desde cTrader y confronta artículos; contradicciones documentadas, y al menos dos votos genuinos e independientes; ni GitHub Actions ni la firma del propio modelo equivalen a un árbitro humano independiente.
3. **G-COG / cognitiva real:** 27 `CAUSAL_FIELDS` vinculados a valores auténticos de una `Situation` real (no una fila dummy): `value, rule_ref, source_bar_id, source_SHA, available_at, provenance`, razonamiento y `WAIT/ABSTAIN/EXECUTE`; integrar `CandidateEvent V2` y `evaluate_provenanced` con validación de firma A/B REAL. Sin metodología source-complete, cognitiva 0 por diseño.
4. **G-EXEC / ejecución fiel:** entrada posicional concreta C3.open, temporalidad de market, BID/ASK, comisiones, swap/slippage/spread, stop real según régimen y objetivo HTF elegido, cierre y evidencias de fills de fuente real (o backtest reproducible con microestructura defendible); no sustituir por CE LIMIT del acelerador.
5. **G-ECON / economía robusta con Gates preregistrados:** PF net, Max DD, Sharpe, Sortino, retorno/expectancy 1R homogénea, densidad mínima, Monte Carlo, OOS y validaciones por mercado/período/sesión. Pre-congelar identidad, thresholds vigentes y reglas de veto antes de observar performance; comparar estratos, no «salvar» un PF con tuning.

**Umbrales heredados no armonizados:** el handoff A R8 registra `PF>=1.80, DD<=6R, MC p95 DD<=15R, P(terminal>0)>=0.90` para un contrato Owner histórico, mientras otro ensayo anterior #787 tenía `PFnet>1.15 / >=100 fills`. **No asignar automáticamente ninguno a esta familia nueva:** obtener del Owner/contrato congelado el set de gates aplicable y sus denominadores; Sharpe/Sortino/densidad requieren thresholds versionados. No hay cálculo neto válido todavía.

## 2. Identidad de datos y universo inmutable: qué significa cada cifra

**Familia física censada:** C2 bullish M30 barre `C1.low` (no `C1.high`), termina en rango de C1 y tiene al menos una figura CISD/PS **proxy** M3 dentro de C2. La entrada candidata estaría en el open de C3 M30, siempre **no orden autorizada**. Ver [A R3](VT08_A_R3_FROZEN_BULLISH_M30M3_FULL_SOURCE_CANDIDATE_CENSUS_AND_B_PROOF_PACKAGE_2026-10-15.md) en rama A.

| Clasificación del censo A R3 | Total |
|---|---:|
| M30 C2 examinadas sobre 5 mercados / ventanas NY | **93.230** |
| C1/C2 incompleto | 83 |
| Agregados M3 vs M15 inconsistentes | **0** |
| No cumple sweep/cierre bullish especificado para familia | **85.312** |
| Cumple C2, sin figura CISD/PS M3 geométrica | **4.702** |
| Figuras M3 múltiples (selección D, no descartadas del conocimiento) | **476** |
| Figuras M3 únicas, source author por adjudicar | **2.657** |
| Techo geométrico una por mercado/día NY | 1.987 días-mercado |

**Desglose de 2.657 geometrías**: EURJPY **538**, USDCHF **518**, NZDUSD **550**, CADJPY **516**, USDCAD **535**. Los 2.657 son «eventos físicos únicos» **no** 2.657 operaciones/fills/Protected Swings auténticos; los 476 múltiples no deben esconderse si se estudia la fidelidad general.

**Contextos 3 H1 totalmente cerrados pre-C2:** 2.656/2.657 con doce M15 completas; 1 CADJPY en cuarentena. La ventana de tres H1 cerradas pre-C2 es una precaución causal del estudio, **NO** la misma definición que el lookback TTrades 3 HTF **incluyendo la vela actual**. Un pivote confirmado de 3 velas requiere el lado derecho cerrado; una ventana viva de 3 HTF tiene otra identidad/clock.

**R7 A, tres fuentes fuente-física (pivote/H1 target/EQ) sin sellar semántica:** de 2.657, **2.119** sin pivote H1-low básico en esas 3 H1 pre-C2; **485** con pivote low y múltiples H1 high untouched; **52** con pivote low y un high; **1** sin contexto H1. Los 52 **no son trades**, ni «fieles» TTrades; hay 537 pivotes lows H1 físicos y falta separación/relevancia auténtica.

## 3. Custodia de fuente y ejecución: no perder los originales

| Fuente / caso | Actions run, comprobación | Archivo y precaución |
|---|---|---|
| M3 cTrader RAW 5 mercados | [#35941643396](https://github.com/mezas3238-hue/qore-core/actions/runs/35941643396) | artifact `qore-vt08-m3-fractal-{MARKET}-bc1379d7661aac202495ec67afdd3098473ba723` → `m3-evidence.json` |
| M15 1.095 días 5 mercados | [#35934924907](https://github.com/mezas3238-hue/qore-core/actions/runs/35934924907) | `qore-vt08-cognitive-5m-fresh-{MARKET}-b2d33e1b4829d8b4afc76983decca8a99131403c` → `market-evidence-1095d.json` |
| A R3 universo original source-firstfail | [#38715560333](https://github.com/mezas3238-hue/qore-core/actions/runs/38715560333) | `vt08-a-frozen-m30m3-firstfail-{MARKET}-394116f13449fc310d7fbc5f0b5f60aa1bb247d4` |
| A R6 untouched H1 | [#38763309669](https://github.com/mezas3238-hue/qore-core/actions/runs/38763309669) | targets H1 por source IDs, 2.437 múltiples |
| A R7 unión triple ciega | [#38765076497](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497) | 2.657 / 52 subconjunto de revisión |
| B R7 independencia raw | [#38748150948](https://github.com/mezas3238-hue/qore-core/actions/runs/38748150948) | **88.276/88.276** recibos bar ID cotejados |
| B R18 fuente POI temporal | [#38902918264](https://github.com/mezas3238-hue/qore-core/actions/runs/38902918264) | FVG H1, primer toque M3 ID/timestamp, 2.657 |
| B R19 muestras 107 pre-PnL | [#38903529731](https://github.com/mezas3238-hue/qore-core/actions/runs/38903529731) | originales 50+50+4+3, seed/hash report por mercado |
| B R20 POI vs run M3 | [#38975212429](https://github.com/mezas3238-hue/qore-core/actions/runs/38975212429) | contacto FVG y source IDs opposing run |
| B R22 contexto multipois | [#38975204483](https://github.com/mezas3238-hue/qore-core/actions/runs/38975204483) | NY DTD y 107 fichas enriquecidas |
| B R23 expedientes 107 | [#39037632164](https://github.com/mezas3238-hue/qore-core/actions/runs/39037632164) | 856 preguntas abiertas, ninguna autor completa |
| B R23 validador dos firmantes | [#39037926346](https://github.com/mezas3238-hue/qore-core/actions/runs/39037926346) | 107 WAIT, trust root Owner **vacío** |
| B R24 bajo PS proxy deteriorado | [#39096870184](https://github.com/mezas3238-hue/qore-core/actions/runs/39096870184) | 809 requieren reevaluación de ancla vieja |
| B R24 visor de 10 M3 por caso | [#39096729106](https://github.com/mezas3238-hue/qore-core/actions/runs/39096729106) | 5/5 jobs SUCCESS; snapshots source-only |
| **B R25 última auditoría** | **[#39338842612](https://github.com/mezas3238-hue/qore-core/actions/runs/39338842612)** | **6/6 SUCCESS, 20 tests + 5 mercados, 316 breaches corrected-low, 301 reclaims, 15 no-reclaims** |

**ATENCIÓN: GH Actions suele aplicar retención ~30 días y los artifacts NO son permanentes.** Hacer inventario de `artifact_id, run_id, SHA256 JSON, SHA raw cTrader, market` y archivar según política/autorización de licencias; no inferir disponibilidad sólo por enlace de Actions. Si falta fuente, reconstruir de original licenciado con hash y documentar nueva custodia, NO falsificar datos ni usar el holdout 7Y. Usar relojes UTC por barra y zona America/New_York con DST real cuando proceda. Los 1.202 reseteos de segmentos en H1 de R6 son cuarentenas ante discontinuidad M15, no necesariamente error de broker.

## 4. Cronología histórica de trabajos realizados (por fases)

### Fase previa / 10–14 octubre: arquitectura y falsación antigua

- Se auditó `VT08_COGNITIVE_EXPANSION_5M` y los contratos `Situation`, reasoning `WAIT/ABSTAIN/EXECUTE`, WAL, persistencia, fuente `as-of`, replay cognitivo, calidad de pruebas y separaciones A/B. Handoff: [B maestro previo](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_COGNITIVE_EXPANSION_5M_MASTER_HANDOFF_2026-10-10.md) y [cognitive transfer](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_COGNITIVE_CORE_TECH_TRANSFER_V1.md).
- Universo H4/M15 legado: 11.655 anclas, 488 candidatos, 457 terminales del replay B01; **son prototipos/replay, no fills de VT08-M30/M3 source-complete**. B verificó 488 linajes, 495 recibos PS/FVG y 294 geometrías C3/C4 M15. C3/C4 y estrategia M30C2→C3 POS no son automáticamente la misma identidad.
- Prototipo económico OLD M30/M3 PS-only: [#38160918903](https://github.com/mezas3238-hue/qore-core/actions/runs/38160918903), **PF bruto POS 0,964184**, LIMIT 0,894996, DD POS bruto ~102,62R en ~3.561 simulaciones OHLC hipotéticas. Fue **NO-GO para ese prototipo**, NO evidencia que TTrades VT08 auténtico sea perdedor ni permiso para tuning de PnL. Antigua issue #787 CLOSED/SUPERSEDED, no resucitar como holdout virgen.
- A inicializó `three-verdict-gate GO/NO_GO/NO_EVALUABLE`, congelación de familia y cuaderno de prioridad de fuente; B revisó mercado/source map para evitar aceptación de misma SHA en mercados diferentes, rechazo de NaN/infinitos, relojes y future data, y verificación de bar-ID por mercado. Herramientas Trader Lab indexado y QORE Research Ultra Fast para **ejecutar pruebas de fuente** si preservan semántica; el acelerador CE LIMIT NO implementa automáticamente el trade posicional C3 OPEN.

### 15 octubre: Censo A y auditorías B R1–R17

- **A R3**: cinco mercados, 93.230 M30 C2, 2.657 figuras únicas, 476 multiformas D, 2.656 contextos H1 completos, receipts originales SHA y firstfail. Fuente original y corpus cTrader M3/M15 verificados. Ningún PnL.
- **A R4–R7**: ruteo Trader Lab, mercado fuente, 2.657 EQ condicionales, H1 target untouched físico y pivotes H1, 52 casos con pivote básico + único H1 target; **no** author-signoff. Revisión B externa: 88.276 originales RAW bar IDs, 5 mercados.
- **B R1–R7**: custodia/provenance, `source_raw_market_map`, autoría de datos, diferencial runner indexado, 93.230 C2 auditadas y 88.276 bar IDs físico vs raw; sintéticos de contrato no deben reportarse como señales.
- **B R9**: contrastes H1 target y geometría con M15 original, no selección arbitraria de target.
- **B R10**: cola ciega 2.657 y **71.739 celdas faltantes** (=2.657×27 `CAUSAL_FIELDS` sin valores y recibos auténticos), [#38788882608](https://github.com/mezas3238-hue/qore-core/actions/runs/38788882608) SUCCESS 5/5 y 100 tests; ninguna cognitiva real admitida.
- **B R11/R12**: 2.504 CISD geométricos M3 **antes** cierre C2, 153 simultáneos al cierre C2, 0 posteriores; 2.657 disponibles `as-of C3.open`. Importantísimo no antedatar una confirmación disponible sólo en el último M3.
- **B R13**: separa pivote M30 confirmado de ventana HTF de tres barras que incluye la actual; barrido por C2 impide tratar sin prueba el mínimo C1 como pivote simétrico confirmado. [R13](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R13_DEEPSEEK_CONTRACT_PRIMARY_SOURCE_AUDIT_M30_PIVOT_CAUSAL_2026-10-15.md).
- **B R14**: 2.657 series originales down-close y cierre CISD sobre su nivel reconstruidos de raw M3, [#38798284641](https://github.com/mezas3238-hue/qore-core/actions/runs/38798284641) PASS, geometría **no** protected swing autor.
- **B R15**: corrección de DeepSeek V2 EQ: para C2 bullish **contra swing bajista** se emplea `(C2.close+C2.high)/2`, **no** `(close+low)/2`; si cierre con swing, `(high+low)/2`. 2.576/2.657 difieren de fórmula errónea en comparación condicional; no autorizar cuál sin reference swing. [#38803620750](https://github.com/mezas3238-hue/qore-core/actions/runs/38803620750) PASS.
- **B R16 OWNER:** exclusión efectiva QORE-alpha para ambos arquitectos, contrato y test fail-closed sobre 2.657 ([#38805194446](https://github.com/mezas3238-hue/qore-core/actions/runs/38805194446), 5/5 y 170 tests). Este validador de fuente debe **integrarse todavía en todos los futuros admission manifests/operativos**: CI puntual no equivale a guard universal.
- **B R17**: fuente primaria vs DeepSeek y semántica de ocho preguntas; distinguir POI importante de existencia física, continuidad vs reversión y Protected Swing por serie causal; corrigió referencias de stop/ breaker/ EQ. [R17](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R17_DEEPSEEK_V4_OCHO_AMBIGUEDADES_DICTAMEN_FINAL_SOURCE_FIRST_2026-10-15.md).

### 16 octubre: reconstrucción contexto POI R18–R22, no trades

- **R18:** cinco mercados, 2.657 física, reconstrucción desde **tres H1 completamente cerradas pre-C2**: **574 FVG geométricos** (290 bullish, 284 bearish), **165 bullish FVG con primer contacto M3 antes de la vela CISD**, 4 primeras interacciones en la propia M3 confirmadora (tick-order UNKNOWN), 20 posteriores, 382 sin contacto en C2. **1.694** casos tocaron al menos uno de tres lows previos H1 antes de la barra CISD; uno CADJPY sin fuente H1 y en cuarentena. Es catálogo local, no conjunto exhaustivo de POI posibles de todo el historial.
- **R19:** **107 expedientes** preseleccionados por SHA/seed **sin ver PnL**: 50 FVG bullish pre-CISD + 50 controles sin FVG H1 local + 4 primeros toques en confirmación M3 intrabar + 3 bearish FVG negativos. Perfiles fuente M3/M15 SHA, **0 revisión humana/0 firmas**.
- **R20 POI→serie bearish:** entre 290 bullish FVG previos: 95 primer toque anterior al inicio del run M3 (73 recontactaron durante run; 22 no), **70** primer toque durante el run; => **143** bullish FVG contactaron en algún punto la serie bearish M3 y coincidieron en una misma M3 con barrido C1.low. Misma M3 NO prueba orden intrabar de ticks y NO certifica `important POI`.
- **R20 distinto, orden C1 sweep→CISD:** la rama contiene `vt08_b_r20_intrac2_cisd_sweep_causal_order_v1.py`; NO confundir esa auditoría con R20-POI-RUN; ambas están documentadas en el handoff B anterior.
- **R21 NY day-to-date:** mínimo del día NY previo hasta C2.open (diagnóstico físico, NO POI del autor): **1.091** C2 barrieron también low NY DTD, **1.555** barrieron sólo C1.low pero NO NY DTD, **11** casos NY contexto incompleto; 2.657 intactos. El autor no define NY-midnight DTD como condición universal del Example1.
- **R22 competing POIs:** **17** casos intersección FVG bullish H1 pre-CISD y NY DTD low barrido; H1 prior lows candidatos pre-CISD: **963** casos con 0, **1.120** con 1, **418** con 2 y **156** con 3 (lows de velas, niveles pueden coincidir). 107 expedientes enriquecidos; no convertir 17 intersecciones en trades.

### 17 octubre: revisión semántica y mecanismo de confianza R23

- **R23 FIRSTFAIL:** une R20 POI-run + R22 competing contexts por 107 `case_id` SHA, rank congelado, relojes, testigos físicos; abre **ocho bloques de requisitos de evidencia por caso** (`relevant_swing`, `important_poi`, `protected_swing`, `equilibrium`, `breaker`, `stop_loss`, `target`, `cognitive`). **856 bloques de fuente pendientes** (107×8), NO 856 fallos de software ni 856 reglas independientes. [#39037632164](https://github.com/mezas3238-hue/qore-core/actions/runs/39037632164) 5/5 PASS, 60 tests.
- **R23 Ed25519 reviewer-contract:** [#39037926346](https://github.com/mezas3238-hue/qore-core/actions/runs/39037926346) 5/5 PASS y 120 tests. Código `vt08_b_r23_signed_semantic_review_contract_v1.py` verifica rol A/B, input SHA R19, ocho findings SOURCE con `URL TTrades+section, bar IDs, available_at<=C3`, firmas diferentes y payload canónico. **Registro Owner de claves públicas A y B está VACÍO e inmutable**; keys de tests son sintéticas, NO revisores humanos. **107/107 `WAIT_UNREVIEWED`**. Aun con dos firmas reales futuras sólo indica `DUAL_SOURCE_REVIEW_CONSISTENT_ONLY`, no autoriza fills/source-complete.
- Las decisiones metodológicas reales del autor no se obtienen firmando dos veces un hallazgo físico ni invocando un LLM dos veces con otro nombre.

### 18 octubre: R24 fuente M3, contradicción con PS proxy

- **R24 native [#39096870184](https://github.com/mezas3238-hue/qore-core/actions/runs/39096870184), 6/6 PASS**: en 2.657 originales `ps_low_proxy` de las velas bearish que antecedieron CISD era demasiado alto como ancla al momento C3 en **809 casos únicos**:
  - 564 CISD-bar.low ya menor que original run-low;
  - 348 M3 después CISD y antes C3 hacen low menor que original run-low;
  - 103 solapan ambas circunstancias; `564+348−103=809`.
  - Otros estados POST-CISD: 2.131 sin M3 low posterior inferior al viejo run-low, 25 retouch igual, 153 CISD al cerrar C2 sin M3 posteriores. **Ninguno equivale a PS verdadero validado**.
- **R24 reviewer visible [#39096729106](https://github.com/mezas3238-hue/qore-core/actions/runs/39096729106), 5/5 SUCCESS**: `vt08_b_r24_real_case_m3_source_review_v1.py`, ejemplos con las **10 velas M3 originales**, IDs y UTC, sin PnL ni firmas inventadas.
- TTrades publicó [How to Have Better Stop Losses (TTFM), 17-oct-2026](https://ttrades.com/how-to-have-better-stop-losses-for-trading-ttfm/); el reporte R24 registra opción de body-stop condicional si supera el 50% del **opposing run**, que NO es el EQ M30 C2, ni override automático del Example1 `SL below EQ AND breaker`. Revisar cita primaria y compatibilidad antes de programarla en entradas.

### 19 octubre: R25 corrige ancla en el CIERRE CISD y estudia posible recuperación

- **[R25 final CI #39338842612](https://github.com/mezas3238-hue/qore-core/actions/runs/39338842612), 6/6 SUCCESS**: 20 tests adversariales y cinco mercados con raw M3, SHA, R14 y R19 fuente inmutable, `vt08_b_r25_ps_reanchor_and_cisd_reclaim_native_v1.py` + workflow `vt08-b-r25-original-ps-reanchor-and-old-cisd-level-reclaim.yml`.
- **Corrección metodológica CRÍTICA de R24:** al cierre de la vela CISD el mínimo físicamente conocido es `corrected_low = min(original_opposing_run_low, confirming_CISD_M3.low)`. Una ruptura POSTERIOR debe compararse contra `corrected_low`, **no contra el low de la serie vieja**. Por eso, **316** nuevas rupturas genuinas del ancla AS-OF-CISD (no 348 contra el nivel viejo); **2.341** sin nueva ruptura bajo el ancla corregida. De 316: **43** ya recierran sobre el nivel antiguo de CISD en la misma M3 de nuevo low, **258** lo recierran en una M3 posterior antes o justo en C3.open, **15** NO lo recierran en ese corte. `43+258+15=316`.
- **No falsificar la interpretación:** los 301 recierres son sobre la **apertura de la serie ORIGINAL**. No garantizan un **nuevo CISD auténtico**, pues podría haber otra serie opuesta relevante que formó el nuevo low, y falta identificar el POI significativo con fuente. No usar 301 como `certified signals`, 15 como `losers` ni 2.341 como PS válidos.
- **Tres casos fuente concretos para continuación inmediata**:
  1. USDCHF **2023-09-27**, CID `83c687ffa373093c3ea211eafdbb4f015f9068cfc8aa0fceb5f8184799bcb990`: C2 13:00Z, primer CISD 13:06Z, run-low `0.91758`, CISD wick `0.91767`, bajo POST confirmado M3 hasta 13:12Z `0.91750`, bar ID `3d2c6d8041545d87abd49fafc600c68e8da2f5dc21a26f7178bc9001302d456a`. Recierra > viejo CISD-level `0.91782` en M3 que cierra 13:30Z (justo C3.open). **No fuente de nueva PS**.
  2. USDCHF **2023-11-07**, CID `c463ba07bb354d4cd617f8d3c0d1a8073a9cd9b67c7c3f19af43b6321189dbae`: C2 12:00Z / CISD 12:09Z, old-low `0.90072`, bajo POST a 12:15Z `0.90069`, source bar `00a27e66ca41b2da89410b6ce7b6ae011d6c750b91638cf24561014f993cae1a`, recierre sobre viejo CISD-level `0.90094` en M3 cierra 12:27Z. Todavía no se probó cierre sobre la serie que creó 0.90069.
  3. NZDUSD **2026-02-25**, CID `ab42c7b10290b2ab1af37cb9efc479fbc3366fb3f3a601f96810a95d510088d1`: C2 09:00Z / CISD 09:18Z, old run-low `0.59735`, pero **vela CISD low `0.59723`**; M3 a 09:21Z da `0.59733` (bajo el VIEJO proxy pero NO bajo ancla corregida). **No segundo low real** bajo el as-of-CISD. Este caso falsifica clasificar 348 de R24 automáticamente como breaches de la ancla correcta.
- Pruebas negativas prioritarias: **15 sin recierre**, + **316** con nuevo low, y **107 sample blind** (manteniendo universo 2.657) para inspección fuente autor. **No rebajar denominador ni seleccionar 15 por desenlaces de PnL.**

## 5. Fuentes originales y lo que SÍ/NO autorizan

| Concepto | Regla explícita de autor (A) | Falta / precaución (D o dependiente) |
|---|---|---|
| Relevant Swing | [Relevant Swings](https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/): pivot tres velas geométrico, lookback tres HTF incluyendo actual, separación cualitativa | No fórmula numérica; selector entre swings candidatos ni timeframe prioritario universal. No confundir pivot confirmado con vela derecha live |
| POI de reversión | [CISD Confirms](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/), [Ideal Formation](https://ttrades.com/ttrades-ideal-formation-high-probability-swing-points/): high/low/FVG importante, reacción + CISD que cierra serie opuesta | Qué POI de varios era importante y cómo seleccionar, pre-CISD vs resultado circular. FVG>swings>CISD retest se describe para continuaciones, NO jerarquía universal reversión |
| Protected Swing | [Protected Swings](https://ttrades.com/protected-swings-understanding-trends-and-invalidations/), [Positional Entries](https://ttrades.com/positional-entries-enter-before-the-expansion/): nivel importante y cierre sobre serie que produjo el extremo | `sweep + primer CISD proxy` no basta; revisar 809 stale, 316 correct-low breach, segunda serie/PS si existe y 476 múltiples |
| EQ Candle 2 | [EQ 10-oct-2026](https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/): full C2 high/low cuando C2 cierra con swing; C2.close a extremo correcto cuando contra swing | Elegir reference swing válido antes; no usar `dealing range EQ` genérico, contra swing bajista bullish `(C2.close+C2.high)/2`; C2 completo disponible al cerrar |
| Breaker bullish | [Breaker Blocks Simplified](https://ttrades.com/breaker-blocks-simplified/): Low→High→Lower Low→Higher High y up-close candles de estructura | Timeframe/ID del breaker, qué breaker-low aplica y si estaba terminado antes C3; 4 velas consecutivas no son requisito A |
| Stop de ejemplo M30→M3 | [Timeframe Alignment Example1](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/): long stop **debajo EQ M30 Y breaker-low** y espacio para FVG inferior, PS invalidation como contexto por otros artículos | Precio exacto, buffer universal, compatibilidad body-stop opcional 17-oct, PS vs breaker/EQ y RR neto. `SL<min(EQ,breaker-low)` necesaria en ejemplo, NO suficiente |
| Targets | [How To Set Price Targets](https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/): swing HTF highs/candle highs previos untouched | **2.437** con múltiples highs físicos, autor no dicta desempate global H1/H4/D1; target source-chosen antes de entrar, nunca por desenlace |
| Calidad CISD | [CISD Confirms](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/): cierre cruzando serie opuesta; V/strength/minimal consolidation como `usually` | No imponer ATR/pips/velas umbral como obligatorio del autor, evitar discriminar por PF; evidencia cualitativa independiente |

**DeepSeek V1–V4:** fuente secundaria de sugerencias NO autoridad; se corrigieron afirmaciones erróneas sobre pivote y H1 live, EQ condicional close-low, POI continuations→reversal, cuatro barras breaker y stop PS-only contra Example1. Todas las variantes alpha sugeridas fueron RECHAZADAS por Owner. [R15](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R15_DEEPSEEK_V2_FIDELIDAD_AUTOR_EQ_POI_CORRECCIONES_SOURCE_2026-10-15.md), [R17](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R17_DEEPSEEK_V4_OCHO_AMBIGUEDADES_DICTAMEN_FINAL_SOURCE_FIRST_2026-10-15.md).

## 6. Problemas descubiertos: síntomas, causa y solución del sucesor

| Código | Severidad | Problema real / peligro | Solución concreta verificable | Estado |
|---|---|---|---|---|
| **P0-01** | BLOCKER | **Swing relevante**: pivote geométrico ≠ relevancia y separación TTrades subjetiva; 3 HTF incluyendo actual ≠ 3 H1 cerradas | Por caso inventario TF/ohlc/bar IDs y as-of, arbitraje fuente cualitativa ciego A y B, comparar competidores. D=>WAIT si no hay selector. No inventar distancia | ABIERTO |
| **P0-02** | BLOCKER | **POI importante**: C1.low o H1 FVG tocado no garantiza importante ni seleccionado; 1.555 C2 no barren NY DTD, 574 multivelas low, 17 doble contexto | Analizar qué nivel creó movimiento real (FVG/high/low), prueba de importancia anterior al CISD, citas originales/ID y causalidad; negativos también | ABIERTO |
| **P0-03** | BLOCKER | **PS proxy físico no es PS TTrades** y su low original queda stale en 809 (R24), con ancla corregida hay 316 roturas POST y 15 sin recierre (R25) | Revisar toda la serie **que formó el NUEVO low**, si hay posterior CISD genuino, POI fuente y validación antes C3. Iniciar por 3 CIDs y 15 casos; B reconstruye independiente | ABIERTO |
| **P0-04** | BLOCKER | **476 C2 con múltiples shapes M3** excluidos de 2.657 únicos sin resolver selección source | Mantener como estrato D; no seleccionar la «mejor» por futuro; decidir por evidencia del autor o no especificable | ABIERTO |
| **P0-05** | BLOCKER | **EQ** fórmula A correcta, pero referencia swing real desconocida; DeepSeek close-low erróneo en bullish against bearish | Primero source swing/bias, THEN régimen `WITH/AGAINST`, Eq A, cite URL, disponible C3. No elegir por RR/PF | PARCIAL |
| **P0-06** | BLOCKER | **Breaker** no tiene identidad TTrades por trade; estructura Low High LL HH + up-close no demostrada para original C2 | Reconstruir swing sequence multi-TF y barras up-close `as-of C3`, que exista real breaker low; revisar Example1 applicability | ABIERTO |
| **P0-07** | BLOCKER | **Stop** sin PS/ EQ/ breaker source no es reproducible; FVG inferior/buffer y precedencia body-stop 17-oct con Example1 | Revisar fuente exacta nueva/antigua, registrar precedencia y `SL< EQ && SL<breaker-low` cuando corresponda, buffer no inventado; feed BID/ASK | ABIERTO |
| **P0-08** | BLOCKER | **Targets** 2.437/2.657 tienen múltiples H1 highs previos untouched; ausencia de desempate | Listar candidatos H1/H4/D1 y sus source IDs/available-at, contacto previo, fuente de selección; D si no existe selector TTrades | ABIERTO |
| **P0-09** | BLOCKER | **27 campos cognitivos**: 71.739 campo×caso sin fuente valor/semántica; tests de interface no generan Situation veraz | Autor source-complete primero; luego 27 receipts reales, M3/M15 SHA, as-of, WAL, independent B, `evaluate_provenanced`; nunca fabricar entradas | ABIERTO |
| **P0-10** | BLOCKER | **Dos firmas auténticas faltantes**: trust root Ed25519 Owner `A_METHOD={}`, `B_INDEPENDENT={}` | Autorización pública real por Owner/arquitectura, firmas de personas/identidades independientes, pruebas contra raw antes de configurar key registry mediante PR revisado. No usar claves sintéticas | ABIERTO |
| **P0-11** | BLOCKER | **R23 no es guard universal operativo**: source-review firmado no conecta aún a CandidateEvent V2 y cognitive ingress | Enlazar con validación criptográfica, source receipts y veto por campo; auditar rutas DEMO/LIVE, no habilitarlas hasta GO | ABIERTO |
| **P0-12** | BLOCKER | **BID/ASK neto incompleto**: QORE Native M1 snapshots históricos 3×~10 minutos (2020/2023/2026), no histórico continuo para entradas/salidas | Diseñar fuente legal íntegra M1/ticks BID/ASK por 3Y (o periodo congelado), spreads/fees, clock-exit/SL, reproducibilidad, revisar paridad con cTrader | ABIERTO |
| **P0-13** | BLOCKER | Gates PF, DD, Sortino, Sharpe/MC/OOS de diferentes contratos históricos pueden ser incompatibles; 0 fills | Congelar gates Owner aplicables a identidad/familia y volumen mínimo ANTES de resultados; economics sólo después de G-MET/G-COG/G-EXEC | ABIERTO |
| **P0-14** | BLOCKER | Riesgo PnL leakage por cribar 52/107/143/165/301/15 como cohorte «rentable» | Cohorte 2.657 original y firstfails siempre; estratos pre-PnL son revisiones, no corte de denominador de backtest; no mirar futuro | CONTROLAR |
| **P0-15** | BLOCKER | R24 dos definiciones de low (viejo run-low vs ancla as-of-confirmación); 348≠316 y caso NZDUSD muestra falso new-break | Adoptar ancla corregida R25 para evaluación temporal; distinguir ruptura de viejo proxy y ruptura de low corregido, mantener R24 como hallazgo de error | CORREGIDO FÍSICO, SEMÁNTICA D |
| **P0-16** | HIGH | 4 FVG first touch misma vela CISD; 143 coincidencias FVG/sweep misma M3 sin orden intrabar | `UNKNOWN` hasta ticks fuente con clock fiable. Nunca interpretar OHLC M3 como ticks ordenados ni falsos SL fills | ABIERTO |
| **P0-17** | HIGH | Datos faltantes (83 C1/C2 incompletos, 1 CADJPY H1, 11 NY day gaps; discontinuidades M15) | Cuaren­tena source gaps; sólo cerrar con feed original / SHA y relojes, nunca imputar posterior | CUARENTENA |
| **P0-18** | HIGH | `QORE-alpha` históricamente sugerido como track alternativo; contaminación de metodología o cognitiva | Contrato Owner R16, vetos por lineage/program/source, conectar guard al ingreso real; nunca mezclar features ni resultados alpha | PROHIBIDO / SOFTWARE GUARD PARCIAL |
| **P0-19** | HIGH | Artefactos GH con 30 días retención / raw cTrader licenciado, pérdida de cadena custodia | Verificar disponibilidad HOY, reproducir hashes y archivar bajo custodia autorizada; no subir original licenciado a repo público | URGENTE |
| **P0-20** | HIGH | Runner ultra fast genérico puede ejecutar CE LIMIT mientras VT08 define positional C3 OPEN, comparaciones no equivalentes | Validar paridad temporal/orden por sample con Trader Lab y QORE Research antes de usar acelerador; no cambiar orden para ganar velocidad | PENDIENTE |
| **P0-21** | HIGH | R3 sólo una familia bullish, H4/M15/H4 CRT históricas distintas; mezclar densidades y «tres sesiones» crea falsa cobertura | Mantener ledger de identidad de familias, 01/05/09 anclas Owner vs M30 C2 NY 01–13 ventanas, sesiones Londres/NY/Asia por fuente separadas y relojes DST; sin afirmar que 2.657 cubre todo VT08 | ABIERTO |
| **P0-22** | HIGH | DeepSeek atribuyó selectores/proporciones no presentes en artículos; nuevo artículo stop 17-oct y fuente EQ 10-oct alteraron lectura | Source URLs/sections con fecha y SHA/recibo de versión de contrato; B independiente, nunca aceptar texto externo como norma | PARCIAL |
| **P0-23** | HIGH | Cultura «CI verde = trader certificado», 0 firmas reales pese a 100+ tests, sesgo de progreso | Reportar siempre por separado `PHYSICAL_PASS`, `SEMANTIC_SIGNOFF`, `COG_RECEIPT`, `BROKER_FILL`, `ECONOMIC_GATE`; 0 en últimas cuatro hasta fuente | PREVENCIÓN |

## 7. Errores de CI encontrados y corregidos (para no repetir trabajo)

- Varios R15/R18/R19/R20/R24 fallaron en primer run por **Ruff** (orden de imports, líneas largas), tests sintéticos que combinaban una excepción esperada con una precondición de clock errónea, o helper `Decimal` incorrecto. Se corrigió test o estilo, **no relajando las barreras físicas**. Guardar logs de primeras ejecuciones; las corridas finales referenciadas arriba están verificadas SUCCESS.
- R18 test `naive clock` originalmente activaba `M3 gap` antes de evaluar naivety; se corrigió aislar el caso; el error de CI no era defecto de fuente cTrader.
- R24 caso NZDUSD mostró una **FALLA DE MODELO MENTAL**, no de pytest: comparar barra posterior con old-run-low cuando CISD ya imprimió low inferior da falso «segundo low». R25 reancló en low conocido al CIERRE de confirmación y cambió 348 old-proxy breaches a 316 corrected-anchor breaches. Esta es la corrección más importante después de R23.
- El validador de firmas R23 implementó `MappingProxyType` para que un payload no rellene el trust-root, pero sigue sin llaves autorizadas reales. `Ed25519 verified` demuestra integridad de voto, no la corrección del contenido semántico.
- Si el código A/B tiene cambiado un SHA o un artifact expira, CI fail-closed; no sustituir SHA inventada ni cambiar silenciosamente denominador de origen para hacerlo verde.
- Algunos informes históricos usan etiquetas R20 para **dos investigaciones diferentes** (orden C1/CISD vs cruce POI/serie bearish) y R23 para **dos contratos diferentes** (firstfail y Ed25519). Citar **nombre completo del informe, workflow y run ID**, nunca solo R20 o R23.

## 8. Checklist secuencial de trabajo pendiente del próximo arquitecto

**FASE P0 — asegurar custodia y leer el problema real (NO PnL)**

1. Verificar branches/HEAD/PRs/issues, estado de CI R25 y fuente M3/M15, R19/107, R23/dual-signature, Owner R16. Revisar informes R24+R25 y **volver a cotejar fuente física concreta**. Registrar commit HEAD al inicio y evitar subir cambios cruzados A/B sin coordinación.
2. Hacer backup **autorizado** y SHA de artifacts críticos antes de su expiración. La metadata de GitHub puede persistir sin bytes de artefacto, por eso comprobación de descarga necesaria. No tocar raw original ni 7Y.
3. Revisar en código `vt08_b_r25_ps_reanchor_and_cisd_reclaim_native_v1.py` junto a `vt08_b_r14_opposing_series_native_cisd_v1.py` y el `vt08_b_r23_semantic_review_firstfail_ledger_v1.py`. Si el helper r25 no representa `corrected_low=min(run.low,CISD.low)` o lee POST C3, abortar.
4. Preparar fichero `semantic_decision_ledger` separado de las geometrías: 107 case IDs y estado por regla, `source_url/section`, `bar_id SHA`, `price`, `available_at`, explicitar competidores. No introducir `approved=True` en generador de muestras.

**FASE P1 — adjudicación source auténtica de tres casos y controles**

5. A estudiar individualmente los tres casos `83c687...`, `c463ba...`, `ab42c7...` de §4. En cada uno:
   - reconstruir la **serie opuesta M3 que realmente crea el mínimo NUEVO**, no sólo serie del primer CISD;
   - decidir si existe **important POI pre-CISD** (FVG/high/low u otro genuino) con nivel/TF/source IDs y por qué ese y no otro;
   - evaluar si hubo **segundo cierre auténtico a través de la serie nueva** antes de C3 y si el low está protegido según autor. Si no hay regla de selección fiel y reproducible: `D_SOURCE_UNSPECIFIED` y `WAIT`;
   - adjuntar las 10 barras M3 + contexto anterior, número de barra que produce nuevo low y barra que confirma, sin mirar PnL.
6. B revisar esos **mismos tres** casos **independientemente** desde raw M3/M15 y artículos, sin copiar la conclusión A; emitir contraargumentos y disenso. Ninguno de los dos puede firmar por el otro. No generar Ed25519 keys como si fuesen identidad humana.
7. Revisar los **15** casos con nuevo low corregido y sin recierre del antiguo nivel hasta C3, todos con bar IDs, para encontrar si existe una invalidez **física** de un PS ya autorvalidado (normalmente no, porque autor PS aún 0) o simplemente una figura no confirmada; mantener `WAIT` cuando no haya fuente.
8. Después auditar estratos ciegos R19/R23 **107/107** de forma independiente (50 FVG+50 control+4 intrabar+3 bearish), incluyendo multipois y los **476** múltiples PS del censo general como problema separado. No reordenar casos por ganancia.
9. Documentar **un árbol de decisión semántica por familia** con nodos A explícitos y nodos D con `ABSTAIN`, sin transformar heurísticas subjetivas en filtros atribuidos al autor. D puede requerir nueva fuente/videos TTrades, no «formalización alpha» disfrazada.

**FASE P2 — de fuente auténtica a cognitiva real**

10. Una vez A/B llegue a acuerdos **sobre casos reales de fuente**, establecer bajo autorización Owner dos identidades de revisores independientes, sus **claves públicas** aprobadas en PR/contrato versionado (nunca private keys o claves sintéticas). Firmas criptográficas completan trazabilidad, pero volver a verificar cada bar ID/clock fuente.
11. Verificar selección correcta de referencia swing/POI/PS/EQ/breaker/SL/target y consumo total de evidence a C3 antes de elevar `methodology_source_complete`. Someter cualquier afirmación fuente positiva a verificación **exhaustiva** no sólo una muestra.
12. Conectar el resultado real al `CandidateEvent V2`, `evaluate_provenanced`, `Vt08ForexSituationModel`/WAL: poblar 27 field receipts genuinos con valor semántico, SHA, sources, as-of, flag unknown, revisión B. Sin ello `WAIT/ABSTAIN`; no introducir lógica de QORE-alpha.
13. Endurecer entrada universal con Owner R16 guard y desacoplar completamente investigación de rutas LIVE/DEMO/VPS hasta gates verde.

**FASE P3 — certificación económica y cierre**

14. Congelar de forma explícita family/sessions/timeframes, condiciones one-per-market/day NY, selección de datos/dev vs holdout, y thresholds PF/MaxDD/Sharpe/Sortino/MonteCarlo/expectancy/densidad. Separar dataset explorado (2023–2026) de OOS verdaderamente no visto; no autoabrir 7Y.
15. Obtener histórico BID/ASK+fees/slippage/stop execution coherente y suficiente; comprobar parity de QORE Research ultra fast o Trader Lab respecto a positional C3 OPEN, NO CE LIMIT.
16. Correr desarrollo con datos auténticos y métricas netas, stress spreads, episodios de mercado, composición temporal, tests de sensibilidad sin optimizar usando holdout, Monte Carlo reproducible. Si número de fills inadecuado => `NO_EVALUABLE`, no GO ficticio.
17. Autorizar liberación controlada de OOS/7Y sólo por Owner y protocolos de una sola lectura. Nunca mezclar validaciones de otras identidades.
18. Publicar artefacto de evidencia final dual A/B con hash y conclusión `GO / NO_GO / NO_EVALUABLE` según thresholds de esta familia; **no** abrir broker/merge sin permiso adicional.

## 9. Orden exacto de archivos/código para reanudar sin incertidumbre

**Leer PRIMEROS:**
1. Este handoff + contrato Owner [NO QORE-alpha](VT08_OWNER_SCOPE_CURRENT_ONLY_NO_QORE_ALPHA_2026-10-15.md).
2. [R25 FULL](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R25_2657_NATIVE_PS_REANCHOR_AND_316_OLD_CISD_RECLAIMS_2026-10-19.md), [R24 FULL](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R24_NATIVE_ORIGINAL_PS_PROXY_REANCHOR_809_OF_2657_PRIMARY_SOURCE_FIRSTFAIL_2026-10-18.md), códigos:
   - `src/qore/infrastructure/trader_lab/vt08_b_r25_ps_reanchor_and_cisd_reclaim_native_v1.py`;
   - `src/qore/infrastructure/trader_lab/vt08_b_r24_protected_swing_post_cisd_invalidation_v1.py`;
   - `src/qore/infrastructure/trader_lab/vt08_b_r14_opposing_series_native_cisd_v1.py`.
3. [R23 FIRSTFAIL](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R23_SEMANTIC_SOURCE_FIRSTFAIL_107_DOSSIERS_2026-10-17.md) + [R23 Ed25519](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R23_ED25519_INDEPENDENT_AB_AUTHOR_REVIEW_AUTHORITY_GATE_2026-10-17.md), source:
   - `vt08_b_r23_semantic_review_firstfail_ledger_v1.py`;
   - `vt08_b_r23_signed_semantic_review_contract_v1.py`;
   - `vt08_b_r19_blind_dual_rater_poi_queue_v1.py`;
   - `vt08_b_r24_real_case_m3_source_review_v1.py`.
4. [A R3 censo fuente](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-methodology-source-20261010/docs/research/VT08_A_R3_FROZEN_BULLISH_M30M3_FULL_SOURCE_CANDIDATE_CENSUS_AND_B_PROOF_PACKAGE_2026-10-15.md), [A R7 52](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-methodology-source-20261010/docs/research/VT08_A_R7_THREE_SOURCE_BLIND_REVIEW_52_PHYSICAL_UNIQUE_CONTEXTS_2026-10-15.md), [A R8 handoff](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-methodology-source-20261010/docs/research/VT08_HANDOFF_MAESTRO_ARQUITECTO_A_CONTINUIDAD_CERTIFICACION_R8_2026-10-15.md).
5. [B R18 POI](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R18_PRE_CISD_H1_POI_NATIVE_CAUSAL_CENSUS_2026-10-16.md), [R19 blind](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R19_PREREGISTERED_BLIND_POI_DUAL_REVIEW_QUEUE_2026-10-16.md), [R20 run](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R20_PRE_CISD_POI_BEARISH_SERIES_CAUSAL_JOIN_2026-10-16.md), [R21 NY](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R21_NY_DAY_TO_DATE_INTRADAY_LOW_SOURCE_CONTEXT_2657_CASES_2026-10-16.md), [R22 multipois](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R22_2657_MULTI_POI_SOURCE_CONFLICT_AND_107_BLIND_REVIEW_2026-10-16.md).
6. [B R10 27 fields](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R10_2657_BLIND_COGNITIVE_ADMISSION_27_FIELD_SOURCE_GAP_2026-10-15.md), [R15 EQ](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R15_DEEPSEEK_V2_FIDELIDAD_AUTOR_EQ_POI_CORRECCIONES_SOURCE_2026-10-15.md), [R17 TTrades](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R17_DEEPSEEK_V4_OCHO_AMBIGUEDADES_DICTAMEN_FINAL_SOURCE_FIRST_2026-10-15.md).
7. [A final family prereg](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-methodology-source-20261010/docs/research/VT08_A_FINAL_ONE_FAMILY_AUTHOR_FIDELITY_FROZEN_TRIAL_PREREG_2026-10-11.md) y reportes negativos anteriores, sin reutilizarlos como ensayo nuevo.

**No confundir herramientas:** `Trader Lab`/QORE Research pueden ejecutar código y comprobaciones fuente; su velocidad no reemplaza raw custody, source rule ni execution order model. **No es necesario que el próximo arquitecto repita 93.230 ni 2.657 geométricos para «demostrar avance».**

## 10. Definición explícita de siguiente resultado útil y criterios de parada

**Primer entregable exitoso que falta, de alto valor real:** una matriz de **tres CIDs originales** (§4 R25) con dos columnas de dictamen independientes A y B, y al menos estas referencias:

`case_id | market | C1.low | prior important POI/bar ID/as-of | relevant swing candidate IDs | opposing series ORIGINAL ids | new low creator series ids | exact new CISD bar ID/closed_at (if any) | PS candidate as-of C3 | disagreement/unknown | TTrades URL/section | A verdict | B verdict | reason WAIT/PASS`.

- Si ambos comprueban mediante fuente original y raw que **no existe nueva serie+close** para ciertos casos, documentar **negativo de ese mecanismo**; no afirmar que no exista otra estructura TTrades en cualquier TF.
- Si encuentran dos interpretaciones plausibles y TTrades no ofrece selector, el resultado valioso es **D / abstención verificable**, no una señal falsa.
- Sólo si la regla fue identificada ANTES de PnL y cada evidencia estaba disponible as-of C3, investigar la integración siguiente (EQ/stop/breaker/target y 27 field receipts).
- Un tribunal A/B real requiere independencia auténtica, no dos comentarios del mismo generador firmados como dos personas. Source semantics + crypto identities deben mantenerse diferenciadas.
- Los 15 no-reclaim, 316 changed-low y 107 blind NO son nuevas cohortes de certificación económica; son **prioridades diagnósticas sin outcome**.

**Orden de reportes en cada ronda:** `commit, CI RUN ID/CONCLUSION, source SHA, censo total, nº casos físicamente clasificados, nº SOURCE-author-real A/B firmados, nº cognition admitidos, nº fills netos, gate PF/DD/Sortino`. Si algún valor no existe => `0` o `NOT_EVALUABLE`, nunca extrapolar.

## 11. Riesgos epistemológicos, científicos y operativos que deben quedar públicos al siguiente arquitecto

- «Si existe un POI y el CISD cierra encima» **no equivale** a «ese POI justificaba este giro según TTrades»; first-touched high/low H1 puede ser un high/low geométrico irrelevante.
- «PS low que no volvió a romperse» **no equivale** a «protected swing» — la validación exige level significativo y cierre a través de **la serie correcta**.
- La posible PS formada después de un nuevo low R25 requiere **nueva serie source** y cierre as-of; recapturar nivel antiguo no basta.
- «CISD se ve en M3 al cerrarse» y «C2 quedó cerrado en M30» son condiciones con relojes diferentes; no aceptar evento a 13:06Z como si hubiera sido fuente HTF disponible a 13:00Z.
- La fuente nueva de stop 17-oct no autoriza reemplazar stops de Example1 por body-stop si no se ha probado familia/régimen; cuidado con comparar **50 % opposing M3 run** contra **EQ C2 M30** (magnitudes distintas).
- 107 expedientes no representan un set de validación OOS sin sesgo: se eligieron estratos físicos bajo seed pre-PnL para **auditar**; preservar todos 2.657/93.230 como contabilidad y tasa de rechazo física.
- 7Y holdout intacto no significa que DEV 2023–2026 aún sea «virgen»; ya se ha consultado intensivamente para construir proxies físicos (no PnL), documentar uso en reportes futuros.
- Distintos mercados, timeframes, sesiones y feeds pueden cambiar si un nivel es observable `as-of`; usar source IDs y clocks reales antes de construir `CandidateEvent`.
- No afirmar «0 trades rentables» cuando lo correcto es «0 trades source-complete EVALUABLES». Tampoco fingir que correr 60/120 tests comprueba rentabilidad.

## 12. Entrega y estado al 20-oct-2026

- Se deja este **HANDOFF MAESTRO INTEGRAL** guardado en el repositorio y se enlazará desde los [issues A #762](https://github.com/mezas3238-hue/qore-core/issues/762) y [B #763](https://github.com/mezas3238-hue/qore-core/issues/763), y desde ambos handoffs anteriores.
- PR A #765 y B #764 **DRAFT / UNMERGED**. No se han creado nuevas entradas ni firmado decisiones de fuente.
- **Último dato físico R25:** 2.657 original; 564 CISD lows más bajos que old-run-low; **316** rupturas POST del anchor corregido; 43+258=**301** recuperaciones del antiguo nivel, **15** sin recuperar; nunca 301 source-valid protected swings. Los 107 expedientes fuente quedan sin dos firmas humanas.
- **La infraestructura no es el bloqueo dominante.** El cuello de botella es la adjudicación semántica autor-real de swing/POI/PS y la selección de stop/target; después queda cognitiva verdadera y finalmente net profitability BID/ASK con Gates congelados.
- Progreso honesto a fecha del documento: **VT08 no certificado**. **QORE-alpha no está ni puede estar dentro del programa.**
