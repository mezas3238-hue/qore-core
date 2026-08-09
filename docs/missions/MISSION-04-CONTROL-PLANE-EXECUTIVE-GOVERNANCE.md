# MISSION-04 — QORE Control Plane & Executive Governance

Status: **ACTIVE FOR OFFLINE / PROVIDER-INDEPENDENT ENGINEERING — EXTERNAL CONTROL-PLANE ACTIVATION CLOSED**

## Purpose

MISSION-04 converts the already-merged executive governance contracts into a complete, transport-neutral and auditable Control Plane architecture that can later serve Desktop, iOS and Android without granting any presentation surface direct access to QORE Core, broker/provider clients, credentials or trading execution.

MISSION-04 may progress while MISSION-03 remains operationally blocked on external OANDA Practice provisioning. The two missions do not redefine each other's gates:

- MISSION-03 remains the authority for real external TEST/DEMO market activation;
- MISSION-04 may advance only through work that does not require OANDA account/token or real provider evidence;
- no MISSION-04 artifact may mark any MISSION-03 operational gate complete;
- no MISSION-03 preparation artifact becomes executive Production authority.

## Existing foundation on `main`

MISSION-04 starts from the repository state already delivered through the Executive Control Plane preparation series:

- `QORE-EXECUTIVE-CONTROL-PLANE-001` — immutable executive identity, authority grants, control intents and read requests;
- `QORE-EXECUTIVE-CONTROL-PORTS-001` — command/query Protocols and deterministic receipts;
- `QORE-EXECUTIVE-CONTROL-TARGETS-001` — explicit scoped governance targets;
- `QORE-GOVERNANCE-MATERIALIZED-STATE-001` — canonical materialized current governance state source;
- `QORE-EXECUTIVE-GOVERNANCE-CURRENT-STATE-001` — executive projection of current governance state;
- `QORE-EXECUTIVE-READ-DELIVERY-001` — binding of authorized request, projection and served receipt;
- executive read models for System Health, CIBO, Markets, Traders, Validation Lab, Trade Forensics, Audit, Portfolio, Risk, Capital, CEO Accounts, Governance and Corporate Profit Vault.

These contracts are inputs to MISSION-04. They are not replaced by a second control-plane model.

## Architectural invariant

The only permitted future presentation path is:

```text
CEO Desktop / iOS / Android
            │
            ▼
External Authentication Boundary
            │
            ▼
Executive Control Plane
            │
            ├── authenticated principal assertion
            ├── current authority source / revocation state
            ├── request authorization
            ├── replay/idempotency protection
            ├── command/query dispatch
            ├── audit/evidence
            ├── observability
            └── governed downstream ports
                    │
                    ▼
             governed QORE surfaces
```

The following paths remain prohibited:

```text
CEO App ─────────────► Core internals
CEO App ─────────────► broker/provider
CEO App ─────────────► execution gateway
CEO App ─────────────► credentials/secrets
CEO App ─────────────► Risk bypass
CEO App ─────────────► direct buy/sell/order controls
```

## Authority doctrine

Executive authority is governance authority, not trading authority.

The CEO may reduce, stop or restore governed operational authority through explicitly allowed executive controls. The CEO may not force a trade, manufacture an order, override CIBO judgment, bypass Risk/Portfolio/Capital Protection, or transform a blocked trading decision into execution.

Every protected operation must preserve the chain:

```text
Authenticated Principal
  → Current Authority Version
  → Grant / Revocation State
  → Request
  → Authorization Evaluation
  → Replay / Idempotency Evaluation
  → Governed Dispatch
  → Result
  → Receipt
  → Audit / Evidence
```

If a mandatory link is missing or contradictory, the result is fail-closed and no downstream action occurs.

## Security doctrine

MISSION-04 contracts must not store or expose raw authentication credentials.

Allowed control-plane security values are opaque references, fingerprints, explicit timestamps, version identifiers and safe reason/evidence codes.

Forbidden in `repr`, logs, telemetry, metadata, evidence and `logical_values()`:

- passwords;
- bearer tokens;
- access/refresh tokens;
- API keys;
- private keys;
- biometric material;
- OANDA/broker credentials;
- secret-bearing headers;
- raw mobile session secrets.

