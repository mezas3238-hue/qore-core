# CIBO Legacy Cognitive / Executive Stack — Quarantine V1

Status: **RESEARCH QUARANTINE / NO PRODUCTIVE AUTHORITY**

The historical CIBO cognitive/executive stack is not deleted because it
contains reusable research infrastructure and tests.

It is also not part of the productive capital-authority chain.

A machine-readable AST import audit now enforces:

- legacy modules may import other legacy modules;
- tests may exercise legacy modules;
- the only allowed current-generation `src/qore` consumer is GEN-C13's reuse
  of `cibo_executive_memory`;
- any other current/runtime import of a legacy module fails the quarantine
  gate.

The retained memory substrate does not grant sizing, Risk, Execution, LIVE or
real-capital authority.

This workstream may close only when the machine audit reports zero forbidden
external import edges.


## Scope correction — Architect B

The quarantine follows the original `QORE-CIBO-COGNITIVE-EXECUTIVE-001`
architecture. It covers the historical cognitive/executive and reasoning
modules (`cibo_cognitive_*`, `cibo_executive_*`, legacy reasoning runtimes and
OpenAI reasoning adapters). It does **not** classify Trader capability/profile,
Trader development, Trader Lab, operational supervision, or the later
`src/qore/infrastructure/cibo/**` functional system as legacy merely because
they share the CIBO name. Those surfaces were outside the bounded #482
cognitive foundation and have independent authority boundaries.

This correction narrows an over-broad audit classification; it does not grant
productive authority to any cognitive/executive component. GEN-C13 remains the
only approved current-generation consumer of the retained
`cibo_executive_memory` substrate.
