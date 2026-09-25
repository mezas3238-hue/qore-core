# VT08 Cognitive Expansion — Post-Anchor PS + Entry-Family Authority Report

Status: **SOURCE SHAPE FOUND / ENTRY AUTHORITY NOT YET EXECUTABLE**

## Post-anchor Protected-Swing audit

Run `36058578818` completed SUCCESS.

Universe:
- exactly 245 C2 source-valid anchors;
- no Protected Swing was available before the H4 open in M15, M5 or M3;
- no PnL and no entry family were used.

Result:

| Market | Pre-anchor no-PS | Post-anchor PS in >=1 profile | Rate |
| --- | ---: | ---: | ---: |
| EURJPY | 48 | 24 | 50.0% |
| USDCHF | 53 | 33 | 62.3% |
| NZDUSD | 46 | 25 | 54.3% |
| CADJPY | 54 | 31 | 57.4% |
| USDCAD | 44 | 17 | 38.6% |
| **TOTAL** | **245** | **130** | **53.1%** |

Therefore 130 structures were not dead. They formed a causal Protected Swing
later inside the same H4.

The remaining **115** did not form a post-anchor PS in any profile during the
current H4.

## LTF visibility of the 130 late structures

Cases with post-anchor PS by profile:
- M15_STANDARD: 67
- M5_FRACTAL: 103
- M3_FRACTAL: 120

Profile-presence masks across all 245 cases:
- all M15+M5+M3: 52
- M15+M3 only: 10
- M15+M5 only: 2
- M5+M3 only: 44
- M15 only: 3
- M5 only: 5
- M3 only: 14
- none: 115

The union is 130; profile counts must not be added as distinct opportunities.

## Confirmation latency

First post-anchor PS confirmation is often materially later than the H4 open.

Per-market/profile medians (minutes after H4 open):

| Market | M15 | M5 | M3 |
| --- | ---: | ---: | ---: |
| EURJPY | 135 | 115 | 117 |
| USDCHF | 105 | 95 | 75 |
| NZDUSD | 75 | 90 | 69 |
| CADJPY | 165 | 125 | 75 |
| USDCAD | 180 | 175 | 96 |

Earliest observed confirmation:
- M15: 30 minutes;
- M5: 10 minutes;
- M3: 6 minutes.

Latest confirmations approach the end of the four-hour lifecycle.

## Critical causal conclusion

These 130 are **not missing B01 positional trades**.

R3.9 binds positional entry reference to the new HTF open. The source kernel
requires entry evidence to be causal:

`formed_at <= confirmed_at <= decision_at`.

A PS/CISD confirmed after the H4 open cannot authorize a retrospective fill at
that open.

## Entry-family authority audit

Revision 3.2 names six source-supported entry-family identities:

- reversal-entry
- continuation-entry
- confident-entry
- positional-entry
- open-entry
- POI-continuation-entry

Repository inspection found no machine-complete historical executable contract
for the five non-positional families in the current canonical line.

Current authority:

| Entry family | Source identity | Machine-complete current line |
| --- | --- | --- |
| positional | yes | **yes — B01 narrow path** |
| reversal | yes | no |
| continuation | yes | no |
| confident | yes | no |
| open | yes | no |
| POI-continuation | yes | no |

The R3.2 freeze explicitly says:
- no universal entry-family priority exists;
- no blanket Cartesian entry/stop/target combination is authorized;
- each executable combination requires a provenance-bound source bundle.

Therefore the 130 post-anchor structures remain **STRUCTURAL_OPPORTUNITY_ONLY**.

## Density accounting after this audit

Known distinct structural opportunity map over the ~3Y five-market corpus:

- 1,157 distinct pre-anchor mechanical C2 identities in >=1 LTF profile;
- 195 distinct C3 closure shapes;
- 130 additional delayed same-H4 Protected-Swing structures from the 245
  pre-anchor no-PS cases.

The 130 are disjoint from the 1,157 pre-anchor C2 mechanical union by
construction. They originate inside the 245 no-PS residual bucket.

This yields **1,482 located structural opportunity identities** if the three
categories are counted diagnostically:

`1,157 + 195 + 130 = 1,482`

But only the first category currently has a machine-complete entry contract.
The figure 1,482 must not be described as 1,482 executable trades.

## Next source work

1. recover the primary-source/framebook provenance for the five non-positional
   entry families;
2. determine exact causal trigger, executable price/zone, compatible stop family
   and compatible target family;
3. build one source bundle at a time;
4. pre-register before economics;
5. only then test whether the 130 late structures can become valid trades.

No fill is inferred from performance.
