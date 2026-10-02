# QORE Shared STI Causal Replay Preregistration Contract 001

## Status

**RESEARCH CONTRACT / NON-PRODUCTIVE / PROTECTED CERTIFICATION HOLDOUT CLOSED**

Primary PR: #635  
Owner directive: `QORE_SHARED_PROACTIVE_TRADER_INTELLIGENCE_OWNER_DIRECTIVE_007.md`

Implementation:

`src/qore/infrastructure/core_stack_v2/shared_trader_intelligence_preregistration.py`

Purpose: bridge the already implemented STI causal replay and same-universe
Control/Treatment attribution contracts into a governed historical research
program without opening the protected Shared certification holdout.

## Research questions

The contract can freeze studies for:

- `OPPORTUNITY_DISCOVERY`;
- `REGIME_TRANSITION`;
- `CONTINUATION_POSITIVE_TAIL`;
- `POSITION_THREAT`.

These are research questions, not Trader commands.

## Mandatory freeze before outcome inspection

A preregistration must freeze:

- Trader identity/version/config fingerprint;
- development/validation dataset fingerprint;
- source-only opportunity-universe fingerprint;
- materiality policy fingerprint;
- distinct Control and Treatment policy fingerprints;
- split identity;
- research questions;
- markets and horizons;
- selection-rule reference;
- threshold-specification reference;
- metric-definition references;
- stress protocol;
- temporal-replication protocol;
- source evidence references.

The contract requires selection rules and thresholds to be frozen before the
study is admitted.

## Holdout isolation

This contract is intentionally unable to open or even identify the protected
Shared certification holdout.

```text
DEVELOPMENT / VALIDATION RESEARCH ONLY
PROTECTED CERTIFICATION HOLDOUT = CLOSED
```

The following are rejected by construction:

- protected-holdout opening;
- protected-holdout fingerprint injection;
- outcome-aware policy mutation;
- productive behavior authority.

## Causal law

Historical research remains bound by the existing contracts:

```text
SAME OPPORTUNITY UNIVERSE
+
IDENTICAL DECISION TIME
+
CONTROL WITHOUT PROACTIVE SHARED
+
TREATMENT WITH PROACTIVE SHARED
+
NO FUTURE OUTCOME IN DECISION RECORD
=
VALID ATTRIBUTION FOUNDATION
```

Behavioral difference alone still does not prove economic value.

## Current disposition

```text
PREREGISTRATION CONTRACT = IMPLEMENTED
HISTORICAL DATASET STUDY = NOT YET EXECUTED
PREDICTIVE VALUE = NOT PROVEN
ECONOMIC VALUE = NOT PROVEN
STI READINESS = RESEARCH_READY
PROTECTED SHARED HOLDOUT = CLOSED
PRODUCTIVE AUTHORITY = FALSE
```

The next authorized scientific step is to instantiate a concrete preregistration
against consumed development/validation evidence and execute causal replay
without using protected certification evidence.
