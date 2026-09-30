# SHARED B TEMPORAL CLOCK SUPPORT FIX 001

Run 36766204231 failed before evidence recovery because mypy analyzed
`scripts/shared_b_temporal_source_clock_audit.py` in isolation and treated the
internal `shared_b_cross_asset_source_replay` import as an installed untyped
package.

This patch does not suppress typing and does not change any temporal evidence.
It makes mypy analyze the imported source module together with the audit script:

```text
mypy shared_b_cross_asset_source_replay.py shared_b_temporal_source_clock_audit.py
```

The source module is also added to the workflow path trigger so changes to the
verification dependency re-run the clock audit.

Scientific assertions, sealed artifact IDs, clock semantics and fail-closed
behavior are unchanged.
