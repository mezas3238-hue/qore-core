# VT08 CRT PURE — R2-I CAUSAL CONTEXT FORENSICS 001

**Identity:** `VT08_CRT_PURE_R2I_CAUSAL_CONTEXT_FORENSICS_001`  
**Workflow run:** `35812383916`  
**Evidence HEAD:** `36483933a07e632e605594f4227a02c2d913a7df`  
**Status:** COMPLETE / ROOT-CAUSE CLUES FOUND  
**Filter promoted:** FALSE

## 1. Objective

R2-I adds no entry filter.

It freezes R2-G's:

`NEWEST_SUPERSEDES_CONFIRMATION_FIRST`

and stratifies the resulting causal entry opportunities by information already known at
or before entry:

- source generation;
- old-reference multiplicity;
- confirmation delay;
- projected RR;
- source body/range;
- source range relative to parent C1;
- penetration depth;
- direction;
- timing triplet;
- generation x delay;
- triplet x direction.

Every slice is reported for full 2Y, Year 1 and Year 2.

## 2. Validation

Run `35812383916`: SUCCESS.

- Ruff: SUCCESS
- Mypy: SUCCESS
- Pytest: SUCCESS
- AUDUSD: SUCCESS
- USDJPY: SUCCESS
- BTCUSD: SUCCESS

Cognitive Gate on evidence HEAD: SUCCESS.

Artifact digests:

- AUDUSD: `sha256:da8c50de9b1bed6ab4535b61180107aeb0a3b210d4e8736de2bfb85a813c3932`
- USDJPY: `sha256:c52fa8cb9b3b6d4305c20ba076dcd6218e4aab7ba1df0ffebcf082fb5994a3e3`
- BTCUSD: `sha256:92d7e643ae8199086ca25c431797f850bc65f05e415011a5ae4982830253bf66`

## 3. AUDUSD — root-cause findings

Overall R2-G NEWEST:

- 114 trades
- PF 0.97640734
- -0.99985228R
- DD 9.68734541R
- Year 1 -4.61987381R
- Year 2 +3.62002153R

### Stable positive development clues

**Generation 1**
- 57 trades
- PF 1.10357523
- +1.88493118R
- Year 1 +0.97320077R
- Year 2 +0.91173041R

**Generation 1 + confirmation delay D3+**
- 23 trades
- PF 1.98420976
- +3.87616897R
- Year 1 +1.25708510R
- Year 2 +2.61908387R

**Reference multiplicity REF2+**
- 45 trades
- PF 1.40208886
- +4.53901032R
- Year 1 +1.04869275R
- Year 2 +3.49031757R

**Source range >= 0.30 x C1 range**
- 67 trades
- PF 1.22643228
- +5.18414080R
- Year 1 +0.57131882R
- Year 2 +4.61282198R

**Penetration 0.50–0.75 of source range**
- 23 trades
- PF 1.31596318
- +1.44273553R
- Year 1 +1.41568337R
- Year 2 +0.02705216R

**T1 bullish**
- 41 trades
- PF 1.60251223
- +8.09031125R
- Year 1 +0.19370338R
- Year 2 +7.89660787R

### Stable negative development clues

**Bearish**
- 49 trades
- PF 0.47796140
- -9.65293067R
- Year 1 -4.50306943R
- Year 2 -5.14986124R

**Generation 2**
- 28 trades
- PF 0.62573706
- -4.28793391R
- negative in both years

**Projected RR >= 2.00**
- 34 trades
- PF 0.75114589
- -4.52545811R
- negative in both years

**Source range 0.10–0.20 x C1**
- 21 trades
- PF 0.76383680
- -2.13957783R
- negative in both years

**T1 bearish**
- 35 trades
- PF 0.50290880
- -6.39308919R
- negative in both years

Interpretation:

AUDUSD's current failure is not random. The bearish side is persistently destructive while
T1 bullish, strong reference multiplicity and larger source geometry are materially better.

## 4. USDJPY — root-cause findings

Overall R2-G NEWEST:

- 104 trades
- PF 1.11385968
- +4.16034174R
- DD 12.32148922R
- Year 1 +4.75173294R
- Year 2 -0.59139120R

### Stable positive development clues

**Confirmation delay D2**
- 21 trades
- PF 1.76695178
- +5.17655241R
- Year 1 +2.83688062R
- Year 2 +2.33967179R

**Source body fraction 0.50–0.75**
- 35 trades
- PF 2.28263528
- +7.52340822R
- Year 1 +0.70690695R
- Year 2 +6.81650127R

**Timing Triplet 1**
- 72 trades
- PF 1.29236281
- +7.14407860R
- Year 1 +5.12524273R
- Year 2 +2.01883587R

T1 is positive for both directions:

- T1 bearish: 40 trades / PF 1.30573963 / +4.44471727R
- T1 bullish: 32 trades / PF 1.27271588 / +2.69936133R

