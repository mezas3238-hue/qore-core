# QORE Shared WP-05 — Post-V13 Sensor Availability Audit Preregistration

Identity: QORE_SHARED_WP05_POST_V13_SENSOR_AVAILABILITY_AUDIT_001
Program: QORE_META_COGNITIVE_SCIENTIFIC_INTELLIGENCE_005
PR: #635
Issue: #643
Scientific V14: NOT OPENED
R6/R5: CLOSED
Fresh holdout: CLOSED

## 1. Why this audit exists

V11 exhausted the current NAS100/SP500/US30 OHLC classifier universe.
V12 falsified source-time USTEC BID/ASK.
V13 falsified sequential USTEC BID/ASK.

The next legal step is therefore not another transformation of consumed
information. Before defining any V14 scientific model, Shared must prove that a
genuinely new historical sensor is actually available and causally replayable.

This audit tests availability only. It has zero authority to select a model,
read Target-V2 outcomes, open R6/R5 or open any fresh holdout.

## 2. First audited sensor family

The first post-V13 source family is cross-market microstructure.

Scientific novelty, if later admitted, would come from synchronized historical
BID/ASK event streams for index peers that V11 saw only through OHLC:

- SP500-equivalent microstructure;
- US30-equivalent microstructure.

USTEC is retained only as a catalogue/control identity and is not a new sensor.

## 3. Frozen provider discovery law

Provider: authenticated cTrader DEMO account already used by V12.

Only enabled provider symbols are considered.

Provider symbol display syntax is normalized to uppercase alphanumeric
characters for catalogue matching only. The raw provider name remains the
identity used for requests.

Frozen peer prefixes:

SP500_PEER:
- US500
- SPX500
- SP500

US30_PEER:
- US30
- DJ30
- DOW30
- WS30

A normalized provider name qualifies as a catalogue candidate only if it starts
with one of the frozen prefixes for its family.

This is not semantic admission. Multiple matches remain an explicit ambiguity
and may not be resolved from market outcomes.

## 4. Frozen temporal availability sample

The audit reuses the already frozen source-only V12 R8 acquisition manifest:

manifest SHA256:
2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191

Temporal probe selection remains exactly:

FIRST / Q1 / MID / Q3 / LAST by manifest ordinal.

No new dates are selected from target labels or V12/V13 outcomes.

For every matched provider candidate, BID and ASK are requested independently
over all five frozen windows. The audit records only source availability
statistics: counts, page counts and provider-event time bounds.

No prices or outcomes are used to choose a scientific candidate.

## 5. Disposition law

For one exact provider symbol:

FULL_BID_ASK_HISTORY:
BID > 0 and ASK > 0 in every one of the five frozen windows.

PARTIAL_BID_ASK_HISTORY:
some but not all required side/window observations exist.

NO_HISTORY:
all five windows contain zero BID and zero ASK observations.

TECHNICAL_ERROR:
the provider request or identity path fails. A technical error is not scientific
evidence and may be repaired without changing this audit identity.

Family-level consequences:

- exactly one semantically valid FULL candidate in both peer families:
  cross-market microstructure may proceed to a separate V14 preregistration;
- multiple FULL candidates in one family:
  resolve provider semantics independently of outcomes before V14;
- only one peer family has replayable history:
  no automatic V14 is authorized; any single-peer experiment requires a new
  preregistration before outcomes;
- neither peer family has replayable history:
  reject this cTrader cross-market microstructure path and audit a genuinely
  different sensor family.

Availability never equals scientific PASS.

## 6. Absolute prohibitions

This audit may not read:

- Target-V2 labels;
- terminal/nonterminal outcomes;
- V11 false-positive identity;
- V12/V13 fold outcomes for sensor selection;
- R6;
- R5;
- fresh WP-05 holdout;
- final Shared certification holdout.

This audit may not:

- create V14;
- fit a classifier;
- choose features;
- choose a threshold;
- tune staleness;
- fabricate a feed;
- infer order book from quotes;
- change Trader methodology;
- change CIBO;
- change Risk;
- submit or mutate orders;
- change Execution.

## 7. Required evidence

The artifact must report:

- audit identity;
- source manifest SHA256;
- frozen five manifest ordinals;
- enabled-symbol count;
- USTEC control presence;
- matched raw provider symbols by peer family;
- exact provider symbol IDs/digits when resolved;
- per-window BID/ASK counts and page counts;
- per-window provider-event time bounds;
- coverage disposition;
- read-only message firewall = true;
- target/outcome read = false;
- R6/R5 read = false;
- fresh holdout opened = false;
- scientific V14 opened = false;
- all Shared actuation authorities = false.

Only after this evidence exists may the architect decide whether a separate V14
scientific preregistration is even possible.
