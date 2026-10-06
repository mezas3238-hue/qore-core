# VT31 NAS100 — DOL2 Reloss Full-Cognition Frontier Plan 001

**Owner:** Sergio Meza  
**Status:** PREDECLARED / CONSUMED EVIDENCE ONLY

## Fixed architecture

Population and entry remain identical to the sovereign specialist.

Base extension mechanism:

- soft DOL1 window = 3 fully closed M1 bars;
- DOL1 acceptance = subsequent closed M1 beyond DOL1;
- DOL2 = DOL1 +/− 0.25 frozen reference width;
- extension active only from the next M1.

## Variants

1. `DOL1_HARD_EXIT`
2. `W3_DOL2_ALL`
3. `W3_DOL2_RELOSS_EXIT`
4. `W3_DOL2_RELOSS_FULL_COGNITION`

## Reloss event

After causal DOL1 acceptance and before DOL2, a fully closed M1 that closes
back inside DOL1 is a reloss observation.

### RELLOSS_EXIT control

Exit at that causal close.

### FULL_COGNITION

At the reloss close:

1. rebuild current causal Situation Model;
2. rerun position reasoning from frozen entry reasoning + current state;
3. use complete memories/domains;
4. classify post-1R persistence from closed M1 only.

HOLD extension only when:

- contextual management is research-ready;
- current reasoning action remains EXECUTE;
- persistence is PERSISTENT_1R_FLOOR or RECOVERED_1R_FLOOR;
- no outcome oracle is present.

Otherwise EXIT at reloss close.

## Frozen gates

Against DOL1 hard baseline:

- PF non-degrade 4/4 preferred, minimum 3/4 for research;
- mean-R non-degrade 4/4 preferred;
- DD non-degrade >=3/4;
- winner count >=80% every fold;
- winner-R >=90% every fold;
- consumed recent 2Y must not degrade;
- half-year mean-R nondegrade for promotion-grade witness.

Against W3_DOL2_ALL the cognition variant should reduce consumed DD/MC p95 DD
without destroying its PF/mean improvement.

R is allowed. Sizing for certification is forbidden.

No fresh holdout, automatic promotion, freeze, LIVE or real capital.
