# CIBO Architect B → Architect A Cross-Boundary Request 001

## Purpose

Architect B has added integration evidence surfaces that the Architect-A-owned
Zero Open Work classifier cannot yet classify. B will not edit
`scripts/cibo_zero_open_work_gate.py`.

Please add the following deterministic inventory assignments in the A surface:

| Path | Required workstream |
|---|---|
| `src/qore/infrastructure/cibo_arch_b_forward_economic_manifest.py` | `FORWARD_QUALIFICATION` |
| `tests/infrastructure/test_cibo_arch_b_forward_economic_manifest.py` | `FORWARD_QUALIFICATION` |
| `src/qore/infrastructure/cibo_research_memory.py` | `LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK` |
| `tests/infrastructure/test_vt31_cibo_market_memory_quarantine.py` | `LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK` |
| `tests/infrastructure/test_cibo_risk_integration_closure.py` | `RISK_INTEGRATION` |
| `.github/workflows/cibo-risk-integration-closure.yml` | `RISK_INTEGRATION` |
| `docs/research/CIBO-RISK-INTEGRATION-CLOSURE-V1.md` | `RISK_INTEGRATION` |

## Observed evidence

Zero Open Work run `36759730460` failed solely with the then-current orphan
set:

- `src/qore/infrastructure/cibo_arch_b_forward_economic_manifest.py`
- `src/qore/infrastructure/cibo_research_memory.py`
- `tests/infrastructure/test_cibo_arch_b_forward_economic_manifest.py`

The Risk-integration files were added after that run and are included above
proactively so the classifier remains complete.

## Governance

This request changes inventory ownership only. It must not:

- alter any B implementation;
- change terminal dispositions;
- lower Zero Open Work criteria;
- authorize LIVE/production/real capital;
- mutate the frozen Phase20 V3 candidate;
- open the sealed 2017H1 holdout.

Architect B will consume the next A-classifier result after integration rather
than editing the A-owned gate directly.
