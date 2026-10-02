# CIBO A1 Phase22 External Execution Preflight Receipt V1

Status: **VERIFIED EXTERNAL PRE-OUTCOME EVIDENCE / NOT SCIENTIFIC OUTCOME EVIDENCE**

Identity:

`CIBO_A1_PHASE22_EXTERNAL_EXECUTION_PREFLIGHT_RECEIPT_V1`

## Verified source

A1 verified the actual GitHub Actions artifact emitted by the Integrator:

- Integrator HEAD: `049c7e8dfba2b0333df6ac23e91c168df1290bcd`
- artifact id: `11202555722`
- artifact archive digest:
  `sha256:3f9bd77c11b6203699b49ddee54c968e03a4bb54afa20be94330b70e235eb579`
- execution manifest SHA256:
  `sha256:6c54051112f2ce190bf3ed20c3e5d1ee0b4d7a7b4cffb0d2b01d590500000a54`
- candidate:
  `CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2`
- candidate code SHA:
  `edf96722fd0505711aa88bc1d15296b09e6dba6f`
- candidate parameter SHA256:
  `sha256:1bfab7bd6ca86201ca6010d5ec72448d318ee6e38d051eb0d126bf76ddec85fb`
- ordered 7/7 Trader lineage: canonical CIBO portfolio order.

## What the artifact actually says

The one-shot preflight is `READY` and:

```text
authorized_to_emit_first_fresh_outcome = true
execution_claimed = false
fresh_outcomes_already_emitted = false
```

The execution manifest itself also records:

```text
fresh_outcomes_executed = false
productive_authority = false
```

## Consequence for A1

A1 can now bind its Phase22 bridge to a concrete, externally verified
pre-outcome execution identity instead of a hypothetical fixture.

This receipt **cannot** be used as Phase22 scientific-outcome evidence and
cannot produce any A1 terminal scientific disposition. Fresh replay outcomes
must exist first.
