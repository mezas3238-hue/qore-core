# MISSION-05 — QORE Mobile & CEO Command Center

Status: **OPEN — NON-PRODUCTION IMPLEMENTATION AUTHORIZED; PRODUCTION CLOSED**

Opening baseline:

```text
main @ 982e68cef28531d8fdba079183f329d49b856f31
```

MISSION-04 — QORE Control Plane & Executive Governance is complete in its provider-independent/offline scope.

MISSION-03 issue `#146 — MISSION-03 Gate #5 — OANDA Practice operational evidence blocker` remains **OPEN / BLOCKED**. MISSION-05 does not close, bypass, replace, or reinterpret any MISSION-03 operational gate.

Production remains **CLOSED**.

## Purpose

MISSION-05 converts the already-defined CEO Command Center architecture and the completed MISSION-04 Executive Control Plane into an implementable, platform-adapted executive product boundary for:

```text
QORE CEO COMMAND CENTER
        │
        ├── Desktop / PC
        ├── iOS
        └── Android
```

The three presentation surfaces must consume the same authorized executive state and the same governance authority model.

MISSION-05 may implement non-production transport adapters, client-safe contracts, state synchronization, CIBO dialogue, notifications, widget/view-state composition and deterministic reference clients. It must not create a second source of governance truth, a direct route to Core, or a trading execution surface.

## Existing foundation

MISSION-05 consumes, rather than replaces, the architecture and contracts already merged on `main`, including:

- `QORE-CEO-COMMAND-CENTER-ARCH-001` — target CEO Command Center and CIBO Widget architecture;
- MISSION-04 authenticated-principal contracts;
- current executive authority and revocation-state contracts;
- unified executive request guard;
- authorized command and query dispatch;
- governance state compare-and-swap mutation boundary;
- durable executive audit/evidence boundary;
- replay/idempotency protection;
- transport-neutral executive request/response envelopes;
- control-plane observability and resilience policies;
- deterministic offline MISSION-04 end-to-end composition;
- stable executive read models already present for system, CIBO, markets, traders, validation, forensics, portfolio, risk, capital, CEO accounts, governance, audit and Corporate Profit Vault presentation.

No MISSION-05 delivery may create duplicate authority, replay, audit or transport-envelope models when an existing MISSION-04 contract can be composed.

## Architectural invariant

The only permitted executive presentation path is:

```text
CEO Desktop / iOS / Android
            │
            ▼
External Device / Session / Authentication Boundary
            │
            ▼
Client Transport Adapter / Executive Gateway
            │
            ▼
MISSION-04 Executive Control Plane
            │
            ├── authenticated principal
            ├── current authority
            ├── authorization
            ├── replay/idempotency
            ├── query/command dispatch
            ├── audit/evidence
            ├── observability
            └── resilience policy
                    │
                    ▼
             governed QORE surfaces
```

The following paths remain prohibited:

```text
CEO App ─────────────► Core internals
CEO App ─────────────► CoreApplication direct call
CEO App ─────────────► broker/provider
CEO App ─────────────► execution gateway
CEO App ─────────────► credential/secret store
CEO App ─────────────► order submit/cancel
CEO App ─────────────► Risk bypass
CEO App ─────────────► Portfolio bypass
CEO App ─────────────► Capital Protection bypass
CEO App ─────────────► forced buy/sell
```

Presentation is not authority. A device is not authority. A notification is not authority. A conversation is not authority.

## Core identity protection

MISSION-05 must preserve the identity and semantics of the existing Core runtime. In particular, presentation composition must not redefine or wrap as client-owned state:

- `EventBus`;
- `RuntimePlan`;
- `RuntimeSnapshot`;
- `RuntimeHealth`.

The Command Center consumes controlled projections. It does not become part of the Core object graph.

Platform-specific code must remain outside the Core domain boundary. No native UI framework dependency may be introduced into `src/qore` merely to support a presentation client.

## Authority doctrine

Executive authority remains governance authority, not trading authority.

The CEO may use explicitly authorized Control Plane commands to reduce operational authority, pause, stop or restrict governed scopes where existing policy allows it.

The Command Center must never expose an equivalent of:

```text
FORCE_BUY
FORCE_SELL
FORCE_ORDER
BYPASS_RISK
BYPASS_PORTFOLIO
BYPASS_CAPITAL_PROTECTION
```

A rejected or blocked trading decision cannot be transformed into execution by Desktop, iOS, Android, CIBO dialogue, notifications or the CIBO Widget.

## State and synchronization doctrine

The canonical authorized state remains server/control-plane side.

