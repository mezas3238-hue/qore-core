# QORE-DEMO-RISK-POLICY-AUTHORITY-001 — DEMO Risk/Policy Authority

## Status

**ENGINEERING CANDIDATE — DEMO ONLY**

This is the bounded engineering candidate for the first end-to-end profitability program:

```text
QUALIFIED TRADER INTENT -> CIBO MANAGEMENT/RECOMMENDATION -> NON-BYPASSABLE RISK -> DEMO EXECUTION
```

It creates NO Production/LIVE authority, NO real-capital authority, NO withdrawal/custody
authority, and NO provider credentials.

## Sovereignty invariant (hard law)

Two planes are separated by construction, not by convention:

- **Risk Deterministic Authority** — the only plane that may issue formal risk
  decisions/authorizations (`ALLOW`, `REDUCE`, `REJECT`, `FREEZE_TRADER`, `CONTAIN_ACCOUNT`,
  `KILL`). Implemented by `qore.infrastructure.risk_authority`.
- **Risk Cognitive Analyst** — may interpret, explain, compare, challenge and reason over
  evidence. It MUST NOT issue formal execution authority, override a deterministic Risk
  rejection, mint/mutate account-policy truth, convert LLM prose into effective policy without
  deterministic admission, or activate Production/LIVE authority. Implemented by
  `qore.infrastructure.risk_cognitive`.

Hard laws encoded in types:

```text
COGNITIVE OPINION != RISK AUTHORITY
CIBO CONFIDENCE != RISK OVERRIDE
TRADER EDGE != RISK BYPASS
LLM POLICY EXTRACTION != EFFECTIVE POLICY
```

The cognitive plane produces only `CognitiveAnalysis` (advisory). It cannot construct a
`RiskDecision` or `RiskAuthorization`; those types are module-private to `risk_authority` and are
only ever produced by the deterministic evaluator, never by the cognitive analyst or by any
CIBO/Trader path.

## Module layout

| Module | Lane | Responsibility |
| --- | --- | --- |
| `src/qore/infrastructure/risk_authority.py` | L1 | Outcomes, identities, immutable input/evidence, decision/authorization/receipt, scope/degradation state machine, counterfactual ledger, master fail-closed admission evaluator. |
| `src/qore/infrastructure/risk_policy_intelligence.py` | L2 | Authoritative-source observation -> candidate normalized rules -> deterministic validation/admission -> immutable `AccountPropPolicySnapshot`; provenance/version/fingerprint; policy-change detection. |
| `src/qore/infrastructure/risk_budgets.py` | L3 | Per-trade/Trader/instrument/group/account budgets, effective-limit composition, safety buffer, stress-before-admit, concentration/correlation heat. |
| `src/qore/infrastructure/risk_capacity.py` | L4 | RESERVE -> COMMIT -> RELEASE/EXPIRE, monotonic generation fencing, idempotency, deterministic reference ledger + fail-closed integration seam. |
| `src/qore/infrastructure/risk_cognitive.py` | L5 | Terra-medium default, typed escalation routing, advisory analysis, receipts/provenance, replay without hidden provider calls, secret safety. |
| `src/qore/infrastructure/risk_runtime.py` | L6 | Composition of authority + budgets + capacity + policy + scope into one fail-closed DEMO admission runtime and a DEMO execution-boundary validation seam. |

Shared identity/outcome types live in `risk_authority.py` and are imported by the other modules;
no module may redefine them.

## Canonical reuse (no duplicate primitives)

- `TradingAccountId`, `TradingAccountKind`, `AccountPolicyReference`, `ClientId`,
  `ExecutionRuntimeReference`, `ProductEntitlementReference`, `TradingAccountLifecycleState`
  — `qore.infrastructure.client_accounts`.
- `AccountPolicySnapshotId`, `AccountPolicyVersion`, `AccountPropPolicySnapshot`,
  `AccountPolicyRule`, `AccountPolicyRegistrySnapshot`, `PolicyRuleScope`,
  `PolicyRuleDisposition`, `DrawdownMode`, `AccountPhase` — `qore.infrastructure.account_policy`.
