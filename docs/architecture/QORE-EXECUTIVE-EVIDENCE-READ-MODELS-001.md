# QORE-EXECUTIVE-EVIDENCE-READ-MODELS-001 — Validation, Forensics & Audit Projections

Status: **PREPARATION READY — TRANSPORT AND MOBILE ACTIVATION REMAIN CLOSED**

## Verified base

```text
main @ 7979e16d1f64a7b1ed8b9edf1620a03f02bd5b29
```

This delivery starts after the market/trader executive read models were merged and verified.

## Purpose

Complete the currently authorized non-financial operational read scopes:

```text
VALIDATION_LAB
TRADE_FORENSICS
AUDIT
```

These contracts reuse `ExecutiveProjectionMetadata` and the canonical authorized executive read
boundary. They do not create a parallel query path.

## Validation Lab projection

The internal Validation Lab retains a complete `SpecialistAnalysis` in `ValidationAssessment`.
That internal object is intentionally not exposed to Desktop/iOS/Android.

The executive surface instead projects:

- explicit assessment identity;
- opaque subject reference;
- sanitized policy-version reference;
- verdict;
- explicit observed confidence when known;
- structured reason codes;
- evidence references.

A `passed` or `failed` verdict cannot be projected without explicit observed confidence.
All assessment summaries require structured reasons and evidence.

## Trade Forensics projection

`ExecutiveTradeForensicsReadModel` represents evidence-backed forensic cases without introducing
a new trading domain object or broker dependency.

A case contains:

- explicit case identity;
- opaque trade reference;
- explicit timezone-aware opening/conclusion timestamps;
- lifecycle state;
- structured outcome code;
- structured reasons;
- supporting evidence;
- optional counter-evidence.

Supporting and counter-evidence must remain disjoint.

Lifecycle chronology is fail-closed:

```text
OPEN          -> no concluded_at
CONCLUDED     -> concluded_at required
INCONCLUSIVE  -> concluded_at required
concluded_at >= opened_at
```

The read model does not expose broker orders, account numbers, provider payloads or corrective
trading authority.

## Audit projection

`ExecutiveAuditReadModel` contains structured audit records rather than raw logs.

Each record contains:

- explicit record identity;
- timezone-aware occurrence timestamp;
- explicit correlation identity;
- canonical actor/category/action codes;
- explicit outcome;
- structured reasons;
- evidence references.

The outcome set deliberately includes:

```text
applied
rejected
no-action
observed
unknown
```

This makes `NO_ACTION` a first-class auditable result, consistent with QORE's reason-for-action
doctrine.

The audit surface contains no arbitrary payload field and no raw log field, reducing the risk of
accidental secret or internal-state exposure.

## Evidence and reason discipline

Every projected validation assessment, forensic case and audit record requires evidence and
structured reason codes.

No important executive assertion can be represented only as unstructured narrative.

Opaque evidence references preserve drill-down capability without embedding secret-bearing source
material into the executive contract itself.

## Internal-object separation

The boundary remains:

```text
Internal state / domain evidence
        ↓
explicit executive projection
        ↓
authorized ExecutiveReadQueryPort
        ↓
CEO Command Center
```

No internal `ValidationAssessment`, `SpecialistAnalysis`, domain event, log entry, broker object or
provider object is returned directly.

## Determinism

- immutable `dataclass(frozen=True, slots=True)` values;
- explicit identities only;
- timezone-aware timestamps only;
- no implicit current time;
- deterministic ordering;
- duplicate identities rejected;
- duplicate evidence rejected;
- deterministic `logical_values()`;
- canonical secret-resistant codes.

## Scope binding

Concrete models are bound exactly to:

```text
ExecutiveValidationLabReadModel  -> VALIDATION_LAB
ExecutiveTradeForensicsReadModel -> TRADE_FORENSICS
ExecutiveAuditReadModel          -> AUDIT
```

A scope mismatch fails closed.

## Safety

These are read-only contracts. They do not authorize:

- buy/sell;
- submit/cancel order;
- close position;
- Risk bypass;
- corrective trading;
- provider connectivity;
- Production accounts;
- real capital;
- mobile activation;
- Profit Vault coupling.

MISSION-03 remains active and unchanged.

## Governance scope gate

The repository still has no `ExecutiveReadScope.GOVERNANCE`. This delivery does not add one.
The Governance product surface remains gated on a separate explicit authorization/scope change.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No gate weakening or suppression is authorized.

## Next controlled boundary

After these operational scopes are merged, the next read-model family should address CEO
proprietary capital only:

```text
CAPITAL_STATE
RISK
PORTFOLIO
CEO_ACCOUNTS
```

The Corporate Profit Vault remains a separate later read surface and must not be merged into the
proprietary-capital model.
