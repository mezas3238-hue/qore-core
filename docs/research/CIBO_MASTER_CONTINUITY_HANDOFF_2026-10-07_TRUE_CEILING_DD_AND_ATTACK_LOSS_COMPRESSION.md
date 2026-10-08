# ACTIVE WORK AT HANDOFF — 2026-10-08 10:33 UTC

> This block is informational and sits above the authoritative Carrier35240 state below.
> A new replay was launched after the Carrier35240 handoff state was determined. It had not completed when this handoff was finalized, so **do not assume a result**. The next architect must inspect this run first.

- Branch HEAD at handoff finalization: **36f86a721cbbfc4e5176e08c4e6a5bfc6518de3f**
- HEAD message: **research(cibo): preempt 2020 50-170x cluster from 1pct DD**
- Active run: **37764222387**
- Workflow: **QORE CIBO Carrier35240 W6 Early Defense Ridge**
- Workflow path: `.github/workflows/cibo-trader-lab-carrier35240-w6-early-defense-ridge.yml`
- Run head SHA: **36f86a721cbbfc4e5176e08c4e6a5bfc6518de3f**
- Objective: preempt the 2020 **50–170x** loss cluster beginning around ~1% live DD, now that the max-DD bottleneck migrated to Apr–May 2020.
- Status at handoff finalization: **IN PROGRESS**
- Required first action for successor: inspect run 37764222387 ranking before creating any overlapping W6 experiment.
- Promotion rule remains: preserve 3,368 entries, zero breach, frozen floor, and require a valid DD/economic improvement. Do not infer success from workflow launch alone.

---

# LATEST STATE OVERRIDE — 2026-10-08 10:32 UTC — CARRIER35240

> **THIS BLOCK IS THE AUTHORITATIVE CURRENT STATE. IT OVERRIDES THE 36.17% SNAPSHOT IMMEDIATELY BELOW.**
>
> A concurrent research run finished just before the prior handoff commit and pushed the DD frontier lower. Preserve the older MASTER UPDATE below as lineage, but continue from this block.

**Repository:** `mezas3238-hue/qore-core`  
**Branch:** `agent/cibo-causal-expectation-leakage-fix-001`  
**HEAD immediately before this correction:** `022878a8ece7e4ac9888e740fb09653751c2ce50`  
**Canonical handoff:** `docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md`

## Current best active dominant carrier — `m1-0700`

Decisive run:

- **37763827843 — QORE CIBO Carrier35838 PostW2 M1 Extension Ridge**
- workflow: `.github/workflows/cibo-trader-lab-carrier35838-postw2-m1-extension-ridge.yml`
- head SHA: **79500d771360f14a94dcc1a261cf7344a870dfca**
- case: **m1-0700**
- strict Pareto: **true**
- dominates-current: **true**
- floor-valid: **true**
- entries: **3,368 / 3,368**
- sovereign breach: **0 by workflow invariants**

Exact metrics:

- terminal capital: **USD 670,926.0074625642083966569884**
- capital above frozen USD 582,440.0252953678696769360345 floor:
  **USD 88,485.9821671963387197209539**
- max DD: **35.24018942564197395053048754%**
- total gross loss: **USD 959,362.0571599843609460255812**
- ATTACK gross loss: **USD 957,795.9847244472650145654346**
- PF: **1.699283448262004584163293675**
- ATTACK override count: **851**
- bootstrap override count: **108**

Improvement versus Carrier35838 comparator:

- capital: **+$0.1562844396065304681218**
- DD: **-0.5977788650072341990019841627 percentage points**
- total GL: **-$7.9458910893656818794540**
- ATTACK GL: **-$15.9391178666946602949352**
- therefore it improves all dominant-current gates used by this workflow.

## Current max-DD bottleneck after m1-0700

The max DD migrated again.

- peak: **2020-04-03T03:05:00+00:00**
- trough: **2020-05-13T06:15:00+00:00**
- max DD: **35.2401894256%**
- net by mode inside max-DD attribution:
  - **ATTACK: -USD 253.8994163924961170769880446**
  - **MEDIUM: +USD 5.412013474518243177149564713**

Therefore the immediate bottleneck is no longer the 2019 MEDIUM plateau. The next architect must now perform fresh forensics on the **2020 Apr–May ATTACK-dominated episode**.

Do NOT keep tightening the 2019 MEDIUM M1 control just because it produced the last jump. The bottleneck has migrated.

## How the last two jumps occurred

### Run 37763614889 — Carrier36173 PostW2 M1 Ridge

Starting from `tb-6500` at 36.17370%, a MEDIUM M1 extension found a narrow safe boundary.

Important dominant cases:

- m1-2250:
  - capital USD 670,937.1943
  - DD 36.005834%
  - strict Pareto + dominates-current
- m1-2300:
  - DD 36.039407%
- m1-2425:
  - DD 36.123340%

A more aggressive DD-first point:

- m1-2000:
  - DD **35.837968%**
  - capital USD 670,925.8512
  - but GL was slightly worse versus tb-6500, so it was not strict Pareto in that direct comparison.

This DD-first point became **Carrier35838** for the next extension sweep.

### Run 37763827843 — Carrier35838 PostW2 M1 Extension Ridge

The extension sweep resolved a new safe region.

Important cases:

- **m1-0700 — current best**
  - DD 35.240189%
  - dominates-current
- m1-0750:
  - DD 35.241528%
  - dominates-current
- m1-0800:
  - DD 35.254047%
  - dominates-current
- m1-0900:
  - DD 35.281002%
  - dominates-current
- m1-1000:
  - DD 35.307956%
  - dominates-current
- m1-1300:
  - DD 35.388820%
  - dominates-current
- m1-1500:
  - DD 35.502237%
  - dominates-current
- m1-1950:
  - DD 35.804395%
  - dominates-current

Rejected cliff below the safe region:

- m1-0500 / m1-0600:
  - terminal capital ~USD 551,746
  - below frozen floor
  - DD ~50.26%
  - therefore reject.

This is another discrete boundary: **0.0700 is currently the safe edge; pushing to 0.0600/0.0500 destroys the trajectory.**

## Immediate next mission

The program is now only ~0.2402 percentage points above the 35% milestone.

But 35% is NOT the goal.

Next steps:

1. freeze `m1-0700` exact parameters and artifact;
2. build a fresh top-10 DD atlas from `m1-0700`;
3. deep-forensics the 2020 Apr–May max episode;
4. identify the handful of ATTACK losses making ~USD 253.9 net damage;
5. compare those losses against winners with the same causal pre-entry context;
6. use context-only ATTACK lifecycle or another highly localized causal control;
7. avoid broad risk-budget/cap changes because prior work showed cliffs;
8. break <35%;
9. immediately re-forensics the migrated max;
10. continue to <30%, then <=25%; ideal <=20%.

## Certification status

Still **NOT CERTIFIED**.

- Current DD **35.24019%**
- Ideal target **<=20%**
- Maximum tolerable **<=25%**
- scientific certification battery begins only after the DD architecture reaches the target zone and is frozen.

---

# MASTER UPDATE — 2026-10-08 — DD COMPRESSION PROGRAM

> **THIS SECTION OVERRIDES ANY OLDER "CURRENT STATE", "BEST CARRIER", "NEXT STEP" OR "PRIORITY" STATEMENT BELOW.**
>
> The remainder of this file is intentionally preserved as historical continuity. Read this update first, then use the older sections only as lineage / experiment history.

**Owner / CEO:** Sergio Meza  
**Repository source of truth:** `mezas3238-hue/qore-core`  
**Canonical branch:** `agent/cibo-causal-expectation-leakage-fix-001`  
**Canonical handoff:** `docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md`  
**HEAD immediately before this update:** `79500d771360f14a94dcc1a261cf7344a870dfca`  
**Initial capital:** USD 60  
**Frozen economic floor:** USD 582,440.0252953678696769360345  
**Preserved Trader admissions:** 3,368 / 3,368  
**Certification state:** ACTIVE RESEARCH — NOT CERTIFIED  
**Sovereign directive:** reduce DD as far as causally possible without degrading the frozen economic ceiling/floor. Ideal DD <=20%; maximum tolerable DD <=25%. Anything above 25% remains unfinished.

---

## A. EXECUTIVE STATE — READ THIS FIRST

The DD-compression program has progressed materially beyond the old 38.46% carrier documented below.

### Current best dominant DD carrier: `tb-6500`

Decisive run:

- Run: **37763397877**
- Workflow: **QORE CIBO Carrier36423 W2 Taper Boundary Ridge**
- Workflow path: `.github/workflows/cibo-trader-lab-carrier36423-w2-taper-boundary-ridge.yml`
- Head SHA: **74c2b0646d8d83845dc55eb29417b9b17900bf6a**
- Case: **tb-6500**
- Result: **STRICT_PARETO = true**
- Result: **DOMINATES_CURRENT = true**
- Result: floor-valid
- Entries: 3,368 / 3,368 preserved by workflow invariants
- ATTACK sovereign breach: 0 by workflow invariants

Exact economics:

- terminal capital: **USD 670,926.0204345728784686849120**
- capital headroom above frozen floor: **USD 88,485.9951392050087917488775**
- max drawdown: **36.17369997743141917180404451%**
- total gross loss: **USD 959,364.9078905783825567884950**
- ATTACK gross loss: **USD 957,806.5608890020828213759980**
- total profit factor: **1.699281383878895618871897448**
- ATTACK override count: **852**
- bootstrap override count: **110**
- stress-confidence direct taper binds: 0
- stress-confidence risk-budget binds: 4

Improvement versus the immediate Carrier36423 comparator:

- capital: **+$206.6419841820094812510288**
- max DD: **-0.2493368296042967372685649642 percentage points**
- total gross loss: **-$69.7578104274674753007922**
- ATTACK gross loss: **-$69.7578104274674753007924**
- therefore the candidate improves capital, DD, total GL and ATTACK GL simultaneously.

The current max-DD bottleneck after `tb-6500` is again the early MEDIUM episode:

- peak: **2019-07-19T06:45:00+00:00**
- trough: **2019-08-09T01:35:00+00:00**
- max-DD net by mode: **MEDIUM = -USD 28.85356784226385744244804277**
- ATTACK is no longer the max-DD driver in this carrier.

### Absolute objective remains unchanged

The work is **not finished**.

- ideal DD: **<=20%**
- tolerable maximum: **<=25%**
- 35%, 30% and 25% are gates / milestones, not reasons to stop early.
- current 36.17370% remains materially outside certification range.

The next architect must continue the loop without resetting the program:

**forensics -> causal hypothesis -> isolated change -> Trader Lab replay -> compare -> promote only valid improvement -> re-forensics new max DD -> repeat.**

---

## B. IMPORTANT DISTINCTION — ECONOMIC CARRIER VS DD-FIRST CARRIER

During the 36–37% phase two ranking concepts appeared and MUST NOT be conflated.

### 1. Dominant-current / economic Pareto

A candidate is strongest when it simultaneously:

- capital >= current comparator capital;
- DD < current comparator DD;
- total gross loss <= current comparator total GL;
- ATTACK gross loss <= current comparator ATTACK GL;
- frozen floor is respected;
- 3,368 entries preserved;
- zero sovereign breach.

`tb-6500` satisfies this stronger condition relative to Carrier36423.

### 2. Floor-valid DD-first / strict Pareto relative to frozen floor

Some experiments intentionally accepted a small reduction from the current terminal capital while staying far above the frozen USD 582,440.03 floor, if DD and gross loss improved materially.

Example:

- run **37762989521**
- case **f-m2850-h0060**
- capital **USD 670,974.1001848462935084207540**
- DD **36.40871215817896688739414547%**
- total GL **USD 957,685.0671680592184528907798**
- ATTACK GL **USD 956,129.1127115113457698208008**
- strict Pareto = true versus Carrier36459
- dominates-current = false because terminal capital was ~USD 103 below the comparator.

The next architect must state explicitly which comparison is being used. Do not call a floor-valid candidate "dominates current" unless it actually does.

---

## C. REAL DD PROGRESSION — DO NOT RESET

The complete program has moved from the original ceiling carrier at ~65% DD through a long chain of localized causal compression.

Important checkpoints:

| Stage | Approx terminal capital | Max DD | Meaning |
|---|---:|---:|---|
| frozen ceiling baseline | 582,440 | 65.10% | economic floor / old true-ceiling reference |
| ATTACK band compression | 663,395 | 64.02% | 2,000–3,999x destructive band discovered |
| residual-window carrier | 687,903 | 51.15% | localized 800–1,900x defense |
| second-window carrier | 689,841 | 48.37% | 350–450x residual |
| low-mult window | 687,114 | 46.25% | 2–20x under live DD |
| high-mult window | 688,634 | 44.05% | 4,800–5,200x |
| exact 2x demotion | 690,681 | 43.85% | 2x useful, broader demotion harmful |
| high-left window | 689,672 | 41.73% | 4,400–4,799x |
| expected-R / MEDIUM lifecycle | 667,465 | 40.01% | MEDIUM floor compression |
| carrier39 | 667,459 | 39.685% | 40% barrier broken |
| capital-gated window6 | 668,086 | 39.174% | 50–170x localized by capital |
| old handoff carrier | 668,086 | 38.462% | p30 + capital-gated window6 |
| Carrier3829 | 668,086 | 38.291% | MFE / causal micro improvements |
| target-stretch + hysteresis | ~667,588–668,045 | 38.263% | first GL-compensated strict Pareto around target stretch |
| Carrier3822 family | ~667,839 | 38.221% | bottleneck migrated to Feb-2021 ATTACK |
| tc-f3000 | 667,846 | 38.217% | strict dominant target-collapse |
| tc-f2800 / Carrier38204 | ~668,094 | 38.2047% | target-collapse fine ridge |
| sc-j | 668,009 | 38.1154% | high-target stress strict Pareto |
| p4150 / Carrier37772 | 668,910 | 37.7721% | state-pressure / contextual pressure phase |
| ctx-s050 / Carrier37655 | 670,939 | 37.6550% | ATTACK context-only stop breakthrough |
| Carrier37082 | 673,215 | 37.0818% | next multi-context carrier |
| tf-b / Carrier36509 | 671,077 | 36.5094% | triple-context DD-first carrier |
| m1-2925 / Carrier36459 | 671,077 | 36.4591% | dominant-current MEDIUM M1 micro improvement |
| f-m2850-h0060 | 670,974 | 36.4087% | floor-valid strict Pareto; lower DD but not current-cap dominant |
| Carrier36423 | 670,719 | 36.4230% | DD-first research carrier used for W2 boundary work |
| **tb-6500** | **670,926** | **36.1737%** | **latest dominant-current carrier** |

