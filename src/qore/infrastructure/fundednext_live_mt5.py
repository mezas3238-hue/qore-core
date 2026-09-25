"""Production-only FundedNext MT5 gateway and broker shadow preflight.

The TEST/DEMO gateway remains separate.  This PRODUCTION boundary requires
exact-SHA activation evidence, a live operational safety boundary, broker-native
``order_check`` and a broker-executable stop-risk recheck before mutation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Protocol

from qore.infrastructure.execution_boundary import ExecutionSubmission
from qore.infrastructure.fundednext_execution_bridge import extract_risk_provenance
from qore.infrastructure.fundednext_live_authorization import (
    FundedNextLiveAccountAuthorization,
    FundedNextLiveAuthorizationError,
)
from qore.infrastructure.fundednext_live_guard import (
    FundedNextLiveGuardError,
    assert_certified_direction,
    assert_certified_entry_drift,
    market_stop_risk_usd,
)
from qore.infrastructure.fundednext_mt5 import (
    FundedNextMt5OrderPlan,
    Mt5AccountState,
    Mt5ExecutionBlockedError,
    Mt5ExecutionOutcomeUnknownError,
    Mt5ExecutionRejectedError,
    Mt5ExecutionValidationError,
    Mt5ProviderOutcome,
    Mt5SymbolSpecification,
)
from qore.infrastructure.fundednext_mt5_clock import normalise_fundednext_server_epoch
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
from qore.infrastructure.fundednext_rule_refresh import RollingStellarInstantRuleVerification
from qore.infrastructure.fundednext_stellar_instant import (
    PILOT_SYMBOL_MAP,
    StellarInstantRuleVerification,
    opening_commission_per_lot,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import OrderSide, OrderType
from qore.infrastructure.trader_execution_profile import M1_PROFILE


_OUTCOME_UNKNOWN_ABSENCE_CONFIRMATION_DELAY = timedelta(seconds=60)


class Mt5CheckResultLike(Protocol):
    retcode: int
    comment: str


class LiveMetaTrader5Api(MetaTrader5Api, Protocol):
    def order_check(self, request: dict[str, object]) -> Mt5CheckResultLike | None: ...


class LiveOperationalSafetyBoundary(Protocol):
    def assert_new_order_allowed(self, submission: ExecutionSubmission) -> None: ...


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
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__(
            api=api,
            qore_account_ref=qore_account_ref,
            expected_login=expected_login,
            expected_server=expected_server,
        )
        self._live_api = api
        self._clock = clock or _system_utc_now

    def account_state(self, account_ref: str) -> Mt5AccountState | None:
        state = super().account_state(account_ref)
        if state is None:
            return None
        return replace(state, observed_at=self._now())

    def symbol_info(self, provider_symbol: str) -> Mt5SymbolSpecification | None:
        spec = super().symbol_info(provider_symbol)
        if spec is None:
            return None
        return replace(spec, observed_at=self._now())

    def assert_fresh_broker_market(
        self,
        provider_symbol: str,
        *,
        max_tick_age: timedelta = M1_PROFILE.tick_max_age,
    ) -> datetime:
        """Fail closed immediately before a LIVE broker mutation.

        SHADOW/order_check may inspect retained broker state while a market is
        closed. Freshness is an execution invariant, not a deployment
        invariant, so the <=2s broker-tick gate belongs only on the mutation
        path.
        """
        self._require_bound_account()
        if not self._live_api.symbol_select(provider_symbol, True):
            raise Mt5ExecutionBlockedError("mt5-symbol-select-failed-before-send")
        info = self._live_api.symbol_info(provider_symbol)
        tick = self._live_api.symbol_info_tick(provider_symbol)
        if info is None or tick is None:
            raise Mt5ExecutionBlockedError("mt5-broker-market-unavailable-before-send")
        if info.trade_mode == self._live_api.SYMBOL_TRADE_MODE_DISABLED:
            raise Mt5ExecutionBlockedError("mt5-symbol-trading-disabled-before-send")
        bid = Decimal(str(tick.bid))
        ask = Decimal(str(tick.ask))
        if bid <= 0 or ask <= 0:
            raise Mt5ExecutionBlockedError("mt5-session-not-open-before-send")
        observed = self._now()
        tick_at = _broker_tick_at(tick)
        tick_age = observed - tick_at
        if tick_age < timedelta(seconds=-0.5):
            raise Mt5ExecutionBlockedError("mt5-broker-tick-from-future")
        if tick_age > max_tick_age:
            raise Mt5ExecutionBlockedError("mt5-broker-tick-older-than-2s")
        return observed

    def check_order(self, plan: FundedNextMt5OrderPlan) -> FundedNextMt5ShadowReceipt:
        self._require_bound_account()
        request = self._submission_payload(plan)
        result = self._live_api.order_check(request)
        now = self._now()
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
            reason=("mt5-order-check-ok" if valid else f"mt5-order-check-retcode-{result.retcode}"),
            checked_at=now,
        )

    def _now(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise Mt5ExecutionValidationError("live MT5 clock must be timezone-aware")
        return value.astimezone(UTC)

    def observed_now(self) -> datetime:
        """Read the same clock used to timestamp completed MT5 observations."""

        return self._now()


class FundedNextLiveMt5ExecutionGateway:
    """Production gateway that cannot create or exceed capital authority."""

    def __init__(
        self,
        *,
        account: MarketTestAccountIdentity,
        transport: MetaTrader5FundedNextLiveTransport,
        mutation_ledger: FundedNextMt5MutationLedger,
        rule_verification: StellarInstantRuleVerification | RollingStellarInstantRuleVerification,
        live_authorization: FundedNextLiveAccountAuthorization,
        safety: LiveOperationalSafetyBoundary,
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
        if not callable(getattr(safety, "assert_new_order_allowed", None)):
            raise Mt5ExecutionValidationError("live operational safety boundary is required")
        try:
            live_authorization.assert_matches(
                account=account,
                git_sha=runtime_git_sha,
                account_identity_fingerprint=account_identity_fingerprint,
                server=expected_server,
            )
        except FundedNextLiveAuthorizationError as error:
            raise Mt5ExecutionBlockedError(str(error)) from error
        if not isinstance(
            rule_verification,
            (StellarInstantRuleVerification, RollingStellarInstantRuleVerification),
        ):
            raise Mt5ExecutionValidationError("Stellar Instant rules verification required")
        if max_spec_age <= timedelta(0):
            raise Mt5ExecutionValidationError("max_spec_age must be positive")
        self._account = account
        self._transport = transport
        self._ledger = mutation_ledger
        self._rules = rule_verification
        self._authorization = live_authorization
        self._safety = safety
        self._submission_enabled = bool(submission_enabled)
        self._max_spec_age = max_spec_age
        self._max_spread_points = max_spread_points
        self._records = {item.idempotency_key: item for item in mutation_ledger.records()}
        self._mark_interrupted_attempts_unknown()

    @property
    def unresolved_mutations(self) -> tuple[FundedNextMt5MutationRecord, ...]:
        return tuple(
            item
            for item in self._records.values()
            if item.state
            in {
                FundedNextMt5MutationState.ATTEMPT_STARTED,
                FundedNextMt5MutationState.OUTCOME_UNKNOWN,
            }
        )

    @property
    def has_unresolved_mutations(self) -> bool:
        return bool(self.unresolved_mutations)

    def read_account(self, *, now: datetime) -> Mt5AccountState:
        if not self._transport.connected():
            raise Mt5ExecutionBlockedError("mt5-disconnected")
        state = self._transport.account_state(self._account.account_ref)
        if state is None:
            raise Mt5ExecutionBlockedError("mt5-account-state-unavailable")
        validation_now = max(now.astimezone(UTC), self._transport.observed_now())
        _fresh(state.observed_at, validation_now, self._max_spec_age, "account-state")
        return state

    def read_symbol(self, qore_symbol: str, *, now: datetime) -> Mt5SymbolSpecification:
        if qore_symbol not in {"AUDJPY", "GBPUSD", "GBPJPY", "EURUSD", "XAUUSD", "NAS100"}:
            raise Mt5ExecutionBlockedError("symbol-outside-certified-live-universe")
        provider_symbol = PILOT_SYMBOL_MAP.get(qore_symbol, qore_symbol)
        catalog = self._transport.available_symbols()
        matches = tuple(symbol for symbol in catalog if symbol == provider_symbol)
        if len(matches) != 1:
            raise Mt5ExecutionBlockedError("live-symbol-must-resolve-exactly-once")
        spec = self._transport.symbol_info(provider_symbol)
        if spec is None:
            raise Mt5ExecutionBlockedError("mt5-symbol-info-missing")
        validation_now = max(now.astimezone(UTC), self._transport.observed_now())
        _fresh(spec.observed_at, validation_now, self._max_spec_age, "symbol-info")
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
        self._safety.assert_new_order_allowed(submission)
        if now > submission.authorized_intent.authorization.expires_at:
            raise Mt5ExecutionBlockedError("canonical-pretrade-authorization-expired")
        intent = submission.authorized_intent.intent
        side_text = "long" if intent.side is OrderSide.BUY else "short"
        try:
            assert_certified_direction(intent.instrument.value, side_text)
        except FundedNextLiveGuardError as error:
            raise Mt5ExecutionBlockedError(str(error)) from error
        spec = self.read_symbol(intent.instrument.value, now=now)
        expected_provider = intent.metadata.attributes.get("provider-symbol")
        if expected_provider != spec.provider_symbol:
            raise Mt5ExecutionBlockedError("risk-provider-symbol-account-mismatch")
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
        _assert_broker_executable_risk(
            submission=submission,
            entry=entry,
            stop=stop,
            spec=spec,
            volume=volume,
        )
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
        plan = self.plan_submission(submission, now=now)
        return self._transport.check_order(plan)

    def submit_live(
        self,
        submission: ExecutionSubmission,
        *,
        now: datetime,
    ) -> str:
        if not self._submission_enabled or not self._authorization.can_submit:
            raise Mt5ExecutionBlockedError("live-order-submission-disabled")
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
        if not self._rules.automated_mt5_allowed(now):
            raise Mt5ExecutionBlockedError("provider-automation-rules-not-current")

        # Final mutation gate: SHADOW can validate retained market state, but
        # LIVE cannot cross the broker boundary unless the broker is producing
        # a genuinely fresh executable tick at this exact point.
        final_checked_at = self._transport.assert_fresh_broker_market(
            plan.provider_symbol,
            max_tick_age=M1_PROFILE.tick_max_age,
        )
        if final_checked_at > submission.authorized_intent.authorization.expires_at:
            raise Mt5ExecutionBlockedError("canonical-pretrade-authorization-expired-before-send")

        # Re-plan against the latest broker snapshot after the fresh-tick gate
        # so certified entry drift, geometry, margin and risk are revalidated
        # immediately before mutation.
        plan = self.plan_submission(submission, now=final_checked_at)
        final_shadow = self._transport.check_order(plan)
        if not final_shadow.broker_valid:
            raise Mt5ExecutionBlockedError(final_shadow.reason)
        self._transport.assert_fresh_broker_market(
            plan.provider_symbol,
            max_tick_age=M1_PROFILE.tick_max_age,
        )

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
            elif (
                found.outcome is Mt5ProviderOutcome.UNKNOWN
                and found.reason == "mt5-order-not-found-conclusive"
                and now - record.transitioned_at
                >= _OUTCOME_UNKNOWN_ABSENCE_CONFIRMATION_DELAY
            ):
                state = FundedNextMt5MutationState.NOT_SUBMITTED
            else:
                if record.state is FundedNextMt5MutationState.ATTEMPT_STARTED:
                    self._persist(
                        record.transition(
                            state=FundedNextMt5MutationState.OUTCOME_UNKNOWN,
                            transitioned_at=found.recorded_at,
                            provider_order_ref=found.provider_order_ref,
                            reason=found.reason or "provider-discovery-not-conclusive",
                        )
                    )
                continue
            self._persist(
                record.transition(
                    state=state,
                    transitioned_at=found.recorded_at,
                    provider_order_ref=found.provider_order_ref,
                    reason=(
                        found.reason
                        if state is not FundedNextMt5MutationState.NOT_SUBMITTED
                        else "provider-history-confirmed-order-absent"
                    ),
                )
            )
            resolved.append(key)
        return tuple(sorted(resolved))

    def _mark_interrupted_attempts_unknown(self) -> None:
        now = datetime.now(UTC)
        for _key, record in tuple(self._records.items()):
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


def _broker_tick_at(tick: object) -> datetime:
    raw_msc = int(getattr(tick, "time_msc", 0) or 0)
    if raw_msc > 0:
        raw_seconds, millis = divmod(raw_msc, 1000)
        return normalise_fundednext_server_epoch(raw_seconds) + timedelta(milliseconds=millis)
    raw_seconds = int(getattr(tick, "time", 0) or 0)
    if raw_seconds > 0:
        return normalise_fundednext_server_epoch(raw_seconds)
    raise Mt5ExecutionBlockedError("mt5-broker-tick-timestamp-unavailable")


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _assert_broker_executable_risk(
    *,
    submission: ExecutionSubmission,
    entry: Decimal,
    stop: Decimal,
    spec: Mt5SymbolSpecification,
    volume: Decimal,
) -> None:
    attrs = submission.authorized_intent.intent.metadata.attributes
    try:
        authorized_risk = Decimal(str(attrs["risk-monetary-stop-loss"]))
        intended_entry = Decimal(str(attrs["risk-intended-entry"]))
        authorized_volume = Decimal(str(attrs["risk-authorized-volume"]))
    except (KeyError, InvalidOperation) as error:
        raise Mt5ExecutionValidationError("sovereign-risk-envelope-missing") from error
    if authorized_volume != volume:
        raise Mt5ExecutionBlockedError("broker-volume-differs-from-risk-authorization")
    intent = submission.authorized_intent.intent
    if intent.order_type is OrderType.MARKET:
        trader_id = attrs.get("trader-id")
        if trader_id == "R34_XAUUSD":
            base_risk = abs(intended_entry - stop)
            if base_risk <= 0:
                raise Mt5ExecutionBlockedError("r34-live-entry-risk-invalid")
            adverse = (
                max(Decimal(0), entry - intended_entry)
                if intent.side is OrderSide.BUY
                else max(Decimal(0), intended_entry - entry)
            )
            if adverse / base_risk > Decimal("0.02"):
                raise Mt5ExecutionBlockedError("r34-live-entry-drift-exceeds-buffer")
        else:
            try:
                assert_certified_entry_drift(
                    intended_entry=intended_entry,
                    executable_entry=entry,
                    tick_size=spec.tick_size,
                )
            except FundedNextLiveGuardError as error:
                raise Mt5ExecutionBlockedError(str(error)) from error
    commission_per_lot = opening_commission_per_lot(
        intent.instrument.value,
        executable_entry=entry,
        contract_size=spec.contract_size,
    )
    actual_risk = market_stop_risk_usd(
        executable_entry=entry,
        stop_loss=stop,
        tick_size=spec.tick_size,
        tick_value=spec.tick_value,
        volume=volume,
        opening_commission_per_lot=commission_per_lot,
    )
    if actual_risk > authorized_risk:
        raise Mt5ExecutionBlockedError("broker-executable-risk-exceeds-sovereign-authorization")


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
    future_skew = observed_at - now
    if future_skew > timedelta(seconds=1):
        raise Mt5ExecutionValidationError(f"{name}-timestamp-from-future")
    reference_now = observed_at if future_skew > timedelta(0) else now
    if reference_now - observed_at > max_age:
        raise Mt5ExecutionBlockedError(f"{name}-stale")
