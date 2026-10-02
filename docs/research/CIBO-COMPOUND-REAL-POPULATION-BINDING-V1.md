# CIBO Compound Real Population Binding V1

Status: **IMPLEMENTED / CI GATE PENDING / REAL POPULATION NOT YET CLAIMED**

Identity:
`CIBO_COMPOUND_REAL_POPULATION_BINDING_V1`

Architect:
A — Capital Science / Economic Closure

## Purpose

Provide the narrow fail-closed bridge between immutable provider/Risk/CMA/
forward evidence delivered by Architect B and the existing Architect A
scientific engines:

```text
B FORWARD EVIDENCE MANIFEST
        |
        v
STRICT REAL-POPULATION BINDING
        |
        +--> CompoundMonteCarloEpisode
        +--> GEN-C9 path population
        +--> adversarial stress
        +--> temporal replication
```

This is a binding contract, not a new allocator and not a collector.

## Frozen lineage

Every accepted record must bind exactly to:

```text
candidate_id = CIBO_PHASE20_FULL_SURFACE_FORWARD_CANDIDATE_V3
code_sha     = edf96722fd0505711aa88bc1d15296b09e6dba6f
```

The decision must occur on or after the frozen-candidate timestamp. No
pre-freeze observation can be relabelled.

## Evidence accepted

Only:

`FORWARD_OBSERVED`

The following are rejected from this certification binding:

- SYNTHETIC_CONTRACT
- BURNED_RESEARCH
- SEALED_HOLDOUT

The 2017H1 holdout is not read by this adapter.

## Required immutable lineage

A record must carry:

- decision evidence SHA-256;
- provider-economics SHA-256;
- Risk lineage SHA-256;
- CMA lineage SHA-256;
- terminal-settlement SHA-256;
- capital-release evidence SHA-256;
- source-manifest SHA-256;
- account identity fingerprint;
- decision/deployment/settlement timestamps;
- Trader/signal/candidate/deployment identities;
- provider-valid USD capital, stop-risk and margin;
- terminal realized PnL;
- floor-graduation evidence when non-zero.

Missing material evidence fails closed. It is never reconstructed.

## Temporal law

All four canonical Phase20D qualification folds must be represented:

- WF1
- WF2
- WF3
- WF4

Folds may not overlap or interleave. IDs for episode, deployment, market event
and decision must be unique.

This does not replace the full Phase20D population thresholds. Architect B
remains responsible for proving the complete candidate/selected/baseline
coverage and frozen thresholds. This binding operates on the settled Compound
episode surface supplied after that evidence exists.

## Output

Accepted records are transformed only into the canonical:

`CompoundMonteCarloEpisode`

No missing value is imputed and no policy decision is changed.

## Non-claims

Implementation of this adapter does not mean:

- a real qualifying population already exists;
- Phase20D has passed;
- economic value has been demonstrated;
- fresh OOS has passed;
- stress has passed;
- temporal replication has passed;
- CIBO is certified.

Until Architect B supplies real qualifying evidence, the scientific workstreams
remain open.