Authentication itself remains an external secret-aware boundary. QORE governance consumes only a validated principal assertion and safe authentication provenance.

## Determinism doctrine

All new value contracts follow existing QORE rules:

- `dataclass(frozen=True, slots=True)`;
- `Protocol` for external/downstream boundaries;
- typed `Result / Success / Failure`;
- typed errors;
- caller-supplied timezone-aware timestamps;
- no implicit `datetime.now()`;
- no implicit `uuid4()`;
- deterministic ordering;
- deterministic `logical_values()`;
- strict bool/int validation where relevant;
- sanitized immutable metadata;
- no hidden retry, sleep, polling loop, scheduler or thread.

## Official MISSION-04 delivery sequence

```text
1.  QORE-MISSION04-DOCS-001
    Mission scope, boundaries, sequence and closure criteria

2.  QORE-EXECUTIVE-AUTHENTICATED-PRINCIPAL-001
    Transport-neutral authenticated principal assertion

3.  QORE-EXECUTIVE-AUTHORITY-STATE-001
    Current grant / revocation / expiry source-of-truth boundary

4.  QORE-EXECUTIVE-REQUEST-GUARD-001
    Unified fail-closed control/query request guard

5.  QORE-EXECUTIVE-COMMAND-DISPATCH-001
    Authorized governance command dispatch composition

6.  QORE-EXECUTIVE-QUERY-DISPATCH-001
    Authorized executive read dispatch composition

7.  QORE-EXECUTIVE-GOVERNANCE-MUTATION-001
    Explicit downstream governance-state mutation port and receipts

8.  QORE-EXECUTIVE-AUDIT-EVIDENCE-001
    Durable-boundary contracts for audit/evidence append and retrieval

9.  QORE-EXECUTIVE-REPLAY-PROTECTION-001
    Request identity, replay and idempotency decision contracts

10. QORE-EXECUTIVE-TRANSPORT-ENVELOPE-001
    Transport-neutral request/response envelopes and error projection

11. QORE-CONTROL-PLANE-OBSERVABILITY-001
    Sanitized control-plane health, authorization and dispatch evidence

12. QORE-CONTROL-PLANE-RESILIENCE-001
    Fail-closed timeout/unavailable/partial-failure policy contracts

13. QORE-CONTROL-PLANE-E2E-001
    Deterministic offline end-to-end validation harness

14. QORE-MISSION04-CLOSURE-001
    Mission closure review and activation prerequisites
```

This sequence may change only through an explicit architecture change merged to the repository.

## Delivery 2 — authenticated principal assertion

The Control Plane must not treat possession of a device, principal string or request payload as authentication.

The authenticated-principal contract must bind at least:

- executive principal identity;
- authentication assertion identity;
- authentication method code;
- issued-at and expiry timestamps;
- external identity-boundary reference;
- safe assurance level / authentication context;
- deterministic correlation provenance.

It must not contain raw credentials or authentication secrets.

Expired, future-issued, malformed or principal-mismatched assertions fail closed.

## Delivery 3 — current authority state

An `ExecutiveAuthorityGrant` is historical evidence of issued authority, but a Control Plane additionally needs a canonical current authority source capable of representing:

- active grant;
- revoked grant;
- superseded authority version;
- expired authority;
- unknown/unavailable authority state.

Readers must not infer revocation by replaying incomplete audit history.

Unknown current authority is not equivalent to authorized.

## Delivery 4 — unified request guard

The request guard composes:

```text
Authenticated Principal Assertion
  + Current Authority State
  + Executive Control Intent / Read Request
  + explicit evaluation timestamp
  → Authorized Request OR Failure
```

The guard must preserve existing authorization functions rather than reimplementing their rules in transport code.

## Delivery 5 — command dispatch

Command dispatch accepts only an authorized executive control intent.

It must:

- route only allowlisted governance actions;
- preserve target identity;
- produce deterministic receipts;
- avoid hidden retries;
- never expose trading actions;
- never call provider/broker execution surfaces;
- fail closed on unknown action/target/state;
- emit audit evidence for success and failure.

A command dispatcher is not a trading executor.

## Delivery 6 — query dispatch

Query dispatch accepts only an authorized executive read request and must return `ExecutiveReadDelivery`.