- `MoneyAmount`, `DrawdownBps`, `CurrencyCode` — `qore.infrastructure.proprietary_accounts`.
- `OrderSide`, `OrderQuantity`, `OrderType`, `ExecutionInstrument`, `OrderPrice`,
  `OrderIntentId` — `qore.infrastructure.order_intent`.
- `ExecutionSafetySwitchSnapshot`, `ExecutionSwitchState`, `PreTradeDecision` —
  `qore.infrastructure.pretrade_safety` (global kill switch seam).
- `ExecutionContainmentSnapshot` — `qore.infrastructure.execution_failure_containment`
  (containment seam).
- `ExternalSourceDescriptor` — `qore.infrastructure.ports` (source provenance).

## Deterministic contracts

- No ambient clock: every timestamp is caller-supplied and timezone-aware. The admission
  evaluator requires an explicit `evaluated_at`.
- No ambient UUID generation inside contracts; ids are caller-supplied `UUID` objects.
- Exact runtime types: `type(x) is int` for `int` (rejects `bool`), exact enum membership,
  exact `Decimal` for money/quantity, no `float`.
- `Decimal` semantics for all money/notional/quantity arithmetic; no float.
- Fail closed: missing, stale, ambiguous, wrong-account, wrong-version or mismatched mandatory
  state never admits new risk.

## L1 — `risk_authority.py` (sovereignty)

### Enums

```text
RiskOutcome       : ALLOW | REDUCE | REJECT | FREEZE_TRADER | CONTAIN_ACCOUNT | KILL
RiskArm           : TRADERS_RISK_ONLY | CIBO_MANAGED_TRADERS_RISK
RiskScopeState    : NORMAL | REDUCED_CAPACITY | FREEZE_TRADER | CONTAIN_ACCOUNT | KILL
RiskScopeKind     : TRADER | ACCOUNT | PORTFOLIO (scope of a freeze/contain)
RiskAuthorizationStatus : ISSUED | VOID (mutation/expiry invalidates; reuse requires new decision)
```

`RiskOutcome` ordering is monotonic severity: `ALLOW < REDUCE < REJECT < FREEZE_TRADER <
CONTAIN_ACCOUNT < KILL`.

### Identities / value objects

```text
RiskDecisionId        value: UUID
RiskAuthorizationId   value: UUID
RiskReservationId     value: UUID
RiskPolicyId          value: UUID
RiskPolicyVersion     value: int  (positive)
RiskFingerprint       value: str  (64 lowercase hex sha256)
RiskTraderFingerprint value: str  (64 lowercase hex sha256)
RiskIntentDigest      value: str  (64 lowercase hex sha256)
RiskEvidenceFreshness value: timedelta-backed integer seconds? NO -> explicit observed_at + evaluated_at
RiskReasonCode        StrEnum (typed reason codes, see below)
```

### Reason codes (typed, non-exhaustive but explicit)

```text
risk.admitted
risk.reduced
risk.rejected.scope-frozen
risk.rejected.scope-contained
risk.rejected.scope-killed
risk.rejected.evidence-missing
risk.rejected.evidence-stale
risk.rejected.account-mismatch
risk.rejected.policy-version-mismatch
risk.rejected.policy-expired
risk.rejected.policy-not-effective
risk.rejected.policy-ambiguous
risk.rejected.internal-limit-exceeded
risk.rejected.external-limit-exceeded
risk.rejected.budget-exceeded
risk.rejected.heat-exceeded
risk.rejected.stress-breach
risk.rejected.concentration-exceeded
risk.rejected.missing-stop
risk.rejected.currency-mismatch
risk.rejected.capacity-exhausted
risk.rejected.stale-reservation
risk.rejected.authorization-mutation
risk.scope.freeze-trader
risk.scope.contain-account
risk.scope.kill
risk.reduced-capacity
```

### Input / evidence contract

