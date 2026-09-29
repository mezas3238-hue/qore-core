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

## Canonical calendar mapping admission

Provider schedule metadata is supporting evidence only. It is never sufficient
to promote a provider instrument into a canonical venue/calendar binding.

A mapping may become `VERIFIED` only with explicit, independently provenance-bound
evidence for all three planes:

- canonical instrument identity;
- trading venue;
- canonical versioned market calendar.

`UNRESOLVED`, `AMBIGUOUS` and `REJECTED` mappings cannot create
`MarketCalendarBinding` objects. The mapping registry is deterministic,
provider-aware and exact-keyed.

Current source-census status remains:

```text
MAPPING GOVERNANCE = IMPLEMENTED_NOT_POPULATED
VERIFIED MAPPINGS  = 0
MAPPING COMPLETE   = FALSE
```

This is deliberate. GEN-2 must not manufacture canonical truth from provider
symbol names or provider schedules.

## Governed cadence, liquidity and temporal-skew policy layers

No global staleness, liquidity or temporal-skew fallback is allowed.

The codebase contains deterministic exact-scope registries for:

- expected update cadence by instrument/provider/session;
- temporal skew by relation kind, source family, target family, horizon,
  session scope and liquidity scope;
- relational comparability policy by explicit relation scope.

Liquidity interpretation is separately policy-bound. Provider degradation,
unavailability, staleness or unknown observability forces liquidity to
`UNKNOWN`; it cannot be relabeled as market illiquidity.

These policy architectures are implemented but not frozen. Their existence does
not authorize relational claims.

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

## Machine-readable closure gate

GEN-2 now exposes a deterministic temporal-governance closure assessment.

The closure assessment is intentionally stricter than workflow success. It
requires, at minimum:

- a non-empty sensor universe;
- canonical mapping coverage equal to the governed sensor universe;
- a non-empty canonical calendar registry;
- calendar binding coverage equal to the governed sensor universe;
- cadence policy registry frozen;
- liquidity policy registry frozen;
- temporal-skew policy registry frozen;
- comparability policy registry frozen;
- anti-leakage PASS;
- deterministic validation PASS.

Any unmet condition is emitted as a canonical blocker code and the result is
`NOT_READY`.

A `READY` temporal-governance result still does **not** authorize relational
claims. GEN-2 establishes legal temporal comparability prerequisites; GEN-3+
must separately establish and validate relation science.

## Current closure rule

Classes alone do not close GEN-2.

Closure additionally requires real source metadata evidence, deterministic
artifact fingerprints, multi-market test matrix GREEN, DST/holiday/partial
session correctness, provider degradation distinction, anti-leakage PASS and
a governed path for canonical calendar mapping.

Until canonical mappings and comparability policies exist, relational claims
remain unauthorized.
