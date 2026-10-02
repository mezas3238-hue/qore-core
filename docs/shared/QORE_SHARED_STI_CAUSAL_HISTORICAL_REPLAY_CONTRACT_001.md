# QORE Shared STI — Causal Historical Replay Contract 001

## Status

**IMPLEMENTED CONTRACT / RESEARCH INFRASTRUCTURE / NON-PRODUCTIVE**

Purpose: reconstruct exactly what was legally knowable at every historical
Shared↔Trader decision point.

## Replay frame

A `SharedTraderCausalReplayFrame` binds:

- decision time;
- the Shared snapshot available then;
- the Trader assessment available then, if any;
- entry-world position lineage if the position already existed;
- world-now delta if already observable;
- source-data fingerprints;
- policy fingerprints;
- provenance.

## Absolute chronology law

At one replay decision time:

```text
Shared snapshot observed_at <= decision_time
Shared evidence_cutoff_at <= decision_time
Trader assessed_at <= decision_time
position opened_at <= decision_time
world delta compared_at <= decision_time
```

The frame rejects:

- future market data;
- future outcome;
- future report;
- future weather;
- future roll state;
- outcome evidence inside the decision frame.

## Replay sequence

Frames must be unique, chronological and deterministic.

The sequence preserves a dataset fingerprint and cannot mutate a policy based
on outcomes.

## Protected holdouts

A protected-holdout replay fails closed unless an explicit upstream
authorization has opened that holdout.

No workflow introduced by this contract opens a protected holdout.

## Separation from post-outcome research

Outcome-based metrics such as:

- false alert;
- missed alert;
- early-exit regret;
- missed-opportunity regret;
- winner preservation;
- profit preservation;

belong to a later, separate post-outcome evaluation layer.

They may never be injected back into the historical decision frame.

## Productive status

```text
CAUSAL REPLAY CONTRACT = IMPLEMENTED
HISTORICAL DATASET RUN = NOT YET EXECUTED
CONTROL/TREATMENT = NOT YET EXECUTED
OOS VALUE CLAIM = NOT AUTHORIZED
PRODUCTIVE TRADER CHANGE = FALSE
PROTECTED HOLDOUT OPENED = FALSE
```
