# CIBO A1 Phase22 Canonical Scientific Manifest Bridge V1

Status: **A1/A2 EXAM-IDENTITY BRIDGE / NO INTEGRATION AUTHORITY**

Identity:

`CIBO_A1_PHASE22_CANONICAL_SCIENTIFIC_MANIFEST_BRIDGE_V1`

## Purpose

Architect A1 keeps a detailed local scientific-consumption manifest that binds
the exact historical replay decision, policy and WF1..WF4 populations.

Architect A2 scientific dispositions use the canonical
`ArchitectAPhase22V2ScientificIntakeReport.manifest_sha256`.

This bridge proves those two identities refer to the same completed Phase22 V2
examination before A1 terminal science is handed to the Integrator.

## Required equality

A1 local manifest and canonical Phase22 intake must agree on:

- candidate id;
- decision-epoch count;
- exact ordered 7/7 Trader lineage;
- exact ordered WF1..WF4 lineage.

A1 also consumes a read-only identity projection of B's frozen pre-outcome
Phase22 execution manifest. Its digest must equal the canonical intake's
`execution_manifest_sha256` receipt, and its candidate code SHA, parameter
SHA256 and 7/7 Trader lineage must match the A1 consumption manifest exactly.

The canonical intake may be terminal PASS or terminal FAIL. Both remain
scientifically consumable; neither is rewritten.

## Result

The bridge records both:

- canonical Phase22 scientific manifest SHA256;
- A1 consumption-manifest SHA256.

The canonical Phase22 SHA is therefore the common cross-lane identity for A1
and A2.

## Governance

The bridge grants no:

- integration authority;
- Master Ledger update;
- productive/LIVE/real-capital authority;
- certification claim.
