# CIBO A1 Phase22 Scientific Consumption Manifest V1

Status: **A1 READ-ONLY EVIDENCE MANIFEST / NO SCIENTIFIC PASS CLAIM**

Identity:

`CIBO_A1_PHASE22_SCIENTIFIC_CONSUMPTION_MANIFEST_V1`

## Purpose

All A1 scientific workstreams must consume one immutable Phase22 evidence
surface. This prevents different tools from silently using different candidate,
code, parameter, policy or fold populations.

The manifest binds:

- candidate id;
- exact code SHA;
- exact parameter SHA256;
- historical replay amendment SHA256;
- complete source-population SHA256;
- complete policy-population SHA256;
- exact decision/policy/outcome counts;
- observed Trader identities;
- deterministic contiguous WF1..WF4 populations.

Policy coverage must match the replay decision surface exactly.

## Causal boundary

WF1..WF4 membership is determined only from chronological decision identity.
Outcomes do not define fold membership.

The manifest rejects:

- mixed candidate ids;
- code drift;
- parameter drift;
- non-historical evidence kind;
- missing or extra policy rows;
- policy digest drift.

## Governance

This manifest performs no tuning, no result interpretation and no terminal
scientific disposition.

It grants no:

- productive authority;
- LIVE authority;
- real-capital authority;
- Master Ledger reconciliation;
- certification authority.

A1 tool-specific gates must bind their evidence to this manifest or an exactly
equivalent canonical population identity before producing terminal science.
