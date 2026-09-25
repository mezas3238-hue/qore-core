# VT08 CRT PURE — BTCUSD R3 CERTIFICATION CANDIDATE FREEZE 001

**Candidate:** `VT08_CRT_PURE_BTCUSD_R3_REF2_PLUS_001`  
**Status:** FROZEN FOR CERTIFICATION BATTERY  
**Methodology:** unchanged CRT PURE + R2-G competition  
**Market:** BTCUSD only

## 1. Exact candidate

The candidate accepts only the already-validated property:

`reference_count >= 2`

on the selected causal Model #1 source event under:

`NEWEST_SUPERSEDES_CONFIRMATION_FIRST`.

No BEARISH requirement is added. No intersection/union composition is used.

## 2. Evidence chain before freeze

The same REF2_PLUS definition survived unchanged:

- 2017-2018 fresh: PASS
- 2018-2020: PASS
- 2020-2022: PASS
- 2022-2024: PASS
- 2024-2026: PASS

Fresh 2017-2018:

- 13 trades
- PF 3.57400417
- +6.25532001R
- DD 1.03888889R
- both half-years positive

The predeclared BEARISH challenger failed fresh half-2 stability and is not the
certification candidate.

## 3. Frozen certification battery

R3 will evaluate the exact frozen candidate over 2017-2026.

Required evidence:

1. chronological 9Y replay;
2. every annual Sep-to-Sep slice;
3. rolling 2Y windows;
4. deterministic block bootstrap;
5. cost/slippage stress;
6. losing-streak and DD characterization;
7. final certification gate.

Frozen certification thresholds before R3 results:

- >=250 trades over 9Y;
- PF >=1.40;
- total R > 0;
- observed max DD <=8R;
- every annual slice >0R;
- every rolling 2Y slice >0R;
- +0.05R/trade cost stress remains positive with PF >=1.20;
- +0.10R/trade stress remains positive;
- block-bootstrap positive-terminal fraction >=0.90 for block lengths 2/4/8;
- block-bootstrap p95 max DD <=15R for block lengths 2/4/8.

No threshold may move after the R3 results are read.

## 4. Governance

R3 certification is research/certification evidence only.

- no merge;
- no VPS;
- no DEMO;
- no LIVE;
- no production;
- no real capital until explicit Owner authorization.
