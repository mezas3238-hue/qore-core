# CIBO A1 Scientific Disposition Contract V1

Status: **A1 TERMINAL SIDECAR CONTRACT / INTEGRATOR-OWNED RECONCILIATION**

Identity:

`CIBO_A1_SCIENTIFIC_DISPOSITION_CONTRACT_V1`

## Purpose

Every A1 workstream must end in exactly one scientific terminal state:

```text
COMPLETED_AND_PROVEN
FALSIFIED_AND_CLOSED
```

This contract standardizes the sidecar handed to the Integrator. It never edits
the Master Ledger and cannot certify CIBO.

## Required disposition fields

Each row binds:

- workstream id;
- terminal scientific status;
- hypothesis;
- mechanism identity;
- candidate id;
- exact code SHA;
- exact parameter SHA256;
- source evidence references;
- population identity;
- decision-time boundary;
- control/baseline;
- metrics;
- causal integrity;
- capital conservation;
- result;
- failure reason or proof reason;
- receipt SHA256.

The receipt is recomputed from canonical disposition content.

The package that carries those dispositions must additionally bind:

- the canonical Phase22 scientific manifest SHA256 used by both A1 and A2;
- the A1 scientific-consumption manifest SHA256;
- the canonical A1↔Phase22 bridge SHA256.

A complete A1 handoff without those three identities is invalid.

## Governance

A1 dispositions always preserve:

```text
productive_authority = false
live_authorized = false
real_capital_authorized = false
global_ledger_reconciled = false
cibo_certified = false
```

The Integrator alone may reconcile these terminal sidecars into the canonical
ledger and certification sequence.

## Complete A1 handoff

A package may set `complete_handoff=true` only when it contains exactly the 18
A1-owned workstreams and every receipt matches its canonical payload.

No partial package can claim A1 completion.
