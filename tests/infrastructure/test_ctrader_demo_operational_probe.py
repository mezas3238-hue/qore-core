from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.infrastructure.ctrader_demo_market_data import CTraderTrendbar
from qore.infrastructure.ctrader_demo_operational_probe import (
    CTraderClientPermissionScope,
    CTraderDemoOperationalObservation,
    CTraderDemoOperationalProbeInputs,
    CTraderDemoOperationalProbeValidationError,
    CTraderFullSymbolObservation,
    CTraderGrantedAccount,
    CTraderLightSymbolObservation,
    CTraderTrendbarsResponseObservation,
    closed_m5_interval,
    run_ctrader_demo_closed_m5_probe,
    unix_milliseconds,
)
from qore.kernel.result import Failure, Success

_STARTED_AT = datetime(2026, 8, 12, 13, 7, 42, 123456, tzinfo=UTC)
_OPENED_AT_MINUTES = 29_775_660
_ACCOUNT_ID = 7_654_321
_SYMBOL_ID = 1_234


def _inputs(
    *,
    instrument: str = "EURUSD",
    started_at: datetime = _STARTED_AT,
) -> CTraderDemoOperationalProbeInputs:
    return CTraderDemoOperationalProbeInputs(
        run_key="290-1",
        instrument=instrument,
        started_at=started_at,
    )


def _trendbar(
    *,
    delta_open: int = 10,
    delta_high: int = 50,
    delta_close: int = 25,
    opened_at_minutes: int = _OPENED_AT_MINUTES,
) -> CTraderTrendbar:
    return CTraderTrendbar(
        low_relative=110_000,
        delta_open=delta_open,
        delta_high=delta_high,
        delta_close=delta_close,
        utc_timestamp_in_minutes=opened_at_minutes,
    )


def _account(
    *,
    account_id: int = _ACCOUNT_ID,
    is_live: bool = False,
    explicit: bool = True,
) -> CTraderGrantedAccount:
    return CTraderGrantedAccount(
        account_id=account_id,
        is_live=is_live,
        is_live_explicit=explicit,
    )


def _light_symbol(
    *,
    symbol_id: int = _SYMBOL_ID,
    symbol_name: str = "EUR/USD",
    enabled: bool = True,
    symbol_name_explicit: bool = True,
    enabled_explicit: bool = True,
) -> CTraderLightSymbolObservation:
    return CTraderLightSymbolObservation(
        symbol_id=symbol_id,
        symbol_name=symbol_name,
        enabled=enabled,
        symbol_name_explicit=symbol_name_explicit,
        enabled_explicit=enabled_explicit,
    )


def _response(
    *,
    account_id: int = _ACCOUNT_ID,
    symbol_id: int = _SYMBOL_ID,
    symbol_id_explicit: bool = True,
    period_code: int = 5,
    trendbars: tuple[CTraderTrendbar, ...] | None = None,
    trendbar_fields_explicit: bool = True,
    has_more: bool = False,
) -> CTraderTrendbarsResponseObservation:
    return CTraderTrendbarsResponseObservation(
        account_id=account_id,
        symbol_id=symbol_id,
        symbol_id_explicit=symbol_id_explicit,
        period_code=period_code,
        trendbars=(_trendbar(),) if trendbars is None else trendbars,
        trendbar_fields_explicit=trendbar_fields_explicit,
        has_more=has_more,
    )


def _observation(
    *,
    permission_scope: CTraderClientPermissionScope = CTraderClientPermissionScope.VIEW,
    permission_scope_explicit: bool = True,
    granted_accounts: tuple[CTraderGrantedAccount, ...] | None = None,
    authorized_account_id: int = _ACCOUNT_ID,
    light_symbols: tuple[CTraderLightSymbolObservation, ...] | None = None,
    full_symbol: CTraderFullSymbolObservation | None = None,
    trendbars_response: CTraderTrendbarsResponseObservation | None = None,
) -> CTraderDemoOperationalObservation:
    return CTraderDemoOperationalObservation(
        permission_scope=permission_scope,
        permission_scope_explicit=permission_scope_explicit,
        granted_accounts=(_account(),) if granted_accounts is None else granted_accounts,
        authorized_account_id=authorized_account_id,
        light_symbols=(_light_symbol(),) if light_symbols is None else light_symbols,
        full_symbol=(
            CTraderFullSymbolObservation(symbol_id=_SYMBOL_ID, digits=5)
            if full_symbol is None
            else full_symbol
        ),
        trendbars_response=_response() if trendbars_response is None else trendbars_response,
    )