The essential lesson remains:

> Max DD is a moving target. Every successful defense exposes another episode. The correct process is multi-episode causal compression, not global derisking.

---

## D. MAJOR BREAKTHROUGH — CONTEXT-ONLY LIFECYCLE

The most important architectural advance after the old handoff was the move from broad sizing/risk-budget gates to **context-only lifecycle overrides**.

### Why this was necessary

Multiple ATTACK sizing experiments showed a discontinuous compounding cliff:

- tiny risk-budget / cap changes often did nothing;
- once a discrete multiplier threshold was crossed, terminal capital collapsed toward ~USD 550k or lower;
- aggressive variants could reduce some local loss but generated 50–70% DD elsewhere.

Therefore, changing initial multiplier was often too coarse.

The successful alternative:

1. keep Trader admission unchanged;
2. keep initial economic sizing / multiplier unchanged;
3. identify a causal pre-entry context signature;
4. apply a defensive lifecycle stop only when the complete signature matches;
5. for nonmatches, preserve original settlement / behavior.

This protects a tiny adverse subset without globally derisking the portfolio.

### First ATTACK context-only implementation

Core commit:

- **6761e1657b156e3f4b64966bed53e3ba881b7338**
- message: `research(cibo): add ATTACK context-only defensive stop`

Decisive workflow:

- run **37755900609**
- workflow **QORE CIBO Carrier37772 ATTACK Context Stop Ridge**
- case **ctx-s050**

Exact result:

- capital: **USD 670,938.6019098824267612724062**
- DD: **37.65503786736055569923678558%**
- total GL: **USD 950,652.1484123080309106915780**
- ATTACK GL: **USD 949,092.0260621076816265570460**
- PF: **1.705703556269580093631776452**
- capital versus previous current: **+$2,028.14**
- total GL improvement: **-$6,573.75**
- ATTACK GL improvement: **-$6,573.75**
- strict Pareto: true
- dominates-current: true

The gate was based on generic causal context, not Trader identity or symbol identity.

The initial forensics found a very narrow context signature that selected only a tiny historical adverse subset. The key lesson is not the literal fields alone; it is the architecture:

> **contextual selectivity + post-entry protection can reduce loss without changing the initial multiplier, avoiding the compounding cliff.**

### MEDIUM context-only overrides

A corresponding MEDIUM context-only path was implemented after ATTACK success.

Important commits / phase:

- **56d3335dfccd1a93d85fcceeed4e212bb0b8b139** — add MEDIUM context-only stop override
- **b4a4c04058cd186f5a5faaa61d7f5b7bccc7e148** — expose MEDIUM context-only stop
- later second MEDIUM context-only support:
  - **3870e2bbadbf2511f64b0471437a841b68ca3bd8**
  - **b4a5d4b522f13dcde94dd01a98d4d84cae86670a**

These mechanisms became critical because the max DD repeatedly migrated back to MEDIUM 2019 after ATTACK episodes were compressed.

### Additional ATTACK context surfaces

The branch later added second and third ATTACK context-only overrides to attack distinct 2020 clusters:

- **2eb5b13377bc81848f14f5e23f101f509433735a**
- **ec0971ef57a19dc82940c46700377c89b542bc08**
- **427f8c7e0281bd0146c1d24b8f4e11435a62fcfd**
- **89541472166e0350869b20087fc10432efd3ad1a**

Representative workflows:

- `.github/workflows/cibo-trader-lab-carrier37655-attack-2020-context2-ridge.yml`
- `.github/workflows/cibo-trader-lab-carrier37655-attack-aprmay-context3-ridge.yml`
- `.github/workflows/cibo-trader-lab-carrier37655-triple-context-fusion-ridge.yml`

The correct principle is generic causal context, not identity hardcoding.

---

## E. TARGET-STRETCH / STATE-PRESSURE WORK — WHAT WAS LEARNED

A major forensic branch studied ultrafast ATTACK stopouts.

Key causal feature:

`planned_target_r = abs(take_profit - intended_entry) / abs(intended_entry - stop_loss)`

A harmful cluster was discovered when very stretched targets coincided with weak causal confidence / high dispersion.

Representative findings:

- targetR >=4 and expected_structural_r / block_dispersion <=0.20:
  - ~17 cases
  - ~94% losers
  - net roughly -USD 10.3k
- targetR >=3 and ratio <=0.20:
  - ~20 cases
  - ~95% losers
- targetR >=3 and ratio <=0.22:
  - ~23 cases
  - ~95.7% losers

Relevant commits:

- **fa1a6c783ce6662bc3adf547e5683c3a1d9d18c6** — gate stress confidence by target R
- **9baf83235fce9e670d7475567067ae6f604f9e85** — CLI exposure

This produced the Target Stretch / Hysteresis sequence.

Important runs:

- 37703003847 — target-stretch + hysteresis joint ridge
- 37703074371 — joint depth
- 37705250732 — target-collapse depth
- 37708965278 — target-collapse fine ridge

Important accepted cases:

- joint-h0010: first clean strict-Pareto combination breaking the prior few-dollar GL barrier
- tc-f3000:
  - capital ~USD 667,846.44
  - DD ~38.21727%
  - total/ATTACK GL improved by USD 2.56 versus Carrier3822
  - strict Pareto + dominates-current
- tc-f2800 / Carrier38204:
  - DD ~38.20474%
  - capital ~USD 668,094
  - became a later base.

Important rejected observation:

- stronger target collapse could lower the physical DD frontier but increased gross loss materially or caused compounding migration.

---

## F. PROJECTED-RISK / STATE-PRESSURE SENSORS ADDED

The 2021 forensics showed that several large ATTACK losses had unusually high projected stop risk relative to live capital.

This led to:

- projected-risk trigger inside state-pressure
- capital floor/ceiling for state-pressure
- H1/H4 range-state selectors
- second state-pressure channel
- optional direct cap taper in state-pressure2.

Relevant commits from this phase include:

- **0c818fd...** — gate state pressure by projected risk
- **509e144...** — expose projected-risk state-pressure gate
- **67795e4...** — localize state pressure by capital regime
- **b8282ab...** — expose state-pressure capital regime
- **73cba533561550b28dcacfecfd7dacd8a95c6ad7** — add state-pressure2 cap taper
- **90d048dfbba4515dbe309de58ef044c6ce667332** — expose state-pressure2 cap taper
- **2c404471c5ae25b7fe321ca55f2125082866fb2c / bc66f664fe4f7129b62dbc313ddaf83ad87227d2** — H1 range selectors / exposure

Key negative lesson:

> risk-budget and direct-cap tapering around the huge 2021 positions is often quantized. A tiny parameter change can produce no effect until a threshold is crossed, then the entire compounding path changes abruptly and terminal capital collapses.

Therefore these tools remain useful for forensics and carefully localized experiments, but they are not a license for broad derisking.

---

## G. DRAWDOWN MOUNTAINS — WHY THE PROBLEM IS HARD

The research proved that CIBO does not have a single DD mountain.

As one episode is compressed, another becomes max DD. Repeatedly observed dominant or near-dominant episodes include:

- 2019 Jul–Aug — MEDIUM-dominated
- 2020 Jan–Mar
- 2020 Apr–May
- 2020 May–Jun
- 2020 Sep–Oct
- 2021 Feb–Mar — ATTACK-dominated before contextual ATTACK protection
- later 2022 paths can become catastrophic if a defense distorts compounding.

Earlier at ~38.20%, the top mountains were roughly:

- ~38.20% — May–Jun 2020
- ~38.11% — Feb 2021
- ~38.03% — Jul–Aug 2019
- ~37.82% — Sep–Oct 2020
- ~36.41% — Apr–May 2020
- ~34.85% — Jan–Mar 2020

This is the central reason global controls fail: they "fix" one episode while moving the max DD elsewhere.

### Current bottleneck after tb-6500

The current max is again:

- **2019-07-19 06:45 UTC -> 2019-08-09 01:35 UTC**
- **MEDIUM net ~ -USD 28.8536**
- max DD **36.17370%**

The immediate task is NOT "turn risk down everywhere."

It is:

1. decompose this exact 2019 episode;
2. identify losing MEDIUM 1x/2x subcontexts;
3. compare them with winners under identical pre-entry state;
4. apply context-only lifecycle / financial management;
5. re-run;
6. after the episode falls, immediately re-forensics the new max episode.

---

## H. W2 459x BOUNDARY — LATEST DISCOVERY

A June-2020 loss around the second DD window produced a discrete boundary around the 459x region.

Workflow sequence:

- **37763166003** — Carrier36423 W2 459 Capture Ridge
- **37763397877** — Carrier36423 W2 Taper Boundary Ridge

The first capture sweep showed an abrupt cliff:

- one side of the boundary did nothing;
- more aggressive settings could lower local DD but collapse capital below the floor or create 50–70% DD elsewhere.

The boundary ridge resolved a useful point:

### tb-6500

- capital: **USD 670,926.0204345728784686849120**
- DD: **36.17369997743141917180404451%**
- total GL: **USD 959,364.9078905783825567884950**
- ATTACK GL: **USD 957,806.5608890020828213759980**
- PF: **1.699281383878895618871897448**
- dominates-current: true
- strict Pareto: true

Rejected neighboring points include:

- tb-6000:
  - same local DD 36.1737%
  - terminal capital ~USD 551,469
  - **below frozen floor**
- tb-7500 / 8000 / 9000 / 9500 etc:
  - large compounding migration
  - DD ~55–61% or worse
  - many below floor.

Conclusion:

> The W2 taper surface is highly discontinuous. `tb-6500` is a narrow safe point. Do not broaden this taper blindly.

---

## I. MEDIUM M1 MICRO / HYSTERESIS EDGE

Once the active max DD returned to MEDIUM 2019, the program resolved a fine boundary in the M1 contextual defense.

### Run 37762724394 — Carrier36509 MEDIUM M1 Micro Ridge

Important case:

`m1-2925`

- capital: **USD 671,077.4539648386230952204858**
- DD: **36.45907191119629854073488139%**
- total GL: **USD 957,746.5414819274567391081328**
- ATTACK GL: **USD 956,190.5468564571041386829792**
- PF: **1.700621119368981431695946134**
- strict Pareto: true
- dominates-current: true

Neighboring m1-2950 / 2975 / 2985 / 2990 / 2995 were also dominant-current, with gradually different DD.

The next fusion run:

### Run 37762989521 — Carrier36459 M1 Hysteresis Fusion Ridge

Best low-DD strict-Pareto point:

`f-m2850-h0060`

- capital: **USD 670,974.1001848462935084207540**
- DD: **36.40871215817896688739414547%**
- total GL: **USD 957,685.0671680592184528907798**
- ATTACK GL: **USD 956,129.1127115113457698208008**
- PF: **1.700558172185753664476943659**
- strict Pareto: true
- dominates-current: false (capital ~USD 103 below Carrier36459)

This is a useful floor-valid research point but it is not the current dominant carrier.

---

## J. ULTRA-FAST TRADER LAB ACCELERATION

Trader Lab execution had become a material bottleneck. The branch now contains a dedicated runtime-acceleration program.

Recent changes include:

- verified research-sweep acceleration
- exact-case result cache
- prepared trade-window cache
- runtime audit workflow
- Ultra Fast batch support
- inline ranking requirements
- reusable cached inputs / prepared windows for research sweeps.

Relevant recent HEAD lineage includes:

- `74ee781d2299d30306daa58f0639bc345524d23b` — verified Trader Lab research sweep acceleration
- runtime audit workflows repeatedly completing successfully
- latest boundary run restored:
  - exact-case result cache
  - prepared trade-window cache
  - inputs
  - replay
  - ranking
  - artifact upload.

Important governance:

> Fast execution is useful only if the ranking and JSON evidence are still produced and validated. Do not trade correctness for speed.

---

## K. EXPERIMENT FAMILIES CLOSED / REJECTED — DO NOT REPEAT BLINDLY

### 1. Broad/global protections

Rejected repeatedly because they destroy compounding:

- broad ATTACK taper
- broad stress-confidence taper
- broad DD budget
- broad lifecycle loss cut
- broad ATTACK partial
- global high-risk protection
- global MEDIUM tighter stop
- global bootstrap stop tightening.

### 2. ATTACK adverse partial

Strongly rejected.

Historical examples:

- DD 50–70%+
- large reductions in gross loss can coexist with catastrophic loss of terminal capital.
- not a valid solution.

### 3. Projected-risk global pressure

