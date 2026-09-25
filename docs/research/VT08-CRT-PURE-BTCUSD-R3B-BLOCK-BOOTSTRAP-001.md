# VT08 CRT PURE — BTCUSD R3-B BLOCK BOOTSTRAP 001

**Candidate:** `VT08_CRT_PURE_BTCUSD_R3_REF2_PLUS_001`  
**Workflow run:** `35850990708`  
**Status:** PASS

Source chronology:
- 279 trades
- +42.40458101R
- observed DD 6.39114189R

Each frozen policy used 5,000 deterministic circular-block resamples.

## Block 2

- positive terminal: 0.9996
- terminal p05: +20.29775127R
- p95 DD: 11.17040267R
- p99 DD: 14.38721627R

## Block 4

- positive terminal: 0.9986
- terminal p05: +19.58711191R
- p95 DD: 11.89604145R
- p99 DD: 15.64539827R

## Block 8

- positive terminal: 0.9982
- terminal p05: +18.48921525R
- p95 DD: 12.38294493R
- p99 DD: 15.90887384R

## Frozen gate

Required:
- positive-terminal fraction >=0.90
- p95 DD <=15R
for block lengths 2 / 4 / 8.

All passed.

`block_gate_passed = TRUE`

This is descriptive deterministic resampling evidence, not a calibrated probability
claim and not deployment authority.
