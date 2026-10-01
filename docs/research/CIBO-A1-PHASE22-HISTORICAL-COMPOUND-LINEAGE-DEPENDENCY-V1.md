# CIBO A1 Phase22 Historical Compound Lineage Dependency V1

Status: **A1 CROSS-BOUNDARY CONSUMER CONTRACT / A2-OWNED IMPLEMENTATION**

Identity:

`CIBO_A1_PHASE22_HISTORICAL_COMPOUND_LINEAGE_DEPENDENCY_V1`

## Problem

The active Phase22 V2 examination is a historical replay.

Its settlement law correctly forbids invented historical broker:

- order ids;
- deal ids;
- position ids.

The legacy Compound realized-profit identity requires positive broker position
and deal identifiers. Those requirements cannot be satisfied truthfully for a
2015–2016 replay by manufacturing identifiers or relabeling current DEMO fills.

## Ownership

`COMPOUND_ENGINE` belongs to Architect A2.

Architect A1 does **not** modify or close that workstream.

A1 only freezes the receipt it needs in order for GEN-C2→GEN-C7 to consume a
historical Compound lineage.

## Required A2/Integrator receipt

The receipt must prove:

- exact A1 Phase22 manifest binding;
- exact Phase22 source-population binding;
- versioned historical replay Compound adapter identity;
- historical replay supported without broker IDs;
- no broker IDs emitted or required for historical events;
- no current DEMO IDs relabelled as historical;
- no fabricated execution identifiers;
- realized profit only;
- floating PnL never treated as capital;
- capital conservation;
- no double spend;
- decision-before-outcome chronology;
- deterministic replay;
- no productive/LIVE/real-capital authority.

## Consequence

Until this receipt exists, A1 must not pretend that GEN-C2→GEN-C7 Compound
lineage is scientifically consumable on V2.

This is an explicit cross-boundary dependency, not permission for A1 to
duplicate A2.