Can reduce some late losses but changes the capital path too broadly. Use only with tight state/context gating.

### 4. Direct cap / risk-budget microtapers

Around some high-multiplier ATTACK losses:

- 0.9995–0.981 risk-budget microtapers often produced no change;
- crossing a discrete threshold produced a compounding cliff.

### 5. Floor-Seeking aggressive sweeps

Using headroom aggressively did not automatically improve DD. Many variants:

- moved DD to another episode;
- fell below USD 582,440.03;
- or worsened DD despite huge gross-loss reduction.

### 6. MEDIUM bootstrap hardening

Bootstrap defensive-stop / partial-depth sweeps were rejected.

Representative old behavior:

- some cases dropped terminal capital to ~USD 550k or lower;
- DD could explode to ~48–69%;
- therefore do not revisit without a new narrow context.

### 7. MEDIUM global stop tightening

The program has repeatedly shown a narrow boundary. Small extra tightening can move the trajectory to a completely different path.

### 8. W2 boundary beyond safe point

Latest run proves:

- `tb-6500` is safe/dominant;
- nearby stronger settings can catastrophically re-route compounding.

---

## L. CORE ENGINEERING CHANGES NOW PRESENT

The next architect should expect the branch to contain, at minimum, the following research capabilities:

### Economic / DD controls

- multiplier-band taper
- risk-fraction-band taper
- seven+ localized DD multiplier windows
- capital floor/ceiling gates
- exact low-multiplier demotion
- same-Trader loss streak pressure
- recent-Trader loss pressure
- portfolio shock
- compound hysteresis
- stress-confidence target-R gate
- stress-confidence risk-budget gate
- target stretch / collapse
- state-pressure
- state-pressure projected-risk trigger
- state-pressure capital regime
- H1/H4 range state
- state-pressure2
- state-pressure2 direct cap taper
- realized-DD-triggered budget research
- multi-band DD budget research
- W2 459x capture/boundary tuning.

### Lifecycle controls

- MEDIUM base defensive initial stop
- adverse partial reduction
- adverse loss cut
- adverse stop tighten
- bootstrap partial
- bootstrap state override
- causal context stop predicates
- ATTACK override map
- ATTACK context-only defensive initial stop
- multiple ATTACK context surfaces
- MEDIUM context-only stop override
- second MEDIUM context-only stop.

### Causality / governance

- all context predicates must be pre-entry causal
- closed-bar post-entry actions execute only when causally observable
- no outcome/future leakage
- no Trader/symbol identity hardcoding as a risk rule
- all Trader admissions preserved.

Core files:

- `src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py`
- `scripts/cibo_trader_lab_three_mode_ceiling.py`
- `src/qore/infrastructure/cibo_position_lifecycle.py`

---

## M. CURRENT FORENSIC PRIORITY — DEEP DRAWDOWN STUDY

The Owner explicitly requires a deep study of what causes DD before applying more controls.

The next architect must maintain / extend a **drawdown causal atlas**.

For each of the top 10 DD episodes, extract and compare:

### Economic state

- total capital
- peak capital
- live realized DD
- Sovereign bank
- Portfolio cushion
- attack credit
- reserved cushion
- open margin
- open stop risk
- current compounding anchors
- requested / approved multiplier
- risk fraction
- exact gate / cap that bound.

### Trader state

Use Trader identity only for attribution, not as the rule.

Record:

- same-Trader settled loss streak
- last 1 / 2 / 3 / 5 outcomes
- recent gross loss
- recent gross profit
- rolling PF
- time since last shock
- whether Trader had recovered from prior shock.

### Cognitive / expectation state

- expected structural R
- expected capital minutes
- dispersion
- confidence ratio
- native confidence band
- context disposition
- market posture
- H1/H4 range state
- M5 volatility state
- body alignment
- rejection wick bucket
- reclaim latency bucket
- close-location bucket
- any other strictly predecision context.

### Position / target geometry

- target R
- structural stop distance
- projected stop-risk fraction
- multiplier
- mode
- expected holding time
- actual holding time for postmortem only.

### Lifecycle path

- MFE
- MAE
- first closed bar after entry
- whether stop occurred before any complete M5 bar
- whether the trade could have been rescued causally post-entry
- whether a defensive initial stop would have protected it
- whether a winner with the same pre-entry signature would have been harmed.

### Cross-portfolio state

- concurrent positions
- same asset overlap
- cross-asset overlap
- cumulative open stop risk
- loss clustering in prior hour/day
- Portfolio cushion recovery state.

### Engine attribution

Explicitly show the contribution of:

- SIZING
- ADAPTIVE_LEVERAGE
- CIBO_COMPOUND
- COMPOUND_PORTFOLIO

Do not stop at "ATTACK lost" or "MEDIUM lost." Explain what economic state allowed the exposure and why.

---

## N. NEXT WORK — PRIORITIZED

### P0 — promote / freeze tb-6500 as the current dominant carrier

Before making another architectural change:

1. preserve `tb-6500` exact parameters;
2. record its artifact / digest;
3. verify 3,368 entries, zero breach, accounting invariants;
4. use it as the comparator for the next dominant-current search.

### P0 — attack current 2019 MEDIUM max DD

Current max DD is 36.17370% and MEDIUM-dominated.

Required sequence:

1. open `tb-6500` artifact;
2. enumerate every MEDIUM settlement between peak and trough;
3. rank gross-loss contribution and net contribution;
4. separate M1 and M2;
5. cluster by causal pre-entry context;
6. search for high-precision losing contexts with minimal winner contamination;
7. prefer context-only lifecycle over global stop hardening;
8. sweep tiny stop / partial changes;
9. require replay evidence.

### P0 — break 35%

The immediate milestone is **<35%**, but do not treat it as completion.

Once <35% is reached:

- re-forensics the new max episode;
- continue toward <30%;
- then <=25%;
- ideal <=20%.

### P1 — retain economic headroom

Current capital remains ~USD 88.5k above the frozen floor.

Use that headroom carefully. Do not spend it through broad derisking.

### P1 — gross loss

Gross loss remains a secondary sovereign objective.

Keep reporting:

- terminal capital
- max DD
- total gross profit
- total gross loss
- ATTACK GL
- net PnL
- PF
- trade count
- entries preserved
- breaches
- bind counts.

### P1 — investigate multiple mountains in parallel

Do not serially optimize one mountain forever.

Maintain candidate defenses for:

- 2019 MEDIUM
- 2020 ATTACK/MEDIUM mixed episodes
- 2021 ATTACK residuals
- 2022 catastrophic migration risks.

---

## O. PROMOTION RULES

Minimum frozen acceptance:

- terminal capital >= **USD 582,440.0252953678696769360345**
- 3,368 / 3,368 entries
- zero sovereign breach
- no admission rejection
- no future/outcome leakage.

Preferred dominant-current promotion:

- capital >= current carrier
- DD < current carrier
- total GL <= current carrier
- ATTACK GL <= current carrier.

If a candidate is floor-valid but not dominant-current, label it exactly:

- `STRICT_PARETO / FLOOR-VALID`
- `NOT DOMINATES_CURRENT`

Do not blur those classes.

For DD-first research, a floor-valid candidate may be valuable even if capital is slightly below current, but it must not silently replace the dominant economic carrier.

---

## P. CERTIFICATION — WHAT STILL HAS TO HAPPEN

CIBO is **not certified**.

Reaching 20–25% is the prerequisite for the scientific battery, not the end.

### Gate 1 — DD target

- ideal <=20%
- maximum tolerable <=25%
- preserve frozen economic floor / ceiling constraints.

### Gate 2 — architecture freeze

When the DD carrier is accepted:

- freeze parameters
- freeze context signatures
- freeze economic functions
- freeze lifecycle maps
- freeze expected-R / confidence models
- freeze exact Git commit and artifacts.

### Gate 3 — accounting / provenance

Formally verify:

- every dollar source
- every reservation
- every release
- every recycle
- Sovereign / cushion / Compound reconciliation
- no double count
- no double spend
- no silent capital creation
- no release before reconciliation.

### Gate 4 — ablations

Ablate individually and jointly:

- SIZING
- ADAPTIVE_LEVERAGE
- CIBO_COMPOUND
- COMPOUND_PORTFOLIO
- lifecycle
- context-only lifecycle
- DD windows
- state pressure
- target-R gates
- hysteresis.

Prove each component has measurable purpose.

### Gate 5 — temporal robustness

- chronological folds
- walk-forward
- temporal replication
- regime slices
- year / semester slices
- no retune across validation periods.

### Gate 6 — Monte Carlo / path stress

- causal-compatible reorder
- clustered losses
- p05 outcome
- p95 DD
- probability positive
- probability of ruin
- recovery time
- tail path stress.

### Gate 7 — cost / execution stress

- spread stress
- slippage stress
- cost x2
- margin compression
- provider constraints
- latency / fill degradation where relevant.

### Gate 8 — concentration stress

- Trader concentration
- asset concentration
- regime concentration
- remove best 1 trade
- remove best 2 trades
- remove best 3 trades
- correlated burst losses.

### Gate 9 — failure engineering

Hard requirements:

- ZERO DOUBLE-SPEND
- ZERO DUPLICATE AUTHORITY
- ZERO SILENT SOURCE CREATION
- ZERO RELEASE BEFORE RECONCILIATION

Test:

- restart
- idempotency
- duplicate events
- duplicate reservation
- partial settlement
- ledger crash
- stale snapshot
- reconciliation mismatch
- concurrent allocation
- recovery after interruption.

### Gate 10 — forward qualification

- predeclared gates
- no retune
- complete observability
- zero-open closure.

### Gate 11 — fresh sealed OOS

Protected holdout:

`CIBO_USD60_6M_HOLDOUT_2017H1_V1`

**DO NOT OPEN EARLY.**

Only after architecture freeze and prerequisites.

### Gate 12 — final exams

Still pending:

1. Worst-Trader Rescue Exam
2. Final Integrated Certification Exam
3. World Cup Maximum Capability Exam
4. fresh OOS
5. zero-open closure
6. final certification candidate.

---

## Q. SOVEREIGN DIRECTIVES THAT MUST SURVIVE CHAT HANDOFF

The next architect must preserve these rules exactly:

- Trader owns admission / execution.
- CIBO manages financially after entry.
- CIBO cannot reject Trader entries.
- preserve 3,368 / 3,368.
- Sizing must not reject/defer custody.
- Sizing + Adaptive Leverage + CIBO Compound + Compound Portfolio work jointly.
- no hardcoded Trader or symbol.
- no future/outcome leakage.
- replay every change.
- do not touch sealed OOS early.
- 8,000% / 36 months was a historical base objective, not the ceiling.
- do not rediscover the ceiling from zero.
- do not sacrifice the frozen economic floor for cosmetic DD.
- do not declare certification before the scientific battery.
- **DD ideal = 20%; tolerable maximum = 25%.**
- current priority is DD compression, not new ceiling discovery.

---

## R. KEY RECENT RUNS / WORKFLOWS TO READ

The next architect should inspect these before changing the engine:

- **37755900609** — Carrier37772 ATTACK Context Stop Ridge
- **37757418981** — Carrier37655 MEDIUM Context Stop Ridge
- **37757846297** — Carrier37655 ATTACK 2020 Context2 Ridge
- **37758109665** — Carrier37655 ATTACK Apr-May Context3 Ridge
- **37758259160** — Carrier37655 Triple Context Fusion Ridge
- **37759321394** — Carrier37082 MEDIUM Trough Context2 Ridge
- **37761751207** — fast replay of Carrier37082 context2 path
- **37761752377** — Carrier36509 Dual MEDIUM Rescue Ridge
- **37761758630** — Carrier36509 Rescue DD Envelope Ridge
- **37762019994** — Carrier36509 Localized DD Budget Ridge
- **37762060159** — Carrier36509 Narrow DD Budget Ridge
- **37762199165** — Carrier36509 Two Band DD Budget Ridge
- **37762433200** — Carrier36509 Rescue DD Envelope Inline Rank
- **37762660789** — Carrier36509 Triggered DD Budget Ridge
- **37762724394** — Carrier36509 MEDIUM M1 Micro Ridge
- **37762989521** — Carrier36459 M1 Hysteresis Fusion Ridge
- **37763166003** — Carrier36423 W2 459 Capture Ridge
- **37763397877** — **Carrier36423 W2 Taper Boundary Ridge — current decisive run**

Workflows:

- `.github/workflows/cibo-trader-lab-carrier37772-attack-context-stop-ridge.yml`
- `.github/workflows/cibo-trader-lab-carrier37655-medium-context-stop-ridge.yml`
- `.github/workflows/cibo-trader-lab-carrier37655-attack-2020-context2-ridge.yml`
- `.github/workflows/cibo-trader-lab-carrier37655-attack-aprmay-context3-ridge.yml`
- `.github/workflows/cibo-trader-lab-carrier37655-triple-context-fusion-ridge.yml`
- `.github/workflows/cibo-trader-lab-carrier37082-medium-trough-context2-ridge.yml`
- `.github/workflows/cibo-trader-lab-carrier36509-medium-m1-micro-ridge.yml`
- `.github/workflows/cibo-trader-lab-carrier36459-m1-hysteresis-fusion-ridge.yml`
- `.github/workflows/cibo-trader-lab-carrier36423-w2-459-capture-ridge.yml`
- `.github/workflows/cibo-trader-lab-carrier36423-w2-taper-boundary-ridge.yml`

---

## S. FAILED / TECHNICAL WORKFLOW NOTES

Not every GitHub failure is negative experiment evidence.

Examples in the latest lineage:

