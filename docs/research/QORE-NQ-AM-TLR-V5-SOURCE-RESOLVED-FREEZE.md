# QORE NQ AM TLR V5 — SOURCE-RESOLVED USTEC 1Y FREEZE

Identity: QORE_NQ_AM_TLR_V5_SOURCE_RESOLVED_001
Issue: #658
PR: #654
Source: UVVmS0de0g0
Status: RESEARCH_ONLY / SOURCE_EVENT_AND_ECONOMIC_POTENTIAL

## Why V5 exists

The primary-source evidence pack plus DeepSeek source-resolution report exposed
source-translation errors in V1-V4. V5 does not mutate those identities. It
creates a new preregistered research identity.

Key repairs:

- daily context = bullish conditional/contextual, not bearish-until-sweep;
- opening "two signatures" = source evidence, not a universal M2 hard gate;
- no gap/4 confluence tolerance;
- no IFVG-before-11:10 hard expiry;
- no 12:00 source expiry;
- no source claim that stop = sweep low - 1 tick;
- no Monday/NFP prohibition;
- entry = inside the IFVG, without the V1-V4 close>=midpoint hard rule;
- 09:30 open and the low of the discount RTH opening gap are the same price
  anchor and must not be double-counted.

## Evidence

Reuse only the immutable Core USTEC/NAS100 M1 holdout:

- source run: 34981033027
- source artifact: 10402199719
- evidence file: fresh/NAS100/market-evidence.json
- evidence SHA-256:
  4031c7e21bb311fdb99d7b1028fd9ff154ace1dc4886249ff978b700fdeeedcb
- retained source coverage:
  2016-04-19T00:00:00Z -> 2018-05-18T20:55:00Z

Frozen evaluation:

2016-04-20 NY -> 2017-04-20 NY, end exclusive.

No new market-data download.

## Source scope

The reviewed setup is a Monday event:

- Thursday daily wick / Thursday low;
- Friday 16:14 ET RTH settlement;
- Monday 09:30 ET open.

V5 primary replay is therefore Monday-only. Generalizing Thursday/Friday/Monday
to every weekday would be a new model, not source reconstruction.

## Source / mechanization ledger

SOURCE_EXPLICIT:
- Thursday close-to-low discount wick and 50% CE;
- Thursday low as sell-side liquidity;
- Friday 16:14 ET settlement to Monday 09:30 ET open RTH gap;
- gap quarters and eighths;
- 10:50-11:10 New York macro;
- price trading through prior low;
- bodies not establishing under Thursday low;
- no close at/below second-standard-deviation reference;
- bearish FVG later behaving as IFVG after price goes above it;
- entry inside the IFVG;
- relative equal highs, wick CE and 09:30 open as upside references.

SOURCE_CONTEXT_ONLY:
- bullish daily expectation;
- opening two-signature delivery weakness;
- Monday/NFP comments;
- public narrative.

QORE_INFERRED:
- second-standard-deviation arithmetic:
  sd2 = monday_0930_open - 2 * opening_gap_size.
  This is retained only because it is the current QORE interpretation. It is not
  upgraded to an explicit ICT formula.

QORE_MECHANIZATION:
- "body establishes below Thursday low" is encoded literally as an M1 body whose
  open and close are both below that low;
- "price went above the bearish FVG" is encoded as an M1 high strictly above the
  FVG upper boundary;
- because M1 cannot prove intrabar order, the IFVG entry is allowed only on a
  later M1 bar that revisits the already-inverted zone;
- entry price for the diagnostic event is the FVG upper boundary, the first
  conservative touch from above.

SOURCE_UNDEFINED:
- exact 2SD formula;
- numeric Thursday-low↔2SD confluence tolerance;
- initial stop;
- hard setup expiry;
- equal-high tolerance;
- exact entry order type;
- exact scale-out percentages.

## Primary event

For each Monday with exact prior Thursday and Friday evidence:

1. Build Thursday ETH daily candle.
2. Compute Thursday CE = (Thursday close + Thursday low) / 2.
3. Read Friday 16:14 settlement.
4. Read Monday 09:30 open.
5. Require discount RTH gap: Monday open < Friday settlement.
6. Compute lower quadrant and lowest octant.
7. Record both possible opening-pair signatures as telemetry only:
   - 09:30/09:31 pair;
   - 09:31/09:32 pair.
8. Compute inferred sd2 and continuous distance to Thursday low. No tolerance
   gate.
9. In 10:50<=t<11:10 require first trade strictly through Thursday low.
10. From that sweep through 11:10 require:
    - no complete M1 body below Thursday low;
    - no M1 close at/below inferred sd2.
11. Identify the most recent bearish M1 FVG created between 09:30 and the sweep.
12. After the sweep, require a later M1 bar to trade above the FVG upper bound.
13. After that inversion bar has completed, require a later M1 bar to revisit
    the FVG.
14. Diagnostic entry = FVG upper bound on that causal revisit.

No opening M2 hard gate.
No 2SD-distance hard gate.
No IFVG-by-11:10 requirement.
No 12:00 expiry.

## Outcome horizon

The source does not define a hard expiry. V5 therefore observes outcomes through
the same RTH session only.

This is EVALUATION_HORIZON_ONLY and has zero source-expiry authority.

Source-defined measurable objectives:

- Thursday wick CE, if above entry;
- Monday 09:30 open / lower RTH-gap boundary, counted once.

Relative equal highs are retained as SOURCE_EXPLICIT but not scored because the
source does not provide a machine-safe equal-high tolerance.

For each objective report:

- reached before a new low below sweep extreme;
- time to target;
- MFE / MAE from entry.

If target and a new structural low both occur in the same M1 bar, V5 scores the
new low first, conservatively.

## Structural-stop robustness

For comparability only, V5 separately reports a QORE robustness simulation with:

stop = sweep extreme - one provider tick.

That is QORE_IMPLEMENTATION_ROBUSTNESS_ONLY, not ICT's stop.

Primary friction: 0.05R/trade.
Stress friction: 0.10R/trade.

The robustness result cannot promote or redefine the source method.

## Output law

No post-result variant selection.

V5 reports:
- source-event funnel;
- event count;
- inferred 2SD distance distribution;
- opening-signature telemetry;
- IFVG inversion semantics telemetry;
- target-reach rates;
- MFE/MAE;
- structural-stop robustness.

If event count is sparse, state that directly.

## Authority

DEMO_ELIGIBLE=false
LIVE_AUTHORIZED=false
REAL_CAPITAL_AUTHORIZED=false
PRODUCTION_AUTHORIZED=false

No merge without explicit Owner order.
