# VT08 CRT PURE — R2-G MODEL #1 COMPETITION FAMILY 001

**Identity:** `VT08_CRT_PURE_R2G_MODEL1_COMPETITION_FAMILY_001`  
**Workflow run:** `35811391351`  
**Evidence HEAD:** `a9fe37e9c69aaad592cd0163d9847540a7f5760a`  
**Status:** FAMILY COMPLETE / COMPETITION-ONLY FIX INSUFFICIENT  
**Research only:** TRUE

## 1. Engineering objective

The CRT methodology is frozen.

R2-G changes one dimension only:

`SAME_PARENT_MODEL1_HYPOTHESIS_COMPETITION`

Every arm keeps:

- the same H4 parent CRT;
- the same close-unmitigated M15 Model #1 source construction;
- source availability only at M15 close;
- body-close confirmation;
- next contiguous M15 open;
- source-candle structural stop;
- C1 50% target control;
- C3-close expiry;
- STOP_FIRST same-M15 ambiguity;
- maximum one trade attempt per parent;
- no fallback after selected invalid risk geometry.

The family was declared before replay outcomes.

## 2. Frozen competition family

1. `FIRST_SOURCE_ONLY_CONTROL`
2. `FIRST_CONFIRMATION_WINS`
3. `NEWEST_SUPERSEDES_CONFIRMATION_FIRST`
4. `NEWEST_SUPERSEDES_SOURCE_FIRST`

Family digest:

`09eb1e13e3158b3b6bccde4c2656aa258941e31835ec6ad53d56fe6b089f8e6b`

In this 2Y sample the two NEWEST tie policies produced identical economic results.

## 3. Validation

Run `35811391351` completed SUCCESS.

- Quality: SUCCESS
- Ruff: SUCCESS
- Mypy: SUCCESS
- Pytest: SUCCESS
- AUDUSD: SUCCESS
- USDJPY: SUCCESS
- BTCUSD: SUCCESS

Cognitive Gate on evidence HEAD:
`35811391236 — SUCCESS`.

## 4. FIRST_SOURCE_ONLY control

### AUDUSD

- 69 trades
- PF 1.02491073
- +0.53735571R
- DD 4.67776095R
- Year 1 -0.57983893R
- Year 2 +1.11719464R

### USDJPY

- 65 trades
- PF 1.03222520
- +0.88660094R
- DD 13.04190777R
- Year 1 +6.70507428R
- Year 2 -5.81847334R

### BTCUSD

- 140 trades
- PF 1.11209035
- +5.80191843R
- DD 11.06504651R
- Year 1 -2.10944578R
- Year 2 +7.91136421R

Combined:

- 274 trades
- approximately PF 1.07165
- +7.22587508R
- mean +0.02637R/trade

## 5. FIRST_CONFIRMATION_WINS

### AUDUSD

- 114 trades
- PF 0.96974741
- -1.29554676R
- DD 9.87485559R

### USDJPY

- 104 trades
- PF 1.05278902
- +2.03822903R
- DD 14.59473135R

### BTCUSD

- 230 trades
- PF 1.02293319
- +1.99164121R
- DD 14.64605839R

Combined:

- 448 trades
- approximately PF 1.01625
- +2.73432348R
- mean +0.00610R/trade

## 6. NEWEST_SUPERSEDES

### AUDUSD

- 114 trades
- PF 0.97640734
- -0.99985228R
- DD 9.68734541R
- Year 1 -4.61987381R
- Year 2 +3.62002153R

### USDJPY

- 104 trades
- PF 1.11385968
- +4.16034174R
- DD 12.32148922R
- Year 1 +4.75173294R
- Year 2 -0.59139120R

### BTCUSD

- 230 trades
- PF 1.05671046
- +4.62598053R
- DD 14.64605839R
- Year 1 -1.91497099R
- Year 2 +6.54095152R

Combined:

- 448 trades
- approximately PF 1.04852
- +7.78646999R
- mean +0.01738R/trade

Combined temporal split:

- Year 1: 225 trades / -1.78311186R / approximately PF 0.97851
- Year 2: 223 trades / +9.56958185R / approximately PF 1.12346

## 7. Finding

Competition policy is a real density lever but is **not the root economic fix**.

The NEWEST policy increases density from 274 to 448 combined trades while keeping total
2Y R approximately comparable to the first-source control. The cost is lower mean R,
lower combined PF and materially worse temporal stability.

Therefore:

- the first-source restriction was too narrow for density;
- simply executing later hypotheses is too permissive for edge;
- the next bottleneck is **pre-entry opportunity quality**, not hypothesis existence.

## 8. Next engineering dimension

The next family isolates projected geometry before entry:

`MINIMUM_PROJECTED_RR_TO_C1_MIDPOINT`

Base competition policy is frozen to:

`NEWEST_SUPERSEDES_CONFIRMATION_FIRST`

The predeclared R2-H thresholds are:

`0.00 / 0.50 / 0.75 / 1.00 / 1.25 / 1.50 / 2.00 R`

R2-H does not change confirmation, stop, target, timing or parent methodology.

## 9. Governance

- PR remains DRAFT / UNMERGED.
- No VPS mutation.
- No DEMO activation.
- No LIVE activation.
- No production authority.
- No real-capital authority.