`RiskEvidence` (frozen) carries, at minimum:

```text
environment               : RiskEnvironment (DEMO | PRACTICE | PRODUCTION | UNKNOWN; DEMO-only admission enforced)
account_id                : TradingAccountId
trader_id                 : RiskTraderIdentity (opaque UUID + version + config fingerprint)
trader_fingerprint        : RiskTraderFingerprint
intent_id                 : OrderIntentId
intent_digest             : RiskIntentDigest
instrument                : ExecutionInstrument
side                      : OrderSide
requested_quantity        : OrderQuantity
requested_notional        : MoneyAmount
stop_loss                 : OrderPrice | None
bounded_loss_at_stop      : MoneyAmount | None (loss at stop if stop is present)
open_positions            : tuple[RiskOpenPosition, ...]
per_trader_exposure       : MoneyAmount
per_instrument_exposure   : MoneyAmount
group_exposure            : MoneyAmount (correlated group, when configured)
portfolio_heat            : MoneyAmount
account_state             : RiskAccountObservedState (balance/equity/margin/drawdown/daily-loss + observed_at)
account_policy_snapshot_id: AccountPolicySnapshotId
account_policy_version    : AccountPolicyVersion
account_policy_ref        : AccountPolicyReference
internal_risk_policy_id   : RiskPolicyId
internal_risk_policy_ver  : RiskPolicyVersion
market_evidence           : RiskMarketEvidence (observed_at + fingerprint)
reservations_committed    : MoneyAmount (currently committed capacity)
containment               : RiskScopeSnapshot
evaluated_at              : datetime (required; no wall clock)
arm                       : RiskArm
```

Mandatory-field validation fails closed (`RiskResolutionError`) on missing/stale/mismatch.

### Decision / authorization

`RiskDecision` (frozen): `decision_id`, `outcome`, `reasons`, `evidence`, `evaluated_at`,
`arm`, optional `authorization`.

`RiskAuthorization` (frozen receipt) — only for `ALLOW`/`REDUCE` — bound to:

```text
authorization_id, account_id, environment, trader_id/fingerprint, intent_id/digest,
instrument, side, requested vs authorized quantity/notional, stop/loss assumptions,
account_policy_snapshot_id + version, internal_risk_policy_id + version,
account_state_fingerprint, market_evidence_fingerprint, reservation_id + generation,
issued_at, validity (derived from explicit evidence/policy timeframes, no universal TTL),
reason codes, arm
```

`RiskAuthorization` is immutable; a `with voided status` copy is produced by
`void_authorization(...)` on material mutation, never by mutating the original. Every issued
authorization also carries an explicit `valid_until` derived from the remaining freshness window
of the exact market/account evidence and clamped by the resolved account-policy expiry when one
is available. Reuse after that instant, after a scope generation change, or after a policy-version
change is invalidated and requires a new decision.

The execution bridge is `DemoRiskRuntime.prepare_execution_submission(...)`. It verifies the
canonical digest of the original `OrderIntent`, applies only the Risk-authorized quantity, maps the
Risk authorization into the existing `PreTradeAuthorization`/`AuthorizedOrderIntent` contracts,
validates and commits the exact capacity reservation, and only then returns `ExecutionSubmission`.
No caller can obtain that submission from Risk by presenting free-form CIBO/Trader output.

### Scope / degradation state machine

`RiskScopeSnapshot` (frozen): `state: RiskScopeState`, `kind: RiskScopeKind`,
`scope_id` (trader/account/portfolio UUID), `since: datetime`, `reason: RiskReasonCode`,
`generation: int` (monotonic).

`RiskGovernanceState` is a deterministic transition function over the registry of scope
snapshots. Allowed transitions (fail-closed otherwise):

```text
NORMAL -> REDUCED_CAPACITY -> FREEZE_TRADER -> CONTAIN_ACCOUNT -> KILL
```