- `cibo-trader-lab-carrier36459-medium-context2-surgical-ridge.yml` had immediate workflow failures during the latest branch work.
- treat those as technical CI/workflow failures unless a replay actually completed and produced metrics.
- never infer "hypothesis rejected" from a YAML / trigger / syntax failure.

The Runtime Audit workflow is now part of the operational health surface and should be checked when research workflows behave unexpectedly.

---

## T. FIRST ACTIONS FOR THE NEXT ARCHITECT

1. Fetch branch HEAD before editing.
2. Read this handoff update.
3. Inspect run **37763397877** and artifact.
4. Reproduce / freeze **tb-6500**.
5. Build top-10 DD atlas from tb-6500.
6. Start with current 2019 MEDIUM max:
   - peak 2019-07-19 06:45 UTC
   - trough 2019-08-09 01:35 UTC
   - MEDIUM net -USD 28.8536.
7. Search high-precision MEDIUM losing contexts:
   - no Trader identity
   - no symbol identity
   - only causal context.
8. Prefer context-only lifecycle / tiny economic changes over global controls.
9. Replay in Ultra Fast Trader Lab.
10. Promote only valid evidence.
11. Repeat immediately on the next migrated max-DD episode.
12. Keep driving toward <=25%; ideal <=20%.

---

## U. CONTINUITY BLOCK FOR A NEW CHAT

> Continue CIBO from repository `mezas3238-hue/qore-core`, branch `agent/cibo-causal-expectation-leakage-fix-001`. Read first `docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md`, especially MASTER UPDATE 2026-10-08 at the top. Frozen economic floor is USD 582,440.0252953678696769360345 from USD 60, with all 3,368 Trader entries preserved. Current decisive dominant carrier is `tb-6500`, run 37763397877: terminal capital USD 670,926.0204345729, max DD 36.1736999774%, total GL USD 959,364.9078905784, ATTACK GL USD 957,806.5608890021, PF 1.69928138, zero sovereign breach by invariants. It dominates Carrier36423 in capital, DD and gross losses. Current max DD is MEDIUM 2019-07-19 -> 2019-08-09, net MEDIUM about -USD 28.8536. Priority is deep causal DD forensics and continued compression without degrading the frozen ceiling/floor. Ideal DD <=20%; tolerable max <=25%; do not stop at 35% or 30%. Do not reject entries, do not hardcode Trader/symbol, do not use future/outcome leakage. Use context-only lifecycle and localized causal controls; replay every modification. Once <=20–25% is reached and architecture frozen, execute the full scientific certification battery: accounting/provenance, ablations, temporal folds, walk-forward, Monte Carlo, cost/margin/concentration stress, failure engineering, forward no-retune, fresh sealed OOS, Worst-Trader Rescue, Final Integrated Certification and World Cup Maximum Capability.

---

## V. FINAL STATUS AT THIS HANDOFF UPDATE

**Best dominant carrier:** `tb-6500`  
**Run:** 37763397877  
**Terminal capital:** USD 670,926.02  
**Max DD:** 36.17370%  
**Total gross loss:** USD 959,364.91  
**ATTACK gross loss:** USD 957,806.56  
**PF:** 1.69928  
**Frozen floor:** PASS by ~USD 88,485.995  
**Entries:** 3,368 / 3,368  
**Sovereign breach:** 0  
**Certification:** NO  
**Immediate bottleneck:** 2019 MEDIUM DD  
**Priority:** reduce DD aggressively but causally, without degrading frozen ceiling/floor  
**Ideal DD:** <=20%  
**Maximum tolerable DD:** <=25%  

---

# HISTORICAL HANDOFF BELOW — PRESERVED FOR LINEAGE

# ACTUALIZACIÓN MAESTRA CANÓNICA — 2026-10-08
## CIBO TRUE CEILING → DRAWDOWN COMPRESSION → PÉRDIDA BRUTA → CERTIFICACIÓN

> **ESTA SECCIÓN ES LA AUTORIDAD NUMÉRICA MÁS RECIENTE Y SUPERA CUALQUIER CIFRA ANTIGUA DEL CUERPO HISTÓRICO QUE APARECE MÁS ABAJO.**
>
> El cuerpo anterior se conserva deliberadamente como historial de investigación, decisiones, hipótesis y arquitectura. Cuando exista contradicción entre una cifra antigua y esta actualización, manda esta actualización.

Owner / CEO: Sergio Meza  
Repositorio fuente de verdad: `mezas3238-hue/qore-core`  
Branch canónico: `agent/cibo-causal-expectation-leakage-fix-001`  
HEAD observado antes de publicar esta actualización: `cfc65b895f21fda94ed3ca14ed4622e5de2caeac` — `research(cibo): attack 36.17 MEDIUM plateau after 459x capture`

---

# 0. DIRECTIVA SOBERANA ACTUAL

La misión ya no es descubrir si CIBO puede producir capital. Eso quedó demostrado.

La misión vigente es:

> **REDUCIR EL MAX DRAWDOWN DE CIBO LO MÁXIMO POSIBLE SIN DEGRADAR EL TECHO ECONÓMICO CONGELADO, SIN ROMPER EL COMPOUNDING, SIN RECHAZAR ENTRADAS Y SIN INTRODUCIR LEAKAGE.**

Objetivos soberanos:

- capital inicial: **USD 60**;
- preservar **3.368 / 3.368 entradas**;
- el Trader decide/admite/ejecuta la entrada;
- CIBO administra financieramente la posición después de la entrada;
- CIBO **NO puede rechazar entradas**;
- piso económico congelado: **USD 582.440,0252953678696769360345**;
- cero Sizing rejection;
- cero Sizing deferral;
- cero ATTACK sovereign breach;
- reglas genéricas, causales, identity-free y sin outcome/future leakage;
- DD ideal: **<=20%**;
- DD tolerable máximo: **<=25%**;
- **26% NO cumple**;
- el rango 20–25% es condición necesaria para pasar a batería científica, pero **NO equivale a certificación**.

El objetivo de 8.000% en 36 meses fue una base histórica, **NO un techo**. No limitar artificialmente la capacidad de CIBO a 8.000%.

---

# 1. ESTADO ACTUAL REAL — NUEVO CARRIER STRICT PARETO GLOBAL

## Carrier global vigente de investigación

Caso:

`f-m2850-h0060`

Workflow:

`.github/workflows/cibo-trader-lab-carrier36459-m1-hysteresis-fusion-ridge.yml`

Run decisivo:

**37762989521**

Commit que lanzó el ridge:

**1f1d65adb54d31d46e67ddee813c34d7fd087676**

Métricas:

- capital final: **USD 670.974,1001848463**
- max DD: **36,40871215817897%**
- total gross loss: **USD 957.685,0671680592**
- ATTACK gross loss: **USD 956.129,1127115113**
- total PF: **~1,70055817**
- entradas: **3.368 / 3.368**
- sovereign breach: **0**
- max-DD peak: **2019-07-19 06:45 UTC**
- max-DD trough: **2019-08-09 01:35 UTC**
- max-DD net por modo: **MEDIUM ~ -USD 29,0410**
- capital sobre piso congelado: **~USD 88.534,07**
- STRICT PARETO: **TRUE** contra el carrier previo `m1-2925`

Configuración diferencial principal:

- MEDIUM context-stop principal alrededor de **-0,2850R**
- ATTACK compound hysteresis **0,0060**

Este carrier reduce simultáneamente DD y gross loss frente al carrier `m1-2925`. El capital baja aproximadamente USD 103 frente a `m1-2925`, pero permanece muy por encima del piso congelado y también por encima de los ceilings históricos que motivaron esta fase. Por tanto, se acepta como carrier de investigación DD bajo la política STRICT PARETO vigente.

---

# 2. TRAYECTORIA DE DRAWDOWN CONSEGUIDA

La compresión no fue cosmética. La secuencia aproximada ha sido:

- **65,10%**
- **64,02%**
- **51,15%**
- **48,37%**
- **46,25%**
- **44,05%**
- **43,85%**
- **41,73%**
- **40,0058%**
- **39,6850%**
- **39,1742%**
- **38,4621%**
- **38,29095%**
- **38,26313%**
- **38,22140%**
- **38,21727%**
- luego nuevas defensas contextuales / microcliffs llevaron el carrier a la zona 37.x
- **37,65504%**
- **37,082% aprox.**
- **36,91% aprox.**
- **36,50943%**
- **36,45907%**
- **36,40871% — CARRIER GLOBAL VIGENTE**

La investigación ya eliminó más de **28,6 puntos porcentuales de DD** desde el estado ~65,10%, preservando las 3.368 entradas.

La misión sigue abierta porque **36,41% todavía está muy por encima del tolerable 25%**.

---

# 3. NUEVA FRONTERA FÍSICA MÁS BAJA — NO PROMOVER TODAVÍA

El ridge:

`.github/workflows/cibo-trader-lab-carrier36423-w2-taper-boundary-ridge.yml`

Run:

**37763397877**

Commit:

**74c2b0646d8d83845dc55eb29417b9b17900bf6a**

encontró:

`tb-6500`

Métricas:

- capital: **USD 670.926,0204345729**
- DD: **36,17369997743142%**
- total GL: **USD 959.364,9078905784**
- ATTACK GL: **USD 957.806,5608890021**
- PF: **~1,69928138**
- peak/trough del DD: **2019-07-19 06:45 → 2019-08-09 01:35 UTC**
- max-DD MEDIUM: **~ -USD 28,8536**
- 3.368 / 3.368 entradas;
- zero sovereign breach;
- floor PASS.

Dentro de su rama `td-f`, `tb-6500` figura como STRICT PARETO y `dominates_current=true`.

**Pero NO debe promoverse todavía como carrier global**, porque comparado contra el carrier global `f-m2850-h0060`:

- DD mejora ~0,235 puntos;
- capital sólo baja ~USD 48;
- pero total GL empeora aproximadamente **USD 1,68k**;
- ATTACK GL empeora aproximadamente **USD 1,68k**.

Interpretación:

> **36,17370% es una frontera física validada y muy prometedora. El siguiente arquitecto debe intentar compensar sólo ese pequeño rebote de GL sin perder la compresión de DD.**

No repetir protecciones globales para lograrlo. Usar una palanca GL-negativa pequeña, localizada y causal.

---

# 4. NUEVO BREAKTHROUGH: MICRO-RIDGE MEDIUM EN EL EPISODIO 2019

Workflow:

`.github/workflows/cibo-trader-lab-carrier36509-medium-m1-micro-ridge.yml`

Run:

**37762724394**

Commit:

**d893b9d48eb844d712f752a6b469d678980ad885**

Carrier de partida:

`carrier36509-tfb`

- capital: **USD 671.077,4137959161**
- DD: **36,50943166421363%**
- total GL: **USD 957.746,5816508499**
- ATTACK GL: **USD 956.190,5468564571**
- PF: **~1,70062105**

El micro-ridge alrededor de -0,30R demostró que el borde es suave y útil antes del cliff.

Resultados relevantes:

### `m1-2925` — STRICT PARETO + DOMINANTE

- capital: **USD 671.077,4539648386**
- DD: **36,45907191119630%**
- total GL: **USD 957.746,5414819275**
- ATTACK GL: **sin degradación**
- PF: **~1,70062112**
- mejora capital;
- mejora DD;
- mejora total GL;
- 3.368 entradas;
- zero breach.

### `m1-2900` — frontera física no Pareto

- capital: **USD 671.094,9012186111**
- DD: **36,44228532685719%**
- total GL rebota sólo **~USD 9,85**
- ATTACK GL rebota **~USD 9,90**

Este caso fue importante porque demostró que se podía profundizar el DD y que el único bloqueo era un gap de gross loss de unos pocos dólares.

### Hysteresis compensation

Al fusionar el stop MEDIUM con hysteresis se obtuvieron varios STRICT PARETO:

- `f-m2900-h0055`
- `f-m2900-h0060`
- `f-m2875-h0055`
- `f-m2875-h0060`
- `f-m2850-h0060`

El mejor carrier global por DD+GL es actualmente `f-m2850-h0060` con **36,40871%**.

Conclusión:

> El primer contexto MEDIUM está bien identificado y produce mejoras continuas, pero **no parece suficiente por sí solo para atravesar 35% sin entrar en un cliff**. Hay que encontrar un segundo cluster MEDIUM independiente o compensar una frontera más agresiva.

---

# 5. REALIZED-DD BUDGET — NUEVA CAPACIDAD Y RESULTADO

Se añadió soporte para activar el ATTACK drawdown budget **sólo después de que exista drawdown realizado**, evitando estrangular compounding desde el peak.

Implementación/exposición:

- commit **3763ab919c4f7feccdb7ad1a0b949eb3fe3f9764**
- parámetro:
  `--ceiling-attack-drawdown-budget-trigger`

Workflow de ridge:

`.github/workflows/cibo-trader-lab-carrier36509-triggered-dd-budget-ridge.yml`

Run:

**37762660789**

Mejor frontera de esa familia:

`td-f`

- capital: **USD 670.719,3784503909**
- DD: **36,42303680703572%**
- total GL: **USD 959.434,6657010059**
- ATTACK GL: **USD 957.876,3186994296**
- floor-valid DD improvement: **TRUE**
- STRICT PARETO: **FALSE**
- motivo: gross loss empeora aproximadamente **USD 1,69k**

Conclusión:

- la activación por realized-DD sí evita parte del daño de los budgets antiguos;
- abre una frontera física útil;
- **no resuelve el carrier global por sí sola**;
- además, el DD gobernante es MEDIUM 2019, por lo que un budget ATTACK no puede ser la única solución.