### Stable negative development clues

**Timing Triplet 2**
- 32 trades
- PF 0.75348230
- -2.98373686R
- negative in both years

**T2 bullish**
- 20 trades
- PF 0.87010563
- -0.89339154R
- negative in both years

**Body fraction < 0.25**
- 30 trades
- PF 0.54382964
- -7.35614726R
- negative in both years

Interpretation:

The apparent USDJPY Year-1/Year-2 inversion is largely hiding a stable timing split.
T1 survives both years; T2 does not. D2 confirmation and medium-thick source bodies are
additional positive clues.

## 5. BTCUSD — root-cause findings

Overall R2-G NEWEST:

- 230 trades
- PF 1.05671046
- +4.62598053R
- DD 14.64605839R
- Year 1 -1.91497099R
- Year 2 +6.54095152R

### Stable positive development clues

**Confirmation delay D2**
- 53 trades
- PF 1.18454441
- +3.43223170R
- Year 1 +0.91904886R
- Year 2 +2.51318284R

**Bearish**
- 117 trades
- PF 1.18670796
- +7.59865213R
- Year 1 +1.40949953R
- Year 2 +6.18915260R

**Generation 3+**
- 57 trades
- PF 1.20767792
- +3.20360436R
- Year 1 +2.61161573R
- Year 2 +0.59198863R

**Reference multiplicity REF2+**
- 97 trades
- PF 1.43631026
- +10.47581892R
- Year 1 +4.68226803R
- Year 2 +5.79355089R

**Body fraction 0.50–0.75**
- 74 trades
- PF 1.47807571
- +10.74791447R
- Year 1 +9.25583767R
- Year 2 +1.49207680R

**Body fraction >= 0.75**
- 41 trades
- PF 1.34360392
- +3.26747879R
- positive in both years

**Penetration < 0.25**
- 78 trades
- PF 1.17653344
- +5.50611405R
- positive in both years

**Penetration 0.50–0.75**
- 53 trades
- PF 1.41428298
- +6.09792649R
- positive in both years

**Projected RR 1.50–2.00**
- 25 trades
- PF 1.96069538
- +7.25880574R
- Year 1 +4.62827378R
- Year 2 +2.63053196R

**T1 bearish**
- 53 trades
- PF 1.59265924
- +9.80769075R
- Year 1 +1.75557345R
- Year 2 +8.05211730R

### Stable negative development clues

**Confirmation delay D1**
- 95 trades
- PF 0.96814216
- -1.28756117R
- negative in both years

**Generation 2**
- 73 trades
- PF 0.91399953
- -2.45884348R
- negative in both years

**Penetration 0.25–0.50**
- 78 trades
- PF 0.78532025
- -6.60640754R
- negative in both years

**Body fraction 0.25–0.50**
- 64 trades
- PF 0.80338788
- -5.52127831R
- negative in both years

**Source range 0.10–0.20 x C1**
- 45 trades
- PF 0.57727104
- -11.26064936R
- negative in both years

**T2 bearish**
- 64 trades
- PF 0.90852632
- -2.20903862R
- negative in both years

Interpretation:

BTCUSD has several strong, repeatable pre-entry quality signals. REF2+, source body >= 0.50,
D2 confirmation and T1 bearish are especially important development candidates.

## 6. Cross-market conclusions

The forensics reject a universal one-parameter repair.

The strongest reusable cross-market clues are:

- **REF2+**: stable positive in AUDUSD and BTCUSD;
- **D2 confirmation**: stable positive in USDJPY and BTCUSD;
- **medium/large source body**: stable positive in USDJPY and BTCUSD;
- **Triplet/context**: decisive in USDJPY and direction-sensitive in AUDUSD/BTCUSD.

Therefore R2-J should be a small, predeclared market-specific candidate family rather than
one common threshold.

## 7. R2-J development family to freeze

The first R2-J family should use simple single-factor or low-complexity gates so that the
historical holdout can identify whether the clues generalize.

Proposed development arms:

### AUDUSD
- A0: R2-G NEWEST control
- A1: Generation 1 only
- A2: REF2+ only
- A3: source range >= 0.30 x C1
- A4: T1 bullish only

### USDJPY
- U0: R2-G NEWEST control
- U1: Triplet 1 only
- U2: D2 confirmation only
- U3: source body 0.50–0.75 only

### BTCUSD
- B0: R2-G NEWEST control
- B1: REF2+ only
- B2: source body >= 0.50 only
- B3: bearish only
- B4: D2 confirmation only
- B5: T1 bearish only

No combination is to be promoted from the consumed 2Y window.

The family should next be replayed on a separate historical holdout with its membership
frozen before results.

## 8. Governance

- Development clues only.
- No R2-I slice is certified.
- No DEMO/LIVE/production authority.
- No real-capital authority.
- PR remains DRAFT / UNMERGED.
