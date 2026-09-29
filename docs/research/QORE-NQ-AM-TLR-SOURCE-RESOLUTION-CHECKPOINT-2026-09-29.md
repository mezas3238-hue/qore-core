# QORE NQ AM TLR — SOURCE-RESOLUTION CHECKPOINT

Date: 29-SEP-2026
PR: #654
Source video: `UVVmS0de0g0`

## DeepSeek source-resolution incorporated

The source-resolution report corrected the main V1-V4 translation errors:

- daily expectation was bullish-conditional/contextual;
- opening "two signatures" are source evidence, not a universal fixed-two-bar
  hard gate;
- `gap/4` 2SD tolerance is unsupported;
- IFVG-by-11:10 is unsupported;
- hard 12:00 expiry is unsupported;
- sweep-low-minus-one-tick is not a source-defined stop;
- Monday/NFP is not a hard gate;
- body rejection of the Thursday low and no-close-below-2SD are distinct source
  observations;
- entry is inside the IFVG and does not require the old
  `close >= midpoint` rule.

QORE also corrected one duplicated source concept:
the 09:30 RTH open is the lower boundary of the discount RTH opening gap, so
those cannot be counted as two independent targets/confirmations.

## V5 — exact-source anchor

Identity:
`QORE_NQ_AM_TLR_V5_SOURCE_RESOLVED_001`

Run:
`36518867487`

SHA:
`457610ae2bbfad4a8dbd3b04cea73809a8be974f`

Artifact:
`11011748318`

Artifact digest:
`sha256:de65c1c972ecae3ba85ac30494450634b2a668ff1870618998434746620346fc`

Evidence:
existing Core USTEC M1 holdout, one year
`2016-04-20 NY -> 2017-04-20 NY`.

Result:
- evaluated Mondays: 45
- exact Thursday/Friday context missing: 15
- non-discount RTH gaps: 17
- no Thursday-low macro sweep: 8
- complete-body acceptance below Thursday low: 5
- source-resolved events: **0**

V5 therefore produced no executable source event.

### Provider defect discovered

The source uses NQ Friday 16:14 ET final RTH print.

The USTEC CFD evidence does not always contain that timestamp:
- 2016-11-11: final provider bar ~15:58 ET;
- 2017-03-10: final provider bar ~15:58 ET;
- after the DST transition, 16:14 bars reappear.

Thus exact 16:14 presence is not a valid USTEC-capability gate.

## V6 — USTEC provider-normalized anchor

Identity:
`QORE_NQ_AM_TLR_V6_USTEC_PROVIDER_NORMALIZED_001`

Run:
`36519248595`

SHA:
`8a0320805247cd6a9aa425829d5f906c8310c1c2`

Artifact:
`11011454576`

Artifact digest:
`sha256:76bcda376ee900a5c0505d8db487e0cf2a520b108e442ade715f5867f1ec63aa`

Provider normalization:
latest actual USTEC M1 print from 15:30-16:30 ET.
No synthetic 16:14 bar and no interpolation.

Observed Friday final-print times in the retained evidence:
- 15:58: 17
- 16:14: 18
- 16:15: 13
- 16:30: 2

Result after removing the provider-anchor confound:
- evaluated Mondays: 45
- calendar context missing: 2
- non-discount provider opening gap: 22
- no Thursday-low sweep during 10:50-11:10: 13
- rejection failed: 8
  - complete body established below Thursday low: 7
  - close at/below inferred 2SD: 1
- source-resolved events: **0**
- IFVG entry events: **0**

The opening two-signature telemetry was present on some days:
- 09:30/09:31 pair: 9
- 09:31/09:32 pair: 8

but it was not used as a hard gate.

## 2SD diagnostic

The current QORE formula
`sd2 = monday_open - 2 * opening_gap`
remains explicitly inferred, not source-authoritative.

On V6 the absolute Thursday-low↔2SD distance normalized by gap had:
- min: 0.3615 gap
- p25: 2.2073 gaps
- p50: 4.3851 gaps
- p75: 8.5429 gaps
- max: 41.4545 gaps

This is strong evidence that the current 2x-gap arithmetic is not reproducing the
source's observed "same general area" geometry on most USTEC Mondays, or that
USTEC CFD opening-gap geometry is not equivalent to NQ futures.

It must not be silently treated as a proven ICT 2SD formula.

## Current scientific conclusion

The literal source-resolved Monday setup does **not occur as an executable event**
in this one-year USTEC holdout under either:

1. exact NQ-style 16:14 anchoring; or
2. a provider-normalized USTEC Friday final print.

This is an incidence result, not a losing-PnL result.

Therefore we still cannot honestly claim:
- "the methodology loses";
- or "the methodology is profitable".

There are zero source-resolved entries to score.

The evidence instead says that the exact reviewed Monday/Thursday-low geometry is
too sparse / non-equivalent on this USTEC year.

Any next attempt to test the broader architecture
`gap delivery -> sell-side -> macro -> rejection -> IFVG -> long`
must be a new generalized research identity. It cannot be presented as an exact
replay of this single Monday source operation.

## Authority

Research only.

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`

No merge without explicit Owner order.
