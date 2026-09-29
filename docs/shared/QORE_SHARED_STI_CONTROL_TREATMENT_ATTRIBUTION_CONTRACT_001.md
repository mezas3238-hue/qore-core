# QORE Shared STI — Control/Treatment Attribution Contract 001

## Status

**IMPLEMENTED CONTRACT / NON-PRODUCTIVE / NO ECONOMIC VALUE CLAIM**

Purpose: prove incremental Shared value instead of crediting Shared merely
because it emitted information.

## Design law

For a valid paired study:

```text
SAME TRADER
SAME TRADER VERSION
SAME TRADER CONFIG
SAME DATASET
SAME OPPORTUNITY UNIVERSE
SAME DECISION TIME
```

The intended difference is:

```text
CONTROL:
Trader without proactive STI

TREATMENT:
same Trader + proactive STI
```

Control and treatment policy fingerprints must differ and be preregistered.

## Decision/outcome separation

Historical decision records contain no future outcome.

Outcome observations belong to a separate post-outcome record.

```text
DECISION RECORD
!=
OUTCOME RECORD
```

## Attribution law

If control and treatment decisions are identical:

```text
NO_BEHAVIORAL_DIFFERENCE
→ NO CAUSAL TRADER VALUE CLAIM
```

If decisions differ:

```text
BEHAVIORAL_DIFFERENCE_OBSERVED
!=
ECONOMIC VALUE PROVEN
```

Economic value still requires causal outcome analysis, OOS, stress and
replication.

## Protected holdouts

The attribution design cannot itself open a protected holdout.

## Value dimensions

The contract can separately identify research for:

- opportunity-discovery value;
- entry-decision value;
- position-management value;
- continuation / positive-tail value.

These dimensions must not be collapsed into one undocumented score.

## Productive status

```text
CONTROL/TREATMENT CONTRACT = IMPLEMENTED
ECONOMIC ATTRIBUTION STUDY = NOT YET RUN
OOS VALUE CLAIM = FALSE
PRODUCTIVE TRADER CHANGE = FALSE
PROTECTED HOLDOUT OPENED = FALSE
```