Clients may retain ephemeral local presentation state, but local cache is never a governance source-of-truth.

Every client-facing state projection that can become stale must distinguish at least:

```text
CURRENT
STALE
UNAVAILABLE
UNKNOWN
```

A sensitive command must fail closed when required authority, precondition or current-state evidence is stale, unavailable, unknown or contradictory.

Clients must not silently convert a stale view into an assumed-current precondition.

## Security doctrine

MISSION-05 must not place raw authentication or provider credentials in domain/read-model values, application logs, audit evidence, telemetry, UI debug payloads or deterministic logical representations.

Forbidden material includes:

- passwords;
- bearer tokens;
- access/refresh tokens;
- API keys;
- private keys;
- biometric material;
- broker/provider credentials;
- authorization headers;
- raw secure-storage contents.

Device authentication, biometrics, hardware-backed keys and platform secure storage remain external secret-aware mechanisms. QORE contracts may consume only safe assertions, opaque references, fingerprints, explicit timestamps and sanitized provenance.

No client-side secret possession grants trading authority.

## Client request model

MISSION-05 presentation traffic must preserve the semantic separation already required by the Command Center architecture:

```text
QUERY
COMMAND
SUBSCRIPTION
EVIDENCE_REQUEST
```

A `QUERY` does not mutate state.

An `EVIDENCE_REQUEST` does not mutate state.

A `SUBSCRIPTION` grants no command authority.

A `COMMAND` must pass the MISSION-04 authenticated-principal, current-authority, request-guard, replay/idempotency, dispatch and audit chain before any governed mutation occurs.

## CIBO doctrine

The CIBO CEO Widget is an evidence-backed executive interaction surface, not an autonomous authority channel.

CIBO may communicate bidirectionally with the CEO using structured responses, notifications and evidence references. Narrative output must be grounded in structured reasons/evidence and must not expose private chain-of-thought.

Conceptual presentation states may include:

```text
CONFIDENT
CAUTIOUS
UNCERTAIN
CONCERNED
CRITICAL
```

These are explainable executive presentation states derived from evidence, not causal emotions and not policy overrides.

## Notification doctrine

MISSION-05 must define deterministic interruption semantics for the conceptual levels already established by architecture:

```text
INFORMATION
ATTENTION
IMPORTANT
DECISION_REQUIRED
CRITICAL
```

Notifications may inform, request attention or navigate to an authorized surface. A notification must never itself execute a governance command or trading action.

A notification must identify its origin domain and must not gain authority merely because it is marked critical.

## Product scope

Within the CEO Command Center, MISSION-05 may implement presentation/composition for the already-defined executive domains, including:

- Home / Executive Overview;
- CIBO;
- Markets;
- Traders;
- Validation Lab;
- Trade Forensics;
- Portfolio;
- CEO Accounts;
- Risk / Capital Protection;
- News;
- Audit;
- System;
- Governance;
- Corporate / Client Profit Vault view.

The Corporate Profit Vault may be presented only through its isolated authorized read model. MISSION-05 does not couple the Profit Vault to Core and does not implement its settlement engine, billing or payment processing.

## Explicitly out of scope

MISSION-05 does **not** authorize or implement:

- MISSION-03 OANDA Practice evidence;
- MISSION-03 Gate #5 or downstream operational gate closure;
- Production trading;
- productive broker/provider credentials;
- real capital activation;
- autonomous real-money execution;
- direct CEO order entry;
- forced-trade override;
- public Production deployment;
- Profit Vault settlement engine;
- client billing or payment processing;
- client identity storage inside Core;
- client EA implementation;
- client widget implementation;
- arbitrary client EA configuration;
- MISSION-06 Production Trading Readiness;
- separate Production authorization.

The future Client EA and Client Widget remain a separate product/deliverable family even if they later reuse safe read models or infrastructure. They must not be implemented inside QORE Core merely because the CEO Command Center exists.

## Repository boundary

MISSION-05 must preserve repository/domain separation deliberately.

Rules:

- `src/qore` remains QORE domain/control-plane code and must not import Android, iOS, browser or desktop UI frameworks;
- platform adapters or reference client code, if added to this repository, must live outside the Core package and depend inward only through stable client-safe contracts;
- no platform presentation module becomes a dependency of Core;
- no platform-specific type becomes a canonical QORE domain identity;
- a future repository split for native applications may be introduced only by an explicit delivery and must preserve this repository as the architecture/contract source-of-truth until governance says otherwise.

## Official MISSION-05 delivery sequence

