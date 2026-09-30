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
