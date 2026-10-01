# CIBO Architect B → Architect A Cross-Boundary Request 002

Supersedes Request 001 for inventory/classifier reconciliation.

Architect B will not edit the A-owned Zero Open Work classifier in this phase.
Please add deterministic assignments for these B surfaces:

| Pattern / path | Workstream |
|---|---|
| `*cibo_arch_b_forward_economic_manifest*` | `FORWARD_QUALIFICATION` |
| `*cibo_phase20_arch_b_forward_economic_manifest*` | `FORWARD_QUALIFICATION` |
| `*cibo_ce2i_phase20_t02_structural_oos*` | `T02` |
| `*cibo_ce2i_phase20_t03_margin_population*` | `T03` |
| `*cibo_ce2i_phase20_t11_execution_population*` | `T11` |
| `*cibo_ce2i_phase20_t11_cost_binding*` | `T11` |
| `*cibo_ce2i_execution_efficiency*` | `T11` |
| `*cibo_ctrader_demo_account_capability*` | `PROVIDER_ECONOMICS` |
| `*cibo_ctrader_demo_capability_registry*` | `PROVIDER_ECONOMICS` |
| `*cibo_ce2i_provider_execution_calibration*` | `PROVIDER_ECONOMICS` |
| `*cibo_phase20_provider_execution_calibration*` | `PROVIDER_ECONOMICS` |
| `*cibo_t20_capital_release*` | `T20` |
| `*cibo_usd60_exam_readiness*` | `USD60_CAPABILITY_PROGRAM` |
| `*cibo_integrated_capital_forward_binding*` | `INTEGRATED_CAPITAL_TRUTH` |
| `*cibo_ce2i_calibration_freeze_manifest*` | `FRESH_OOS` |
| `*cibo_calibration_freeze_manifest*` | `FRESH_OOS` |
| `*cibo_research_memory*` | `LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK` |
| `*cibo_risk_integration_closure*` | `RISK_INTEGRATION` |

Also classify the corresponding tests, dedicated workflows and B closure docs to
the same workstream rather than the generic `FORWARD_QUALIFICATION` or
`SOURCE_OF_TRUTH_RECONCILIATION` fallbacks where a more specific B workstream
exists.

This request changes inventory ownership only. It must not change scientific
thresholds, terminal dispositions, frozen V3 identity, holdout state, or productive
authority.

Canonical B status/evidence package:
`docs/research/CIBO-ARCH-B-CLOSURE-HANDOFF-V1.json`.


## Addendum — provider taxonomy and T11 calibration surfaces

Please also classify the following B-owned surfaces deterministically:

| Pattern / path | Workstream |
|---|---|
| `*cibo_ctrader_demo_instrument_taxonomy*` | `PROVIDER_ECONOMICS` |
| `*cibo_ce2i_t11_execution_cost_calibration*` | `T11` |

The same ownership applies to their tests, CI workflow coverage and associated
closure documentation. This addendum changes inventory ownership only; it does
not alter any scientific threshold or terminal disposition.


## Addendum — T17 limited-risk provider evidence

Please additionally classify these surfaces under `T17`:

| Pattern / path | Workstream |
|---|---|
| `*cibo_ce2i_t17_limited_risk_capability*` | `T17` |
| `*cibo_t17_limited_risk_capability_probe*` | `T17` |

Their tests and provider-economics workflow evidence remain B-owned and must not
be absorbed into a generic provider bucket during final inventory closure.


## Addendum — T16 preregistration, T03 direct screen and B terminal dispositions

Please classify these additional B surfaces:

| Pattern / path | Workstream |
|---|---|
| `*cibo_ce2i_t16_preregistered_hedge_universe*` | `T16` |
| `*cibo_t03_provider_equivalent_candidate_screen*` | `T03` |

Architect B also emits:

`docs/research/CIBO-ARCH-B-TERMINAL-DISPOSITION-PACKAGE-V1.json`

This package is the canonical B recommendation for final A+B ledger reconciliation.
It does **not** modify the Master Ledger from branch B. It distinguishes genuine
scientific closure from `EXTERNAL_DEPENDENCY_BLOCKED` states. Every
certification-blocking external dependency must remain blocking after
reconciliation; do not treat terminal classification as certification success.


## Addendum — exact Master Ledger patch request

Architect B now provides the exact machine-readable reconciliation delta:

`docs/research/CIBO-ARCH-B-MASTER-LEDGER-PATCH-REQUEST-V1.json`

and its human-readable companion:

`docs/research/CIBO-ARCH-B-MASTER-LEDGER-PATCH-REQUEST-V1.md`

The Integrator must refresh its own HEAD first and then apply only evidence-backed
rows. The package currently contains 12 B-owned rows that are open in
the B-branch ledger snapshot but have terminal B dispositions. External
dependency dispositions remain certification-blocking.
