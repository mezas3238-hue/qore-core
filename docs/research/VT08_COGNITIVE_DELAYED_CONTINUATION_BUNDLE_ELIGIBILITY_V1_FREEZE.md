# VT08 Cognitive Expansion — Delayed Continuation Bundle Eligibility V1 Freeze

Status: **PRE-RESULT / SOURCE-BUNDLE ELIGIBILITY ONLY**

## Source provenance

This experiment re-adjudicates a source formalization retained from PR #518,
not its economics.

Primary-video audit in PR #518 recorded:

- 08:46–09:58: missed reversal -> wait for continuation; retracement into FVG;
  close through opposing candles -> new Protected Swing; stop at Protected
  Swing; trade only with remaining room.
- SF-03: conservative `CISD_CONFIRMATION_CLOSE` is eligible only when the
  confirming close lies inside the causal source-marked POI.
- SF-04: conservative automatic invalidation uses the Protected Swing.
- later official TTrades clarifications continue to teach protected-swing /
  continuation entries after POI reach + CISD.

PR #518 economics are invalid for current qualification. The source trace is
used only as forensic input.

## Frozen universe

Only the 245 anchors already proven to be:

- C2 source-valid;
- no Protected Swing before the H4 open in M15/M5/M3.

Within them, the post-anchor audit found 130 anchors with >=1 Protected Swing
later in the current H4.

## Eligibility rule

For each independent LTF profile, a post-anchor PS confirmation is
`CONTINUATION_BUNDLE_ELIGIBLE` only when:

1. the PS is causally confirmed inside the current H4;
2. at least one FVG in the trade direction formed before confirmation;
3. the FVG remained active before confirmation;
4. the confirmation candle reached the FVG;
5. the CISD confirmation close lies inside the FVG;
6. exactly one such causal FVG is active at confirmation.

Multiple active matching FVGs abstain as unresolved POI ambiguity.

## Prohibited in this stage

- no historical fill;
- no target;
- no outcome/PnL read;
- no PF;
- no cross-profile confirmation;
- no profile ranking;
- no post-hoc parameter selection.

The report counts:
- eligible confirmation events;
- anchors with >=1 eligible event by profile;
- distinct anchor union across profiles;
- overlap masks;
- POI ambiguity/no-POI reasons.

A later economic replay requires a separate pre-registration of entry, stop,
target, fill semantics and daily selection.

No DEMO/LIVE/production/real-capital authority.