The dispatcher must preserve exact scope, principal, authority version, correlation and projection provenance.

No raw internal Core/domain/provider objects are returned to presentation clients.

## Delivery 7 — governance mutation

Current Governance state already has a materialized source contract. MISSION-04 must add the complementary mutation boundary without embedding persistence implementation.

Mutation must be explicitly versioned and compare expected/current state where required to prevent blind overwrite.

No mutation may create buy/sell/order semantics.

## Delivery 8 — audit/evidence

Audit/evidence persistence is an external boundary. Core governance contracts must not silently depend on a database implementation.

The append/read contracts must preserve:

- immutable audit identity;
- principal/request/correlation linkage;
- authority version;
- outcome;
- reason/evidence codes;
- explicit timestamp;
- deterministic ordering for reads;
- secret sanitization.

NO_ACTION and blocked/rejected requests are auditable outcomes.

## Delivery 9 — replay protection

The Control Plane must distinguish a legitimate retry of the same logical request from a replay with modified content.

Replay/idempotency contracts must be explicit and deterministic. No hidden random nonce generation is allowed inside governance logic.

A reused request key with different logical content fails closed.

## Delivery 10 — transport envelope

Transport-neutral envelopes may later be mapped to HTTP/WebSocket/gRPC/mobile IPC, but MISSION-04 does not require any server implementation.

The envelope must carry safe typed references, not raw provider or credential objects.

Transport errors must project into stable public error codes without leaking exception text or secrets.

## Delivery 11 — observability

Control-plane observability must cover at least:

- authentication assertion accepted/rejected;
- authority source healthy/degraded/unavailable;
- authorization accepted/rejected;
- replay/idempotency result;
- command/query dispatch outcome;
- governance mutation result;
- audit append result;
- latency supplied as explicit observed metrics rather than hidden runtime clocks;
- environment and service-state classification.

Observability is descriptive evidence and grants no authority.

## Delivery 12 — resilience

Failure policy must cover at least:

- authentication boundary unavailable;
- authority source unavailable;
- audit sink unavailable;
- downstream governance port unavailable;
- query source unavailable;
- timeout;
- duplicate/replay ambiguity;
- partial failure after downstream mutation but before audit acknowledgement.

Ambiguous command outcomes must not be automatically reissued.

## Delivery 13 — deterministic offline E2E

The E2E harness must prove, using deterministic fakes only:

- unauthenticated request → no authorization / no dispatch;
- expired authentication → no dispatch;
- revoked/unknown authority → no dispatch;
- valid control → exact governance target reaches one downstream port call;
- valid read → exact structured `ExecutiveReadDelivery`;
- duplicate exact request → deterministic idempotent result where policy allows;
- modified replay → fail closed;
- audit/evidence emitted for success, rejection and NO_ACTION;
- downstream ambiguity → containment, no automatic repeat;
- Core identity (`EventBus`, `RuntimePlan`, `RuntimeSnapshot`, `RuntimeHealth`) remains unchanged when the Control Plane is composed externally.

Offline E2E evidence does not activate a network service or Mobile app.

## Mission closure criteria

MISSION-04 may be marked complete only when all fourteen deliveries are merged with unchanged QORE CI and the repository demonstrates a complete provider-independent Control Plane composition.

MISSION-04 closure does **not** authorize:

- public Internet exposure;
- Android/iOS/Desktop deployment;
- Production trading;
- productive broker/provider credentials;
- real capital;
- autonomous real-money execution;
- direct CEO order entry;
- Risk/Portfolio/Capital Protection bypass.

Those require their own later operational/deployment gates.

## Relationship to MISSION-05

MISSION-05 — QORE Mobile & CEO Command Center may consume MISSION-04 transport-neutral contracts after MISSION-04 provides a stable, auditable boundary.

Mobile/Desktop remain presentation clients. They do not become governance sources-of-truth.

## Quality Gate

Every functional MISSION-04 delivery must pass unchanged:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

CI failures are corrected on the same branch without suppressions or weakened checks.

## Immediate next delivery

After `QORE-MISSION04-DOCS-001` merges, continue with:

```text
QORE-EXECUTIVE-AUTHENTICATED-PRINCIPAL-001
```

This next delivery is fully provider-independent and requires no OANDA Practice account or token.
