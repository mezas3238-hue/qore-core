# VT08 Cognitive Expansion 5M — Three-Year Opportunity Census Master Report

Status: **CENSUS COMPLETE / CURRENT LOW-DENSITY LINE REMAINS REJECTED**

Evidence scope:
- five markets: EURJPY, USDCHF, NZDUSD, CADJPY, USDCAD;
- common ~1095-day corpus;
- 01/05/09 New York anchors;
- immutable base evidence run 35934924907;
- exact-window M3 evidence run 35941643396;
- latest source-adjudicated Protected Swing selector;
- no PnL used to define opportunity identity.

Census run:
- `36057198230` — SUCCESS.

Residual reconciliation run:
- `36057627121` — SUCCESS.

No-PS forensics run:
- `36058018066` — SUCCESS.

## 1. Profile counts are not distinct-trade counts

Terminal profile variants:

- M15_STANDARD: 579
- M5_FRACTAL: 759
- M3_FRACTAL: 812

Naively summing these yields 2,150 profile variants. That is incorrect as a
distinct-trade count because many are the same market + anchor + side event.

Identity used by this census:

`market + signal_at + side`

Distinct terminal C2 opportunity identities across the three profiles:

**1,057**

Therefore 1,093 of the 2,150 profile observations are duplicate profile views
of an opportunity already present in another source-authorized LTF profile.

## 2. Exact distinct terminal C2 opportunities by market

| Market | M15 | M5 | M3 | Distinct union |
| --- | ---: | ---: | ---: | ---: |
| EURJPY | 116 | 147 | 161 | 207 |
| USDCHF | 98 | 150 | 149 | 197 |
| NZDUSD | 139 | 172 | 182 | 237 |
| CADJPY | 107 | 152 | 161 | 216 |
| USDCAD | 119 | 138 | 159 | 200 |
| **TOTAL** | **579** | **759** | **812** | **1,057** |

These 1,057 identities are diagnostic union density only. The source requires
M15/M5/M3 profiles to remain independent; this report does not authorize
executing their union.

## 3. Terminal overlap map

Across all five markets:

- M15 only: 98
- M5 only: 101
- M3 only: 110
- M15 + M5 only: 46
- M15 + M3 only: 90
- M5 + M3 only: 267
- M15 + M5 + M3: 345

Totals:
- exactly one profile: **309**
- two or more profiles: **748**
- distinct union: **1,057**

Thus ~70.8% of distinct terminal opportunities are visible in more than one
LTF profile and ~29.2% are genuinely profile-exclusive.

## 4. Mechanical opportunity census before daily-cardinality containment

Distinct C2 mechanical identities:

**1,157**

Profile variants:
- M15: 633
- M5: 857
- M3: 953
- total profile variants: 2,443

Mechanical overlap map:
- M15 only: 73
- M5 only: 91
- M3 only: 123
- M15 + M5 only: 40
- M15 + M3 only: 104
- M5 + M3 only: 310
- all three: 416

The drop from 1,157 distinct mechanical identities to 1,057 distinct terminal
identities is downstream containment/profile-specific daily selection, not the
main density bottleneck.

## 5. C3 source-authorized shape census

C3 shape identities are fully disjoint from the executable C2 mechanical union:

| Market | C3 shape identities | Overlap with C2 mechanical |
| --- | ---: | ---: |
| EURJPY | 56 | 0 |
| USDCHF | 40 | 0 |
| NZDUSD | 36 | 0 |
| CADJPY | 41 | 0 |
| USDCAD | 22 | 0 |
| **TOTAL** | **195** | **0** |

Therefore the current corpus contains:

- 1,157 distinct executable-mechanical C2 identities;
- plus 195 additional C3 structural shapes;
- = 1,352 distinct C2/C3 structural opportunity identities at the mechanical
  census level.

The 195 C3 shapes are **not trades**. Their POI/CISD/PS/entry/stop/target bundle
is not machine-complete.

## 6. Complete reconciliation of all 11,655 observed anchors

Every anchor is now classified exactly once:

- C2 executable in at least one LTF profile: **1,157**
- C2 source-valid but no Protected Swing in any profile: **245**
- C3 shape arising from non-executable current C2: **195**
- no executable C2 and no C3 shape: **10,058**

Total:

**1,157 + 245 + 195 + 10,058 = 11,655**

This closes the census with no unclassified anchor.

## 7. Source-state root causes

Across the 11,655 anchors:

- C2 source-valid before LTF PS requirement: 1,402
- C2 close not inside reference: 3,987
- bias unresolved: 2,071
- both-side sweep: 1,347
- side/bias mismatch: 1,317
- no reference sweep: 1,085
- incomplete source H4: 406
- incomplete source day: 40

Of the 1,402 valid C2 H4 structures:
- 1,157 (82.5%) become mechanical candidates in at least one LTF profile;
- 245 (17.5%) fail to form a Protected Swing in all three profiles.

## 8. Forensics of the 245 C2-valid / no-PS cases

The exact PS algorithm requires:
1. opposing delivery series;
2. its structural extreme reaches the important level;
3. a non-opposing candle closes through the series open (CISD).

Per-profile failure totals:

### M15
- important level swept but CISD not confirmed: 154
- opposing series still open at C2 end: 21
- opposing series never sweeps important level: 70

### M5
- swept but CISD not confirmed: 184
- series open at C2 end: 8
- no opposing-series sweep: 53

### M3
- swept but CISD not confirmed: 190
- series open at C2 end: 7
- no opposing-series sweep: 47
- incomplete exact-window evidence: 1

Most important cross-profile result:

**129 / 245 cases** have the same root cause in M15, M5 and M3:
the important level is swept but CISD never confirms inside C2.

Therefore these are not primarily timeframe-resolution losses.

## 9. Entry-family source boundary

The source kernel models six entry families:

- reversal-entry
- continuation-entry
- confident-entry
- positional-entry
- open-entry
- POI-continuation-entry

Only the narrow B01 positional path currently has an executable historical
implementation in this line.

The source contract requires causal ordering:
`formed_at <= confirmed_at <= decision_at`.

The positional entry reference is the new HTF open. A CISD/PS that confirms
after that open cannot retroactively justify a fill at that open.

Therefore delayed CISD may be relevant to another source-supported entry family,
but it is not a missing B01 positional trade until that family's exact
source-to-code contract exists.

## 10. Current conclusion

The original 457-trade count materially understated source opportunity density.

After source adjudication and cross-profile identity de-duplication:

- original narrow terminal trades: 457
- M15 latest-PS terminal trades: 579
- diagnostic distinct C2 terminal union across M15/M5/M3: **1,057**
- distinct C2 mechanical union: **1,157**
- additional non-executable C3 shapes: **195**

However, profile union execution is not authorized and C3 is not yet
machine-executable. Density has been located, not yet converted into a valid
single trader contract.

Next source-first work:
1. adjudicate executable semantics for the non-positional entry families;
2. determine whether delayed same-H4 CISD/PS can causally feed one of them;
3. complete C3 POI/CISD/PS bundle;
4. keep all resulting hypotheses separate and validate on unseen evidence.
