# SHARED B — Global World Perception Checkpoint 001

**Lane:** Architect B — Global World Perception, Sensor Fabric & Relational Reality  
**Primary PR:** #635  
**B branch:** `agent/shared-b-global-world-perception-001`  
**Common ancestor:** `7d1b54cfa5453c0eb5c0662438ed15e7d656da61`  
**Status:** ACTIVE / NOT COMPLETE / NOT CERTIFIED  
**Fresh WP-05 holdout:** CLOSED  
**Final Shared certification holdout:** CLOSED

## Ownership boundary

Architect B owns provider/sensor identity, global observation, market-hours/time
comparability, data health, relational observability, agriculture/commodities,
Active Perception sensor-side acquisition, Core/Broker observation, blindspot
sensor-side detection, deterministic replay and provenance.

Architect B does not own Trader methodology, STI scientific/economic policy,
CIBO, Risk, Execution, order authority, capital authority or protected holdout
opening.

## Revalidated starting state

- PR #635 is OPEN / DRAFT / UNMERGED / MERGEABLE.
- PR #635 HEAD at lane split:
  `7d1b54cfa5453c0eb5c0662438ed15e7d656da61`.
- B branch existed at the exact common ancestor with zero additional commits.
- Post-V14 provider catalogue contract is source-only.
- Frozen prior provider catalogue evidence recorded 177 enabled symbols with
  catalogue SHA256
  `4c10aede99704b937caa772e1ae07257c8e12c3d0644c06ca751b6885b9a363f`.
- Post-V14 cross-asset candidates remain:
  `US2000/10012`, `XAUUSD/41`, `XTIUSD/10019`.
- V15 source acquisition admits only US2000 and XAUUSD; XTIUSD remains excluded
  from full acquisition because its prior source availability was partial.
- R8 source manifest identity remains frozen at 2,948 windows with SHA256
  `2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191`.
- No Target-V2 outcomes, R6/R5 or fresh holdout may be opened by B.

## First blocker found after split

The canonical provider-catalog and post-V14 source-availability workflows listen
to pushes on `agent/qore-core-stack-v2-shared-001`, not the B branch. They are
valid historical/canonical workflows but are not an isolated execution lane for
parallel B development.

Per the split contract, B must not edit A workflows or share A concurrency
groups. Therefore B introduces B-namespaced workflows while leaving canonical
history intact.

## Immediate B-01 execution

Create and execute:

`.github/workflows/qore-shared-b-wp05-provider-catalog.yml`

Purpose:

1. validate the existing provider-catalog contract;
2. reacquire the exact enabled cTrader DEMO catalogue read-only;
3. persist raw source evidence before downstream evaluation;
4. upload raw evidence;
5. create a provenance manifest containing Git SHA, run ID, artifact ID,
   account fingerprint, catalogue digest and raw-evidence digest;
6. preserve all anti-outcome / anti-R6-R5 / holdout-closed / authority-firewall
   invariants.

If the provider catalogue digest changes, B must treat that as a new provider
catalogue identity/version. No silent update is allowed.

## Completion law

This checkpoint is not a completion claim.

`B REQUIRED OPEN WORK = ZERO` is required before B can freeze its lane.
