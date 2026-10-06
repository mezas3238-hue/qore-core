# VT31 NAS100 — Pure Structural Protection V1 Superseded 001

**Status:** SUPERSEDED / NOT CERTIFICATION-AUTHORITATIVE  
**Owner:** Sergio Meza  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Reason

The first `vt31_nas100_pure_structural_protection_v1.py` experiment correctly
removed runtime R thresholds from its exit logic, but it used the dense OCO
selection path as its admission population.

That produced fold populations such as:

- R5: 328 trades;
- R6: 299 trades;
- R8: 257 trades.

Those are not the current sovereign cognition-admitted VT31 populations:

- R5: 54 trades;
- R6: 37 trades;
- R8: 33 trades;
- recent consumed 2Y: 48 trades.

Therefore V1 can answer a research question about the dense OCO population, but
it cannot determine whether `LBB_PATH_SHALLOW_PS1` survives on the current
certifiable VT31 candidate.

## Replacement authority

The replacement is:

`scripts/vt31_nas100_sovereign_lbb_structural_survivor_v2.py`

and workflow:

`.github/workflows/vt31-nas100-sovereign-lbb-structural-survivor-v2.yml`

V2 uses `specialist.replay()` as the sole admission authority and asserts
identical `signal_at` populations between baseline and candidate.

## Governance

No V1 result may be used to:

- promote runtime policy;
- freeze a candidate;
- open fresh holdout;
- claim certification;
- authorize LIVE or real capital.

This supersession changes no trade admission and makes no merge.
