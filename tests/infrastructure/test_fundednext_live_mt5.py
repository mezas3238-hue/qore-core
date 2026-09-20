from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import (
    RiskAuthorization,
    RiskDecision,
    TraderLineage,
)
from qore.infrastructure.execution_boundary import ExecutionSubmission
from qore.infrastructure.fundednext_live_authorization import (
    FundedNextLiveAccountAuthorization,
)
from qore.infrastructure.fundednext_live_mt5 import (
    FundedNextLiveMt5ExecutionGateway,
    MetaTrader5FundedNextLiveTransport,
)
from qore.infrastructure.fundednext_mt5 import (
    Mt5ExecutionBlockedError,
    Mt5ExecutionValidationError,
)
from qore.infrastructure.fundednext_mt5_mutation_ledger import (
    InMemoryFundedNextMt5MutationLedger,
)
from qore.infrastructure.fundednext_operational import build_account_bound_submission
from qore.infrastructure.fundednext_stellar_instant import (
    AutomationVerificationState,
    RuleVerificationState,
    StellarInstantRuleVerification,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.pretrade_safety import (
    ExecutionSafetySwitchSnapshot,
    ExecutionSwitchState,
)

_NOW = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
_SHA = "a" * 40
_HASH = "b" * 64


@dataclass
class _Terminal:
    connected: bool = True
    trade_allowed: bool = True
    tradeapi_disabled: bool = False


@dataclass
class _Account:
    login: int = 123456
    server: str = "FundedNext-Server"
    balance: float = 2000.0
    equity: float = 2000.0
    margin: float = 0.0
    margin_free: float = 2000.0
    trade_allowed: bool = True
    trade_expert: bool = True


@dataclass
class _Symbol:
    name: str = "GBPUSD"
    digits: int = 5
    point: float = 0.00001
    trade_contract_size: float = 100000.0
    trade_tick_size: float = 0.00001
    trade_tick_value: float = 1.0
    volume_min: float = 0.01
    volume_max: float = 40.0
    volume_step: float = 0.01
    trade_stops_level: int = 0
    trade_freeze_level: int = 0
    trade_mode: int = 4
    filling_mode: int = 3
    trade_exemode: int = 2


@dataclass
class _Tick:
    bid: float = 1.2500
    ask: float = 1.2502
    time: int = int(_NOW.timestamp())
    time_msc: int = int(_NOW.timestamp() * 1000)


@dataclass
class _Result:
    retcode: int
    order: int = 9001
    comment: str = ""


@dataclass
class _Order:
    ticket: int = 0
    magic: int = 0
    comment: str = ""
    state: int = 0


@dataclass
class _Deal:
    order: int = 0
    magic: int = 0
    comment: str = ""


class _Safety:
    def assert_new_order_allowed(self, submission: ExecutionSubmission) -> None:
        del submission


class _Api:
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5
    TRADE_ACTION_REMOVE = 8
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TIME_GTC = 0
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
    SYMBOL_TRADE_MODE_DISABLED = 0
    SYMBOL_TRADE_EXECUTION_MARKET = 2
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_PLACED = 10008
    TRADE_RETCODE_DONE_PARTIAL = 10010
    TRADE_RETCODE_TIMEOUT = 10012
    TRADE_RETCODE_CONNECTION = 10031
    ORDER_STATE_CANCELED = 2
    ORDER_STATE_REJECTED = 3
    ORDER_STATE_FILLED = 4
    ORDER_STATE_PARTIAL = 5

    def __init__(self, *, bid: float = 1.2500) -> None:
        self.sent = 0
        self.checked = 0
        self.bid = bid
        self.tick_time = int(_NOW.timestamp())
        self.tick_time_msc = int(_NOW.timestamp() * 1000)

    def terminal_info(self) -> _Terminal | None:
        return _Terminal()

    def account_info(self) -> _Account | None:
        return _Account()

    def symbols_get(self) -> tuple[_Symbol, ...] | None:
        return (_Symbol(),)

    def symbol_select(self, symbol: str, enable: bool) -> bool:
        return enable and symbol == "GBPUSD"

    def symbol_info(self, symbol: str) -> _Symbol | None:
        return _Symbol() if symbol == "GBPUSD" else None

    def symbol_info_tick(self, symbol: str) -> _Tick | None:
        return (
            _Tick(
                bid=self.bid,
                ask=self.bid + 0.0002,
                time=self.tick_time,
                time_msc=self.tick_time_msc,
            )
            if symbol == "GBPUSD"
            else None
        )

    def order_calc_margin(
        self,
        order_type: int,
        symbol: str,
        volume: float,
        price: float,
    ) -> float | None:
        del order_type, symbol, price
        return volume * 50.0

    def order_check(self, request: dict[str, object]) -> _Result | None:
        del request
        self.checked += 1
        return _Result(retcode=0, order=0)

    def order_send(self, request: dict[str, object]) -> _Result | None:
        del request
        self.sent += 1
        return _Result(retcode=self.TRADE_RETCODE_DONE)

    def orders_get(self) -> tuple[_Order, ...] | None:
        return ()

    def history_orders_get(
        self,
        date_from: datetime,
        date_to: datetime,
    ) -> tuple[_Order, ...] | None:
        del date_from, date_to
        return ()

    def history_deals_get(
        self,
        date_from: datetime,
        date_to: datetime,
    ) -> tuple[_Deal, ...] | None:
        del date_from, date_to
        return ()



class _NasApi(_Api):
    def symbols_get(self) -> tuple[_Symbol, ...] | None:
        return (
            _Symbol(
                name="NDX100",
                digits=1,
                point=0.1,
                trade_contract_size=1.0,
                trade_tick_size=0.1,
                trade_tick_value=1.0,
            ),
        )

    def symbol_select(self, symbol: str, enable: bool) -> bool:
        return enable and symbol == "NDX100"

    def symbol_info(self, symbol: str) -> _Symbol | None:
        if symbol != "NDX100":
            return None
        return _Symbol(
            name="NDX100",
            digits=1,
            point=0.1,
            trade_contract_size=1.0,
            trade_tick_size=0.1,
            trade_tick_value=1.0,
        )

    def symbol_info_tick(self, symbol: str) -> _Tick | None:
        return _Tick(bid=20000.0, ask=20000.2) if symbol == "NDX100" else None


def _account_identity() -> MarketTestAccountIdentity:
    return MarketTestAccountIdentity(
        provider_key="fundednext-stellar-instant-mt5",
        account_ref="fundednext-stellar-instant-live",
        environment=MarketRuntimeEnvironment.PRODUCTION,
    )


def _live_auth(*, complete: bool) -> FundedNextLiveAccountAuthorization:
    return FundedNextLiveAccountAuthorization(
        account=_account_identity(),
        git_sha=_SHA,
        account_identity_fingerprint=_HASH,
        expected_server="FundedNext-Server",
        provider_rules_fingerprint=_HASH,
        no_send_evidence_sha256=_HASH,
        shadow_evidence_sha256=_HASH,
        restart_recovery_evidence_sha256=_HASH,
        ea_entitlement_verified=True,
        vps_entitlement_verified=True,
        provider_rules_current=True,
        no_send_passed=True,
        shadow_passed=complete,
        service_24_7_verified=complete,
        restart_recovery_passed=complete,
        activation_timestamp=_NOW,
        order_submission_authorized=complete,
    )


def _rules() -> StellarInstantRuleVerification:
    return StellarInstantRuleVerification(
        verification_state=RuleVerificationState.CURRENT,
        automation_state=AutomationVerificationState.VERIFIED,
        ea_addon_verified=True,
        platform_verified=True,
        exact_product_verified=True,
    )


def _submission() -> ExecutionSubmission:
    auth = RiskAuthorization(
        authorization_id="risk-test",
        account_binding_id=_HASH,
        trader_id=TraderLineage.VT08_FOREX,
        request_id="request-test",
        signal_fingerprint="signal-test",
        qore_symbol="GBPUSD",
        provider_symbol="GBPUSD",
        side="short",
        entry_type="market",
        intended_entry=Decimal("1.2500"),
        stop_loss=Decimal("1.2550"),
        take_profit=Decimal("1.2400"),
        requested_volume=Decimal("0.01"),
        authorized_volume=Decimal("0.01"),
        monetary_stop_loss=Decimal("5.07"),
        aggregate_pre_order_worst_case=Decimal("0"),
        aggregate_post_order_worst_case=Decimal("5.07"),
        provider_headroom=Decimal("120"),
        internal_qore_headroom=Decimal("20"),
        margin_reserved=Decimal("0.5"),
        decision=RiskDecision.ALLOW,
        reason="test",
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=2),
        authorization_fingerprint="c" * 64,
    )
    return build_account_bound_submission(
        auth,
        switch=ExecutionSafetySwitchSnapshot(
            state=ExecutionSwitchState.ENABLED,
            observed_at=_NOW,
            reason="test live switch",
        ),
        authorized_at=_NOW,
        submitted_at=_NOW,
    )