---

# 6. W2 459x JUNE-2020 CAPTURE — QUÉ SE APRENDIÓ

La rama concurrente atacó una pérdida ~459x de junio 2020.

Workflow:

`.github/workflows/cibo-trader-lab-carrier36423-w2-459-capture-ridge.yml`

Run:

**37763166003**

Commit:

**a7839fdc72bdd0f3b14d36d47e561997cebad60d**

Una variante agresiva:

`w2-u460-f60`

alcanzó:

- DD **36,17370%**
- total GL fuertemente menor;
- pero capital **~USD 551.468,70**, por debajo del piso congelado.

RECHAZADA.

Después se resolvió el taper boundary y apareció `tb-6500`, que conserva capital ~USD 670,9k y el mismo DD físico 36,17370%, pero con un rebote pequeño de GL contra el carrier global.

Conclusión:

> La pérdida 459x es una palanca real para bajar DD, pero la intensidad debe estar extremadamente localizada. El boundary ~0,65 muestra una zona económicamente viable que merece fusión con una palanca de compensación de GL.

---

# 7. SECOND MEDIUM CONTEXT — HIPÓTESIS PROMETEDORA, WORKFLOW FALLÓ TÉCNICAMENTE

Se identificó una segunda firma MEDIUM muy selectiva, independiente del primer contexto:

- sólo **2 operaciones MEDIUM 1x** en los 3 años;
- **2 perdedoras**;
- **0 ganadoras**;
- ambas dentro del max-DD 2019;
- pérdida agregada aproximada **-USD 3,56**;
- sin solaparse con el primer contexto.

La idea era probar un segundo context-only stop con requisitos causales tipo:

- `ctx_cisd_progress_bucket=q2:<=0.50`
- `ctx_source_range_state_bucket=q1:<=0.75`
- `reg_h1_range_state=balanced`
- `reg_m5_efficiency_state=high`

Workflow:

`.github/workflows/cibo-trader-lab-carrier36459-medium-context2-surgical-ridge.yml`

Commit de creación:

**31093449f3b75b8ba3b72acefc5048e4492e480b**

Runs técnicos fallidos:

- **37763320214**
- **37763396352**

**IMPORTANTE: estos failures NO son evidencia económica negativa. El replay no llegó a ejecutarse.**

Problema observado:

- el YAML quedó malformado durante generación del bloque `run_case`;
- se mezclaron líneas viejas del micro-ridge con el nuevo bloque;
- el archivo debe repararse antes de volver a lanzar.

Primer trabajo recomendado para el siguiente arquitecto:

1. reparar ese workflow;
2. basarlo sobre el carrier global vigente `f-m2850-h0060`, no sobre una cifra vieja;
3. mantener el primer contexto MEDIUM exactamente congelado;
4. variar sólo el segundo context-stop;
5. ejecutar vía Ultra Fast batch;
6. rankear contra el carrier global 36,40871%.

Esta hipótesis puede ser más valiosa que seguir apretando el primer stop, porque ataca un cluster independiente del mismo trough.

---

# 8. BUDGETS Y RESCATES RECIENTES RECHAZADOS — NO REPETIR

Sobre `carrier36509-tfb` se probaron:

## Localized DD Budget

Run **37762019994**

- `FLOOR_VALID_DD_CASES=[]`
- `STRICT_PARETO_CASES=[]`

RECHAZADO.

## Narrow DD Budget

Run **37762060159**

- algunos casos bajaron DD a ~36,40%;
- pero destruyeron capital hasta ~USD 551k o peor;
- cero floor-valid Pareto.

RECHAZADO.

## Two-Band DD Budget

Run **37762199165**

- destrucción extrema del compounding;
- capital en muchos casos ~USD 43k–65k;
- cero Pareto.

RECHAZADO.

## Rescue DD Envelope

Runs **37761758630** y **37762433200**

- algunas cifras visuales de DD ~35,84%;
- pero capital colapsó a ~USD 1k;
- cero floor-valid DD cases.

RECHAZADO.

## Dual MEDIUM Rescue

Run **37761342431**

- no produjo ruta válida al objetivo;
- las defensas MEDIUM demasiado fuertes cruzan el cliff y rompen compounding.

## Long-horizon / broad protections anteriores

También siguen rechazadas:

- broad ATTACK lifecycle;
- broad DD budgets;
- broad state pressure;
- global multiplier cuts;
- broad partial reduction;
- aggressive compound hysteresis;
- global low-multiplier demotion;
- cualquier variante que baje GL “bonito” a costa de matar el terminal capital.

Patrón soberano confirmado:

> **Las defensas globales pueden bajar pérdidas brutas, pero destruyen la trayectoria de compounding. La solución debe ser quirúrgica, causal, state-aware y reversible.**

---

# 9. DIAGNÓSTICO ACTUAL DEL MAX DRAWDOWN

El max-DD global sigue gobernado por un episodio **MEDIUM**, no por el ATTACK que originalmente dominaba 2020/2021.

Carrier global `f-m2850-h0060`:

- peak: **2019-07-19 06:45 UTC**
- trough: **2019-08-09 01:35 UTC**
- modo responsable: esencialmente **MEDIUM**
- max-DD net MEDIUM ~**-USD 29,041**

Esto cambia la metodología.

No sirve seguir optimizando sólo ATTACK.

Hay que diseccionar el episodio 2019 operación por operación y explicar:

1. qué trades construyen el peak-to-trough;
2. qué pérdidas son direct-to-stop;
3. cuáles tuvieron MFE antes de deteriorarse;
4. qué evidencia de barras cerradas existía antes de la pérdida;
5. cuáles son 1x vs 2x;
6. qué expected-R / confidence / dispersion tenían;
7. qué regime state compartían;
8. qué capital state / peak state existía;
9. qué losers tienen twins ganadores y por qué;
10. qué acción habría ahorrado pérdida sin matar recovery winners;
11. cómo interactuaron Sizing, Adaptive Leverage, CIBO Compound y Compound Portfolio;
12. si CIBO reescaló demasiado rápido después de una pérdida;
13. si hubo clustering temporal de pérdidas;
14. si hay un segundo o tercer cluster causal pequeño no cubierto por el primer context-stop.

No aceptar la explicación “MEDIUM perdió”. Se necesita **atribución causal por trade y por motor económico**.

---

# 10. METODOLOGÍA OBLIGATORIA DESDE AQUÍ

Ciclo operativo:

> **FORensics profundo → hipótesis causal → cambio mínimo → Trader Lab replay → STRICT PARETO → conservar/rechazar → recalcular atlas → repetir**

Reglas:

- una modificación por hipótesis cuando sea posible;
- no hardcodear Trader/símbolo;
- no outcome leakage;
- predecision o closed-bar evidence;
- preservar 3.368 entradas;
- mantener invariantes;
- comparar siempre contra el carrier global vigente;
- no promover una “frontera física” si empeora GL sin una razón explícitamente aceptada;
- aprovechar fronteras físicas para diseñar compensadores, no para redefinir el criterio después del resultado.

Hitos intermedios útiles:

- <36%;
- <35%;
- <32%;
- <30%;
- <27,5%;
- <=25%;
- ideal <=20%.

**Ningún hito intermedio es meta final.**

---

# 11. PRIORIDAD ABSOLUTA: ESTUDIO PROFUNDO DE LAS CAUSAS DEL DD

El Owner exige un estudio a profundidad de los factores que ocasionan Drawdown para atacar la problemática existente.

El siguiente arquitecto debe producir un **Drawdown Causal Atlas** por episodio.

Para cada peak-to-trough dominante:

## A. Ledger temporal

- timestamp;
- capital antes;
- peak capital causal;
- live DD;
- posición abierta;
- settlement;
- capital después;
- DD después;
- modo económico;
- multiplier;
- risk fraction;
- stop risk;
- realized PnL;
- cumulative PnL dentro del episodio.

## B. Contexto causal de cada operación

- expected structural R;
- confidence / dispersion;
- planned target R;
- projected risk;
- M5/H1/H4 range state;
- efficiency state;
- volatility state;
- body alignment;
- close location;
- rejection wick;
- CISD progress;
- raid depth;
- reclaim latency;
- source range state;
- capital band;
- peak-capital band;
- generation;
- loss streak;
- recent loss pressure.

## C. Lifecycle

- duration;
- MAE;
- MFE;
- first +0,25R / +0,5R / +1R;
- first adverse threshold;
- última barra causal antes del stop;
- si existió oportunidad real para partial reduction;
- si el mismo rule dañaría winners.

## D. Atribución económica

Medir contribución de:

- SIZING;
- ADAPTIVE_LEVERAGE;
- CIBO_COMPOUND;
- COMPOUND_PORTFOLIO.

La arquitectura económica debe trabajar **en conjunto**. No convertir CIBO en un simple stop manager.

## E. Cross-portfolio

- simultaneidad;
- concentración por asset;
- concentración por Trader;
- correlación temporal;
- stop-risk overlap;
- pérdida agregada por ventanas;
- reescalado después de drawdown;
- recovery velocity.

---

# 12. STRICT PARETO — CRITERIO DE PROMOCIÓN

Carrier global sólo se reemplaza si:

1. capital >= **USD 582.440,0252953678696769360345**;
2. DD mejora;
3. total GL <= carrier comparator;
4. ATTACK GL <= carrier comparator;
5. 3.368/3.368;
6. zero reject/defer;
7. zero sovereign breach;
8. reglas causales;
9. sin leakage;
10. sin quitar autoridad de entrada al Trader.

`dominates_current` es más fuerte y pide además capital >= capital del comparator.

Puede existir un STRICT PARETO no-dominante si cede una pequeña parte de capital pero mejora DD y GL y permanece ampliamente sobre el floor, como `f-m2850-h0060`.

---

# 13. TRADER LAB — ESTADO DE VELOCIDAD

Se trabajó también sobre la lentitud de Trader Lab.

Cambios recientes migraron numerosos workflows legacy al **Ultra Fast prepared batch**.

Evidencia documentada en commits recientes:

- varios workflows de 6–11 minutos bajaron a aproximadamente **43–114 segundos cold**;
- benchmark de 13 casos pasó de ~16m23s a ~2m03s cold;
- repeticiones exact-cache han llegado a ~**20–21 segundos**;
- se añadió Runtime Audit para impedir nuevas regresiones de fanout;
- se exige ranking verificado y JSON artifact en suites Ultra Fast.

No volver a introducir fanout oversubscribed ni workflows de investigación que ignoren el batch runner.

Core:

- `scripts/cibo_trader_lab_batch_runner.py`
- cache prepared M5;
- exact result cache;
- workers acotados;
- timeout fail-closed.

La prioridad científica sigue siendo DD, pero el laboratorio debe mantenerse suficientemente rápido para iterar sin ciclos de 9–11 minutos.

---

# 14. QUÉ FALTA PARA LLEGAR A 20–25% DD

## P0 — congelar carrier global actual para comparación

Usar:

`f-m2850-h0060` / run **37762989521**

hasta que exista un nuevo STRICT PARETO global.

## P1 — reparar y ejecutar second MEDIUM context

Es la acción más directa sobre el cuello actual.

## P2 — fusionar la frontera `tb-6500` 36,17370% con GL compensation

El gap de GL frente al carrier global es sólo ~USD 1,68k.

Buscar compensación localizada, por ejemplo:

- hysteresis pequeño;
- taper causal de un microcluster distinto;
- state-pressure ya validado sólo si no destruye compounding;
- defensa de una pérdida ATTACK específica por estado, no por identidad.

No usar broad budget.

## P3 — descubrir tercer cluster dentro del trough 2019

Cuando el primer + segundo context no basten, volver al atlas y buscar la siguiente contribución marginal.

## P4 — cuando el DD migre, cambiar de episodio inmediatamente

No sobreoptimizar julio-agosto 2019 cuando deje de ser el máximo.

Cada migración de max-DD define un nuevo problema causal.

## P5 — objetivos de escalón

- bajar de 36%;
- perforar 35%;
- 32%;
- 30%;
- 27,5%;
- <=25%;
- ideal <=20%.

No parar en 35/30/27,5.

---

# 15. QUÉ FALTA PARA CERTIFICAR CIBO

**CIBO NO ESTÁ CERTIFICADO.**

Llegar a DD 20–25% sólo habilita la fase científica final.

Después de cerrar ingeniería de DD/pérdidas:

## A. Freeze de arquitectura

- policy;
- parámetros;
- expected-R;
- confidence;
- calibration;
- lifecycle;
- economic group;
- hashes;
- commit reproducible;
- artifacts y digests.

## B. Accounting / provenance / conservation

Demostrar:

- conservación exacta;
- provenance de cada dólar;
- no double counting;
- no double spend;
- reservations;
- releases;
- settlement;
- recycling;
- reconciliation Sovereign/Portfolio/Compound;
- generation invariants.

## C. Ablations

Ablar:

- SIZING;
- ADAPTIVE_LEVERAGE;
- CIBO_COMPOUND;
- COMPOUND_PORTFOLIO;
- lifecycle;
- DD windows;
- expected-R;
- confidence;
- state pressure;
- hysteresis;
- context stops.

## D. Temporal robustness

- chronological folds;
- walk-forward;
- temporal replication;
- múltiples regímenes;
- años/semestres separados;
- estabilidad de DD y PF;
- no dependencia de un único régimen.

## E. Monte Carlo / path stress

- clustering;
- p05/P95;
- probability positive;
- probability of ruin;
- recovery time;
- loss bursts;
- compatible reorderings.

## F. Cost / execution stress

