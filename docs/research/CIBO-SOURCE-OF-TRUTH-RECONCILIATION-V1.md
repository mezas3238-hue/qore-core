# CIBO Source-of-Truth Reconciliation V1

Date: 30-SEP-2026

## Integrated checkpoint — 30-SEP-2026 / PR #670

This section supersedes the historical current-state wording below while
preserving the common-checkpoint provenance.

Current observed child heads:

- Architect A PR #660: `f10e47e8f3127c5997168dd221fd30d9160dbe08`
- Architect B PR #661: `868213aa07309b1d3e65745e581c11d45d851fcf`
- Integrator PR #670 branch: `agent/cibo-integrator-ab-001`

Canonical integrated machine ledger:

```text
MANDATORY = 64
TERMINAL  = 14
OPEN      = 50
ZERO OPEN = FALSE
FINAL CERTIFICATION CANDIDATE = FALSE
```

The terminal union now includes `RISK_INTEGRATION`. Its mechanical closure is
backed by GitHub Actions run `36769958686/SUCCESS` and a direct verification
that the Risk closure surface is unchanged through the current Architect-B
head and byte-identical in the Integrator.

Current A/B delta accounting proves:

- all Architect-A changed files are integrated or deliberately overridden by
  the canonical Integrator Zero Open workflow;
- all Architect-B technical/evidence files are integrated;
- only branch-local B handoff snapshots are deliberately noncanonical;
- no child-delta files are unaccounted.

PR #670 body has been reconciled to this same 64 / 14 / 50 state.

The current integrated certification ordering is:

```text
ALL NON-EXAM MANDATORY WORK TERMINAL
→ PRE_EXAM
→ FINAL_INTEGRATED_CIBO_EXAM
→ WORLD_CUP_MAXIMUM_CAPABILITY_EXAM
→ STRICT ZERO-OPEN
→ FINAL CERTIFICATION CANDIDATE
```

Both certification exams remain mandatory and certification-blocking.
PRE_EXAM is a sequencing scope only; it excludes those two exams and nothing
else. STRICT includes all 64 mandatory workstreams.

The executable reconciliation gate is:

`scripts/cibo_source_of_truth_reconciliation_gate.py`

It verifies agreement among the ledger, A/B acceptance matrix, child-delta
accounting, integrated evidence register and current governance documents.
A passing reconciliation gate proves checkpoint consistency only. It does not
turn open scientific/economic work into terminal work and grants no productive
authority.

Source-of-truth terminal disposition remains pending the Integrator
reconciliation CI on the current integrated state.

Common checkpoint: `1460435615a663a614cd5ee8873f719d08086200`

Architect A child PR: #660

## Authority order

1. GitHub HEAD
2. code
3. tests
4. GitHub Actions evidence
5. canonical artifacts / ledgers
6. ADRs and roadmaps
7. PR body

Historical checkpoint prose is preserved, but it must not override newer machine-readable state.

## Common-checkpoint state

At `1460435615a663a614cd5ee8873f719d08086200`:

- master ledger mandatory workstreams = 64
- terminal workstreams = 7
- open workstreams = 57
- zero-open-work pass = false
- final certification candidate = false
- GEN-C0 = COMPLETED_AND_PROVEN
- GEN-C1..GEN-C7 = engines/foundations implemented; scientific closure still open where required
- GEN-C8..GEN-C14 = engines implemented and their dedicated workflows are GREEN
- Compound Engine integrated-cycle workflow = GREEN
- Protected Base Overlay workflow = GREEN
- GEN-C9 workflow also directly exercises dependency-aware Compound Monte Carlo, adversarial stress, and temporal-replication harnesses
- two red workflows at the common checkpoint are Legacy Stack Quarantine and CMA↔Compound Authority Boundary; both belong to Architect B under the parallel split

## Stale statements identified

The PR #651 body and older sections of Roadmap V3 / World Cup gap matrix still contain historical statements such as:

- 62 mandatory / 1 terminal / 61 open
- GEN-C9..GEN-C14 = ARCHITECTURE_DEFINED
- implementation of GEN-C9..GEN-C14 as future work

Those statements remain valid only as historical checkpoints. They are not the current state.

## Reconciliation rule

Current-state sections must be updated without deleting historical provenance. A superseding current checkpoint should be added to PR #651, Roadmap V3 and the World Cup gap matrix.

## Parallel-work caveat

Architect A owns the canonical ledger and current-state governance documents during the split. Architect B must not edit them.

Final source-of-truth closure cannot be terminal until A and B work are integrated and a final post-integration reconciliation proves that code, CI, artifacts, ledger, roadmap and PR body agree.

## Integrator static reconciliation checkpoint — 30-SEP-2026

This checkpoint is a deterministic read-only reconciliation of the canonical
artifacts after the Actions queue cleanup and the Integrator's `[skip ci]`
repair batches.

- Architect A observed HEAD: `40137ab89e2ed575700384be84847eb1c2d27fb1`
- Architect B observed HEAD: `99ac91c2880af541966bb4c20445b9cc228c5afd`
- Integrator validated parent HEAD: `06329da5a95cf610fd2cb058f809c7fa10e0c88a`
- mandatory workstreams: `64`
- terminal workstreams: `14`
- open workstreams: `50`
- static reconciliation errors: `0`
- productive authority: `false`
- certification claim: `false`

The static check reconciled ledger counts, terminal union, both mandatory exams,
A/B HEAD identity across acceptance + child-delta + evidence register, Risk
terminal evidence, and the required roadmap / World Cup / sequence / source-of-
truth phrases.

This is **not** a substitute for GitHub Actions revalidation. The prior Source
of Truth run failed before semantic execution because of lint/import-format
defects that are now repaired in the Integrator. Exact-head CI remains pending
under the Owner's no-workflow-flood policy.


## 2026-10-01 atomic child snapshot integration

- Frozen Architect A snapshot: `70db6a38011ff2b69e073f59a437051e04b37e28`.
- Frozen Architect B snapshot: `cd41a8e224812ee6944a70a947d7d4d5f3e7d9de`.
- Integrator predecessor fully evaluated: `67939c275d901f45a217b442ab904a82d6661f0d`.
- A: 122 changed = 110 byte-integrated + 12 deliberate overrides.
- B: 99 changed = 79 byte-integrated + 16 deliberate overrides
  + 4 deliberately noncanonical operational/handoff files.
- Unaccounted child files: 0.
- T17 governed-provider ineligibility closure is staged, not terminal, until
  exact-head CI validates cTrader DEMO plus FundedNext evidence together.
- Productive/runtime/LIVE/merge authority remains false.