```text
1.  QORE-MISSION05-DOCS-001
    Mission scope, boundaries, repository rules, sequence and closure criteria

2.  QORE-MISSION05-SURFACE-BOUNDARY-001
    Client/repository dependency boundary and platform-neutral presentation contracts

3.  QORE-EXECUTIVE-CLIENT-SESSION-001
    Device/session/authentication-consumption boundary above MISSION-04 principal assertions

4.  QORE-EXECUTIVE-CLIENT-GATEWAY-001
    Non-production external transport adapter mapping to existing MISSION-04 envelopes

5.  QORE-EXECUTIVE-STATE-SYNC-001
    Snapshot/subscription/version/freshness and CURRENT/STALE/UNAVAILABLE/UNKNOWN semantics

6.  QORE-EXECUTIVE-NOTIFICATIONS-001
    Deterministic interruption and notification policy contracts

7.  QORE-CIBO-EXECUTIVE-DIALOGUE-001
    Evidence-backed CEO/CIBO dialogue and explanation contracts

8.  QORE-CIBO-WIDGET-001
    Cross-platform CIBO CEO Widget state, events and safe navigation contracts

9.  QORE-CEO-COMMAND-CENTER-VIEW-MODEL-001
    Platform-neutral executive overview/navigation/view-state composition

10. QORE-CEO-GOVERNANCE-UX-001
    Safe presentation semantics for allowed pause/stop/restrict governance controls

11. QORE-CEO-DESKTOP-001
    Desktop reference client composition using only approved client boundaries

12. QORE-CEO-IOS-001
    iOS reference client composition using the same logical state and authority model

13. QORE-CEO-ANDROID-001
    Android reference client composition using the same logical state and authority model

14. QORE-MOBILE-SECURITY-RESILIENCE-001
    Session expiry, offline/stale containment, secure-secret boundary and no-auto-redispatch policies

15. QORE-MISSION05-E2E-OFFLINE-001
    Deterministic cross-surface end-to-end validation against the MISSION-04 Control Plane

16. QORE-MISSION05-CLOSURE-001
    Security/readiness review and mission closure without Production activation
```

This order may change only through an explicit architecture change merged to the repository.

## Delivery 2 — surface/repository boundary

Before native or desktop product code is added, MISSION-05 must define exactly which contracts are platform-neutral, where presentation code may live and which dependency directions are forbidden.

The delivery must prove that Core does not depend on any presentation surface.

## Delivery 3 — client session boundary

The client-session boundary must consume externally validated authentication/session state without storing secret-bearing credentials in QORE contracts.

It must bind safe device/session provenance to the authenticated principal assertion without treating a device identifier, biometric result string or local session cache as authority.

Expired, revoked, mismatched or ambiguous sessions fail closed.

## Delivery 4 — client gateway

The gateway is an adapter around the existing MISSION-04 transport-neutral envelope. It must not create a second authorization engine.

It may support deterministic non-production transport mapping required by Desktop/iOS/Android reference clients, but public Production exposure remains closed.

Unknown routes, unsupported message kinds, malformed envelopes and secret-bearing payloads fail closed.

## Delivery 5 — state synchronization

State synchronization must preserve explicit projection version, observation time/freshness and source provenance.

Clients must be able to distinguish current state from stale/unavailable state without guessing.

No subscription delivery becomes authority for a command; commands must still re-enter the current MISSION-04 authorization chain.

## Delivery 6 — notifications

Notification contracts must bind origin domain, level, safe subject/reference, observed timestamp, evidence references where applicable and deterministic ordering.

Critical notifications may demand attention but cannot auto-dispatch commands.

## Delivery 7 — CIBO executive dialogue

Dialogue contracts must support evidence-backed structured answers, uncertainty, reasons, evidence references and authorized navigation targets.

They must not persist or expose private chain-of-thought, secret material or implicit trading authority.

## Delivery 8 — CIBO Widget

The CIBO Widget must expose a common logical state across Desktop/iOS/Android and may support conceptual modes such as collapsed, ambient, attention, expanded, full conversation, evidence review and critical interruption.

Widget interaction may create authorized queries or command intents, but the widget itself never bypasses Control Plane authorization.

## Delivery 9 — Command Center view model

The Command Center view model composes stable executive read models into presentation-safe navigation/state without exposing internal object graphs.

CEO proprietary performance and Corporate Profit Vault views remain economically and technically separated.

## Delivery 10 — governance UX

Governance UX must make destructive/protective state changes explicit and reconstructible.

Allowed controls remain limited to already-governed authority such as pause, stop, restriction and authority reduction.

The UX must surface pending/current/result state safely and must not imply success before a deterministic Control Plane receipt exists.

