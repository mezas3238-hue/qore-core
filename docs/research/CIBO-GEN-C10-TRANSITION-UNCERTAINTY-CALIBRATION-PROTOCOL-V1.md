# CIBO GEN-C10 Transition-Uncertainty Calibration Protocol V1

Status: **IMPLEMENTED / RESEARCH-ONLY / REAL CALIBRATION POPULATION REQUIRED**

Calibration identity:

`CIBO_GENC10_TRANSITION_UNCERTAINTY_CALIBRATION_V1`

Frozen GEN-C10 descriptive identity that remains untouched:

`CIBO_GENC10_CAUSAL_CAPITAL_DIGITAL_TWIN_V1`

## Architectural rule

The frozen GEN-C10 V1 contract explicitly requires:

- `uncertainty_calibrated = false`;
- no market-probability claim;
- no economic-value claim;
- no productive authority.

Therefore calibration is implemented as a separate research evidence layer. It
does not mutate V1 and cannot silently turn a descriptive scenario into a
probabilistic forecast.

Any productive or semantically changed GEN-C10 successor still requires:

```text
NEW IDENTITY
NEW FREEZE
NEW EVIDENCE
```

## Legal calibration evidence

Only chronological:

`FORWARD_OBSERVED`

transition evidence is accepted.

Rejected:

- SYNTHETIC_CONTRACT;
- BURNED_RESEARCH;
- SEALED_HOLDOUT.

The 2017H1 holdout remains excluded.

Each transition binds:

- account identity;
- start/end twin digests;
- provider-registry digest;
- decision-population digest;
- start/end timestamps;
- realized-capital delta;
- compound-value delta;
- protected-floor delta;
- stop-risk capacity/use deltas;
- margin capacity/use deltas;
- active-deployment-count delta;
- known-option-count delta;
- provider-constraint-change observation.

No future data and no market probability may be attached.

## Calibration output

The V1 calibrator produces descriptive empirical support only.

For each predeclared decision-time conditioning key, it records:

- observation count;
- observed chronological span;
- minimum/maximum observed support for each monetary transition dimension;
- minimum/maximum observed support for deployment/option count deltas;
- provider-constraint-change observation count.

It does **not** convert those observations into:

- a market probability;
- an expected return;
- a sizing multiplier;
- Risk authority;
- execution authority;
- a production policy.

## Cutoff law

Every observation used for calibration must terminate strictly before the
calibration cutoff.

The source population digest must be identical across every observation.

Mixed accounts are invalid.

Duplicate transition identities are invalid.

Missing provider or population lineage is invalid.

## Downstream GEN-C11 law

GEN-C11 may not claim calibrated multi-period economic value merely because this
engine exists.

Before GEN-C11 can consume calibrated transition evidence:

1. a real provider-valid chronological population must exist;
2. calibration must be executed on legally prior observations;
3. the evaluation population must remain temporally later and untouched;
4. the GEN-C11 treatment/control population must be identical;
5. the non-compensatory utility gate must pass;
6. adversarial stress must pass;
7. the treatment must replicate independently in WF1/WF2/WF3/WF4.

## Implementation

Engine:

`src/qore/infrastructure/cibo_genc10_transition_uncertainty_calibration.py`

Tests:

`tests/infrastructure/test_cibo_genc10_transition_uncertainty_calibration.py`

## Non-claims

Implementation is not calibration proof.

Until a legal real population is bound and the later evaluation gates pass:

- GEN-C10 remains open;
- GEN-C11 remains open;
- economic value remains unproven;
- CIBO remains uncertified.