- `FREEZE_TRADER`, `CONTAIN_ACCOUNT`, `KILL` are terminal for new admission in their scope.
- Recovery (`CONTAIN_ACCOUNT -> REDUCED_CAPACITY -> NORMAL`) requires explicit evidence/state and
  a governed transition function `recover_scope(...)`; CIBO/Trader cannot self-reactivate.
- A stale pre-freeze authorization cannot resurrect exposure: admission checks the current
  scope generation against the authorization's recorded generation.

### Counterfactual / attribution ledger

`RiskCounterfactualRecord` (frozen): binds a `RiskDecision` to later realized outcomes without
fabricating future evidence. Fields: `record_id`, `decision_id`, `authorization_id | None`,
`arm`, `outcome`, `reason_codes`, `intent_digest`, `account_id`, `evaluated_at`, and
`realized_outcome: RiskRealizedOutcome | None` (linked later). `RiskCounterfactualLedger` is an
immutable append-only value with `append(...)`, `link_outcome(...)`, deterministic ordering and
`logical_values()`.

### Master admission evaluator

```text
evaluate_risk_admission(
    evidence: RiskEvidence,
    internal_policy: RiskPolicySnapshot,          # internal QORE config (id/version/fingerprint + budget config)
    budget_evaluator: RiskBudgetEvaluator,        # L3 protocol (pure)
    capacity: RiskCapacityStore,                  # L4 protocol (pure transition)
    scope: RiskScopeSnapshot,                     # current scope for this account/trader
    evaluated_at: datetime,
) -> Result[RiskDecision, RiskError]
```

Order of checks (each fail-closed):

1. Evidence/type/mandatory-field validation.
2. Environment must be DEMO/PRACTICE (never PRODUCTION admission here).
3. Scope state check: frozen/contained/killed scope -> `REJECT` (or escalate), no new admission.
4. Account/policy resolution: exact account id/ref/version; policy effective/not-expired/complete.
   The internal risk-policy identity/version/arm must also match the supplied `internal_policy`
   (else fail closed with a typed reason), so a substituted or mismatched internal policy or A/B
   arm can never be laundered into a decision.
5. Freshness: `evaluated_at - observed_at <= freshness_budget`.
6. Internal + external effective-limit composition (`SAFEST APPLICABLE BOUND`).
7. Budgets/heat/stress (delegated to `budget_evaluator`): per-trade/trader/instrument/group/
   account; stress-before-admit uses bounded-loss-at-stop when present; missing mandatory stop
   -> fail closed.
8. Capacity reservation (delegated to `capacity`): `RESERVE` under monotonic generation; if
   reservation fails, `REJECT` with capacity reason.
9. On success: `ALLOW` (full) or `REDUCE` (reduced) + immutable `RiskAuthorization` bound to the
   reservation.

The evaluator returns a typed `RiskDecision`; it never issues execution or calls a provider.

## L2 — `risk_policy_intelligence.py`

Conceptual chain:

```text
AUTHORITATIVE SOURCE OBSERVATION -> CANDIDATE NORMALIZED RULES
  -> DETERMINISTIC VALIDATION/ADMISSION -> IMMUTABLE AccountPropPolicySnapshot -> RISK ENFORCEMENT
```

- `PolicySourceKind` (StrEnum): `PLATFORM_API` | `ACCOUNT_METADATA` | `VERSIONED_RULE_DOCUMENT`
  | `FIRM_WEBSITE` | `UNRESOLVED`.
- `PolicyAuthorityRank` (StrEnum/ordered): `PLATFORM_API` (highest) > `ACCOUNT_METADATA` >
  `VERSIONED_RULE_DOCUMENT` > `FIRM_WEBSITE` > `UNRESOLVED` (lowest).
- `PolicySourceObservation` (frozen): source identity/provenance/version/fingerprint, observed
  content digest, rank, observed_at, `ExternalSourceDescriptor` provenance.
- `CandidatePolicyRule` (frozen): canonical rule code + typed parameters/semantics + source
  provenance. It is candidate-only; it carries no authority.
