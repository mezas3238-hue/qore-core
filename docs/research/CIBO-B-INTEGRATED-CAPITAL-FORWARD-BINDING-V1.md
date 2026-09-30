# CIBO Architect B — Integrated Capital Forward Population Binding V1

Status: **BINDING GATE IMPLEMENTED / REAL PHASE20D POPULATION REQUIRED**

This gate closes the missing integration seam between Architect-B forward
settlement truth and the existing five-store / GEN-C capital-accounting truth.

Before Integrated Capital Truth is accepted for scientific consumption, it now
requires:

1. the Architect-B manifest account scope to equal the Compound account scope;
2. the exact set of terminal settlement SHA + signal + Trader + realized PnL
   tuples in the manifest to equal the Compound Cycle settlement population;
3. aggregate positive realized profit to reconcile;
4. the existing Source Ledger ↔ Compound admission equivalence gate to pass.

The gate does not manufacture `source_id` mappings. Those bindings must already
exist and reconcile to exact GEN-C admission lots. A mismatch remains fail-closed.

A small or synthetic fixture can prove gate mechanics, but
`ready_for_scientific_consumption=true` additionally requires the upstream
manifest itself to be scientifically ready under the frozen Phase20D thresholds.

No non-fungible capacity is added together and no LIVE/sizing/Risk/execution
authority is created.
