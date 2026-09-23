# VT08 CRT PURE — R2-P BTCUSD HISTORICAL VALIDATION 001

**Identity:** `VT08_CRT_PURE_R2P_BTCUSD_HISTORICAL_VALIDATION_001`  
**Workflow run:** `35844228939`  
**Evidence HEAD:** `77652f8d16c45eca3e452bc706cbda4e0578c2d6`  
**Validation:** `2020-09-21 -> 2022-09-21`  
**Status:** COMPLETE / TWO SINGLE-FACTOR CANDIDATES SURVIVE

## 1. Frozen family

Definitions were reused unchanged from R2-J/R2-M:

- CONTROL
- BTC_BEARISH
- BTC_BODY_GE_050
- BTC_REF2_PLUS

The R2-J research gate was reused unchanged:

- >=24 trades
- PF >=1.05
- total R >0
- DD <=12R
- both annual halves >0R

No combination or ranking was allowed.

## 2. CONTROL

- 168 trades
- PF 1.09920637
- +5.42597214R
- DD 7.79288415R
- Year 1 +2.58521811R
- Year 2 +2.84075403R
- **SURVIVED**

The control remains weak but positive in this earlier period.

## 3. BTC_BEARISH

- 86 trades
- PF 1.67095371
- +15.31766920R
- mean +0.17811243R
- DD 5.53814155R
- losing streak 5

Year 1:
- 40 trades
- PF 1.24881562
- +3.06691035R

Year 2:
- 46 trades
- PF 2.16633240
- +12.25075885R

**SURVIVED.**

Combined with R2-M, this factor is now positive across six consecutive years of
non-overlapping annual evidence.

## 4. BTC_REF2_PLUS

- 69 trades
- PF 1.91351525
- +12.89655914R
- mean +0.18690665R
- DD 3.46121681R
- losing streak 3

Year 1:
- 37 trades
- PF 2.04092429
- +7.65838907R

Year 2:
- 32 trades
- PF 1.77485299
- +5.23817007R

**SURVIVED.**

This is also positive in both earlier annual halves and remains consistent with the
2022-2026 robustness evidence.

## 5. BTC_BODY_GE_050

- 78 trades
- PF 1.14001532
- +2.96081731R
- DD 4.85243812R

Year 1:
- +3.53366909R

Year 2:
- -0.57285178R / PF 0.94028709

**FAILED** because Year 2 is negative.

The factor is therefore not eligible to advance as a stable standalone rule despite its
strong 2022-2026 results.

## 6. Adjudication

The BTC research family narrows to:

- `BTC_BEARISH`
- `BTC_REF2_PLUS`

The unfiltered control remains a reference baseline, not the preferred engineering
candidate.

`BTC_BODY_GE_050` is removed from advancement.

No combination of BEARISH + REF2+ is authorized yet. They remain independent candidate
families until their overlap and incremental contribution are characterized.

## 7. Next chain

1. Complete R2-O deterministic block robustness.
2. Preserve BTC_BEARISH and BTC_REF2_PLUS separately.
3. Validate both on an earlier 2018-2020 window.
4. Preserve 2017-2018 BTC history as possible final fresh evidence.
5. Only after separate evidence is complete may an overlap/composition lab be opened.

## 8. Governance

- candidate certification remains FALSE;
- PR DRAFT / UNMERGED;
- no VPS / DEMO / LIVE / production / real capital.