- Third-party blogs/forums/social sources are rejected at admission (`UNRESOLVED`/non-authoritative
  ranks never admit).
- `admit_policy_rules(...)`: deterministic validation/normalization -> `Result` of admitted
  normalized rules; ambiguous mandatory semantics -> fail closed.
- `compose_policy_snapshot(...)`: admitted rules + existing `AccountPropPolicySnapshot` fields ->
  immutable `AccountPropPolicySnapshot` (reusing `account_policy.AccountPropPolicySnapshot`).
- `detect_policy_change(...)`: fingerprint/version comparison. On material change ->
  `POLICY_CHANGED`, prior snapshot stale, new trading blocked until revalidated. Tested for:
  source version change; semantic change with same label; effective/expiry boundaries;
  account/program/phase mismatch; changed reset timezone; changed drawdown mode; unchanged
  equivalent content (deterministic identity).

## L3 — `risk_budgets.py`

`RiskBudgetPolicy` (frozen config; explicit/versioned, no universal percentage defaults):

```text
per_trade_limit_bps, per_trader_limit_bps, per_instrument_limit_bps,
group_limit_bps, portfolio_heat_limit_bps, account_risk_capacity_bps,
safety_buffer_bps (internal buffer: QORE stops admitting before external breach),
correlation groups (explicit grouping config), freshness budgets, stress rules
```

`RiskBudgetEvaluator` (Protocol) with pure `evaluate(...)`:

- Effective limit composition: `EFFECTIVE LIMIT = SAFEST APPLICABLE BOUND`; internal QORE may be
  stricter than external account/provider limits, never looser.
- Safety buffer: `available = effective_limit * (1 - safety_buffer_bps / 10000)`.
- Per-trade/Trader/instrument/group/account budgets; concentration/correlation heat.
- `stress_before_admit`: given bounded-loss-at-stop, compute post-stop state; an intent must not
  pass when its bounded adverse outcome would immediately breach effective policy. Boundary
  equality, one-unit/basis-point around limits, rounding/precision (Decimal), zero/negative/
  invalid, currency compatibility, fail-closed when loss semantics cannot be determined.

## L4 — `risk_capacity.py`

Lifecycle: `RESERVE -> COMMIT -> RELEASE / EXPIRE` (or architecturally equivalent exact model).

- `RiskCapacityLedger` (immutable value) with pure transition functions; no threads/global state.
- Capacity accounting is notional-based: each `RiskReservation` carries its authorized `notional`,
  and `reserve` refuses to exceed `capacity` against the sum of reserved + committed notional.
- Reservation scoped/bound to exact account + intent + policy + state/config fingerprints.
- Monotonic `generation` fencing: a stale reservation/generation cannot be committed.
- Repeated commit/release follows explicit idempotency semantics; duplicate release cannot
  fabricate negative/free capacity.
- Failed/aborted downstream execution releases capacity where policy requires.
- Deterministic replay surface preserves admitted event/result history; the reference
  implementation is an in-memory deterministic ledger and the doc states the external durability
  requirement explicitly (no false claim of distributed atomicity). A `RiskCapacityStore`
  (Protocol) plus `InMemoryRiskCapacityStore` fail-closed integration seam.

## L5 — `risk_cognitive.py`

- Default route: model `gpt-5.6-terra`, effort `medium`.
- Typed escalation (explicit typed situational signals, never prompt keyword heuristics):
  - ordinary monitoring/explanation/clear interpretation -> Terra / medium;
  - materially ambiguous rule or portfolio interpretation -> Terra / high;
  - contradictory authoritative sources / difficult ambiguity -> GPT-5.6 Sol / high;
  - exceptional unresolved ambiguity with serious account-breach consequences -> GPT-5.6 Sol /
    max (analysis only; deterministic Risk remains fail-closed).
- De-escalation after resolution (no sticking in high/max).
- `CognitiveAnalysis` (advisory, frozen) + `CognitiveReceipt` (provenance: provider, exact model,
  effort, request/evidence digest, source/policy refs, routing situation fingerprint, config/
  schema fingerprint, provider response ref if available, admitted output digest, completion
  timestamp). No hidden chain-of-thought persistence.
