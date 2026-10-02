# CIBO PROTECTED BASE — STRICT FOUR-FOLD TEMPORAL REPLICATION V1

Status: **PREREGISTERED / ENGINE IMPLEMENTED / REAL EVIDENCE REQUIRED**

Identity:

`CIBO_PROTECTED_BASE_STRICT_FOUR_FOLD_TEMPORAL_REPLICATION_V1`

Protected Base already has a frozen non-compensatory numeric policy gate. This
contract adds the missing temporal-replication law.

The same frozen control and numeric treatment candidate must re-pass the
Protected Base gate independently on four distinct populations:

```text
WF1 PASS
WF2 PASS
WF3 PASS
WF4 PASS
---------
REPLICATED
```

Requirements:

- four distinct population digests;
- one unchanged provider surface;
- identical frozen control candidate in every fold;
- identical frozen treatment candidate in every fold;
- each raw observation binds exactly one canonical fold;
- each fold independently returns
  `ELIGIBLE_FOR_FURTHER_RESEARCH`;
- no pooled rescue, 3/4 rescue, weighted compensation or post-outcome winner.

A GREEN CI for this wrapper proves only that the replication law is executable.
It does not prove real Protected Base value, stress robustness, fresh OOS
success, certification or production authority.

Frozen V3 remains unchanged. The sealed 2017H1 holdout remains untouched.
