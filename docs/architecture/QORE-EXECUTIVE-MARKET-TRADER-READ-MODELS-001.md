# QORE-EXECUTIVE-MARKET-TRADER-READ-MODELS-001 — Market & Trader Executive Projections

Status: **PREPARATION READY — TRANSPORT AND MOBILE ACTIVATION REMAIN CLOSED**

## Verified base

```text
main @ 6521b62308b9c596cc7dcdb461c40457557ed9ed
```

This delivery starts only after `QORE-EXECUTIVE-READ-MODELS-001` was merged and verified on
`main`.

## Purpose

Define two additional executive projections already authorized by the canonical
`ExecutiveReadScope` allowlist:

```text
MARKETS
TRADERS
```

The contracts extend the projection provenance established by
`QORE-EXECUTIVE-READ-MODELS-001`. They do not create a second query port or bypass executive
authorization.

## Canonical path

```text
internal market/trader state
        ↓
projection adapter
        ↓
ExecutiveMarketsReadModel / ExecutiveTradersReadModel
        ↓
authorized ExecutiveReadQueryPort boundary
        ↓
CEO Command Center
```

The projection adapter is a future implementation boundary. This delivery defines contracts only.

## MARKETS projection

`ExecutiveMarketsReadModel` exposes an ordered set of `ExecutiveMarketSummary` values.

Each market summary contains only executive-safe, provider-neutral information:

- canonical instrument;
- extensible asset-class code;
- availability state;
- authorization state;
- regime code;
- session code;
- structured reason codes;
- evidence references.

### Open market universe

Asset class is deliberately an extensible validated value rather than a closed Forex enum.

The model can therefore represent future classes such as:

```text
forex
indices
futures
crypto
metals
commodities
synthetics
```

without adding provider branching to Core or changing the executive contract merely because a new
provider supports another class.

### Provider independence

The read model contains no:

- OANDA object;
- MT4/MT5 object;
- exchange session;
- broker account;
- provider credential;
- provider-native instrument object.

A future projection adapter may translate internal/provider-certified state into this model, but
the model itself remains platform-free.

## TRADERS projection

`ExecutiveTradersReadModel` exposes an ordered set of `ExecutiveTraderSummary` values.

Each trader summary may expose:

- stable executive trader identifier;
- extensible trader-kind code;
- sanitized strategy-version reference;
- lifecycle/operating state;
- authorization state;
- explicit finite confidence projection when available;
- structured judgment code;
- authorized/associated market instruments;
- structured reason codes;
- evidence references.

The lifecycle states support the Command Center architecture:

```text
eligible
operating
restricted
training
suspended
unknown
```

The authorization state is kept separate from lifecycle state so a trader may be structurally
eligible while governance or risk still restricts its authority.

## Internal-object separation

Current internal Virtual Trader contracts produce `SpecialistAnalysis` values. Those domain objects
are not returned to the CEO Command Center.

Likewise, canonical infrastructure market data uses internal `Instrument`, quote and OHLC snapshot
contracts. Those objects are not returned directly either.

The required shape remains:

```text
internal object
    ↓
explicit executive projection
    ↓
stable authorized read surface
```

This prevents Desktop/iOS/Android from coupling to internal event, specialist, provider or runtime
object layouts.

## Evidence requirement

Every individual market and trader summary requires non-empty, sanitized
`ExecutiveEvidenceRef` values and non-empty structured reason codes.

Important executive state therefore cannot silently appear as unsupported narrative.

The common `ExecutiveProjectionMetadata` still supplies projection-level evidence, source
freshness, timestamps and projection version.

## Determinism

The contracts preserve deterministic behavior:

- market summaries are ordered by canonical instrument;
- trader summaries are ordered by executive trader id;
- associated market instruments are ordered by symbol;
- reason codes and evidence refs are sorted;
- duplicates are rejected;
- all value contracts are immutable `dataclass(frozen=True, slots=True)` values;
- `logical_values()` contains only explicit deterministic values.

No implicit UUID or current time is generated.

## Confidence

`ExecutiveTraderConfidence` is a public projection value, not the internal
`SpecialistConfidence` object.

It requires an explicit finite `float` in the closed interval `[0.0, 1.0]`.

Absence of confidence is represented explicitly by `None`; it is never fabricated.

## Strategy boundary

A trader projection may expose only a sanitized strategy version reference.

It does not expose:

- strategy implementation;
- strategy parameters;
- entry/exit code;
- risk settings;
- credentials;
- hidden prompts;
- chain-of-thought.

This preserves both implementation encapsulation and governance.

## Capital preservation

A market or trader being `available`, `eligible`, or `operating` is descriptive executive state.
It does not grant execution authority and does not bypass CIBO, Portfolio, Risk or Capital
Protection.

No read model can generate an order.

## Governance scope gate remains unchanged

This delivery uses only existing scopes:

```text
ExecutiveReadScope.MARKETS
ExecutiveReadScope.TRADERS
```

It does not introduce `ExecutiveReadScope.GOVERNANCE`. The Governance product surface remains
gated on a separate explicit allowlist/authorization change.

## No runtime activation

This delivery introduces no:

- HTTP/WebSocket/gRPC;
- mobile backend;
- database;
- provider connection;
- broker connection;
- retries or polling;
- scheduler/thread;
- Production account;
- real capital;
- order submission/cancellation;
- Client Profit Vault coupling.

MISSION-03 remains active and unchanged.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or gate weakening is authorized.

## Next controlled boundary

After this delivery, the remaining operational read scopes already present in the canonical
allowlist are:

```text
VALIDATION_LAB
TRADE_FORENSICS
AUDIT
```

They should be introduced as a separate narrow and auditable delivery before proprietary capital
or isolated Corporate Profit Vault projections are composed into the future Command Center.