No automatic repeat is allowed after an ambiguous command outcome.

## Deliveries 11–13 — platform reference clients

Desktop, iOS and Android must represent the same logical authorized state and authority semantics.

Platform adaptation may change layout, interaction modality, navigation density and secure-storage implementation, but not:

- authorization semantics;
- allowed governance commands;
- audit requirements;
- replay protection;
- stale-state behavior;
- evidence requirements;
- trading restrictions.

No platform receives more trading authority than another.

## Delivery 14 — mobile security and resilience

The security/resilience layer must cover at least:

- expired/revoked authentication;
- device/session mismatch;
- gateway unavailable;
- Control Plane unavailable;
- stale cached state;
- subscription interruption;
- notification duplication;
- command timeout;
- ambiguous downstream command outcome;
- audit acknowledgement failure;
- app restart/reconnect;
- secure-secret boundary failures.

Sensitive ambiguity fails closed.

No hidden retry, sleep, polling loop, scheduler or automatic command redispatch may be introduced into governance semantics.

## Delivery 15 — deterministic offline E2E

The E2E harness must prove with deterministic fakes/reference adapters that:

- unauthenticated client request never reaches command/query dispatch;
- expired/revoked/mismatched session fails closed;
- valid query returns only a structured executive delivery;
- stale state is visibly stale and cannot be silently promoted to current;
- valid subscription updates presentation state without granting command authority;
- exact duplicate command remains protected by MISSION-04 replay/idempotency semantics;
- modified replay fails closed;
- valid governance command reaches exactly one permitted downstream mutation;
- ambiguous command outcome is contained without automatic redispatch;
- notifications cannot execute commands by themselves;
- CIBO dialogue is evidence-backed and cannot force trading execution;
- Desktop/iOS/Android share equivalent authority semantics;
- Core runtime identity remains unchanged by external presentation composition;
- no broker/provider/credential boundary is reachable from a presentation client.

Offline E2E evidence does not authorize public deployment or Production trading.

## Mission closure criteria

MISSION-05 may be marked `COMPLETED` only when all official deliveries have merged and the final closure review proves that:

- Desktop/iOS/Android consume a single Control Plane authority model;
- no presentation surface has direct Core/broker/provider/credential access;
- authenticated sessions are externalized and secret-safe;
- state freshness/staleness is explicit and fail-closed for sensitive operations;
- replay/idempotency, audit and command authorization remain MISSION-04 responsibilities and are not duplicated or bypassed;
- CIBO dialogue and Widget output are evidence-backed and non-authoritative for trading;
- notifications cannot execute commands;
- governance UX cannot create forced trades or bypass Risk/Portfolio/Capital Protection;
- deterministic E2E evidence covers success, rejection, NO_ACTION, stale state and ambiguity containment;
- Core runtime identity remains unchanged;
- client EA/client widget remain separate;
- MISSION-03 issue #146 remains governed by MISSION-03 evidence only;
- Production remains CLOSED.

MISSION-05 closure does **not** automatically open MISSION-06 and does **not** constitute Production authorization.

## Quality Gate

Every MISSION-05 delivery that modifies Python or repository-governed contracts must pass the repository's unchanged quality gate:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Platform-specific quality gates may be added only as additive checks. Existing Ruff/Mypy/Pytest enforcement must not be weakened, suppressed or bypassed.

CI failures are corrected on the same branch without `type: ignore`, avoidable `noqa`, hidden test exclusions or reduced coverage discipline.

## Relationship to MISSION-03

MISSION-03 remains the authority for real external TEST/DEMO market activation.

No simulator, mock, fixture, mobile UI, desktop UI, client gateway or MISSION-05 E2E test can close Gate #5 or downstream MISSION-03 operational gates.

## Relationship to MISSION-04

MISSION-04 is the stable executive governance foundation consumed by MISSION-05.

MISSION-05 must compose MISSION-04; it must not reopen or weaken its authority, replay, audit, resilience or transport-neutral guarantees.

## Relationship to MISSION-06 / Production

MISSION-06 Production Trading Readiness remains closed until explicitly opened by its own repository scope.

Even a completed MISSION-05 does not authorize:

- Production deployment;
- productive credentials;
- real-capital autonomous execution;
- Production broker accounts/orders;
- separate Production authorization.

## Opening decision

MISSION-05 is formally opened by `QORE-MISSION05-DOCS-001` only for the non-production implementation sequence defined above.

The next authorized delivery after this document merges is:

```text
QORE-MISSION05-SURFACE-BOUNDARY-001
```

No later delivery is considered complete merely because its concept appears in this mission definition.