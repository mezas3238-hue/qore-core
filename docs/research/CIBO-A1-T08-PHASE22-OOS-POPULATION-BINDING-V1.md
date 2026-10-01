# CIBO A1 T08 Phase22 OOS Population Binding V1

Status: **A1 EXACT EVIDENCE-BINDING CONTRACT / NO NETTING AUTHORITY**

Identity:

`CIBO_A1_T08_PHASE22_OOS_POPULATION_BINDING_V1`

## Problem closed

The inherited T08 OOS ablation is causal and four-fold, but its shadow epoch
does not carry the Phase22 decision SHA. A green ablation alone therefore does
not prove that the tested population is exactly the active Phase22 V2
population.

## Binding law

Every T08 shadow epoch must bind to:

- one exact Phase22 historical replay decision SHA256;
- the identical decision timestamp;
- one or more actual replay outcome evidence IDs belonging to that decision;
- exactly one canonical WF1..WF4 fold.

The binding must cover the **entire** replay decision population exactly once.

For each fold, A1 recomputes the population digest from the ordered Phase22
decision SHA256 values and requires exact equality with the canonical A1
Phase22 scientific-consumption manifest.

Only after that binding is valid does A1 execute the existing
`CIBO_T08_FRESH_OOS_NETTING_ABLATION_V1` evaluator.

## Non-claims

This wrapper does not certify:

- the signed factor-risk map;
- the correlation state;
- runtime netting credit;
- productive policy;
- CIBO certification.

Those claims remain independently gated. The purpose here is exact Phase22
population identity and causal outcome lineage.
