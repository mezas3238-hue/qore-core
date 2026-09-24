# VT08 Cognitive Expansion 5M — Density Root-Cause Audit V1

Status: **COMPLETED / OWNER DENSITY REJECTION CONFIRMED**

Source:
- immutable 1095-day evidence run: `35934924907`
- source HEAD: `b2d33e1b4829d8b4afc76983decca8a99131403c`
- PF truth audit run: `35938734279`
- density funnel audit run: `35939376821`

No market/anchor/side selection, no trade filtering, no capital weighting.

## 1. Total trades and 3Y production

| Market | Trades | Raw VT08 PF | Raw VT08 Total R | Core Stack PF | Core Stack Total R |
| --- | ---: | ---: | ---: | ---: | ---: |
| EURJPY | 82 | 1.325069 | +12.520381R | 1.886829 | +18.118688R |
| USDCHF | 77 | 0.563803 | -22.730976R | 0.671900 | -9.902007R |
| NZDUSD | 114 | 1.227797 | +12.836435R | 1.205148 | +6.763744R |
| CADJPY | 86 | 1.083672 | +3.760583R | 1.436682 | +9.440997R |
| USDCAD | 98 | 0.625639 | -23.349301R | 0.611490 | -14.444236R |

Totals:
- 457 terminal trades over the common ~1095-day corpus.
- Raw VT08 equal-risk total: **-16.962879R**.
- Core Stack managed-R total: **+9.977186R**.
- Capital weighting: not applied.

The Core Stack result must not be presented as the raw methodology PF or raw
methodology return.

## 2. Density funnel across all five markets

Observed exact 01/05/09 New York anchor bars:
- 11,655

Mechanical candidates after the full frozen admission funnel:
- 488

Terminal trades after daily cardinality / exit completeness:
- 457

Therefore:
- only 4.19% of observed anchor opportunities became mechanical candidates;
- only 3.92% became terminal trades;
- candidate-to-terminal loss is only 31 trades.

The density problem is overwhelmingly upstream of daily uniqueness.

## 3. First failure counts across all five markets

| First failure | Count | Share of observed anchors |
| --- | ---: | ---: |
| C2 close not inside reference H4 | 3,987 | 34.21% |
| Daily bias unresolved | 2,071 | 17.77% |
| C2 both sides swept | 1,347 | 11.56% |
| C2 side disagrees with daily bias | 1,317 | 11.30% |
| C2 no reference sweep | 1,085 | 9.31% |
| No Protected Swing | 769 | 6.60% |
| Incomplete source H4 | 406 | 3.48% |
| Multiple Protected Swings | 145 | 1.24% |
| Incomplete source day | 40 | 0.34% |

C2-related first failures total **7,736**, which is approximately **66.37% of
all observed anchor opportunities**.

Protected-Swing related first failures total 914 (~7.84%).

Risk geometry was not a material bottleneck: every candidate that reached the
risk-geometry stage was valid.

## 4. Candidate-to-terminal losses

Across all five markets:
- mechanical candidates: 488
- lost to multi-candidate daily cardinality: 30
- incomplete exit window: 1
- terminal trades: 457

By market:
- EURJPY: 88 candidates -> 82 trades; 6 lost to daily cardinality
- USDCHF: 88 -> 77; 10 daily-cardinality losses + 1 incomplete exit
- NZDUSD: 126 -> 114; 12 daily-cardinality losses
- CADJPY: 88 -> 86; 2 daily-cardinality losses
- USDCAD: 98 -> 98; zero downstream loss

## 5. Root-cause conclusion

The current VT08 density collapse is **not** primarily produced by:
- daily uniqueness;
- exit-window incompleteness;
- risk geometry.

It is primarily produced before candidate creation, especially by the frozen
C2 admission contract.

The next research stage must inspect source-authorized ways to recover density
without inventing a new methodology:
- exact C2 semantics and whether the current replay is narrower than source;
- source-authorized C3;
- independently authorized LTF profiles;
- Protected Swing ambiguity/selection rules;
- bias-resolution semantics.

No one of these may be relaxed solely because it increases trade count.
Every density-recovery hypothesis requires source justification and then
fresh economic validation.