- spread;
- slippage;
- costs x2;
- latency;
- fill degradation;
- margin compression;
- provider constraints.

## G. Concentration stress

- por Trader;
- por asset;
- por regime;
- simultaneous correlation;
- remove best 1/2/3 trades;
- worst-cluster stress.

## H. Failure engineering

Probar:

- restart;
- duplicate event;
- duplicate reservation;
- partial settlement;
- stale snapshot;
- ledger crash;
- reconciliation mismatch;
- concurrent allocation;
- provider unavailable;
- idempotency.

Hard invariants:

- ZERO DOUBLE-SPEND;
- ZERO DUPLICATE AUTHORITY;
- ZERO SILENT SOURCE CREATION;
- ZERO RELEASE BEFORE RECONCILIATION.

## I. Forward qualification

- forward separado;
- gates definidos antes;
- no retune;
- observabilidad completa;
- zero-open final.

## J. Fresh sealed OOS

Holdout protegido:

**CIBO_USD60_6M_HOLDOUT_2017H1_V1**

**NO ABRIR todavía.**

Sólo usar después de freeze + prerequisites.

## K. Exámenes finales

Pendientes:

1. Worst-Trader Rescue Exam;
2. Final Integrated Certification Exam;
3. World Cup Maximum Capability Exam;
4. fresh sealed OOS;
5. zero-open closure;
6. final certification candidate.

---

# 16. COSAS QUE EL SIGUIENTE ARQUITECTO NO DEBE HACER

- no volver a empezar ceiling discovery desde cero;
- no tratar 8.000% como techo;
- no rechazar entradas;
- no blacklistar Trader o símbolo;
- no usar identidad para defender;
- no usar futuro/outcome leakage;
- no sacrificar el floor para presumir DD bajo;
- no promover `tb-6500` como global sin reparar el rebote de GL;
- no considerar los failures 37763320214/37763396352 como resultado económico;
- no repetir Localized/Narrow/Two-Band broad budgets;
- no usar stop MEDIUM global duro;
- no seguir apretando el mismo context-stop cuando la curva entra en cliff;
- no tocar el sealed holdout;
- no declarar certificación por un replay reutilizado;
- no olvidar que Sizing + Leverage + CIBO Compound + Portfolio Compound deben trabajar conjuntamente.

---

# 17. RUNS / COMMITS QUE EL SIGUIENTE ARQUITECTO DEBE LEER PRIMERO

## Runs

- **37762724394** — Carrier36509 MEDIUM M1 Micro Ridge.
- **37762989521** — Carrier36459 M1 Hysteresis Fusion Ridge — contiene carrier global 36,40871%.
- **37762660789** — Triggered DD Budget Ridge — `td-f` 36,42303%, frontera no-Pareto global.
- **37763166003** — W2 459 Capture Ridge.
- **37763397877** — W2 Taper Boundary Ridge — `tb-6500` 36,17370%, frontera física.
- **37763320214 / 37763396352** — failures técnicos del second MEDIUM context workflow.

## Commits

- **d893b9d48eb844d712f752a6b469d678980ad885** — launch MEDIUM M1 micro ridge.
- **1f1d65adb54d31d46e67ddee813c34d7fd087676** — fuse 36.45 MEDIUM edge with GL hysteresis.
- **3763ab919c4f7feccdb7ad1a0b949eb3fe3f9764** — expose realized-DD budget trigger.
- **a7839fdc72bdd0f3b14d36d47e561997cebad60d** — capture 459x June-2020 loss in DD window2.
- **31093449f3b75b8ba3b72acefc5048e4492e480b** — second MEDIUM context workflow, requiere reparación.
- **74c2b0646d8d83845dc55eb29417b9b17900bf6a** — resolve 459x W2 taper boundary.

---

# 18. CONTINUIDAD INMEDIATA PARA EL SIGUIENTE ARQUITECTO

Leer este handoff completo y luego:

1. **Tomar `f-m2850-h0060` como carrier global vigente.**
2. Reparar `cibo-trader-lab-carrier36459-medium-context2-surgical-ridge.yml`.
3. Relanzarlo contra el comparator **36,40871215817897%** y los GL del carrier global.
4. En paralelo, usar `tb-6500` como frontier para buscar **GL compensation de ~USD 1,68k**.
5. No degradar el floor USD 582.440,03.
6. Preservar 3.368 entradas.
7. Si aparece nuevo STRICT PARETO, promover y recalcular max-DD attribution.
8. Si el max-DD migra, detener tuning del episodio viejo y atacar el nuevo episodio.
9. Repetir hasta <=25%, ideal <=20%.
10. Sólo entonces freeze + batería científica completa.

Frase soberana:

> **“Reducir Drawdown a lo máximo posible sin degradar el techo; estudiar causalmente cada episodio de pérdida; reparar, replay, comparar STRICT PARETO y repetir. Ideal 20%, tolerable hasta 25%. No detenerse en metas intermedias.”**

---

# 19. RESUMEN EJECUTIVO PARA HANDOFF

Estado histórico de referencia:

- capital ~USD 582.440;
- DD ~65,10%;
- GL ~USD 1,445M.

Carrier global actual:

- capital **USD 670.974,10**
- DD **36,40871%**
- total GL **USD 957.685,07**
- ATTACK GL **USD 956.129,11**
- PF **~1,70056**
- 3.368/3.368
- zero breach
- ~USD 88,5k sobre floor.

Frontier física más baja identificada:

- **36,17370%** en `tb-6500`;
- capital ~USD 670.926;
- todavía requiere compensar ~USD 1,68k de GL para superar al carrier global bajo el criterio completo.

La prioridad absoluta sigue siendo **DRAWDOWN**.

**Ideal = 20%. Tolerable = hasta 25%.**

CIBO **NO está certificado**.

---



# QORE CORE — CIBO MASTER CONTINUITY HANDOFF

## TRUE CEILING FROZEN → STRICT-PARETO DD / GROSS-LOSS COMPRESSION → 20% IDEAL / 25% MAX TOLERABLE → SCIENTIFIC CERTIFICATION

**Owner / CEO:** Sergio Meza  
**Repositorio fuente de verdad:** mezas3238-hue/qore-core  
**Branch canónico:** agent/cibo-causal-expectation-leakage-fix-001  
**Documento canónico de continuidad:** docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md  
**HEAD inmediatamente anterior a este handoff:** f25888f76f6def9f702922f0f3dafabf5353f209  
**Capital inicial canónico:** USD 60  
**Holdout de investigación reutilizado:** 3.368 entradas / aproximadamente 36 meses  
**Estado:** investigación activa; CIBO NO está certificado  

---

# 0. DIRECTIVA SOBERANA — LEER ANTES DE TOCAR CÓDIGO

Este documento sustituye el estado operativo anterior del handoff y es la referencia de continuidad para el siguiente arquitecto.

La fase de búsqueda del techo ya no gobierna el trabajo. El **techo mínimo de referencia está congelado** y la prioridad absoluta ahora es:

> **REDUCIR EL DRAWDOWN HASTA EL MÁXIMO POSIBLE SIN DEGRADAR EL TECHO Y, EN PARALELO, REDUCIR DE FORMA SUSTANCIAL LA PÉRDIDA BRUTA.**

Objetivo de drawdown del Owner:

- **ideal: 20% o menor**;
- **tolerable como máximo: 25%**;
- **más de 25%: todavía no está en la zona objetivo**;
- 38%, 35%, 30% son solamente escalones intermedios, no metas finales.

No detenerse al romper 40%, 35% o 30%. El ciclo obligatorio continúa hasta llegar a <=25% si la arquitectura causal lo permite sin destruir el techo.

Reglas soberanas que NO se negocian:

1. El Trader decide y ejecuta la entrada. **CIBO no tiene potestad para rechazar la entrada del Trader.**
2. CIBO administra financieramente todas las entradas después de ejecutadas.
3. Deben mantenerse **3.368 / 3.368 entradas**.
4. Cero reject, defer o withheld financiero de Sizing.
5. Cero ATTACK sovereign breach.
6. SIZING + ADAPTIVE_LEVERAGE + CIBO_COMPOUND + COMPOUND_PORTFOLIO deben permanecer trabajando conjuntamente.
7. No usar outcome leakage ni información futura.
8. No hardcodear Traders concretos como defensa. El Trader culpable cambia entre episodios.
9. Toda mejora debe validarse mediante Trader Lab con replay causal.
10. La metodología obligatoria es:
   **forensics → hipótesis causal → modificación → replay → STRICT PARETO → conservar o rechazar → repetir**.

Una defensa que baja DD pero cae por debajo del techo congelado es **RECHAZADA como solución final**, aunque sea útil como evidencia forense.

---

# 1. BENCHMARK CONGELADO — SUELO ECONÓMICO QUE NO SE DEBE DEGRADAR

El benchmark congelado que gobierna la fase actual es:

- capital inicial: **USD 60**;
- capital final mínimo aceptable: **USD 582.440,0252953678696769360345**;
- ganancia total aproximada: **+970.633,38%**;
- max DD original: **65,1041975924%**;
- ATTACK cap del benchmark: **10.000x**;
- entradas: **3.368 / 3.368**;
- sovereign breach: **0**;
- total gross loss original: **USD 1.444.736,060362508738067914772**;
- ATTACK gross loss original: **USD 1.443.117,897425126985300959340**;
- ATTACK gross profit original: aproximadamente **USD 2.025.323,73**;
- total PF original: aproximadamente **1,40310478936**;
- ATTACK PF original: aproximadamente **1,403436**.

IMPORTANTE:

**USD 582.440,03 es el piso congelado de aceptación, no un techo absoluto metafísico.**  
Si una variante produce más capital y menor DD/loss, ese capital adicional se usa como headroom para seguir comprimiendo DD.

---

# 2. MEJOR ESTADO ACTUAL — NUEVO STRICT PARETO 38,4621%

El mejor candidato de investigación confirmado al momento de este handoff es:

## p30-cg600-1500-f95

Run decisivo: **37692116415 — SUCCESS**  
Workflow: **QORE CIBO Carrier39 P30 Capital-Gated Window6 Fast**  
Artifact: **11514255866**  
Digest: **sha256:552a31bc9cb44d2de27c04425dbab5d2379176ac0a774f04c3aa0a0e6b543a16**

Resultados exactos:

- capital final: **USD 668.085,9185341914931181005054**;
- ganancia total desde USD 60: aproximadamente **+1.113.376,53%**;
- max DD: **38,4621082823%**;
- total gross loss: **USD 960.833,3801149893950274727244**;
- ATTACK gross loss: **USD 959.269,4507748429533595932652**;
- total profit factor: **1,69525677642**;
- ATTACK profit factor: **1,69616846660**;
- entradas: **3.368 / 3.368**;
- all entries preserved: **true**;
- ATTACK sovereign breach: **0**.

Mejora contra el benchmark congelado:

- DD: **65,1042% → 38,4621%**;
- reducción absoluta de DD: **26,6421 puntos porcentuales**;
- reducción relativa importante, pero TODAVÍA insuficiente para el objetivo 20–25%;
- total gross loss: **USD 1.444.736,06 → USD 960.833,38**;
- reducción de total gross loss: **USD 483.902,68**, aproximadamente **-33,49%**;
- ATTACK gross loss: **USD 1.443.117,90 → USD 959.269,45**;
- reducción ATTACK gross loss: **USD 483.848,45**, aproximadamente **-33,53%**;
- capital final queda aproximadamente **USD 85.645,89 por encima** del suelo congelado.

Este es el **carrier principal de investigación** que debe usar el siguiente arquitecto salvo que encuentre en GitHub un commit posterior con un STRICT PARETO mejor.

NO llamar este resultado “certificado”. Todo esto sigue siendo investigación sobre holdout reutilizado.

---

# 3. PROGRESIÓN REAL DEL DRAWDOWN CONSEGUIDA

La trayectoria de compresión ya demuestra que el problema no es monolítico. Se ha ido desplazando de episodio en episodio:

| Etapa | Capital aprox. | Max DD | Lectura |
|---|---:|---:|---|
| benchmark congelado | 582.440 | 65,10% | punto de partida |
| primer band Pareto | 663.395 | 64,02% | 2.000–3.999x era destructivo |
| carrier DD selectivo | 687.903 | 51,15% | ventana 800–1.900x |
| segunda ventana | 689.841 | 48,37% | aparece piso bootstrap temprano |
| tercera ventana low-mult | 687.114 | 46,25% | 2–20x bajo DD |
| cuarta ventana high-mult | 688.634 | 44,05% | 4.800–5.200x |
| democión exacta 2x | 690.681 | 43,85% | sólo 2x, no 3x/4x |
| high-left window | 689.672 | 41,73% | fuga 4.4k–4.8k |
| expected-R partial | 667.465 | 40,0058% | piso MEDIUM casi roto |
| carrier39 | 667.459 | 39,6850% | 40% roto |
| capital-gated window6 | 668.086 | 39,1742% | 50–170x localizado |
| **p30 + capital-gated window6** | **668.086** | **38,4621%** | mejor actual |

La lección central:

> **Cada vez que se comprime un episodio dominante, el max DD migra a otro episodio distinto. Por tanto no existe una sola “perilla de DD”; hay que hacer forensics del nuevo máximo después de cada carrier aceptado.**

---

# 4. ARQUITECTURA EXACTA DEL CARRIER 38,4621%

La arquitectura que llevó al mejor carrier combina defensas causales localizadas, no un derisking global.

## Núcleo económico

