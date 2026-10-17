# VT08 CRT PURE — R2-D WAIT RESCUE LAB 001

**Identity:** `VT08_CRT_PURE_R2D_WAIT_RESCUE_ENTRY_FAMILIES_001`  
**Run:** `35798441327`  
**Evidence HEAD:** `4d35e5ac0c18ead4e05bc6de28f5c4638e60eec4`  
**Status:** CHARACTERIZATION COMPLETE / NOT PROMOTED  
**Authority:** RESEARCH ONLY

## 1. Question

R2-C leaves a large population in:

`FIRST_CLOSE_UNMITIGATED_SOURCE_NOT_CONFIRMED`

R2-D tested whether three alternate trigger families, formalized from Level-B audit
language, could explain that WAIT population without changing the parent CRT contract.

The arms were deliberately independent:

- CISD;
- FVG;
- OTE.

They were not OR-combined, ranked, voted, or selected by PnL.

KOD, Order Block and standalone time entry remained disabled because their exact
source-faithful machine contracts are not closed.

## 2. Frozen controls

R2-D retained:

- the same scheduled H4 parent CRT;
- the same R2-C first close-unmitigated Model #1 source event;
- M15 execution;
- next contiguous M15 open after alternate trigger close;
- stop at the original R2-C source-candle extreme;
- R1 C1 50% midpoint as target control;
- R1 C3 close as expiry control;
- STOP_FIRST for same-M15 ambiguity.

Therefore the lab characterizes entry-family behavior only. It does not rewrite R1,
R2-A, R2-B or R2-C.

## 3. Quality

Run `35798441327` completed successfully.

- Ruff: SUCCESS
- Mypy: SUCCESS
- Pytest: SUCCESS
- AUDUSD replay: SUCCESS
- USDJPY replay: SUCCESS
- BTCUSD replay: SUCCESS

Artifacts were bound to the evidence HEAD and hashed.

## 4. AUDUSD

R2-C WAIT parents: **128**

Parents rescued by at least one R2-D family: **43**

### CISD

- trades: 0
- total: 0R

### FVG

- trades: 12
- PF: 0.12807774
- total: -7.17198801R
- mean: -0.59766567R
- DD: 7.96044955R
- Year 1: -6.19215687R
- Year 2: -0.97983114R

### OTE

- trades: 43
- PF: 0.16290513
- total: -30.97251010R
- mean: -0.72029093R
- DD: 30.97251010R
- Year 1: -17.43181818R
- Year 2: -13.54069192R

## 5. USDJPY

R2-C WAIT parents: **121**

Parents rescued by at least one R2-D family: **40**

### CISD

- trades: 0
- total: 0R

### FVG

- trades: 14
- PF: 0.34604184
- total: -6.34473769R
- mean: -0.45319555R
- DD: 6.60389497R
- Year 1: -1.64268321R
- Year 2: -4.70205448R

### OTE

- trades: 37
- PF: 0.15265212
- total: -26.41322464R
- mean: -0.71387094R
- DD: 26.84049737R
- Year 1: -14.86611254R
- Year 2: -11.54711210R

## 6. BTCUSD

R2-C WAIT parents: **181**

Parents rescued by at least one R2-D family: **89**

### CISD

- trades: 0
- total: 0R

### FVG

- trades: 21
- PF: 0.05490279
- total: -11.49357449R
- mean: -0.54731307R
- DD: 11.72709158R
- Year 1: -3.45821897R
- Year 2: -8.03535552R

### OTE

- trades: 84
- PF: 0.17416493
- total: -57.34096914R
- mean: -0.68263058R
- DD: 58.21158278R
- Year 1: -25.54892914R
- Year 2: -31.79204000R

## 7. Adjudication

The naive WAIT-rescue hypothesis is **falsified as implemented**.

That statement is intentionally narrower than:

- "CISD does not work";
- "FVG does not work";
- "OTE does not work";
- "Romeo OTE is invalid".

Those broader conclusions are not supported.

The R2-D CISD/FVG/OTE detectors are explicitly
`ENGINEERING_FORMALIZATION_OF_LEVEL_B_HYPOTHESIS`.

RomeoTPT primary material does authorize Model #1 and OTE as important families, but
the exact OTE machine contract remains source-open. Therefore these economic results
cannot be used to reject canonical OTE or to tune a more profitable OTE threshold.

## 8. Causal interpretation

R2-D shows that simply adding more recognizable technical triggers after an
unconfirmed first R2-C source is not a valid solution to density.

The next causal question is whether the R2-C engineering restriction:

`single_source_event_per_parent = true`

is itself suppressing independent later Model #1 source events.

This is not permission to add fallback entries. A later event must be measured as a
separate causal source event with separate reference evidence.

That question is assigned to:

`VT08_CRT_PURE_R2E_SOURCE_MULTIPLICITY_CENSUS_001`

R2-E is a census only:

- no trades;
- no PnL;
- no methodology mutation;
- no automatic rearm;
- no promotion.

## 9. Governance

- PR remains DRAFT / UNMERGED.
- No VPS mutation.
- No runtime registration.
- No DEMO activation.
- No LIVE activation.
- No production authority.
- No real-capital authority.