def test_closed_m5_interval_uses_latest_completed_boundary() -> None:
    opened_at, closed_at = closed_m5_interval(_STARTED_AT)

    assert opened_at == datetime(2026, 8, 12, 13, 0, tzinfo=UTC)
    assert closed_at == datetime(2026, 8, 12, 13, 5, tzinfo=UTC)


def test_closed_m5_interval_at_exact_boundary_uses_preceding_bar() -> None:
    opened_at, closed_at = closed_m5_interval(
        datetime(2026, 8, 12, 13, 5, tzinfo=UTC)
    )

    assert opened_at == datetime(2026, 8, 12, 13, 0, tzinfo=UTC)
    assert closed_at == datetime(2026, 8, 12, 13, 5, tzinfo=UTC)


def test_unix_milliseconds_is_exact_without_float_conversion() -> None:
    assert unix_milliseconds(datetime(1970, 1, 1, tzinfo=UTC)) == 0
    assert (
        unix_milliseconds(datetime(2026, 8, 12, 13, 5, tzinfo=UTC))
        == 1_786_539_900_000
    )


def test_real_observation_projects_through_existing_flow_into_sanitized_evidence() -> None:
    result = run_ctrader_demo_closed_m5_probe(_inputs(), _observation())

    assert isinstance(result, Success)
    evidence = result.value
    assert evidence.provider_key == "ctrader-open-api"
    assert evidence.environment == "demo"
    assert evidence.endpoint_host == "demo.ctraderapi.com"
    assert evidence.instrument == "EURUSD"
    assert evidence.symbol_id == _SYMBOL_ID
    assert evidence.digits == 5
    assert evidence.timeframe_seconds == 300
    assert evidence.opened_at == datetime(2026, 8, 12, 13, 0, tzinfo=UTC)
    assert evidence.closed_at == datetime(2026, 8, 12, 13, 5, tzinfo=UTC)
    assert evidence.open == 1.1001
    assert evidence.high == 1.1005
    assert evidence.low == 1.1
    assert evidence.close == 1.10025
    assert isinstance(evidence.snapshot_id, UUID)
    payload = evidence.public_payload()
    assert "account_id" not in payload
    assert str(_ACCOUNT_ID) not in evidence.to_json()
    assert "access_token" not in evidence.to_json().lower()
    assert "client_secret" not in evidence.to_json().lower()


@pytest.mark.parametrize(
    ("scope", "explicit"),
    (
        (CTraderClientPermissionScope.TRADE, True),
        (CTraderClientPermissionScope.VIEW, False),
    ),
)
def test_probe_requires_explicit_view_only_permission(
    scope: CTraderClientPermissionScope,
    explicit: bool,
) -> None:
    result = run_ctrader_demo_closed_m5_probe(
        _inputs(),
        _observation(permission_scope=scope, permission_scope_explicit=explicit),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoOperationalProbeValidationError)


@pytest.mark.parametrize(
    "accounts",
    (
        (),
        (_account(), _account(account_id=_ACCOUNT_ID + 1)),
        (_account(is_live=True),),
        (_account(explicit=False),),
    ),
)
def test_probe_requires_exactly_one_explicit_demo_account(
    accounts: tuple[CTraderGrantedAccount, ...],
) -> None:
    result = run_ctrader_demo_closed_m5_probe(
        _inputs(),
        _observation(granted_accounts=accounts),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoOperationalProbeValidationError)


def test_probe_rejects_authorized_account_mismatch() -> None:
    result = run_ctrader_demo_closed_m5_probe(
        _inputs(),
        _observation(authorized_account_id=_ACCOUNT_ID + 1),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoOperationalProbeValidationError)