- distributed ATTACK frontier;
- coordinated economic group;
- ceiling discovery mode de laboratorio;
- ATTACK cap base: 10.000x;
- MEDIUM cap: 14x;
- medium drawdown intensity trigger: 0,05;
- bootstrap cushion share: 1,00;
- growth leverage slope: 10;
- ATTACK single-trade risk fraction: 0,20;
- same-Trader ATTACK loss-streak trigger: 3;
- loss-streak taper: 0,75;
- Portfolio shock trigger: 0,05;
- Portfolio shock taper: 0,50;
- lifecycle base: DEFENSIVE_INITIAL_STOP_CAP;
- lifecycle base sólo MEDIUM 1x;
- defensive stop base: -0,20R;
- lifecycle Trader loss streak trigger: 2;
- lifecycle min stop-risk fraction trigger: 0,03.

## Capa selectiva por multiplier/risk

- ATTACK multiplier band 2.000–3.999x;
- taper fraction: 0,20;
- ATTACK risk-fraction band 0,025–0,05;
- taper fraction: 0,50.

## Ventanas DD causales acumuladas

Ventana 1:
- DD 0,10–0,30;
- multiplier 800–1.900x;
- taper 0,40.

Ventana 2:
- DD 0,10–0,35;
- multiplier 350–450x;
- taper 0,60.

Ventana 3:
- DD 0,15–0,50;
- multiplier 2–20x;
- taper 0,80.

Ventana 4:
- DD 0,15–0,50;
- multiplier 4.800–5.200x;
- taper 0,90.

Ventana 5:
- DD 0,10–0,50;
- multiplier 4.400–4.799x;
- taper 0,85.

## Democión causal muy estrecha

- low-multiplier demotion upper: **2x**;
- activa desde DD: **0,15**;
- democión 2x → MEDIUM 1x;
- ampliar a 3x/4x fue perjudicial y quedó rechazado.

## Bootstrap lifecycle causal con expected-R

- feature: ADVERSE_PARTIAL_REDUCTION;
- requiere expectativa causal disponible;
- expected-R ceiling: **0,10**;
- adverse loss cut: **-0,40R**;
- partial fraction: **0,30** en el mejor carrier;
- capital ceiling: **USD 100**;
- DD trigger: **0,10**;
- same-Trader loss streak trigger: **1**;
- MEDIUM max multiplier: **2**.

## Ventana 6 capital-gated — hallazgo más reciente

- DD: **0,05–0,45**;
- multiplier: **50–170x**;
- taper: **0,95**;
- capital floor: **USD 600**;
- capital ceiling: **USD 1.500**.

Esta última capa es importante porque el taper 50–170x global destruía capital; al limitarlo al episodio económico real, se volvió útil.

---

# 5. NUEVO MAX DRAWDOWN DEL CARRIER 38,4621% — PRIORIDAD P0 DEL SIGUIENTE ARQUITECTO

El max DD actual ya NO es el episodio ATTACK de 2020/2021.

Ahora el episodio dominante es **MEDIUM temprano**, en 2019.

Datos exactos:

- peak: **2019-07-19 06:45 UTC**;
- peak capital: **USD 79,7639386081**;
- trough: **2019-08-12 11:25 UTC**;
- trough capital: **USD 49,0850461704**;
- pérdida peak-to-trough: **USD 30,6788924377**;
- max DD: **38,4621082823%**;
- modo neto del episodio: **MEDIUM = -USD 30,6788924377**;
- ATTACK no domina este nuevo máximo;
- multiplier 1x net: aproximadamente **-USD 26,6207**;
- multiplier 2x net: aproximadamente **-USD 4,05815**.

Gross loss dentro del episodio por multiplier:

- 1x: aproximadamente **USD 48,3391**;
- 2x: aproximadamente **USD 4,05815**.

Atribución neta por Trader dentro del episodio:

- R43_GBPUSD: aproximadamente **-USD 10,001**;
- VT31_NAS100: aproximadamente **-USD 6,162**;
- R38_GBPJPY: aproximadamente **-USD 5,5097**;
- R42_AUDJPY: aproximadamente **-USD 5,1919**;
- R38_EURUSD: aproximadamente **-USD 2,254**;
- R34_XAUUSD: aproximadamente **-USD 1,758**;
- VT08_FOREX: aproximadamente **+USD 0,198**.

Esto demuestra otra vez por qué NO se debe blacklistar un Trader: el daño está distribuido y cambia con el episodio.

Estado del trough relevante:

- Sovereign bank: aproximadamente **USD 29,32**;
- Portfolio cushion: aproximadamente **USD 19,76**;
- open margin: 0;
- open stop risk: 0;
- el episodio termina por pérdida realizada, no por riesgo abierto pendiente.

Rachas en el trough:

- VT31: 7;
- R38_GBPJPY: 3;
- R42_AUDJPY: 3;
- R38_EURUSD: 1;
- otros variables.

## Conclusión forense P0

El próximo gran problema no se puede arreglar reduciendo multiplicador por debajo de 1x.  
**MEDIUM 1x ya está en la intensidad mínima permitida sin rechazar la entrada.**

Por tanto, para bajar de 38,46% hacia 25% hay que estudiar profundamente:

- lifecycle post-entry causal;
- partial reduction inteligente;
- expected-R / confidence previa a decisión;
- deterioro intratrade observable sólo con barras ya cerradas;
- same-Trader / portfolio loss state;
- duración underwater;
- recuperación parcial;
- riesgo de cerrar demasiado pronto trades que luego recuperan;
- diferencias entre direct-to-stop losers y posiciones que primero tuvieron excursión favorable;
- posibilidad de reducir cola negativa sin cortar winners.

NO repetir stops rígidos globales: ya se probó que destruyen compounding.

---

# 6. FORENSICS PROFUNDO OBLIGATORIO DEL DRAWDOWN

El Owner exige un estudio a profundidad de los factores que ocasionan DD. El siguiente arquitecto debe trabajar por episodios y construir un **atlas causal del drawdown**.

Para cada uno de los top 10 episodios de DD registrar, como mínimo:

## A. Estado económico antes de cada trade

- capital total;
- peak capital;
- drawdown vivo;
- Sovereign bank;
- Portfolio cushion;
- capital generation;
- recycled generation;
- reserved cushion;
- open margin;
- open stop risk;
- requested multiplier;
- approved multiplier;
- cap que hizo bind;
- risk fraction propuesta y aprobada;
- Compound state;
- Portfolio credit/release/recycle state.

## B. Estado causal del Trader

- Trader ID únicamente para atribución, no como regla fija;
- últimos 1/2/3/5 outcomes ya liquidados;
- same-Trader loss streak;
- rolling net PnL;
- rolling gross loss;
- rolling gross profit;
- rolling PF;
- shock magnitude;
- tiempo desde último shock;
- recuperación desde último shock;
- causal expected-R;
- causal confidence / dispersion;
- régimen;
- volatilidad;
- spread / liquidity state si está disponible.

## C. Estado cross-portfolio

- posiciones simultáneas;
- overlap de stop risk;
- clustering same asset;
- clustering cross asset;
- clustering same Trader;
- correlación de pérdidas;
- varias pérdidas liquidadas en ventana corta;
- si CIBO volvió a escalar antes de recuperar cushion.

## D. Lifecycle

Para cada gran perdedor:

- initial stop;
- MFE antes de pérdida;
- MAE;
- si alcanzó +0,25R / +0,5R / +1R;
- si cayó directo a stop;
- si hubo señal causal de deterioro previa al stop;
- cuánto habría ahorrado una partial reduction;
- cuánto profit futuro habría sacrificado;
- si el mismo patrón aparece en winners.

## E. Atribución de motores

Registrar cuál de los cuatro motores aportó a la intensidad económica:

- SIZING;
- ADAPTIVE_LEVERAGE;
- CIBO_COMPOUND;
- COMPOUND_PORTFOLIO.

No aceptar explicaciones del tipo “ATTACK perdió” sin identificar qué estado económico permitió el tamaño y por qué.

---

# 7. PÉRDIDA BRUTA — SEGUNDO OBJETIVO SOBERANO

El Owner pidió explícitamente reducir también la pérdida bruta.

Situación original:

- total gross loss: **USD 1.444.736,06**;
- ATTACK gross loss: **USD 1.443.117,90**.

Mejor carrier actual:

- total gross loss: **USD 960.833,38**;
- ATTACK gross loss: **USD 959.269,45**.

Reducción ya conseguida:

- total gross loss: aproximadamente **-33,49%**;
- ATTACK gross loss: aproximadamente **-33,53%**.

Esto es una mejora grande, pero **no se considera terminado**.

La meta no es minimizar gross loss a cualquier costo. Una defensa que corta USD 300k de pérdidas pero también destruye USD 500k de gross profit queda rechazada.

Siempre reportar simultáneamente:

- terminal capital;
- gross profit;
- gross loss;
- net;
- PF;
- max DD;
- número de trades;
- entradas preservadas;
- sovereign breach;
- binds de cada defensa.

---

# 8. DESCUBRIMIENTOS CAUSALES ACEPTADOS

## 8.1 Banda ATTACK 2.000–3.999x

Primer gran breakthrough post-ceiling.

Caso histórico decisivo:
- b2000-3999-f25;
- capital ~USD 663.394,79;
- DD ~64,02%;
- total GL ~USD 1.302.694,09.

Demostró que ciertas zonas de intensidad ATTACK son económicamente destructivas: reducirlas puede **subir capital y bajar pérdidas a la vez**.

## 8.2 Risk-fraction band 0,025–0,05

Mejoró capital y gross loss, aunque el DD bajó poco. Se conservó como bloque complementario.

## 8.3 Ventanas DD × multiplier

Hallazgo fundamental:

El derisking global mata compounding; las ventanas causales estrechas pueden comprimir episodios concretos.

Ventanas útiles descubiertas:

- 800–1.900x;
- 350–450x;
- 2–20x;
- 4.800–5.200x;
- 4.400–4.799x.

## 8.4 Democión exacta 2x

Demover sólo 2x durante DD fue útil.

Ampliar a 3x/4x fue demasiado agresivo.

## 8.5 Expected-R + adverse partial reduction

El gating causal por expected-R permitió reducir el piso MEDIUM sin destruir el capital.

El área útil es estrecha. Cambios agresivos en expected-R ceiling o partial fraction pueden romper la trayectoria.

## 8.6 Capital-gated sixth window

El rango 50–170x era destructivo sólo en un tramo de capital concreto.

Taper global 50–170x: RECHAZADO.  
Taper limitado a capital aproximadamente 600–1.500: ÚTIL.

Esto confirma que el **estado de capital debe formar parte de la causalidad de DD**, no sólo multiplier y live-DD.

---

# 9. HIPÓTESIS / DEFENSAS RECHAZADAS — NO REPETIR CIEGAMENTE

Quedan rechazadas como arquitectura final, aunque algunas sirvieron como evidencia:

- rechazar entradas;
- Sizing rejection / defer;
- fixed Trader blacklist;
- global ATTACK taper amplio;
- hard DD budget global desde peak;
- broad multiplier taper sin state gating;
- confidence-only global;
- stress-confidence global fuerte;
- Portfolio shock one-shot amplio;
- broad lifecycle stop compression;
- ATTACK-only adverse loss cut global;
- high-risk lifecycle post-entry global;
- democión low-multiplier amplia 10x/20x/50x/100x;
- democión 3x/4x;
- MEDIUM 1x lifecycle ampliado globalmente;
- bootstrap lifecycle stop rígido;
- ultra-tight MEDIUM stop;
- global 50–170x window6;
- 50–150x taper global;
- early-capital DD budgets que estrangulan el crecimiento;
- cualquier defensa que caiga por debajo de USD 582.440,03.

Patrón observado repetidamente:

> **Cuanto más global es la defensa, más fácil es bajar pérdida bruta y DD, pero mayor es el daño al compounding. La solución debe ser causal, localizada y reversible.**

---

# 10. TRADER LAB — BANCO OFICIAL DE PRUEBAS

El laboratorio de pérdidas + Drawdown está incorporado en Trader Lab de GitHub. No crear un laboratorio separado.

Core principal:

- src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py
- scripts/cibo_trader_lab_three_mode_ceiling.py
- src/qore/infrastructure/cibo_position_lifecycle.py

Trader Lab mide conjuntamente:

- terminal capital;
- max DD;
- total gross loss;
- ATTACK gross loss;
- total PF;
- ATTACK PF;
- entradas 3.368/3.368;
- rejection/defer;
- sovereign breach;
- drawdown attribution;
- multiplier attribution;
- Trader attribution;
- lifecycle;
- causal expectation;
- confidence;
- binds de ventanas y risk controls;
- engineering trace;
- trade receipts;
- epoch receipts.

Capacidades añadidas durante esta fase:

- multiplier-band taper;
- risk-fraction-band taper;
- múltiples ventanas DD×multiplier;
- segunda/tercera/cuarta/quinta/sexta ventana causal;
- low-multiplier exact demotion;
- recent-Trader loss pressure;
- state-gated lifecycle override;
- distinct bootstrap lifecycle features;
- expected-R gating;
- peak/capital state gating;
- early-capital Trader shock;
- capital-band DD budget;
- full causal receipts;
- **capital floor/ceiling para window6**.

Últimas implementaciones relevantes:

- feat(cibo): capital-gate sixth causal DD multiplier window  
  commit **67ee5aecd64c887c4a556669070c09cdffd5667f**
- cli(cibo): expose capital-gated sixth DD window  
  commit **3b9db9ff7e7a7601860490256aea3c7c81f71da5**
- exp(cibo): capital-gate 50x-170x defense on 39pct carrier  
  commit **ccb017f63f824e55c598b0f8a97ebaa982d34f63**