def _gateway(
    api: _Api,
    *,
    complete: bool,
    submission_enabled: bool,
    clock: Callable[[], datetime] | None = None,
    rules: StellarInstantRuleVerification | None = None,
) -> FundedNextLiveMt5ExecutionGateway:
    transport = MetaTrader5FundedNextLiveTransport(
        api=api,
        qore_account_ref="fundednext-stellar-instant-live",
        expected_login=123456,
        expected_server="FundedNext-Server",
        clock=clock or (lambda: _NOW),
    )
    return FundedNextLiveMt5ExecutionGateway(
        account=_account_identity(),
        transport=transport,
        mutation_ledger=InMemoryFundedNextMt5MutationLedger(),
        rule_verification=rules or _rules(),
        live_authorization=_live_auth(complete=complete),
        safety=_Safety(),
        runtime_git_sha=_SHA,
        account_identity_fingerprint=_HASH,
        expected_server="FundedNext-Server",
        submission_enabled=submission_enabled,
    )


def test_shadow_order_check_never_sends() -> None:
    api = _Api()
    gateway = _gateway(api, complete=False, submission_enabled=False)
    receipt = gateway.shadow_check(_submission(), now=_NOW)
    assert receipt.broker_valid is True
    assert api.checked == 1
    assert api.sent == 0


