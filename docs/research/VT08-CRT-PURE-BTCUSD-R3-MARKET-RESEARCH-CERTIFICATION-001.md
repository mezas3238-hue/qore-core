# VT08 CRT PURE — BTCUSD R3 MARKET RESEARCH CERTIFICATION 001

**Exact candidate:** `VT08_CRT_PURE_BTCUSD_R3_REF2_PLUS_001`  
**Market:** BTCUSD  
**Status:** `RESEARCH_CERTIFIED = TRUE`  
**Combined CRT certification:** FALSE  
**DEMO / LIVE / production / real capital:** FALSE

## Exact candidate

- R2-G competition: `NEWEST_SUPERSEDES_CONFIRMATION_FIRST`
- Model #1 selected source
- `reference_count >= 2`
- no BEARISH overlay
- no union/intersection composition
- structural source stop
- C1 midpoint destination
- C3-close expiry
- STOP_FIRST ambiguity control

## Frozen evidence chain

### Final fresh

Run `35850545418`  
HEAD `ca3a37658ab176b6f9b255e19efe79b57bfa28a0`  
Artifact:
`sha256:fac3bc8862577a213101ba222bd81c8d533915856e9d8d9b9ecb6e7e56042bcd`

2017-2018:
- 13 trades
- PF 3.57400417
- +6.25532001R
- DD 1.03888889R
- both fresh half-years positive

### R3-A chronological / stress

Run `35851040583`  
HEAD `59a958a068861257c2caa1f666c04857011c055a`  
Artifact:
`sha256:0ecc45a425717fef066d47438d6ecbcb143fdfd6866f01c9259afa60c90f0b27`

9Y:
- 279 trades
- PF 1.64627528
- +42.40458101R
- mean +0.15198775R
- DD 6.39114189R
- losing streak 6
- all 9 annual folds positive
- all rolling 2Y windows positive

Cost stress:
- +0.05R/trade: PF 1.40394697 / +28.45458101R
- +0.10R/trade: +14.50458101R

### R3-B deterministic block bootstrap

Run `35850990708`  
HEAD `056d0d4e863de749ef0d5a3397bdd8b06b0b84c4`  
Artifact:
`sha256:c790710328574cdf7f7c8afa96a8edbd30fd2952a71b36f5da5b90f738237874`

5,000 resamples per block length.

Positive terminal:
- block 2: 0.9996
- block 4: 0.9986
- block 8: 0.9982

p95 DD:
- block 2: 11.17040267R
- block 4: 11.89604145R
- block 8: 12.38294493R

All frozen block gates PASS.

### R3-C fixed walk-forward / execution slippage

Run `35852361769`  
HEAD `8719ae1b8fe1676594912ef37cdf713a01716ff3`  
Artifact:
`sha256:a0eccfd2337d4ef3b4f2b2a9eb65080655caa6c151bca8dd04d423167aad2be2`

Walk-forward:
- no parameter re-fit between folds
- all 9 folds positive
- every fold >=10 trades
- every fold DD <=8R

Adverse entry+exit slippage:
- 0.025R per fill (~0.05R nominal round trip):
  PF 1.40394696 / +27.76056680R / DD 6.77184576R
- 0.05R per fill (~0.10R nominal round trip):
  PF 1.19152596 / +13.81388663R / DD 7.21642613R

All frozen R3-C gates PASS.

## Certification adjudication

The repository now binds the exact evidence through:

`src/qore/infrastructure/traders/crt_pure_btcusd_r3_research_certification.py`

and evaluates it through the fail-closed per-market readiness gate.

Result:

`BTCUSD_RESEARCH_CERTIFIED = TRUE`

This means the in-repo market research/economic chain is closed for this exact candidate.

It does **not** grant:
- combined AUDUSD/USDJPY/BTCUSD CRT certification;
- DEMO eligibility;
- LIVE authority;
- production authority;
- real-capital authority.

External Risk/CIBO review and later combined-portfolio validation remain separate gates.