- exp(cibo): pair p30 MEDIUM floor with capital-gated window6  
  commit **339cf8747c6b73e724b59036c26be7c4cda5350d**
- exp(cibo): micro-gate 140x-150x ATTACK stress confidence  
  commit **f25888f76f6def9f702922f0f3dafabf5353f209**

Micro stress-confidence 140–150x no mejoró el carrier: los casos quedaron esencialmente iguales al base 39,685%. No priorizar esa línea salvo nueva evidencia.

---

# 11. RUNS CLAVE QUE EL SIGUIENTE ARQUITECTO DEBE CONOCER

Referencias recientes:

- 37662670595 — ATTACK Multiplier Band Frontier — primer gran STRICT PARETO.
- 37663346696 — ATTACK Risk-Fraction Band Frontier.
- 37663861074 — multiplier-band fine ridge.
- 37663937350 — Pareto band + DD compression.
- 37664970209 — residual DD multiplier window.
- 37665136328 — Band05 sub60 DD.
- 37665838598 — dual carrier residual DD.
- 37669012561 — dual carrier two DD windows.
- 37669404090 — recent Trader loss pressure.
- 37669717694 — MEDIUM1x DD defense — rechazado.
- 37669937494 — low-multiplier demotion.
- 37670103941 — sub40 bootstrap demotion.
- 37670289160 — layered sub40 ridge.
- 37670671920 — localized bootstrap MEDIUM defense.
- 37675317327 — bootstrap 46% fine ridge.
- 37675905414 — carrier46 fourth window.
- 37677062833 — exact2x demotion ridge.
- 37677997932 — high-left fifth window, 41,73%.
- 37683996926 — expected-R micro ridge.
- 37683815572 — peak-latched initial stop.
- 37684905114 — mid-low window6 global, evidencia de por qué hacía falta capital gating.
- 37689995899 — ultra-tight MEDIUM bootstrap stop — no solucionó el problema.
- 37691976414 — capital-gated window6, **39,1742%**.
- 37692116415 — p30 + capital-gated window6, **38,4621% BEST ACTUAL**.
- 37692140731 — micro stress-confidence — sin mejora.

---

# 12. PLAN INMEDIATO PARA BAJAR DE 38,46% A 25%

## P0 — Congelar carrier 38,4621% como baseline de investigación actual

No “certificarlo”. Usarlo como carrier para la siguiente forensia.

Guardar siempre:

- exact CLI;
- commit;
- run;
- artifact;
- digest;
- capital;
- DD;
- GL;
- PF;
- binds;
- entry preservation;
- breaches.

## P1 — Forensics profundo del episodio MEDIUM 2019

Ésta es la prioridad técnica inmediata.

Responder cuantitativamente:

1. ¿Cuántas de las pérdidas 1x/2x son direct-to-stop?
2. ¿Cuántas tuvieron MFE positiva antes de caer?
3. ¿Qué winners del mismo estado serían dañados por cada defensa?
4. ¿Expected-R separa losers de winners?
5. ¿Confidence/dispersion añade información incremental?
6. ¿Same-Trader streak ayuda o sólo llega tarde?
7. ¿El deterioro en barras M5 cerradas aparece con suficiente antelación?
8. ¿La partial reduction óptima debe ser 20%, 25%, 30% u otra?
9. ¿Hay una combinación causal de MFE + adverse bar + expected-R que reduzca pérdidas sin cerrar winners?
10. ¿El efecto depende del capital absoluto, peak capital o generation?
11. ¿R43/VT31/R42 aparecen porque son malos o sólo porque coinciden con ese régimen? No hardcodear ID.
12. ¿Se puede preservar recuperación dejando un “runner” tras partial reduction?

## P2 — Diseñar defensa MEDIUM 1x post-entry no destructiva

Restricción difícil:

1x ya es mínimo. No se puede bajar sizing sin rechazar o mutilar la entrada.

Por eso evaluar:

- conditional partial reduction;
- adverse excursion threshold;
- recovery-aware partial;
- profit-protected runner;
- time-underwater + expected-R;
- closed-bar deterioration;
- peak-capital/generation gating;
- causal regime gating;
- partial fraction adaptativa.

NO usar stop duro global.

## P3 — Recalcular atlas después de cada mejora

Cuando el DD 2019 deje de ser el máximo, inmediatamente identificar el nuevo episodio.

No seguir afinando un episodio que ya dejó de gobernar max DD.

## P4 — Escalones de control

Usar hitos intermedios:

- <38%;
- <35%;
- <32%;
- <30%;
- <27,5%;
- <=25%;
- ideal <=20%.

Pero NO congelar como meta ninguno de los escalones intermedios.

## P5 — Mantener gross loss bajo control

Cada reducción DD debe comprobar que no reintroduce pérdida bruta.

Objetivo: continuar por debajo de ~USD 960k total GL y seguir comprimiendo.

---

# 13. CRITERIO STRICT PARETO VIGENTE

Una variante es aceptable como nuevo carrier de investigación sólo si:

1. capital final >= **USD 582.440,0252953678696769360345**;
2. max DD mejora contra el carrier que se está intentando reemplazar;
3. total gross loss no se degrada materialmente y, preferiblemente, mejora;
4. ATTACK gross loss no se degrada materialmente;
5. 3.368 / 3.368 entradas;
6. zero Sizing rejection;
7. zero Sizing deferral;
8. zero ATTACK sovereign breach;
9. reglas causales;
10. zero outcome leakage;
11. ninguna alteración a la autoridad del Trader para entrar.

Para la fase final de DD:

> **20% es ideal. 25% es máximo tolerable.**

Una solución de 26% sigue sin cumplir la directiva final.

---

# 14. QUÉ FALTA PARA CERTIFICAR CIBO

CIBO sigue NO CERTIFICADO.

Llegar a 20–25% DD es condición necesaria de arquitectura, pero no suficiente para certificación.

Después de cerrar DD/gross-loss engineering todavía falta:

## A. Freeze de arquitectura

- congelar policy;
- congelar parámetros;
- congelar calibration;
- congelar expected-R/confidence models;
- hash/commit reproducible;
- documentar toda autoridad económica.

## B. Accounting / provenance / conservation

Demostrar formalmente:

- conservación de capital;
- provenance de cada dólar;
- cero double counting;
- cero double spend;
- reservations correctas;
- releases correctos;
- recycling correcto;
- reconciliación Sovereign/Portfolio/Compound;
- semántica de Sovereign negativo si existe;
- invariantes de generations.

## C. Ablations

Ablar individual y conjuntamente:

- SIZING;
- ADAPTIVE_LEVERAGE;
- CIBO_COMPOUND;
- COMPOUND_PORTFOLIO;
- lifecycle;
- DD windows;
- expected-R;
- shock protection.

Demostrar qué aporta cada componente y que ninguno es decorativo.

## D. Robustez temporal

- chronological folds;
- walk-forward;
- temporal replication;
- diferentes regímenes;
- años/semestres separados;
- no depender de un solo periodo favorable.

## E. Monte Carlo / path stress

- reorder compatible con causalidad;
- Monte Carlo;
- loss clustering;
- tail stress;
- p05 PnL;
- p95 DD;
- probability positive;
- probability of ruin;
- recovery-time distribution.

## F. Cost / execution stress

- spread stress;
- slippage stress;
- cost x2;
- margin compression;
- provider constraints;
- latency si aplica;
- fill degradation.

## G. Concentration stress

- por Trader;
- por asset;
- por régimen;
- remover best 1 trade;
- remover best 2 trades;
- remover best 3 trades;
- burst losses;
- simultaneous correlation stress.

## H. Failure engineering

Hard invariants:

- ZERO DOUBLE-SPEND;
- ZERO DUPLICATE AUTHORITY;
- ZERO SILENT SOURCE CREATION;
- ZERO RELEASE BEFORE RECONCILIATION.

Probar:

- restart;
- duplicate event;
- duplicate reservation;
- partial settlement;
- ledger crash;
- reconciliation mismatch;
- stale snapshot;
- provider unavailable;
- concurrent allocation;
- idempotency;
- recovery after interruption.

## I. Forward qualification

- periodo forward separado;
- gates predefinidos;
- sin retune;
- observabilidad completa;
- zero-open al cierre.

## J. Fresh sealed OOS

Holdout protegido mencionado por governance:

**CIBO_USD60_6M_HOLDOUT_2017H1_V1**

NO abrirlo antes del freeze y prerequisites.

## K. Exámenes finales

Pendientes:

1. Worst-Trader Rescue Exam;
2. Final Integrated Certification Exam;
3. World Cup Maximum Capability Exam;
4. fresh OOS;
5. zero-open closure;
6. final certification candidate.

Cuando CIBO llegue al rango **20–25% DD**, debe entrar a la batería científica completa antes de declararlo certificado.

---

# 15. COSAS QUE EL SIGUIENTE ARQUITECTO NO DEBE HACER

- No volver a descubrir el ceiling desde cero.
- No tratar 8.000% como ceiling; era sólo base histórica.
- No degradar deliberadamente el capital por una cifra bonita de DD.
- No rechazar entradas.
- No quitar autoridad al Trader.
- No blacklistar R34, R42, R43, VT31 o cualquier Trader por identidad.
- No usar resultados futuros para decidir una entrada actual.
- No confundir reused holdout con certificación.
- No reabrir defensas globales ya rechazadas salvo que exista una hipótesis causal nueva.
- No optimizar sólo ATTACK: el max DD actual es MEDIUM 1–2x.
- No olvidar gross loss mientras baja DD.
- No apagar Compound/Portfolio/Leverage/Sizing para “resolver” riesgo.
- No declarar CIBO certificado por alcanzar un buen replay.

---

# 16. ARCHIVOS CLAVE

Motor de laboratorio:

- src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py
- scripts/cibo_trader_lab_three_mode_ceiling.py
- src/qore/infrastructure/cibo_position_lifecycle.py

Handoff canónico:

- docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md

Protocolos de certificación:

- docs/research/CIBO-FINAL-INTEGRATED-CERTIFICATION-EXAM-PROTOCOL-V1.md
- docs/research/CIBO-INTEGRATED-CERTIFICATION-SEQUENCE-AMENDMENT-V1.md
- docs/research/CIBO-USD60-6M-MAXIMUM-REAL-CAPABILITY-CERTIFICATION-V1.md
- docs/research/CIBO-WORST-TRADER-RESCUE-EXAM-CONTRACT-V1.md

Workflows recientes que contienen la arquitectura moderna:

- .github/workflows/cibo-trader-lab-carrier39-capital-gated-window6-fast.yml
- .github/workflows/cibo-trader-lab-carrier39-p30-capital-gated-window6-fast.yml
- .github/workflows/cibo-trader-lab-carrier39-micro-stress-confidence.yml
- .github/workflows/cibo-trader-lab-carrier40-midlow-window6-ridge.yml
- .github/workflows/cibo-trader-lab-carrier40-expected-r-micro-ridge.yml
- .github/workflows/cibo-trader-lab-carrier40-peak-latched-initial-stop.yml
- .github/workflows/cibo-trader-lab-carrier43-exact2x-demotion-ridge.yml
- .github/workflows/cibo-trader-lab-carrier43-high-left-fifth-window.yml
- .github/workflows/cibo-trader-lab-dual-carrier-two-dd-windows.yml

---

# 17. FRASE DE CONTINUIDAD PARA COPIAR AL SIGUIENTE CHAT

> Continuar CIBO en mezas3238-hue/qore-core, branch agent/cibo-causal-expectation-leakage-fix-001. Leer primero el handoff canónico docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md. El ceiling mínimo congelado es USD 582.440,03 desde USD 60. El mejor STRICT PARETO de investigación al cierre del handoff es p30-cg600-1500-f95, run 37692116415: USD 668.085,92, DD 38,4621%, total gross loss USD 960.833,38, ATTACK gross loss USD 959.269,45, PF total ~1,6953, 3.368/3.368, cero sovereign breach. La prioridad absoluta es seguir reduciendo DD sin degradar el ceiling; ideal <=20%, máximo tolerable <=25%. El max DD actual ya es MEDIUM 1–2x en julio–agosto de 2019, peak USD 79,76 → trough USD 49,09. Hacer forensics profundo de ese episodio y diseñar protección post-entry causal, no stop global. Seguir forensics → modificación → Trader Lab replay → STRICT PARETO → repetir. No certificar con reused holdout. Tras llegar a 20–25% ejecutar batería científica, accounting/provenance, ablations, Monte Carlo, stress, temporal replication, forward, fresh sealed OOS, Rescue Exam, Final Integrated Exam y World Cup Maximum Capability Exam.

---

# 18. RESUMEN EJECUTIVO FINAL

CIBO ya demostró que puede preservar las 3.368 entradas, mantener un techo superior al benchmark congelado y reducir simultáneamente DD y pérdida bruta.

Estado original:
- capital USD 582.440;
- DD 65,10%;
- gross loss USD 1,445M.

Estado actual:
- capital **USD 668.086**;
- DD **38,46%**;
- gross loss **USD 960,8k**.

La investigación ha eliminado aproximadamente:

- **26,64 puntos porcentuales de DD**;
- **USD 483,9k de gross loss**.

Pero la misión todavía NO está terminada.

El próximo arquitecto debe considerar **38,46% como un carrier intermedio**, no como éxito final.

**Objetivo soberano: ideal 20% DD; máximo tolerable 25%, sin degradar el ceiling.**

Cuando ese rango esté alcanzado de forma causal y reproducible, recién entonces congelar la arquitectura y someter CIBO a la batería científica de certificación.