def test_live_send_rechecks_broker_order_after_final_fresh_market_gate() -> None:
    api = _Api()
    gateway = _gateway(api, complete=True, submission_enabled=True)
    gateway.submit_live(_submission(), now=_NOW)
    assert api.checked == 2
    assert api.sent == 1


def test_live_send_requires_complete_activation() -> None:
    api = _Api()
    gateway = _gateway(api, complete=False, submission_enabled=True)
    with pytest.raises(Mt5ExecutionBlockedError, match="submission-disabled"):
        gateway.submit_live(_submission(), now=_NOW)
    assert api.sent == 0


def test_rule_verification_failure_occurs_after_order_check_and_before_send() -> None:
    api = _Api()
    blocked_rules = StellarInstantRuleVerification(
        verification_state=RuleVerificationState.CONFLICTED,
        automation_state=AutomationVerificationState.VERIFIED,
        ea_addon_verified=True,
        platform_verified=True,
        exact_product_verified=True,
    )
    gateway = _gateway(
        api,
        complete=True,
        submission_enabled=True,
        rules=blocked_rules,
    )
    with pytest.raises(Mt5ExecutionBlockedError, match="provider-automation-rules-not-current"):
        gateway.submit_live(_submission(), now=_NOW)
    assert api.checked == 1
    assert api.sent == 0


def test_broker_price_may_not_expand_sovereign_risk_in_shadow() -> None:
    api = _Api(bid=1.2498)
    gateway = _gateway(api, complete=False, submission_enabled=False)
    with pytest.raises(Mt5ExecutionBlockedError, match="entry-drift|risk-exceeds"):
        gateway.shadow_check(_submission(), now=_NOW)
    assert api.sent == 0


def test_account_observation_allows_subsecond_call_order_skew() -> None:
    api = _Api()
    gateway = _gateway(
        api,
        complete=False,
        submission_enabled=False,
        clock=lambda: _NOW + timedelta(milliseconds=500),
    )
    state = gateway.read_account(now=_NOW)
    assert state.balance == Decimal("2000.0")


def test_shadow_read_allows_retained_tick_but_live_send_requires_fresh_tick() -> None:
    api = _Api()
    stale = _NOW - timedelta(seconds=2, milliseconds=1)
    api.tick_time = int(stale.timestamp())
    api.tick_time_msc = int(stale.timestamp() * 1000)

    shadow_gateway = _gateway(api, complete=False, submission_enabled=False)
    spec = shadow_gateway.read_symbol("GBPUSD", now=_NOW)
    assert spec.provider_symbol == "GBPUSD"
    assert shadow_gateway.shadow_check(_submission(), now=_NOW).broker_valid is True
    assert api.sent == 0

    live_gateway = _gateway(api, complete=True, submission_enabled=True)
    with pytest.raises(Mt5ExecutionBlockedError, match="broker-tick-older-than-2s"):
        live_gateway.submit_live(_submission(), now=_NOW)
    assert api.sent == 0


def test_account_observation_rejects_material_future_timestamp() -> None:
    api = _Api()
    gateway = _gateway(
        api,
        complete=False,
        submission_enabled=False,
        clock=lambda: _NOW + timedelta(seconds=2),
    )
    with pytest.raises(Mt5ExecutionValidationError, match="account-state-timestamp-from-future"):
        gateway.read_account(now=_NOW)


def test_live_gateway_resolves_nas100_to_ndx100() -> None:
    api = _NasApi()
    gateway = _gateway(api, complete=False, submission_enabled=False)
    spec = gateway.read_symbol("NAS100", now=_NOW)
    assert spec.provider_symbol == "NDX100"
