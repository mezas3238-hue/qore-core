# VT08 CRT PURE — MASTER HANDOFF 2026-10-13

> **14-OCT-2026 — DATOS ORIGINALES LOCALIZADOS Y REPLAY REAL COMPLETADO:** [RESULTADOS 33 FUENTES M5 / AUDUSD+USDJPY](VT08_CRT_PURE_ORIGINAL_QORE_NATIVE_M5_INSIDE_BAR_REPLAY_RESULT_2026-10-14.md). El Owner tenía razón: no se debe buscar Dukascopy/GetData/cTrader porque GitHub **Actions artifacts** conserva 12 originales (run 35166210458) + 21 nuevas (run 38193802541), **24.377.420 M5**. Originales AUDUSD artifact **10475697610** y USDJPY **10475389415**, con SHA/manifest anuales. Nuevo lector QORE Native original, sin URL de datasets externos, sin broker auth. [Replay #38546723415 SUCCESS 3/3](https://github.com/mezas3238-hue/qore-core/actions/runs/38546723415): **AUDUSD 69 control PF bruto 1,02491; inside 59 PF 1,10597**; **USDJPY 64 control PF 0,86449; inside 58 PF 0,98402**; 296.372 M5 consumidas. Datos hasta 2026-09-17 (falta tramo final 4 días solicitado), cohorte usada previamente, sin BID/ASK histórico ni costos ejecutables. El inside-bar Level B no queda fuente certificada y no se promueve por resultados. **PR DRAFT, 0 certificación, no sizing, no LIVE.** [Issue Data Vault #837](https://github.com/mezas3238-hue/qore-core/issues/837) requiere resguardar antes de expirar en diciembre.

> **ORDEN NUEVA OWNER 14-OCT-2026 — TRES FUENTES Y REPLAY SOLO INVESTIGACIÓN:** [COMPARACIÓN ROMEO / SPECULATORFL / TRADERFLAMESN Y PREREGISTRO](VT08-CRT-PURE-THREE-SOURCE-COMPARISON-REPLAY-2026-10-14.md). El Owner autoriza **replay de investigación para contrastar aportaciones** de las tres fuentes, levantando **solo para estos estudios** la pausa cuantitativa previa; sigue NO MERGE, NO DEMO/LIVE operaciones, NO VPS, NO producción, NO sizing/lotaje/volumen/apalancamiento. SpeculatorFL y TraderFlameseN comparten casi literalmente protocolos y no son dos pruebas independientes. Control R2-C ya implementado es QORE_ENGINEERING; nuevo ensayo compara únicamente el **contexto inside-bar en C1** (fuente Level B), manteniendo intacta la geometría de trades y reportando AUDUSD/USDJPY por periodos. Se ejecuta desde [workflow Three-Source](https://github.com/mezas3238-hue/qore-core/actions/workflows/vt08-crt-pure-three-source-insidebar-replay.yml); nunca etiquetar hipótesis Level B como regla Romeo ni certificar por PF. Estado económico debe consultarse en runs/artefactos; **NO INVENTAR resultados**. CSD, HTF-PD-array y jerarquía Model #1 siguen sin definición causal universal y NO fueron hechos filtros automáticos.

> **EXAMEN G-M1 FUENTE ORIGINAL Y COBERTURA DE CERTIFICACIÓN (13-OCT-2026):** [ACTA G-M1 primaria y código auditado](VT08-CRT-PURE-CERTIFICATION-PRIMARY-SOURCE-EXAM-GM1-2026-10-13.md). Verificado texto directo oficial RomeoTPT para old CRTH, key level journey/reaction, 50%, MOB, CRT incompleto, Model #1/OTE y no forzar operaciones. **CRÍTICO: `strategy_identity_ready()=True` NO significa selección old-level Model #1 cerrada**: `MODEL_1_REFERENCE_SELECTION=AMBIGUOUS` está fuera de `CRT_PURE_CORE_EXECUTION_CONCEPTS`. Bloquea G-M1 y G-M5 hasta acta metodológica específica, sin falsificar `CERTIFIED`. G-M2 real visual continúa OPEN: rama GitHub no contiene OHLC persistido suficiente en archivos; no se han inventado casos. Sin nuevos testigos ni investigación cuantitativa.

> **ORDEN ACTUAL DEL OWNER — MISIÓN PRIORITARIA (13-OCT-2026):** [CERTIFICACIÓN METODOLÓGICA Y COGNITIVA NO CUANTITATIVA](VT08-CRT-PURE-OWNER-NONQUANTITATIVE-CERTIFICATION-MISSION-2026-10-13.md). La finalidad del trabajo es **certificar la metodología CRT y que VT08 razona de forma causal/estructural correcta**, mediante fuentes originales y casos de mercado reales auditados sin PnL. QC-003 fue infraestructura auxiliar, **NO** gate de certificación ni justificación para seguir creando testigos. Los gates G-M1 a G-M5 constan en la misión; ninguno se declara PASS sin evidencia. **NO confundir** posible certificado metodológico con `CrtPureCertificationStage.CERTIFIED` global: económico/validación siguen pendientes, no se modifican ni simulan. No más cuantitativa, no sizing, no merge, no DEMO/LIVE.

> **AVANCE CUALITATIVO QC-003 (13-OCT-2026):** [testigo causal origin-level → Model #1 → Situation Model](VT08-CRT-PURE-QUALITATIVE-CAUSAL-SOURCE-WITNESS-QC003-2026-10-13.md). Implementado `CrtPureModel1CausalWitness` y bridge `build_model1_cognitive_situation` con validación temporal, precio/velas, parent C3, confirmación corporal, referencias múltiples como un único evento y estado `PARTIAL/WAIT` sin promoción automática. Admite referencia M15 o H4 explícita; RomeoTPT usa **old CRTH** en un mensaje original, y eso NO convierte cualquier swing-strength-1 M15 en un CRTH fuente-autorizado. Integridad/ready/destino externos se proporcionan explícitamente; la propiedad del old-level sigue `AMBIGUOUS`. Nueva interfaz solo piloto documental/sintético y SIN integrarse a adaptadores históricos R2-BY/BZ/CC/CD ni ejecutar backtests.

> **AVANCE CUALITATIVO QC-002 (13-OCT-2026):** [auditoría método↔código y corrección cognitiva](VT08-CRT-PURE-QUALITATIVE-COGNITIVE-SOURCE-CODE-AUDIT-QC002-2026-10-13.md). Corregido estado `PARTIAL` que antes podía clasificar como `WELL_SUPPORTED`/dar `EXECUTE`; ahora exige `WAIT` y conserva motivo en `auditable_why`. Pruebas semánticas del Cognitive Foundation y Cognitive Gate exitosas. R2-BY/BZ WFO pasados a manual-only para respetar pausa cuantitativa. Permanece pendiente la autoridad entre old highs/lows y el testigo de referencia causal que debe alimentar el Situation Model. Este aviso no reanuda las tareas cuantitativas antiguas.

> **ACTUALIZACIÓN DE GOBERNANZA — 13-OCT-2026 (PREVALECE SOBRE EL PLAN DE ESTE HANDOFF):** el Owner ordenó **suspender nuevas investigaciones cuantitativas** de VT08 y **volver a la investigación CRT metodológica, de fuentes y cognitiva, vela por vela**. Todas las instrucciones antiguas de ejecutar PF/WFO/Monte Carlo/optimización o nuevos ensayos cuantitativos se consideran **en pausa hasta nueva orden**. Leer primero [directiva Owner vigente](VT08-CRT-PURE-OWNER-QUALITATIVE-RETURN-DIRECTIVE-2026-10-13.md) y [primer cuaderno CRT Model #1 cognitivo](VT08-CRT-PURE-QUALITATIVE-MODEL1-COGNITIVE-RESEARCH-001.md). El resto del handoff conserva sus resultados históricos, NO son tareas activas. No merge/LIVE/producción/sizing/volumen.

**Repository:** `mezas3238-hue/qore-core`  
**PR:** #626 — `[DRAFT] VT08 CRT PURE — source identity + hybrid cognitive foundation`  
**Branch:** `agent/vt08-crt-pure-source-identity-001`  
**Prepared:** 2026-10-13  
**Repository state before this handoff commit:** `e49ed06db7e9fc5095e856491fcd68de7f61aca0`  
**PR state:** OPEN / DRAFT / UNMERGED / MERGEABLE  
**Commits before handoff:** 566  
**Changed files before handoff:** 376  
**Deployment authority:** NONE

---

## 0. OWNER HARD RULES — READ BEFORE TOUCHING CODE

This project is still research-only.

### Forbidden without explicit Owner order

- NO MERGE.
- NO VPS activation.
- NO DEMO activation.
- NO LIVE.
- NO production.
- NO real capital.
- NO FundedNext LIVE.
- NO outcome-aware tuning.
- NO future leakage.
- NO post-hoc rule promotion.
- NO fallback execution after ABSTAIN on the same source event.
- NO resurrection of a KILLED thesis.
- NO copying another trader's economics into CRT PURE.

### CRITICAL: SIZING IS FORBIDDEN INSIDE THE TRADER

VT08 CRT PURE must **not perform sizing or decide volume**.

The trader may decide:

- whether a valid CRT hypothesis exists;
- market-specific cognitive state;
- EXECUTE / WAIT / ABSTAIN;
- causal lifecycle / hypothesis state;
- position HOLD / PROTECT / EXIT only where explicitly researched and frozen.

The trader must not decide:

- position size;
- account allocation;
- leverage budget;
- capital fraction;
- risk budget;
- portfolio sizing;
- any volume multiplier.

Sizing/volume is external authority. It must not be used to manufacture PF, DD, expectancy, certification or economic viability.

Economic research in this PR must stay normalized in R/trade and trade-count/density terms.

### Cognitive authority boundary

Frozen intended authority:

`CRT -> CIBO/context -> QORE RISK -> EXECUTION`

The CRT trader is not a capital authority.

---

# 1. STRATEGY IDENTITY — WHAT CRT PURE IS

## 1.1 Core CRT semantics

Frozen central semantics:

- C1 = reference range.
- C2 = unilateral penetration + rejection/reclaim.
- Accepted body close outside = breakout, not the rejection condition.
- C3 = distribution window.

Current Model #1 execution lineage:

- H4 CRT structure.
- M15 confirmation/execution.
- source candle pierces an old high/low.
- body-close confirmation.
- wick-only confirmation is not accepted.
- original control entry = next contiguous M15 open after confirmation.
- structural stop = source extreme.
- principal frozen economic target in current research = fixed 1.5R.
- expiry = C3 close.
- same-M15 stop/target ambiguity = **STOP_FIRST**.

Competition policy:

`NEWEST_SUPERSEDES_CONFIRMATION_FIRST`

CRT-AMD / AMD / PO3 remain excluded.

Do not import VT31 or Turtle Soup methodology. Generic QORE cognitive architecture may be reused, but strategy rules, thresholds, targets, stops, sessions and market-specific economics may not be transferred.

---

# 2. COGNITIVE ARCHITECTURE ALREADY IMPLEMENTED

The PR contains a hybrid cognitive foundation with these layers:

1. MASTER_BRAIN
2. GLOBAL_WORLD_MODEL
3. MARKET_BRAINS
4. DATA_PERCEPTION_INTEGRITY
5. CRT_STRATEGY_IDENTITY
6. CIBO_MARKET_MEMORY
7. CRT_EXPERIENCE_MEMORY
8. ATTENTION_SYSTEM
9. CAUSAL_SITUATION_MODEL
10. HYPOTHESIS_LIFECYCLE
11. CROSS_MARKET_CAUSALITY
12. OPPORTUNITY_COMPETITION
13. UNCERTAINTY_METACOGNITION
14. ADVERSARIAL_REASONING
15. DECISION_SOVEREIGNTY
16. JOURNEY_DESTINATION_INTELLIGENCE
17. POSITION_INTELLIGENCE
18. COGNITIVE_AUDIT

Primary files:

- `src/qore/infrastructure/traders/crt_pure_cognitive_contract.py`
- `src/qore/infrastructure/traders/crt_pure_cognitive_state.py`
- `src/qore/infrastructure/traders/crt_pure_cross_market_cognition.py`
- `src/qore/infrastructure/traders/crt_pure_strategy_identity_memory.py`
- `src/qore/infrastructure/traders/crt_pure_certification_readiness.py`

Three market brains:

- CRT_AUDUSD
- CRT_USDJPY
- CRT_BTCUSD

They share immutable CRT Strategy Identity, but **must not share learned Trader Experience**.

Final cognitive action remains:

- EXECUTE
- WAIT
- ABSTAIN

Knowledge states:

- KNOWN
- PARTIAL
- UNKNOWN
- CONFLICTED

No invented numeric win probability is allowed.

---

# 3. DATA / MARKET SCOPE

Current markets:

- AUDUSD
- USDJPY
- BTCUSD

Historical cTrader M5 evidence already used:

- AUDUSD: history reaches at least 2011–2026 in current lineage.
- USDJPY: history reaches at least 2014–2026.
- BTCUSD: approximately 2017–2026 with schedule-aware completeness.

Evidence loader:

`src/qore/infrastructure/trader_lab/vt08_crt_pure_window_evidence.py`

Important:

- cTrader evidence is fail-closed.
- no fabricated missing bars.
- BTCUSD uses market-calendar-aware closed-slot semantics.
- provider duplicate contradictions fail closed.

---

# 4. EARLY BASELINES AND WHAT THEY PROVED

## R1 / initial baseline

Initial economics were insufficient:

- AUDUSD: 226 trades, PF ~0.885, about -10.25R.
- USDJPY: 205 trades, PF ~1.035, about +2.70R.
- BTCUSD schedule-aware baseline: ~384 trades, PF ~1.033, about +5.02R.

This established that CRT identity alone did not create a certifiable trader.

## R2-C close-unmitigated

- AUDUSD: 69 trades, PF ~1.025, +0.54R.
- USDJPY: 65 trades, PF ~1.032, +0.89R.
- BTCUSD: 140 trades, PF ~1.112, +5.80R.

Too sparse.

## R2-D CISD/FVG/OTE rescue

FALSIFIED.

Naive rescue through CISD/FVG/OTE was materially negative.

Do not repeat without a new preregistered methodological reason.

## R2-E / R2-F source multiplicity

Confirmed that the system is a multi-source / multi-hypothesis problem.

R2-F:

- 1,013 parents.
- 2,084 events.
- 590 parents with multiple source events.
- 481 concurrent awaiting hypotheses.
- 323 later confirmations.

This was a structural discovery, not an economic candidate.

## R2-G competition

Improved density, not edge.

Combined result around:

- 448 trades.
- PF ~1.048.
- +7.79R.

Not sufficient.

## R2-H universal RR filter

FALSIFIED.

Do not revive universal RR gating as a candidate-selection shortcut.

---

# 5. BTCUSD — CURRENT BEST-CLOSED MARKET

BTCUSD produced the strongest research result.

Candidate family:

- BTC_BEARISH
- BTC_REF2_PLUS
- intersection diagnostics

Key results already established:

### BTC_BEARISH

- 331 trades / ~8Y.
- PF ~1.491.
- +49.35R.
- DD ~8.78R.

### BTC_REF2_PLUS

- 266 trades.
- PF ~1.572.
- +36.15R.
- DD ~6.39R.

### Intersection

- 130 trades.
- PF ~1.803.
- +23.45R.
- DD ~4.30R.

### Neither population

- 210 trades.
- PF ~0.646.
- -32.75R.

The candidate survived major chronological blocks including approximately:

- 2018–2020
- 2020–2022
- 2022–2024
- 2024–2026

Current BTCUSD status:

**MARKET RESEARCH CERTIFIED / NOT GLOBAL TRADER CERTIFIED**

Reference documentation:

- `docs/research/VT08-CRT-PURE-BTCUSD-R3-CANDIDATE-FREEZE-001.md`
- `docs/research/VT08-CRT-PURE-BTCUSD-R3-MARKET-RESEARCH-CERTIFICATION-001.md`
- `docs/research/VT08-CRT-PURE-BTCUSD-R3A-CHRONOLOGICAL-001.md`
- `docs/research/VT08-CRT-PURE-BTCUSD-R3B-BLOCK-BOOTSTRAP-001.md`

Do not reopen BTCUSD merely because AUDUSD/USDJPY remain unresolved.

---

# 6. AUDUSD — HIGH-DENSITY RESEARCH LINEAGE

## R2-AO high-density fixed 1.5R

Approximately:

- 1,465 trades / 6Y.
- 244.2 trades/year.
- PF ~0.999.
- ~-0.66R.
- 4/6 positive years.

Important: density was real, edge was not.

## R2-AY confirmation geometry WFO

This was the first meaningful high-density causal improvement.

Baseline:

- 1,693 trades.
- PF ~0.9844.
- -11.43R.
- DD ~46.52R.

Retained:

- 1,463 trades.
- ~209 trades/year.
- PF ~1.02534.
- +15.69R.
- DD ~31.20R.
- 5/7 positive years.

## R2-AZ protection

BE_CLOSE_075 improved the candidate:

- 1,463 trades.
- ~209/year.
- PF ~1.03543.
- +20.60R.
- DD ~27.77R.

Still too thin economically after realistic friction.

## R2-BB fresh 2011–2016 candidate check

Candidate:

- 901 trades.
- PF ~1.06368.
- +21.97R.
- DD ~23.73R.

But wide BE0.75 control was better:

- PF ~1.07431.
- +36.07R.

Therefore the candidate did not uniquely explain the improvement.

## R2-BE 15Y control vs overlap candidate

Control BE075:

- 3,727 trades.
- 248.47/year.
- PF ~1.03599.
- +53.21R.
- DD ~61.11R.
- cost 0.02R -> PF ~0.98597 / -21.33R.

Overlap candidate:

- 2,645 trades.
- 176.33/year.
- PF ~1.0668.
- +69.07R.
- DD ~36.38R.
- cost 0.02R -> PF ~1.0152 / +16.17R.
- cost 0.05R -> negative.

Important: nominal PF was not enough. Cost margin remained weak.

---

# 7. AUDUSD ROOT CAUSE

## R2-BF

Dominant loss mechanism:

- 1,272 full -1R stops.
- about 86% of gross loss.

Gross positive components existed, but stop frequency dominated.

Clues observed:

- slots 1–3 negative.
- slots 4–6 positive.
- slot 5 PF ~1.273.
- REF1 PF ~0.979.
- REF2+ PF ~1.178.
- D2 weak.
- NOT_D2 stronger.

These were **clues only**, not promotion rules.

## R2-BG pre-stop path

Of 1,272 full stops:

- 895 never achieved a positive completed M15 close.
- 182 achieved positive close but < +0.25R.
- 1,077 / 1,272 = **84.67%** failed before meaningful favorable progress.
- 195 reached >= +0.25R.
- 69 reached >= +0.50R.
- 0 reached >= +0.75R and later ended full stop.

Root conclusion:

**AUDUSD is primarily an entry/selection viability problem, not a late position-management problem.**

## R2-BH DOA classifier

FALSIFIED economically.

It reduced DOA but worsened economics.

Do not repeat the same classifier formulation.

## R2-BI broad Expected-R

FALSIFIED.

- 2,189 retained.
- ~199/year.
- PF ~0.99625.
- -3.36R.
- DD ~64.53R.

Broad Expected-R did not solve the problem.

## R2-BJ small causal memories

Best arm:

`REF_DELAY_DIRECTION`

- 2,014 trades.
- 183.09/year.
- PF ~1.05794.
- +46.22R.
- DD ~27.68R.
- cost 0.02R -> PF ~1.00724 / +5.94R.
- cost 0.05R -> PF ~0.93625 / -54.48R.

Useful information, insufficient economic margin.

---

# 8. PASSIVE ENTRY RESEARCH — CRITICAL CORRECTION

## R2-BK capacity

Passive price capacity:

- NEXT_OPEN: 3,727 / 248.47y.
- SOURCE_OPEN: 2,503 / 166.87y.
- CONF_RANGE_MID: 2,469 / 164.6y in original capacity census.
- CONF_BODY_MID: 2,430 / 162y.

Capacity only.

## Critical same-M15 correction

The first passive economic simulator could count a target on an earlier M5 before a later stop inside the same M15.

That violated the frozen CRT ambiguity contract.

The simulator was corrected to:

**aggregate/evaluate at M15 and apply STOP_FIRST if both are reachable in the same M15.**

Any pre-correction passive PF must be treated as superseded.

### AUTHORITATIVE R2-BM corrected run

Run:

`36055427737`

Corrected CONF_RANGE_MID:

- 2,462 trades.
- 164.13/year.
- PF **1.01916562**.
- +21.362854R.
- DD 44.450236R.
- cost 0.02R -> PF **0.97562377** / -27.877146R.
- cost 0.05R -> PF ~0.91433 / -101.737R.

The earlier PF ~1.1189 was INVALID/SUPERSEDED.

Conclusion:

**passive price alone does not create a post-cost edge.**

## R2-BO corrected terminal rearm

Run:

`36055427972`

CAP2 terminal rearm:

- 2,514 trades.
- 167.6/year.
- PF **1.01649472**.
- +18.712984R.
- cost 0.02R -> PF ~0.97288 / -31.567R.

Second trades: 52.

Conclusion:

**terminal rearm is insufficient and slightly worsens economics.**

## R2-BR cap2 concurrent OCO

Run:

`36055412564`

CAP2 concurrent OCO == CAP1:

- 2,462 trades.
- PF 1.01916562.
- +21.36R.

Diagnostics:

- secondary activated = 0.
- secondary winners = 0.

Conclusion:

under the strict R2-BR timing contract, no eligible concurrent secondary activation exists.

Do not generalize this as “multi-hypothesis never exists”; R2-F proved multiplicity in a different population/timing definition.

## R2-BS passive/BJ overlap

Run:

`36055412458`

Common OOS passive fills:

- 1,776 trades.
- PF 0.97837.
- -17.94R.
- DD 44.45R.

BJ-retained passive fills:

- 1,294 trades.
- PF **1.01676**.
- +10.02R.
- DD 27.06R.
- cost 0.02R -> PF ~0.97411 / -15.86R.

BJ-rejected passive fills:

- 482 trades.
- PF **0.87945**.
- -27.96R.

Conclusion:

BJ contains real directional information, but not enough economic margin for passive execution.

---

# 9. AUDUSD PASSIVE-OPPORTUNITY LEARNING

## R2-BT

Run:

`36077766140`

R2-BT changed the target variable correctly:

- passive fill -> actual corrected passive R.
- no fill -> 0R.
- no future leakage.
- 2 passive-valid rows lacked homologous feature records and were explicitly excluded rather than fabricated.

Results:

### REF_DELAY
- 1,233 fills.
- 112.09/year.
- PF 0.98751.
- -7.08R.

### REF_DELAY_DIRECTION
- 1,320 fills.
- 120/year.
- PF 0.99790.
- -1.29R.

### TIMING_REF_DELAY
- 1,394 fills.
- 126.73/year.
- PF **1.01782**.
- +11.28R.
- DD 30.20R.
- cost 0.02R -> PF 0.97443 / -16.60R.

Conclusion:

label alignment helped slightly, but still fails density and post-cost economics.

## R2-BW overlap Expected-R

Run:

`36078221492`

- 1,334 fills.
- 121.27/year.
- PF 0.96166.
- -23.97R.
- DD 49.58R.
- cost 0.02R -> PF 0.92099 / -50.65R.

FALSIFIED.

Do not reopen this overlap flag family without new causal evidence.

---

# 10. USDJPY ROOT CAUSE AND PASSIVE LINES

## R2-BL root cause

2014–2026:

- 3,056 trades.
- 254.67/year.
- PF ~0.94380.
- -74.58R.
- DD ~111.95R.
- 1,136 full stops.

Pre-entry quality failure:

- 761 never positive.
- 132 positive but < +0.25R.
- 893 / 1,136 = **78.6%** pre-entry failure.

Important market-specific observations:

- REF1 PF ~0.929.
- REF2+ ~0.978.
- D2 ~0.876.
- D3+ ~1.003.
- slots have different behavior from AUDUSD.

Conclusion:

**USDJPY must learn USDJPY structure; do not transfer AUDUSD selectors.**

## R2-BN small-memory Expected-R

FALSIFIED.

Baseline OOS:

- 1,968 trades.
- PF ~0.88942.
- -97.55R.

Best small memories remained negative.

## R2-BP passive capacity

- control ~3,056 fills / 254.67y.
- RISK_RETRACE_025: 2,114 / 176.17y.
- RISK_RETRACE_050: 1,333 / 111.08y.
- RISK_RETRACE_075: 853 / 71.08y.

Capacity only.

## R2-BQ corrected passive economics

Authoritative run:

`36055459147`

RISK_RETRACE_025:

- 2,114 trades.
- 176.17/year.
- PF **0.93050**.
- -73.28R.
- DD 100.47R.
- cost 0.02R -> PF ~0.89291 / -115.56R.

Deeper retracements were worse.

Conclusion:

**USDJPY passive retracement family is economically falsified.**

---

# 11. USDJPY OVERLAP / SMALL MEMORY RESEARCH

## R2-BU

Run:

`36060371524`

Best arm:

`REF_DELAY_OVERLAP`

- 1,331 trades.
- 166.38/year.
- PF **0.95745**.
- -23.09R.
- DD **38.19R**.
- 50% positive OOS years.
- cost 0.02R -> PF ~0.91082 / -49.71R.

This was materially better than baseline but still negative and slightly below density floor.

Signal useful, economics FAIL.

## R2-BV tie-safe overlap

Run:

`36077884981`

- 1,819 trades.
- 227.375/year.
- PF **0.90140**.
- -79.38R.
- DD 94.52R.
- cost 0.02R -> PF 0.85981 / -115.76R.

Tie-safe retention restored density but destroyed the useful economic separation.

Conclusion:

**do not treat threshold-tie handling as the missing edge.**

## R2-BX displacement-overlap toxic flag

Run:

`36078194144`

- 1,547 trades.
- 193.375/year.
- PF **0.94371**.
- -37.58R.
- DD 57.57R.
- cost 0.02R -> PF 0.89996 / -68.52R.

FALSIFIED as candidate.

---

# 12. EXPLICIT COGNITIVE EXPERIENCE — MAJOR STEP

The cognitive stack was then used explicitly rather than indirectly.

Preregistered contract:

`docs/research/VT08-CRT-PURE-COGNITIVE-EXPERIENCE-WFO-FREEZE-001.md`

Cognitive mapping:

- positive Expected-R + lower DOA than training baseline -> KNOWN.
- negative/non-positive Expected-R + high DOA -> CONFLICTED.
- mixed evidence -> PARTIAL.
- unsupported cell -> UNKNOWN.

Final action is produced by frozen:

`qore.infrastructure.traders.crt_pure_cognitive_state.reason()`

No numeric confidence invented.

## R2-BY AUDUSD Cognitive Experience

Run:

`36084033222`

Baseline OOS:

- 2,733 trades.
- PF 1.02370.
- +26.18R.
- DD 61.11R.
- DOA 29.53%.

### EXECUTE

- 815 trades.
- 74.09/year.
- PF **1.06376**.
- +18.87R.
- DD **18.38R**.
- DOA **24.91%**.
- cost 0.02R -> PF **1.00841** / +2.57R.
- cost 0.05R -> negative.

### WAIT

- 1,070 trades.
- PF **1.07138**.
- +31.04R.
- DD 28.30R.
- DOA 29.91%.
- cost 0.02R -> PF **1.02158** / +9.64R.

### ABSTAIN

- 848 trades.
- PF **0.93655**.
- -23.72R.
- DD 54.41R.
- DOA 33.49%.

Major conclusion:

**Cognition is separating toxicity.**

But EXECUTE density collapses.

Also:

**WAIT is not garbage; WAIT was economically stronger than EXECUTE.**

## R2-BZ USDJPY Cognitive Experience

Run:

`36084125329`

Baseline OOS:

- 1,968 trades.
- PF 0.88942.
- -97.55R.
- DD 107.53R.
- DOA 31.10%.

### EXECUTE

- 432 trades.
- 54/year.
- PF **0.97329**.
- -4.60R.
- DD **22.31R**.
- DOA 25.93%.

### WAIT

- 641 trades.
- PF **1.04210**.
- +10.31R.
- DD **20.12R**.
- DOA 25.27%.
- cost 0.02R -> PF ~0.99005 / -2.51R.

### ABSTAIN

- 895 trades.
- PF **0.77793**.
- -103.26R.
- DD 111.10R.
- DOA 37.77%.

Major conclusion:

Cognition isolated a highly toxic ABSTAIN population.

Again, WAIT contains the useful unresolved opportunities.

---

# 13. WAIT JOURNEY — STRONGEST NEW CAUSAL DISCOVERY

Preregistered lifecycle contract:

`docs/research/VT08-CRT-PURE-COGNITIVE-WAIT-RESOLUTION-FREEZE-001.md`

Rule:

- initial EXECUTE -> original entry.
- initial ABSTAIN -> terminal.
- initial WAIT -> observe exactly one completed M15.
- if structural stop is touched -> invalidated.
- if destination consumed -> no chase.
- otherwise observe first-M15 close in normalized original R.
- second decision may then reason again.

No third WAIT stage in this experiment.

## R2-CA AUDUSD WAIT Journey Atlas

Run:

`36172926396`

WAIT rows:

- 1,070.
- missing first M15 = 0.

Attribution by first completed M15 state:

### CLOSE >= +0.50R
- 127 trades.
- PF **13.9568**.
- +110.84R.
- mean +0.87275R.
- DOA 0%.

### CLOSE +0.25R to +0.50R
- 132 trades.
- PF **2.8036**.
- +51.73R.
- mean +0.39191R.
- DOA 0%.

### CLOSE 0 to +0.25R
- 231 trades.
- PF **1.4018**.
- +26.62R.
- DOA 19.48%.

### CLOSE -0.50R to 0
- 352 trades.
- PF **0.6506**.
- -56.78R.
- DOA 34.09%.

### CLOSE < -0.50R
- 83 trades.
- PF **0.11634**.
- -56.37R.
- DOA 60.24%.

### Destination consumed before reassess
- 40.
- +60R attribution.
- no chase allowed.

### Invalidated before reassess
- 105.
- -105R attribution.
- DOA 100%.

This is one of the strongest causal separations found in AUDUSD.

Important:

This atlas is attribution of the original-entry outcome by a later-but-causal-to-reassessment state. It is **not itself a trading rule** and must not be directly converted to a filter without a delayed-entry causal replay.

## R2-CB USDJPY WAIT Journey Atlas

Run:

`36172931454`

WAIT rows:

- 641.
- missing first M15 = 0.

### CLOSE >= +0.50R
- 60 trades.
- PF **5.6654**.
- +44.77R.
- DOA 0%.

### CLOSE +0.25R to +0.50R
- 90 trades.
- PF **2.7181**.
- +32.66R.
- DOA 0%.

### CLOSE 0 to +0.25R
- 155 trades.
- PF **1.6803**.
- +25.18R.
- DOA 13.55%.

### CLOSE -0.50R to 0
- 222 trades.
- PF **0.58517**.
- -39.96R.
- DOA 27.93%.

### CLOSE < -0.50R
- 54 trades.
- PF **0.26140**.
- -27.33R.
- DOA 61.11%.

### Destination consumed
- 14.

### Invalidated
- 46.
- DOA 100%.

Again, WAIT has strong causal trajectory information.

---

# 14. COGNITIVE WAIT RESOLUTION — CURRENT LATEST ECONOMIC RESULT

## R2-CC AUDUSD Cognitive WAIT Resolution

Authoritative run:

`36173116494`

Portfolio combines:

- initial cognitive EXECUTE;
- WAIT opportunities that survive one-M15 observation;
- second cognitive decision;
- delayed next-M15 entry only when second decision = EXECUTE.

Delayed entry:

- next M15 open.
- original structural stop.
- fixed 1.5R recalculated from delayed entry.
- original C3 close expiry.
- STOP_FIRST.
- AUDUSD BE_CLOSE_075.

Baseline:

- 2,733 trades.
- PF 1.02370.
- +26.18R.
- DD 61.11R.
- DOA 29.53%.
- cost 0.02R -> PF 0.97492 / -28.48R.

Cognitive portfolio:

- **1,067 trades**.
- **97 trades/year**.
- PF **1.07424084**.
- +28.1440R.
- DD **17.0056R**.
- DOA **24.18%**.
- origins:
  - 815 INITIAL_EXECUTE.
  - 252 WAIT_DELAYED_EXECUTE.
- positive OOS-year fraction: **72.73%**.
- cost 0.02R -> PF **1.01741** / **+6.804R**.
- cost 0.05R -> PF 0.93833 / -25.206R.

Research checks:

- PF improved = TRUE.
- Total-R improved = TRUE.
- DD improved = TRUE.
- DOA improved = TRUE.
- density >=170 = **FALSE**.

This is the strongest AUDUSD cognitive economic result so far.

Problem:

**quality improved strongly, but density collapsed to 97/year.**

## R2-CD USDJPY Cognitive WAIT Resolution

Authoritative run:

`36173125334`

Baseline:

- 1,968 trades.
- PF 0.88942.
- -97.55R.
- DD 107.53R.
- DOA 31.10%.
- cost 0.02R -> PF 0.84867 / -136.91R.

Cognitive portfolio:

- **511 trades**.
- **63.875/year**.
- PF **1.01154342**.
- +2.2637R.
- DD **15.1626R**.
- DOA **24.46%**.
- origins:
  - 432 INITIAL_EXECUTE.
  - 79 WAIT_DELAYED_EXECUTE.
- positive OOS-year fraction: 50%.
- cost 0.02R -> PF 0.96054 / -7.96R.
- cost 0.05R -> PF 0.88920 / -23.29R.

Research checks:

- PF improved = TRUE.
- Total-R improved = TRUE.
- DD improved = TRUE.
- DOA improved = TRUE.
- density >=170 = **FALSE**.

Conclusion:

Cognition nearly repaired USDJPY gross expectancy and massively reduced DD, but it is not economically robust and density is far too low.

---

# 15. WHAT IS FALSIFIED / DO NOT REPEAT

Unless there is a new preregistered causal reason, do not rerun these as tuning loops:

- naive CISD/FVG/OTE rescue.
- universal RR filter.
- broad Expected-R R2-BI.
- R2-BH DOA classifier formulation.
- AUDUSD passive price as standalone edge.
- AUDUSD terminal rearm as economic rescue.
- R2-BR strict concurrent cap2 OCO.
- AUDUSD passive overlap R2-BW.
- USDJPY passive retracement family.
- USDJPY BN small root-cause Expected-R family.
- USDJPY tie-safe overlap as an edge source.
- USDJPY displacement-overlap toxic flag R2-BX.
- post-hoc slot/ref/day rules from root-cause atlases.
- previously failed context/regime families I/J/K/L without new causal basis.

Do not destroy density merely to manufacture PF.

Do not treat a nominal PF around 1.03–1.07 as sufficient if 0.02R friction destroys expectancy.

---

# 16. CURRENT PROBLEMS THE NEXT ARCHITECT MUST SOLVE

## Problem 1 — AUDUSD quality-density frontier

R2-CC proves cognition can improve:

- PF.
- Total-R.
- DD.
- DOA.
- low-friction economics.

But only at **97 trades/year**.

Research density floor is roughly 170–250/year per market.

Mission:

Recover density without reintroducing toxic ABSTAIN states or using sizing.

Candidate directions must be causal and preregistered.

The best evidence currently points to the WAIT journey, not another static pre-entry filter.

## Problem 2 — USDJPY still lacks post-cost edge

R2-CD gross PF crossed 1.0 and DD collapsed from >107R to ~15R.

But:

- only 63.875 trades/year.
- cost 0.02R remains negative.
- positive OOS years only 50%.

Mission:

Find market-specific Journey Experience that improves delayed execution without importing AUDUSD states.

Do not transfer AUDUSD cell winners.

## Problem 3 — WAIT journey atlas is powerful but can be misused

CA/CB show extremely strong separation after one M15.

Danger:

Using the original-entry final outcome to pick the best journey bucket retrospectively would be post-hoc leakage at the research-design level.

The correct route is:

- delayed-entry outcome.
- prior-window learning only.
- next-year OOS.
- frozen bucket semantics.
- no threshold movement after result inspection.

R2-CC/CD already implement the first causal delayed-entry version. Any next extension must preserve this.

## Problem 4 — destination-consumed WAIT cases

Some WAIT cases reach the original destination before reassessment:

- AUDUSD: 40.
- USDJPY: 14.

Current contract correctly forbids chasing them.

Question for future research:

Can the cognitive architecture identify these cases earlier without leaking future information?

Do not simply enter after the target has already been consumed.

## Problem 5 — unresolved second WAIT population

R2-CC/CD use one WAIT stage only.

Second decision may still return WAIT/PARTIAL/UNKNOWN.

Current experiment takes no trade there.

A possible future research line is a **second WAIT journey**, but only after:

- quantifying how many cases remain unresolved;
- proving one-step WAIT result is stable;
- preregistering maximum wait horizon;
- proving no C3-expiry distortion.

Do not create an indefinite WAIT loop.

## Problem 6 — AUDUSD friction margin is still thin

R2-CC at 0.02R:

- PF ~1.0174.
- +6.8R.

At 0.05R:

- negative.

Therefore it is not yet certifiable.

Need genuine edge margin, not capital/sizing amplification.

## Problem 7 — USDJPY friction is still negative

R2-CD at 0.02R:

- PF ~0.9605.
- -7.96R.

Not candidate-ready.

## Problem 8 — exact candidate freeze not yet available for all 3 markets

BTCUSD is market-research certified.

AUDUSD and USDJPY are not final candidates.

Therefore global exact candidate freeze is not ready.

## Problem 9 — combined three-market replay is open

Certification readiness requires:

- exact candidate frozen.
- WFO green.
- Monte Carlo green.
- stress green.
- slippage green.
- robustness green.
- fresh holdout green.
- combined three-market validation green.
- full QORE green.

Current certification code:

`src/qore/infrastructure/traders/crt_pure_certification_readiness.py`

Do not bypass any gate.

## Problem 10 — some foundation documentation is stale

`docs/research/VT08-CRT-PURE-HYBRID-COGNITIVE-FOUNDATION-001.md`

still contains historical closure-state lines such as SOURCE_STRATEGY_IDENTITY = OPEN and MARKET_SPECIFIC_EXPERIENCE = OPEN.

The runtime/strategy-identity readiness has advanced beyond that document.

Next architect should reconcile documentation with the actual current code/evidence, but must not rewrite history. Mark old closure state as historical/superseded rather than silently changing prior facts.

---

# 17. NEXT WORK — EXECUTION ORDER FOR THE NEXT ARCHITECT

Do not stop after each test for permission. Continue the scientific loop unless a true Owner-only boundary is reached.

## Step 1 — Freeze and document R2-CA / CB / CC / CD

Create authoritative result docs for:

- R2-CA AUDUSD WAIT Journey.
- R2-CB USDJPY WAIT Journey.
- R2-CC AUDUSD Cognitive WAIT Resolution.
- R2-CD USDJPY Cognitive WAIT Resolution.

Bind:

- run id.
- head SHA.
- artifact hashes if available.
- exact economics.
- no-promotion decision.

## Step 2 — Audit R2-CC/CD implementation for causal correctness

Specifically verify:

- first WAIT M15 is fully completed before second decision.
- delayed entry is next M15 open.
- stop is original structural source stop.
- target 1.5R is recalculated from delayed entry.
- C3 expiry is unchanged.
- same-M15 ambiguity remains STOP_FIRST.
- AUDUSD BE_CLOSE_075 activates only from the next completed bar.
- USDJPY has no imported AUDUSD protection.
- no original-entry final outcome enters second-decision features.
- no source resurrection after ABSTAIN.

If any bug exists, corrected replay supersedes current economics.

## Step 3 — Quantify second-decision action populations

For each fold and market:

- how many initial WAIT.
- invalidated before reassessment.
- destination consumed.
- delayed candidates.
- second EXECUTE.
- second WAIT.
- second ABSTAIN.
- unsupported cells.
- each group's delayed-entry economics.

This must be done before opening a second WAIT stage.

## Step 4 — Attack AUDUSD density scientifically

Current best cognitive portfolio:

- 97/year.
- PF 1.07424.
- DD 17R.
- 0.02R PF 1.0174.

Goal:

raise density toward >=170/year **without losing post-cost positive expectancy**.

Priority research directions:

1. analyze the second WAIT/PARTIAL population causally;
2. test whether Journey Experience needs market-state memory in addition to journey bucket, but only one added dimension at a time;
3. investigate whether WAIT resolution can be dynamic within the same fixed maximum horizon;
4. use hypothesis lifecycle rather than static exclusion;
5. preserve ABSTAIN toxicity separation.

Do not use sizing.

## Step 5 — Repair USDJPY with USDJPY-only journey memory

Current R2-CD is a major risk reduction but not edge.

Priority:

- inspect second WAIT states.
- inspect delayed-execution journey cells by fold.
- identify whether the useful +0.25R/+0.50R first-M15 states survive when evaluated on delayed-entry outcomes, not original-entry outcomes.
- add at most one preregistered USDJPY-specific state dimension if required.
- do not import AUDUSD winner states.

## Step 6 — Only freeze market candidate when margin exists

Candidate should not be frozen merely because PF > 1.

Minimum practical expectations:

- causal WFO.
- acceptable density.
- stable positive OOS breadth.
- DD controlled.
- positive 0.02R stress with meaningful margin.
- no catastrophic 0.05R fragility if 0.05R is considered plausible for the execution environment.
- no single-fold dependence.

## Step 7 — Robustness only after material candidate exists

Then run:

- chronological block tests.
- rolling 2Y.
- block bootstrap / Monte Carlo.
- slippage/cost stress.
- perturbation robustness.
- provider/data integrity replay.
- fresh unseen holdout.

Do not burn fresh holdout on weak candidates.

## Step 8 — Three-market validation

Once BTCUSD + AUDUSD + USDJPY each have frozen candidates:

- integrated deterministic replay.
- no learned-experience sharing between markets.
- cross-market cognition may supply context only where allowed.
- normalized R economics.
- no trader sizing/volume.
- verify portfolio interaction without granting capital authority.

## Step 9 — Full QORE gate

Only after three-market validation:

- full cognitive gate.
- full QORE integration.
- authority-boundary audit.
- risk/execution seam.
- certification-readiness evaluation.

## Step 10 — Certification

Certification is evidence, not a declaration.

Only when every `CrtPureCertificationEvidence` gate is actually GREEN may stage become CERTIFIED.

Even CERTIFIED does **not** itself authorize DEMO, LIVE, production or capital.

---

# 18. CURRENT CERTIFICATION READINESS

Relevant code:

`src/qore/infrastructure/traders/crt_pure_certification_readiness.py`

Required independent validation flags:

- walk_forward_green
- monte_carlo_green
- stress_green
- slippage_green
- robustness_green
- fresh_holdout_green
- combined_three_market_validation_green
- full_qore_green

Current practical status:

### Source / identity

Largely implemented and runtime strategy identity reports ready in current cognitive labs.

### Market evidence

Historical evidence exists for all three markets in current research lineage.

### Deterministic replay

Substantial replay infrastructure is GREEN, but final exact-candidate deterministic replay is not closed because AUDUSD/USDJPY candidates are not final.

### Per-market forensics

Deep forensics exist, but AUDUSD/USDJPY economic closure is not complete.

### Exact candidate freeze

- BTCUSD: yes at market-research level.
- AUDUSD: no final candidate.
- USDJPY: no final candidate.
- global: no.

### Independent validation

Not globally complete.

### CERTIFIED

**FALSE**

### DEMO/LIVE/PRODUCTION/REAL CAPITAL

**NOT AUTHORIZED**

---

# 19. AUTHORITATIVE RECENT RUN INDEX

Use these as the primary recent references.

### Corrected passive / overlap

- R2-BM corrected: `36055427737`
- R2-BO corrected: `36055427972`
- R2-BQ corrected: `36055459147`
- R2-BR corrected: `36055412564`
- R2-BS corrected: `36055412458`

### Opportunity-learning / USDJPY overlap

- R2-BT: `36077766140`
- R2-BU: `36060371524`
- R2-BV: `36077884981`
- R2-BW: `36078221492`
- R2-BX: `36078194144`

### Explicit cognitive experience

- R2-BY AUDUSD: `36084033222`
- R2-BZ USDJPY: `36084125329`

### WAIT journey / resolution

- R2-CA AUDUSD: `36172926396`
- R2-CB USDJPY: `36172931454`
- R2-CC AUDUSD: `36173116494`
- R2-CD USDJPY: `36173125334`

### Cognitive Gate

Current HEAD cognitive gate at handoff preparation:

- run `36173125106`
- SUCCESS

---

# 20. KEY DOCUMENTS FOR CONTINUITY

Read these before modifying the methodology:

- `docs/research/VT08-CRT-PURE-HYBRID-COGNITIVE-FOUNDATION-001.md`
- `docs/research/VT08-CRT-PURE-COGNITIVE-EXPERIENCE-WFO-FREEZE-001.md`
- `docs/research/VT08-CRT-PURE-COGNITIVE-WAIT-RESOLUTION-FREEZE-001.md`
- `docs/research/VT08-CRT-PURE-AUDUSD-PF-ROOT-CAUSE-001.md`
- `docs/research/VT08-CRT-PURE-AUDUSD-CONFIRMATION-GEOMETRY-RESULT-001.md`
- `docs/research/VT08-CRT-PURE-USDJPY-CONFIRMATION-GEOMETRY-RESULT-001.md`
- `docs/research/VT08-CRT-PURE-R2BM-AUDUSD-PASSIVE-ENTRY-ECONOMICS-001.md`
- `docs/research/VT08-CRT-PURE-R2BN-USDJPY-EXPECTED-R-WFO-001.md`
- `docs/research/VT08-CRT-PURE-R2BQ-USDJPY-PASSIVE-ECONOMICS-001.md`
- `docs/research/VT08-CRT-PURE-R2BR-AUDUSD-CAP2-PASSIVE-OCO-001.md`
- `docs/research/VT08-CRT-PURE-R2BS-AUDUSD-PASSIVE-BJ-OVERLAP-001.md`
- `docs/research/VT08-CRT-PURE-R2BU-USDJPY-OVERLAP-EXPECTED-R-001.md`
- `docs/research/VT08-CRT-PURE-R2BY-AUDUSD-COGNITIVE-EXPERIENCE-001.md`
- `docs/research/VT08-CRT-PURE-R2BZ-USDJPY-COGNITIVE-EXPERIENCE-001.md`
- `docs/research/VT08-CRT-PURE-BTCUSD-R3-CANDIDATE-FREEZE-001.md`
- `docs/research/VT08-CRT-PURE-BTCUSD-R3-MARKET-RESEARCH-CERTIFICATION-001.md`

---

# 21. OPERATING MODE FOR THE NEXT ARCHITECT

The Owner expects continuous execution.

Required loop:

`run test -> read economics -> adjudicate -> document -> formulate next causal test -> preregister -> run -> continue`

Do not stop after each ordinary research test waiting for permission.

Stop only for:

- missing repository/data access.
- missing required external evidence.
- methodological change that changes CRT identity.
- Owner-only governance boundary.
- merge.
- VPS.
- DEMO.
- LIVE.
- production.
- real capital.

Technical GREEN is not economic PASS.

A failed candidate is a valid scientific result.

The mission is not to force VT08 to become profitable.

The mission is to determine, causally and honestly, whether a certifiable CRT PURE trader exists under the frozen methodology and QORE governance.

---

# 22. BOTTOM LINE FOR THE NEXT ARCHITECT

What has been learned:

1. BTCUSD has the strongest market-level research candidate and is already research-certified.
2. AUDUSD has weak but real structural edge that cognition improves substantially.
3. USDJPY baseline is poor, but cognition nearly neutralizes it and dramatically reduces DD.
4. The dominant loss mechanism in AUDUSD/USDJPY is pre-entry viability / DOA.
5. Static filters repeatedly failed to solve the problem without destroying density.
6. Passive-entry changes did not create robust edge.
7. Explicit cognition successfully separated toxic ABSTAIN populations.
8. WAIT is not indecision/noise; it contains major causal information.
9. First-M15 WAIT trajectory is the strongest recent state variable discovered.
10. One-step cognitive WAIT resolution improves quality and DD but still destroys density.
11. The unsolved frontier is now:

**recover enough causal density while preserving the cognitive toxicity separation and post-cost edge.**

12. Sizing/volume is forbidden inside the trader and is not a solution to this frontier.

Do not restart from generic filters.

Continue from the cognitive WAIT lifecycle.
