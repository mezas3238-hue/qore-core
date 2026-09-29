# QORE NQ AM TLR V6 — USTEC PROVIDER-NORMALIZED SOURCE REPLAY

Identity: QORE_NQ_AM_TLR_V6_USTEC_PROVIDER_NORMALIZED_001
Issue: #659
PR: #654
Status: RESEARCH_ONLY

## Trigger

V5 run 36518867487 was GREEN but exact-source anchoring exposed a provider
session incompatibility:

NQ source anchor:
Friday 16:14 ET final RTH print.

USTEC holdout:
multiple standard-time Fridays terminate around 15:58 ET and contain no 16:14
bar.

Therefore exact 16:14 availability cannot be used as an USTEC capability gate.

## Frozen provider normalization

For every provider day:

- require exact 09:30 ET opening bar;
- collect USTEC M1 bars from 09:30 through 16:30 ET;
- define provider final RTH print as the latest available bar whose opening time
  is between 15:30 and 16:30 ET;
- use that bar's close as the provider-equivalent settlement anchor;
- retain the exact provider timestamp.

No interpolation.
No synthetic 16:14 bar.
No previous-day substitution.

## Methodology

All V5 source-resolved rules remain unchanged except the Friday anchor:

- Monday-only source replay;
- exact prior Thursday ETH daily low / discount-wick CE;
- Friday provider final RTH print -> Monday 09:30 open gap;
- opening two-signature information is telemetry, not a hard gate;
- inferred 2SD = Monday open - 2*gap is QORE_INFERRED, not source authority;
- no arbitrary 2SD-distance tolerance;
- 10:50-11:10 macro;
- price trades through Thursday low;
- no complete M1 body establishes below Thursday low;
- no M1 close at/below inferred 2SD;
- most recent bearish delivery FVG;
- later price trades above the FVG;
- only a subsequent M1 revisit can create the diagnostic IFVG entry;
- entry price = FVG upper boundary;
- no source-defined stop;
- no source-defined 12:00 expiry;
- outcome observation ends with provider RTH session only.

## Robustness

A structural stop at sweep low - 1 provider tick is reported only as
QORE_IMPLEMENTATION_ROBUSTNESS. It has zero ICT/source-rule authority.

## Evidence

Existing immutable Core USTEC M1 holdout only:

- source run: 34981033027
- source artifact: 10402199719
- evidence SHA-256:
  4031c7e21bb311fdb99d7b1028fd9ff154ace1dc4886249ff978b700fdeeedcb

Evaluation:
2016-04-20 NY -> 2017-04-20 NY end exclusive.

## Authority

DEMO_ELIGIBLE=false
LIVE_AUTHORIZED=false
REAL_CAPITAL_AUTHORIZED=false
PRODUCTION_AUTHORIZED=false

No merge without explicit Owner order.
