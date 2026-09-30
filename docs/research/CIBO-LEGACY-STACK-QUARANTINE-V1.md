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
