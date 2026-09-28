# QORE Shared WP-05 V12 — Source-Only Evaluation Anchor Preregistration

Identity:

`QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_SOURCE_ANCHORS_001`

## Purpose

Freeze the exact R8 evaluation timestamps for the first causal BID/ASK
microstructure representation before any V12 target/outcome discovery.

The anchors are the exact causal source population already used to construct the
frozen V12 acquisition manifest. They are not selected using matured structural
failure labels, trade outcomes, PnL, R6/R5, any WP-05 fresh holdout or the final
Shared certification holdout.

## Frozen upstream identity

- partition: `R8`;
- causal source population: **6,804**;
- frozen acquisition-manifest SHA256:
  `2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191`;
- acquisition source range:
  `2016-04-20T14:00:00Z → 2018-05-18T19:30:00Z`;
- historical tick dataset SHA256:
  `ebbe30a887867bb917f0992b15e1600f9f06eccb07562b9625fcb9517fb381c8`.

## Anchor construction law

1. Reconstruct source timestamps from immutable R8 NAS100/SP500/US30 market
   evidence using the exact same causal source-state algorithm as the frozen
   acquisition manifest.
2. Sort chronologically and require uniqueness.
3. Require exactly 6,804 anchors.
4. Rebuild the acquisition manifest from those anchors and require the exact
   frozen acquisition-manifest SHA256.
5. Persist every anchor timestamp, not only merged acquisition windows.
6. Produce a deterministic source-anchor SHA256 from the complete ordered
   population plus governance identity.
7. Bind the artifact to the producing Git SHA and immutable R8 evidence
   checksums.

Any population, ordering, source-range or manifest-digest drift fails closed.

## Evaluation semantics

Each anchor is an **evaluation timestamp**, not a target timestamp.

A later V12 representation may consume only provider events satisfying:

`provider_event_at <= evaluation_at`

No +future tick, terminal state, MAE/MFE, outcome or target may enter the
representation.

The historical provider retrieval timestamp is provenance only and is never
treated as historical Core availability.

## Representation boundary after this freeze

The causal microstructure representation may use:

- latest causal BID state;
- latest causal ASK state;
- explicit side ages;
- spread only when both sides satisfy the frozen staleness law;
- side-age skew;
- independent BID/ASK update counts;
- update imbalance;
- per-side path variation;
- per-side displacement;
- source-only availability / missingness state.

It may not:

- force one-to-one BID/ASK pairing;
- interpolate future quotes;
- forward-fill beyond the frozen staleness limit;
- choose feature windows based on target performance;
- use outcome-aware missing-data treatment.

## Still closed

This anchor freeze does **not** authorize target-aware V12 discovery by itself.

Before target outcomes are read, the following must also be frozen:

- raw source integrity = GREEN;
- numerical staleness policy;
- missingness policy;
- multiscale windows;
- exact feature family;
- normalization/scaling semantics;
- representation fingerprint;
- information-gain / candidate-selection protocol.

R6/R5 and all fresh holdouts remain closed until the final V12 representation
is frozen.

## Sovereignty

This is scientific observation infrastructure only. Shared gains no Trader,
CIBO, Risk, order or Execution authority.
