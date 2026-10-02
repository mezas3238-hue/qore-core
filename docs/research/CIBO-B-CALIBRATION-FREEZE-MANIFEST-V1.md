# CIBO Architect B — Calibration Freeze Manifest V1

Status: **DYNAMIC PRE-HOLDOUT BRIDGE IMPLEMENTED / NOT SEALED FOR REAL EXAM**

The historical T01..T20 calibration matrix remains immutable provenance. It is
not rewritten when later forward evidence closes a calibration.

This bridge adds the terminal integration artifact required after Architect A and
Architect B finish their evidence programs.

A valid manifest requires exactly T01..T20 in canonical order. Every active tool
must be OOS-ready and certification-ready. T16/T17 are the only tools allowed to
be structurally disabled, and even that state requires explicit provider-economics
binding rather than an assumption.

The manifest binds by SHA:

- the scientifically-consumable Phase20D forward economic manifest;
- the provider-economics component freeze;
- per-tool terminal evidence references.

The pre-holdout gate now has two modes:

1. **historical mode** — no terminal manifest exists, so the original calibration
   matrix blockers remain exactly as before;
2. **terminal mode** — a sealed calibration manifest supersedes those historical
   blockers for readiness evaluation, but only if its Phase20D SHA and provider
   freeze SHA match exactly.

The terminal mode still requires the Phase20D causal gate and Phase21 policy freeze.
It never reads holdout market data or outcomes and does not mutate
`ACTIVE_PRE_HOLDOUT_FREEZE`.

A unit-test fixture may prove that the gate mechanics can reach
`READY_TO_UNSEAL_2017H1`; that fixture is not an authorization to open 2017H1.
The real holdout remains `SEALED_UNTOUCHED` until the governed production-quality
freeze artifact exists and every prerequisite passes.
