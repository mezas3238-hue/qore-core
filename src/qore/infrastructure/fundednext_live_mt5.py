"""Production-only FundedNext MT5 gateway and broker shadow preflight.

The existing FundedNextMt5ExecutionGateway remains TEST/DEMO-only.  This module
creates a separate PRODUCTION boundary requiring FundedNextLiveAccountAuthorization.
It preserves the same deterministic client-order identity and durable mutation
fence while adding MT5 ``order_check`` shadow evidence before any live mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Protocol

from qore.infrastructure.execution_boundary import ExecutionSubmission
from qore.infrastructure.fundednext_execution_bridge import extract_risk_provenance
from qore.infrastructure.fundednext_live_authorization import (
    FundedNextLiveAccountAuthorization,
    FundedNextLiveAuthorizationError,
)
from qore.infrastructure.fundednext_mt5 import (
    FundedNextMt5OrderPlan,
    Mt5ExecutionBlockedError,
    Mt5ExecutionOutcomeUnknownError,
    Mt5ExecutionRejectedError,
    Mt5ExecutionValidationError,
    Mt5ProviderOutcome,
    Mt5SymbolSpecification,
)
from qore.infrastructure.fundednext_mt5_mutation_ledger import (
    FundedNextMt5MutationLedger,
    FundedNextMt5MutationRecord,
    FundedNextMt5MutationState,
    fundednext_submission_digest,
)
from qore.infrastructure.fundednext_mt5_transport import (
    MetaTrader5Api,
    MetaTrader5FundedNextTransport,
)
from qore.infrastructure.fundednext_stellar_instant import StellarInstantRuleVerification
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import OrderSide, OrderType


class Mt5CheckResultLike(Protocol):
    retcode: int
    comment: str


class LiveMetaTrader5Api(MetaTrader5Api, Protocol):
    def order_check(self, request: dict[str, object]) -> Mt5CheckResultLike | None: ...


@dataclass(frozen=True, slots=True)
class FundedNextMt5ShadowReceipt:
    client_order_id: str
    provider_symbol: str
    broker_valid: bool
    retcode: int | None
    reason: str
    checked_at: datetime


class MetaTrader5FundedNextLiveTransport(MetaTrader5FundedNextTransport):
    """Concrete live transport with a non-mutating MT5 order_check boundary."""

    def __init__(
        self,
        *,
        api: LiveMetaTrader5Api,
        qore_account_ref: str,
        expected_login: int,
        expected_server: str,
    ) -> None:
        super().__init__(
            api=api,
            qore_account_ref=qore_account_ref,
            expected_login=expected_login,
            expected_server=expected_server,
        )
        self._live_api = api

    def check_order(self, plan: FundedNextMt5OrderPlan) -> FundedNextMt5ShadowReceipt:
        self._require_bound_account()
        request = self._submission_payload(plan)
        result = self._live_api.order_check(request)
        now = datetime.now().astimezone()
        if result is None:
            return FundedNextMt5ShadowReceipt(
                client_order_id=plan.client_order_id,
                provider_symbol=plan.provider_symbol,
                broker_valid=False,
                retcode=None,
                reason="mt5-order-check-no-result",
                checked_at=now,
            )
        valid = int(result.retcode) == 0
        return FundedNextMt5ShadowReceipt(
            client_order_id=plan.client_order_id,
            provider_symbol=plan.provider_symbol,
            broker_valid=valid,
            retcode=int(result.retcode),
            reason="mt5-order-check-ok" if valid else f"mt5-order-check-retcode-{result.retcode}",
            checked_at=now,
        )


class FundedNextLiveMt5ExecutionGateway:
    """Production gateway that cannot exist without exact live activation evidence."""

    def __init__(
        self,
        *,
        account: MarketTestAccountIdentity,
        transport: MetaTrader5FundedNextLiveTransport,
        mutation_ledger: FundedNextMt5MutationLedger,
        rule_verification: StellarInstantRuleVerification,
        live_authorization: FundedNextLiveAccountAuthorization,
        runtime_git_sha: str,
        account_identity_fingerprint: str,
        expected_server: str,
        submission_enabled: bool,
        max_spec_age: timedelta = timedelta(seconds=10),
        max_spread_points: Decimal | None = None,
    ) -> None:
        if account.environment is not MarketRuntimeEnvironment.PRODUCTION:
            raise Mt5ExecutionValidationError("live gateway requires PRODUCTION account")
        if account.provider_key != "fundednext-stellar-instant-mt5":
            raise Mt5ExecutionValidationError("live gateway provider mismatch")
        if not isinstance(live_authorization, FundedNextLiveAccountAuthorization):
            raise Mt5ExecutionValidationError("explicit live authorization is required")
        try:
            live_authorization.assert_matches(
                account=account,
                git_sha=runtime_git_sha,
                account_identity_fingerprint=account_identity_fingerprint,
                server=expected_server,
            )
        except FundedNextLiveAuthorizationError as error:
            raise Mt5ExecutionBlockedError(str(error)) from error
        if not isinstance(rule_verification, StellarInstantRuleVerification):
            raise Mt5ExecutionValidationError("Stellar Instant rules verification required")
        if max_spec_age <= timedelta(0):
            raise Mt5ExecutionValidationError("max_spec_age must be positive")
        self._account = account
        self._transport = transport
        self._ledger = mutation_ledger
        self._rules = rule_verification
        self._authorization = live_authorization
        self._submission_enabled = bool(submission_enabled)
        self._max_spec_age = max_spec_age
        self._max_spread_points = max_spread_points
        self._records = {item.idempotency_key: item for item in mutation_ledger.records()}
        self._mark_interrupted_attempts_unknown()

    @property
    def has_unresolved_mutations(self) -> bool:
        return any(
            item.state in {
                FundedNextMt5MutationState.ATTEMPT_STARTED,
                FundedNextMt5MutationState.OUTCOME_UNKNOWN,
            }
            for item in self._records.values()
        )

    def read_account(self, *, now: datetime):
        if not self._transport.connected():
            raise Mt5ExecutionBlockedError("mt5-disconnected")
        state = self._transport.account_state(self._account.account_ref)
        if state is None:
            raise Mt5ExecutionBlockedError("mt5-account-state-unavailable")
        _fresh(state.observed_at, now, self._max_spec_age, "account-state")
        return state

    def read_symbol(self, qore_symbol: str, *, now: datetime) -> Mt5SymbolSpecification:
        if qore_symbol not in {"AUDJPY", "GBPUSD", "GBPJPY"}:
            raise Mt5ExecutionBlockedError("symbol-outside-frozen-vt08-forex-universe")
        catalog = self._transport.available_symbols()
        matches = tuple(symbol for symbol in catalog if symbol == qore_symbol)
        if len(matches) != 1:
            raise Mt5ExecutionBlockedError("live-symbol-must-resolve-exactly-once")
        spec = self._transport.symbol_info(qore_symbol)
        if spec is None:
            raise Mt5ExecutionBlockedError("mt5-symbol-info-missing")
        _fresh(spec.observed_at, now, self._max_spec_age, "symbol-info")
        if not spec.trade_enabled or not spec.session_open:
            raise Mt5ExecutionBlockedError("mt5-symbol-not-tradable")
        if self._max_spread_points is not None and spec.spread_points > self._max_spread_points:
            raise Mt5ExecutionBlockedError("spread-outside-operational-containment")
        return spec

    def plan_submission(
        self,
        submission: ExecutionSubmission,
        *,
        now: datetime,
    ) -> FundedNextMt5OrderPlan:
        if now > submission.authorized_intent.authorization.expires_at:
            raise Mt5ExecutionBlockedError("canonical-pretrade-authorization-expired")
        intent = submission.authorized_intent.intent
        spec = self.read_symbol(intent.instrument.value, now=now)
        volume = intent.quantity.value
        if not spec.minimum_volume <= volume <= spec.maximum_volume:
            raise Mt5ExecutionBlockedError("authorized-volume-outside-broker-range")
        units = volume / spec.volume_step
        if units != units.to_integral_value():
            raise Mt5ExecutionBlockedError("authorized-volume-not-on-broker-step")
        if intent.stop_loss is None or intent.take_profit is None:
            raise Mt5ExecutionValidationError("live FundedNext order requires SL and TP")
        if intent.order_type is OrderType.LIMIT:
            if intent.limit_price is None:
                raise Mt5ExecutionValidationError("limit order requires limit price")
            entry = intent.limit_price.value
            limit_price = entry
        else:
            entry = spec.ask if intent.side is OrderSide.BUY else spec.bid
            limit_price = None
        stop = intent.stop_loss.value
        target = intent.take_profit.value
        _validate_geometry(intent.side, entry, stop, target, spec)
        margin_required = volume * spec.margin_per_volume
        account_state = self.read_account(now=now)
        if margin_required > account_state.free_margin:
            raise Mt5ExecutionBlockedError("insufficient-mt5-free-margin")
        return FundedNextMt5OrderPlan(
            client_order_id=f"qore-{submission.idempotency_key.value.hex[:24]}",
            qore_symbol=intent.instrument.value,
            provider_symbol=spec.provider_symbol,
            side=intent.side,
            order_type=intent.order_type,
            volume=volume,
            effective_entry=entry,
            limit_price=limit_price,
            stop_loss=stop,
            take_profit=target,
            margin_required=margin_required,
            planned_at=now,
        )

    def shadow_check(
        self,
        submission: ExecutionSubmission,
        *,
        now: datetime,
    ) -> FundedNextMt5ShadowReceipt:
        """Run complete broker-native preflight without order_send."""
        plan = self.plan_submission(submission, now=now)
        return self._transport.check_order(plan)

    def submit_live(
        self,
        submission: ExecutionSubmission,
        *,
        now: datetime,
    ) -> str:
        """Submit once after shadow check and durable mutation fence."""
        if not self._submission_enabled or not self._authorization.can_submit:
            raise Mt5ExecutionBlockedError("live-order-submission-disabled")
        if not self._rules.automated_mt5_allowed(now):
            raise Mt5ExecutionBlockedError("provider-automation-rules-not-current")
        if self.has_unresolved_mutations:
            raise Mt5ExecutionOutcomeUnknownError("unresolved-provider-state-suspends-new-orders")
        key = str(submission.idempotency_key.value)
        digest = fundednext_submission_digest(submission)
        prior = self._records.get(key)
        if prior is not None:
            if prior.submission_digest != digest:
                raise Mt5ExecutionValidationError("idempotency-key-submission-conflict")
            if prior.state is FundedNextMt5MutationState.ACCEPTED:
                assert prior.provider_order_ref is not None
                return prior.provider_order_ref
            raise Mt5ExecutionOutcomeUnknownError("existing-mutation-is-not-safely-replayable")
        plan = self.plan_submission(submission, now=now)
        shadow = self._transport.check_order(plan)
        if not shadow.broker_valid:
            raise Mt5ExecutionBlockedError(shadow.reason)
        risk_id, risk_fingerprint, reservation_id = extract_risk_provenance(submission)
        record = FundedNextMt5MutationRecord(
            idempotency_key=key,
            receipt_id=str(submission.receipt_id.value),
            submission_digest=digest,
            client_order_id=plan.client_order_id,
            state=FundedNextMt5MutationState.ATTEMPT_STARTED,
            transitioned_at=now,
            risk_authorization_id=risk_id,
            risk_authorization_fingerprint=risk_fingerprint,
            risk_reservation_id=reservation_id,
        )
        self._persist(record)
        outcome = self._transport.submit_order(plan)
        if outcome.outcome is Mt5ProviderOutcome.ACCEPTED and outcome.provider_order_ref:
            accepted = record.transition(
                state=FundedNextMt5MutationState.ACCEPTED,
                transitioned_at=outcome.recorded_at,
                provider_order_ref=outcome.provider_order_ref,
            )
            self._persist(accepted)
            return outcome.provider_order_ref
        if outcome.outcome is Mt5ProviderOutcome.REJECTED:
            rejected = record.transition(
                state=FundedNextMt5MutationState.REJECTED,
                transitioned_at=outcome.recorded_at,
                reason=outcome.reason or "provider-rejected",
            )
            self._persist(rejected)
            raise Mt5ExecutionRejectedError("provider-definitively-rejected-order")
        unknown = record.transition(
            state=FundedNextMt5MutationState.OUTCOME_UNKNOWN,
            transitioned_at=outcome.recorded_at,
            provider_order_ref=outcome.provider_order_ref,
            reason=outcome.reason or "provider-outcome-unknown",
        )
        self._persist(unknown)
        raise Mt5ExecutionOutcomeUnknownError("provider-outcome-unknown-reconcile-first")

    def reconcile_unknown(self, *, now: datetime) -> tuple[str, ...]:
        """Discover interrupted/unknown orders before any new mutation is allowed."""
        resolved: list[str] = []
        for key, record in tuple(self._records.items()):
            if record.state not in {
                FundedNextMt5MutationState.ATTEMPT_STARTED,
                FundedNextMt5MutationState.OUTCOME_UNKNOWN,
            }:
                continue
            found = self._transport.discover_order(record.client_order_id)
            if found is None:
                if record.state is FundedNextMt5MutationState.ATTEMPT_STARTED:
                    self._persist(
                        record.transition(
                            state=FundedNextMt5MutationState.OUTCOME_UNKNOWN,
                            transitioned_at=now,
                            reason="restart-discovery-not-yet-conclusive",
                        )
                    )
                continue
            if found.outcome is Mt5ProviderOutcome.ACCEPTED and found.provider_order_ref:
                state = FundedNextMt5MutationState.ACCEPTED
            elif found.outcome is Mt5ProviderOutcome.REJECTED:
                state = FundedNextMt5MutationState.REJECTED
            elif found.outcome is Mt5ProviderOutcome.CANCELLED:
                state = FundedNextMt5MutationState.CANCELLED
            else:
                continue
            self._persist(
                record.transition(
                    state=state,
                    transitioned_at=found.recorded_at,
                    provider_order_ref=found.provider_order_ref,
                    reason=found.reason,
                )
            )
            resolved.append(key)
        return tuple(sorted(resolved))

    def _mark_interrupted_attempts_unknown(self) -> None:
        now = datetime.now().astimezone()
        for key, record in tuple(self._records.items()):
            if record.state is FundedNextMt5MutationState.ATTEMPT_STARTED:
                self._persist(
                    record.transition(
                        state=FundedNextMt5MutationState.OUTCOME_UNKNOWN,
                        transitioned_at=now,
                        reason="runtime-restart-after-mutation-fence",
                    )
                )

    def _persist(self, record: FundedNextMt5MutationRecord) -> None:
        self._ledger.upsert(record)
        self._records[record.idempotency_key] = record


def _validate_geometry(
    side: OrderSide,
    entry: Decimal,
    stop: Decimal,
    target: Decimal,
    spec: Mt5SymbolSpecification,
) -> None:
    if side is OrderSide.BUY and not stop < entry < target:
        raise Mt5ExecutionBlockedError("invalid-long-order-geometry")
    if side is OrderSide.SELL and not target < entry < stop:
        raise Mt5ExecutionBlockedError("invalid-short-order-geometry")
    minimum_distance = spec.minimum_stop_distance_points * spec.point
    if abs(entry - stop) < minimum_distance or abs(target - entry) < minimum_distance:
        raise Mt5ExecutionBlockedError("broker-minimum-distance-violation")


def _fresh(observed_at: datetime, now: datetime, max_age: timedelta, name: str) -> None:
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise Mt5ExecutionValidationError(f"{name}-timestamp-naive")
    if observed_at > now:
        raise Mt5ExecutionValidationError(f"{name}-timestamp-from-future")
    if now - observed_at > max_age:
        raise Mt5ExecutionBlockedError(f"{name}-stale")