- Replay must not make a new provider call to replace retained admitted evidence; deterministic
  replay reads retained receipts.
- LLM-extracted natural-language policy is only `CandidatePolicyRule` (via L2); it becomes
  effective only after deterministic admission. Ambiguous mandatory rule -> fail closed.
- Transport is an injected `RiskCognitiveTransport` Protocol; fake transport for unit
  certification; no live API key required. Secret-safety validation on prompts/results.

## L6 — `risk_runtime.py`

- `DemoRiskRuntime` composes authority + budgets + capacity + policy + scope; its `admit(...)`
  resolves the account-policy snapshot against an explicit registry (fail-closed on substitution,
  expiry, not-yet-effective, or version mismatch) before delegating to `evaluate_risk_admission`.
- `resolve_account_policy_for_evidence(...)` — typed account-policy resolution seam.
- A DEMO execution-boundary validation seam `validate_risk_authorization(...)` that validates an
  exact `RiskAuthorization` (fingerprint, environment, validity, scope-generation, policy version)
  rather than trusting free-form CIBO/Trader output.
- `compose_execution_safety_from_scope(...)` — bridges Risk governance scope to the existing
  `ExecutionSafetySwitchSnapshot` kill switch (frozen/contained/killed scope => BLOCKED).
- `compose_demo_risk_runtime(...)` — constructs a coherent runtime from explicit, fingerprinted
  configuration (fails closed on budget-config-fingerprint or arm mismatch).
- Composes with existing `controlled_execution` / `execution_boundary` / `pretrade_safety` seams.
- Full adversarial/root-family test battery + e2e deterministic tests + unchanged FULL QG.

## Required adversarial / root-family closure

1. concurrent double-spend of remaining risk capacity;
2. stale reservation and stale fencing generation;
3. duplicate release/commit/idempotency races;
4. Trader identity/version/config swap after authorization;
5. intent/quantity/price/stop mutation after authorization;
6. account/policy snapshot substitution;
7. effective/expiry transition race;
8. external source/policy change while an authorization exists;
9. static/trailing drawdown confusion;
10. balance/equity/open-PnL inclusion ambiguity;
11. daily reset timezone/boundary errors;
12. risk concentration/correlation undercount;
13. stale market/account/position state;
14. missing stop/loss-at-stop where mandatory;
15. precision/rounding limit boundaries;
16. CIBO/Trader direct bypass attempt;
17. cognitive-output laundering into formal policy/authority;
18. untrusted/third-party policy source admission attempt;
19. conflicting authoritative policy sources;
20. kill/contain/recovery lifecycle races;
21. previous authorization reuse after freeze/policy change;
22. A/B Risk-policy/config asymmetry;
23. deterministic replay/id stability;
24. secret/account-identifier leakage.

## Security / privacy

No API keys, passwords, bearer tokens, raw account login numbers, client civil identity or
sensitive provider credentials in logs, repr, public evidence, error messages, cognitive prompts
(where not strictly required), or durable policy/source records. Opaque/fingerprinted references
are used. `risk_cognitive` reuses the secret-detection discipline from
`qore.modules.cibo.cognitive_contracts.contains_secret_material` where applicable.

## Non-claims

This candidate does not claim LIVE/Production readiness, real-capital authority, withdrawal/
custody authority, provider credentials, automatic acceptance of unsupported prop-firm rules,
direct LLM/CIBO/Trader Risk authority, or bypass of DEMO execution/fill/reconciliation/
economic-evidence gates.

## Acceptance

`CANDIDATE READY — DEMO RISK/POLICY ROOT FAMILIES EXHAUSTED` only when the exact candidate
satisfies authority, policy-intelligence, capacity/concurrency, cognition, security, integration
and the unchanged FULL QG (`ruff check .`, `mypy src tests`,
`pytest --cov=src/qore --cov-report=term-missing`).