def test_symbol_name_normalization_accepts_ctrader_slash_form() -> None:
    result = run_ctrader_demo_closed_m5_probe(
        _inputs(instrument="GBPUSD"),
        _observation(
            light_symbols=(
                _light_symbol(symbol_name="GBP/USD"),
                _light_symbol(symbol_id=_SYMBOL_ID + 1, symbol_name="EUR/USD"),
            ),
            full_symbol=CTraderFullSymbolObservation(
                symbol_id=_SYMBOL_ID,
                digits=5,
            ),
            trendbars_response=_response(symbol_id=_SYMBOL_ID),
        ),
    )

    assert isinstance(result, Success)
    assert result.value.instrument == "GBPUSD"


@pytest.mark.parametrize(
    "symbols",
    (
        (),
        (_light_symbol(enabled=False),),
        (
            _light_symbol(),
            _light_symbol(symbol_id=_SYMBOL_ID + 1, symbol_name="EURUSD"),
        ),
        (_light_symbol(symbol_name_explicit=False),),
        (_light_symbol(enabled_explicit=False),),
    ),
)
def test_probe_rejects_unusable_or_ambiguous_symbol_selection(
    symbols: tuple[CTraderLightSymbolObservation, ...],
) -> None:
    result = run_ctrader_demo_closed_m5_probe(
        _inputs(),
        _observation(light_symbols=symbols),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoOperationalProbeValidationError)


def test_probe_rejects_full_symbol_id_mismatch() -> None:
    result = run_ctrader_demo_closed_m5_probe(
        _inputs(),
        _observation(
            full_symbol=CTraderFullSymbolObservation(
                symbol_id=_SYMBOL_ID + 1,
                digits=5,
            )
        ),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoOperationalProbeValidationError)


@pytest.mark.parametrize(
    "response",
    (
        _response(account_id=_ACCOUNT_ID + 1),
        _response(symbol_id=_SYMBOL_ID + 1),
        _response(symbol_id_explicit=False),
        _response(period_code=6),
        _response(trendbar_fields_explicit=False),
    ),
)
def test_probe_rejects_unbound_trendbar_response(
    response: CTraderTrendbarsResponseObservation,
) -> None:
    result = run_ctrader_demo_closed_m5_probe(
        _inputs(),
        _observation(trendbars_response=response),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoOperationalProbeValidationError)


@pytest.mark.parametrize(
    "response",
    (
        _response(trendbars=()),
        _response(trendbars=(_trendbar(), _trendbar())),
        _response(has_more=True),
    ),
)
def test_existing_mapping_rejects_non_exact_trendbar_set(
    response: CTraderTrendbarsResponseObservation,
) -> None:
    result = run_ctrader_demo_closed_m5_probe(
        _inputs(),
        _observation(trendbars_response=response),
    )

    assert isinstance(result, Failure)


def test_operational_probe_rejects_zero_delta_high_as_upstream_ambiguous() -> None:
    result = run_ctrader_demo_closed_m5_probe(
        _inputs(),
        _observation(
            trendbars_response=_response(
                trendbars=(
                    _trendbar(
                        delta_open=0,
                        delta_high=0,
                        delta_close=0,
                    ),
                )
            )
        ),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoOperationalProbeValidationError)
    assert "ambiguous" in str(result.error)


def test_canonical_flow_rejects_trendbar_interval_mismatch() -> None:
    result = run_ctrader_demo_closed_m5_probe(
        _inputs(),
        _observation(
            trendbars_response=_response(
                trendbars=(
                    _trendbar(opened_at_minutes=_OPENED_AT_MINUTES - 5),
                )
            )
        ),
    )

    assert isinstance(result, Failure)


def test_evidence_and_probe_are_deterministic_for_identical_observation() -> None:
    first = run_ctrader_demo_closed_m5_probe(_inputs(), _observation())
    second = run_ctrader_demo_closed_m5_probe(_inputs(), _observation())

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value == second.value
    assert first.value.to_json() == second.value.to_json()
    assert first.value.snapshot_id == second.value.snapshot_id


def test_probe_inputs_reject_non_allowlisted_instrument() -> None:
    with pytest.raises(CTraderDemoOperationalProbeValidationError):
        _inputs(instrument="USDJPY")


def test_account_identifiers_are_redacted_from_repr() -> None:
    account = _account()
    observation = _observation()

    assert str(_ACCOUNT_ID) not in repr(account)
    assert str(_ACCOUNT_ID) not in repr(observation)
    assert "sha256:" in repr(account)
    assert "sha256:" in repr(observation)
