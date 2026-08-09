# QORE-FUTURES-CROSS-PROVIDER-CERTIFICATION-001 — Three-Provider Cross-Certification

## Status

**NON-PRODUCTION CROSS-PROVIDER EVIDENCE — PRODUCTION CLOSED**

This delivery implements Delivery 12 of the Futures & Hosting Reliability Certification Program.

It compares certification evidence from the three mandatory Futures providers already implemented:

```text
TradeStation
IBKR
tastytrade
```

The comparison is evidence-only. It does not select, activate, switch or mutate any provider.

## Minimum-three requirement

Cross-certification requires unique evidence for all three mandatory providers.

Two-provider evidence is insufficient and fails validation.

This enforces the program requirement:

```text
MINIMUM 3 INDEPENDENT BROKER/API PROVIDERS
```

## Provider evidence

`FuturesProviderCertificationEvidence` binds one provider to one exact canonical OHLC interval and preserves:

- provider identity;
- canonical `OhlcSnapshot`;
- Market Data certification status;
- PAPER/SIM execution certification status;
- execution reconciliation status;
- measured ingress latency;
- observation timestamp;
- immutable evidence references.

## Market Data status

The cross-provider layer distinguishes:

```text
CERTIFIED_REALTIME
CERTIFIED_DELAYED
NOT_CERTIFIED
UNKNOWN
```

This is necessary because the three certification environments are not equivalent.

Current deterministic evidence includes a deliberate asymmetry:

- TradeStation may provide realtime-certifiable market-data evidence when proven;
- IBKR may provide realtime or delayed evidence depending on entitlements/session state;
- tastytrade sandbox is currently documented as delayed and therefore represented as `CERTIFIED_DELAYED`, not realtime.

Cross-certification does not erase that difference.

## Execution status

Initial execution certification remains strictly:

```text
CERTIFIED_PAPER_SIMULATION
```

or:

```text
NOT_CERTIFIED
UNKNOWN
```

No Production execution status exists in this delivery.

Every provider must also have execution reconciliation:

```text
MATCHED
```

before cross-provider certification can succeed.

Ambiguous/diverged execution evidence blocks rather than triggering redispatch.

## Same canonical interval

OHLC values are compared only when every provider record has the same:

- canonical instrument;
- timeframe;
- opened timestamp;
- closed timestamp.

Different source descriptors are expected because each provider has its own adapter/source identity.

A scope mismatch blocks before value comparison.

## OHLC comparison

The policy defines a positive maximum OHLC spread in basis points.

For each OHLC component the comparison calculates:

```text
(max provider value - min provider value)
/ min provider value
* 10,000
```

The resulting evidence preserves independent spread values for:

- open;
- high;
- low;
- close.

If the maximum component spread exceeds policy, the result is:

```text
DISAGREEMENT
OHLC_DISAGREEMENT
```

This is evidence of provider disagreement. It is not automatic permission to switch feeds.

## Delay-aware certification

When all three providers are certified for their declared modes, execution is certified/reconciled, and OHLC values are aligned, the state depends on timing class.

If all three are explicitly realtime and realtime ingress is within policy:

```text
CERTIFIED
THREE_PROVIDER_REALTIME_ALIGNED
```

If one or more providers are certified delayed:

```text
DELAY_AWARE_CERTIFIED
ALIGNED_WITH_DELAYED_PROVIDER
```

The second state is intentionally **not** represented as three-provider realtime certification.

This preserves the current tastytrade sandbox limitation rather than pretending a delayed sandbox feed is comparable to realtime operational evidence.

## Realtime ingress ceiling

`FuturesCrossProviderPolicy` includes a realtime ingress-latency ceiling.

It applies only to provider evidence declared `CERTIFIED_REALTIME`.

A delayed provider's expected delivery lag is not compared to the realtime ingress ceiling because doing so would conflate:

```text
PROVIDER DATA DELAY
```

with:

```text
NETWORK/HOSTING INGRESS LATENCY
```

A realtime provider outside the certified ingress ceiling blocks cross-certification.

## Delay does not become normal realtime

The current tastytrade sandbox delay may still participate in historical interval agreement evidence, but:

```text
DELAY_AWARE_CERTIFIED
 != THREE_PROVIDER_REALTIME_CERTIFIED
```

Future authenticated/read-only evidence may establish different provider modes, but that must be proven explicitly rather than inferred.

## Provider disagreement does not authorize provider switching

`FuturesCrossProviderAssessment.provider_switch_authorized` is always false.

The module exposes no method to:

- select a provider;
- switch feeds;
- route an order;
- retry/redispatch an order;
- activate an adapter;
- create a Core Decision.

The redundancy domains remain separate:

```text
SERVER REDUNDANCY
 != MARKET-DATA PROVIDER REDUNDANCY
 != EXECUTION-PROVIDER PORTABILITY
```

A future feed-switch policy would require its own repository-authorized evidence and action boundary.

## Blocking conditions

Cross-provider assessment blocks for:

```text
MISSING MANDATORY PROVIDER
OHLC SCOPE MISMATCH
UNCERTIFIED MARKET DATA
UNCERTIFIED PAPER/SIM EXECUTION
AMBIGUOUS/DIVERGED EXECUTION RECONCILIATION
REALTIME INGRESS OUTSIDE POLICY
```

Material aligned-scope price disagreement becomes `DISAGREEMENT`, not `BLOCKED`, so the reason remains explicit.

## Trading authority

Nothing in cross-provider evidence creates strategic authority.

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

A provider that appears healthier or better aligned does not gain order authority from this certificate.

## Operational evidence boundary

This delivery uses deterministic/offline certification evidence.

It does not claim that all three providers were simultaneously connected in authenticated realtime sessions.

That operational proof belongs to later Shadow/Drill/Paper E2E gates and must use real sanitized evidence when external access exists.

## Files

```text
src/qore/infrastructure/futures_cross_provider_certification.py
tests/infrastructure/test_futures_cross_provider_certification.py
docs/architecture/QORE-FUTURES-CROSS-PROVIDER-CERTIFICATION-001.md
```

## Quality Gate

The exact PR head must pass:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Production remains CLOSED.
