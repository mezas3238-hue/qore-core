# QORE Shared GEN-2 — Global Market Hours, Temporal Synchronization & Relational Comparability

**Identity:** `QORE_SHARED_GEN2_TEMPORAL_COMPARABILITY_001`  
**Status:** ACTIVE / SOURCE-ONLY FOUNDATION  
**Primary PR:** #635  
**Owner law:** Directive 006  
**GEN-1 upstream:** run `36566029876`, 177 DISCOVERED / 0 ADMITTED

## Absolute law

```text
NO RELATIONAL CLAIM
WITHOUT RELATIONAL COMPARABILITY

TIME INTEGRITY
BEFORE
RELATIONAL INTELLIGENCE
```

Shared must never confuse a missing/non-comparable peer with a market that
failed to confirm.

## Clock separation

GEN-2 preserves distinct clocks when available:

- MARKET_TIME;
- VENUE_TIME;
- PROVIDER_EVENT_TIME;
- RECEIPT_TIME;
- OBSERVATION_TIME;
- PROCESSING_TIME;
- DECISION/EVALUATION_TIME.

The causal provider path must satisfy:

```text
PROVIDER_EVENT_TIME
<= RECEIPT_TIME
<= OBSERVATION_TIME
<= PROCESSING_TIME
<= EVALUATION_TIME
```

Future observations are rejected rather than paired backwards.

## Canonical market session vs provider availability

These are separate planes.

Canonical market session represents venue/economic activity using versioned
IANA/DST-aware calendars.

Provider availability represents what the data source is actually delivering.

A market may be economically active while its provider is delayed or degraded.
A provider may expose a symbol while the canonical market is closed.

Provider metadata never silently becomes canonical market truth.

## Canonical session states

- OPEN_ACTIVE
- OPEN_LOW_LIQUIDITY
- PRE_SESSION
- POST_SESSION
- SESSION_BREAK
- CLOSED
- HOLIDAY
- PARTIAL_SESSION
- HALTED
- UNKNOWN

UNKNOWN is a legal epistemic state and cannot produce a relational claim.

## Provider observability states

- HEALTHY
- DELAYED
- STALE
- PARTIAL
- DEGRADED
- UNAVAILABLE
- UNKNOWN

Provider degradation is not market behavior.

## Relational comparability states

- COMPARABLE
- PARTIALLY_COMPARABLE
- STALE_PEER
- ASYNC_MARKET
- ILLIQUID_PEER
- CLOSED_PEER
- PARTIAL_SESSION
- HOLIDAY_SESSION
- TRADING_HALT
- PROVIDER_DELAYED
- PROVIDER_DEGRADED
- TIMESTAMP_INCONSISTENT
- INSUFFICIENT

Only COMPARABLE evidence may currently materialize a strong
`GlobalMarketRelationEdge`.

## Expected update cadence

No global staleness threshold is allowed.

Cadence policies are explicit and scoped to instrument/provider/session.
They carry their own version, provenance and fingerprint.

## Governed comparability policy registry

The codebase now contains a deterministic, versioned
`RelationalComparabilityPolicyRegistry`.

The registry:

- requires canonical scope ordering;
- rejects duplicate relation scopes;
- carries provenance and a deterministic fingerprint;
- resolves policies by exact scope only;
- has no implicit global fallback.

This is infrastructure hardening only. The production GEN-2 evidence pack must
continue to report the comparability policy registry as not frozen until
canonical calendar mappings and governed scope-specific policies are actually
sealed. No relational claim is authorized by the existence of the registry
class alone.

## Source census

The first GEN-2 source census queries cTrader full symbol metadata for the
exact GEN-1 177-symbol registry and freezes:

- provider symbol/id;
- provider trading schedule intervals;
- provider schedule timezone;
- provider trading mode;
- provider holidays.

This is provider observability metadata only.

No canonical instrument mapping is inferred from a provider symbol name.
No market history, Target-V2 outcome, R6/R5 or fresh holdout is opened.

## Global observability matrix

Every GEN-1 instrument receives one deterministic row containing:

- provider identity;
- family if known;
- canonical identity if known;
- calendar mapping status;
- calendar/timezone metadata;
- provider schedule availability;
- historical/realtime availability capability;
- expected-cadence capability;
- liquidity observability;
- readiness stage;
- scientific admission state.

The maturity ladder is:

```text
DISCOVERED
→ IDENTITY_VERIFIED
→ CALENDAR_MAPPED
→ TEMPORALLY_OBSERVABLE
→ RELATIONALLY_COMPARABLE
→ SCIENTIFICALLY_ADMITTED
```

GEN-2 never promotes a sensor merely because provider schedule metadata exists.

## Anti-leakage

Required tests prove:

- future quote cannot be paired backwards;
- future provider event cannot repair earlier missing evidence;
- timestamp inversion fails closed;
- provider identity drift fails closed;
- later session state cannot contaminate an earlier evaluation;
- deterministic inputs produce deterministic fingerprints.

## Sovereignty

All GEN-2 outputs remain read-only cognition.

Shared methodology, sizing, Risk, order, execution and broker-mutation
authority remain false.

## Current closure rule

Classes alone do not close GEN-2.

Closure additionally requires real source metadata evidence, deterministic
artifact fingerprints, multi-market test matrix GREEN, DST/holiday/partial
session correctness, provider degradation distinction, anti-leakage PASS and
a governed path for canonical calendar mapping.

Until canonical mappings and comparability policies exist, relational claims
remain unauthorized.
