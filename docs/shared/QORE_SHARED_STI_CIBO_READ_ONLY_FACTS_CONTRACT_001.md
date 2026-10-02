# QORE Shared STI-13 — CIBO Read-Only Shared Facts Contract 001

## Status

**IMPLEMENTED CONTRACT / NON-PRODUCTIVE**

Binding flow:

```text
SHARED DISCOVERS / WARNS
↓
TRADER VALIDATES ITS OWN METHODOLOGY
↓
VALID_TRADE
↓
SHARED FACTS MAY BE EXPOSED READ-ONLY TO CIBO
↓
CIBO DECIDES CAPITAL
```

Shared facts cannot reach this boundary while the Trader disposition is
`WAIT` or `ABSTAIN`.

The fact object may carry:

- opportunity support;
- continuation support;
- failure hazard;
- positive-tail support;
- relationship stability;
- regime-transition state;
- systemic stress;
- uncertainty;
- causal maturity;
- provenance.

It cannot carry:

- sizing authority;
- allocation authority;
- reserve authority;
- release authority;
- compounding authority;
- Risk authority;
- execution authority.

Absolute law:

```text
SHARED INFORMS.
CIBO DECIDES CAPITAL.
```

Even maximally supportive Shared evidence cannot compel CIBO to deploy capital.
The contract explicitly preserves CIBO's ability to abstain or allocate zero.

This contract does not certify the economic usefulness of Shared facts to CIBO
and does not modify CIBO runtime behavior.
