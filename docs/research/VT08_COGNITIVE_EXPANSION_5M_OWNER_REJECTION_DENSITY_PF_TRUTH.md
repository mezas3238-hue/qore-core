# VT08 Cognitive Expansion 5M — Owner Rejection: Density + PF Truth

Status: **OWNER REJECTED CURRENT CANDIDATE / DENSITY FAILURE**

The current five-market candidate line is rejected by the Owner because trade
density is insufficient. Any earlier research gate that treated ~50 trades per
market / 2Y as sufficient is no longer an acceptable density standard for this
program.

## Truth-audit source

All five markets were audited on the exact same immutable 1095-day evidence:

- source run: 35934924907
- source HEAD: b2d33e1b4829d8b4afc76983decca8a99131403c
- no market selection
- no anchor selection
- no side selection
- no trade filtering
- no capital weighting

Audit run: 35938734279.

## Profit Factor semantics

Three PF concepts must remain separate:

1. **VT08 equal-risk PF** — raw methodology economics, each terminal trade
   represented by its realized R without capital weighting.
2. **Core Stack managed-R PF** — same admitted trades after banking/protection
   mechanics. Still no capital weighting.
3. **Capital-weighted PF** — variable exposure/risk sizing. NOT used in this
   audit and must never be presented as the raw methodology PF.

## Comparable 1095-day truth

| Market | Trades | Annualized | 2Y equivalent | VT08 equal-risk PF | Core Stack PF |
| --- | ---: | ---: | ---: | ---: | ---: |
| EURJPY | 82 | 27.33 | 54.67 | 1.325069 | 1.886829 |
| USDCHF | 77 | 25.67 | 51.33 | 0.563803 | 0.671900 |
| NZDUSD | 114 | 38.00 | 76.00 | 1.227797 | 1.205148 |
| CADJPY | 86 | 28.67 | 57.33 | 1.083672 | 1.436682 |
| USDCAD | 98 | 32.67 | 65.33 | 0.625639 | 0.611490 |

Total portfolio density over the same ~3Y corpus: 457 terminal trades, or about
152.33 trades/year across all five markets. This does not fix the per-market
density problem.

## Density root-cause clue

The bottleneck is upstream of daily uniqueness:

| Market | Mechanical candidates | Terminal trades | Multi-candidate days |
| --- | ---: | ---: | ---: |
| EURJPY | 88 | 82 | 3 |
| USDCHF | 88 | 77 | 5 |
| NZDUSD | 126 | 114 | 6 |
| CADJPY | 88 | 86 | 1 |
| USDCAD | 98 | 98 | 0 |

Therefore the main density loss is NOT caused by one-trade-per-day selection.
The frozen source admission itself produces only ~88-126 candidates over three
years per market.

## Decision

- Current candidate: REJECTED_FOR_DENSITY.
- EURJPY is NOT promoted despite the higher managed PF.
- No five-year aggregate result can rescue insufficient density.
- No capital weighting may be used to disguise a weak raw PF.
- No post-hoc market/anchor/side deletion is authorized.

## Next research objective

Open a density root-cause investigation that traces the complete funnel:

anchor opportunity
-> complete source H4
-> daily bias resolved
-> C2 reversal geometry
-> Protected Swing count
-> CISD/confirmation
-> valid risk geometry
-> daily uniqueness
-> terminal trade

The goal is to identify exactly which frozen VT08 condition is suppressing
opportunity count and whether source-authorized alternatives already present in
the VT08 rulebook (for example C3 or independently authorized LTF profiles) can
recover density without changing methodology or inventing rules.

A new numeric density acceptance gate must be frozen separately; the old
50-trades/2Y threshold is retired for this program.
