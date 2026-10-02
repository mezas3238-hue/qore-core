# CIBO A1/A2 Scientific Dependency Admission V1

Status: **CROSS-LANE CONSUMER CONTRACT / A2 OWNERSHIP PRESERVED**

Identity:

`CIBO_A1_A2_SCIENTIFIC_DEPENDENCY_ADMISSION_V1`

## Purpose

Some A1 hypotheses consume mechanisms that belong exclusively to Architect A2.
A1 may use them only after A2 has emitted a canonical Phase22 scientific
disposition receipt on the same canonical Phase22 manifest.

Allowed cross-lane dependencies are limited to:

- `COMPOUND_ENGINE`;
- `INTERNAL_CAPITAL_MARKET`;
- `PROTECTED_BASE_CAPITAL`;
- `PROFIT_PROTECTION`.

## Admission law

A1 accepts an A2 dependency only when:

- the receipt uses the canonical Phase22 scientific-disposition schema;
- its `phase22_manifest_sha256` equals the A1 canonical bridge identity;
- the workstream is on the explicit allowlist;
- disposition is exactly `COMPLETED_AND_PROVEN`;
- `passed=true`;
- blockers and failed dimensions are empty;
- the exact A2 source HEAD is bound.

Falsified or externally blocked A2 work is not silently converted into an A1
dependency.

## Ownership law

Admission means consumption only.

A1 never:

- modifies the A2 workstream;
- closes the A2 workstream;
- updates the Master Ledger;
- gains integration, productive or certification authority.
