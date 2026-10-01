# CIBO Architect 2 — Integrator Patch Request 005

Status: **INTEGRATOR IMPORT GRAPH REGRESSION DETECTED**

Architect 2 found a reproducible Integrator-side import failure while running
its independent scientific regression suite.

## Broken edge

`src/qore/infrastructure/cibo_ce2i_calibration_terminal_evidence.py`

imports:

`qore.infrastructure.cibo_ce2i_calibration_freeze_readiness`

but the file:

`src/qore/infrastructure/cibo_ce2i_calibration_freeze_readiness.py`

is absent from the current Integrator branch.

Observed current Integrator checkpoint when reconfirmed:

`agent/cibo-integrator-ab-001@51fdbc992594275addcb97676342f651e96bbc36`

The missing module was also absent from Architect-2 because Architect-2 is
correctly based on the Integrator branch.

A second broken edge was then observed:

`src/qore/infrastructure/cibo_phase22_external_dependency_evidence.py`

imports:

`qore.infrastructure.cibo_ce2i_phase20_historical_shadow`

but `src/qore/infrastructure/cibo_ce2i_phase20_historical_shadow.py` is also
absent from the current Integrator branch.

## Impact

Any import path passing through:

`cibo_ce2i_calibration_terminal_evidence.py`

can fail at Python module import before its own scientific tests execute.
Architect-2 observed this through the forward-qualification reconciliation test.

## Architect-2 action

Architect-2 did **not** modify #670 or invent the missing module. Its own
forward-qualification reconciliation was narrowed to consume independent
pre-outcome governance receipts and no longer imports the affected execution
manifest graph.

## Requested Integrator action

Reconcile both missing-module edges. For each one determine whether the module
should be restored from already-verified integrated lineage or whether the stale
import should be removed/repointed to the canonical replacement.

Then run the Integrator pre-holdout / calibration regression surface.

This request has no Phase22 V2 consumption, ledger mutation, VPS, LIVE, or
productive authority.
