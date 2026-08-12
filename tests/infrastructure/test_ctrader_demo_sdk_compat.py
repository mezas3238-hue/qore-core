from __future__ import annotations

from datetime import UTC, datetime

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
)
from qore.infrastructure.ctrader_demo_sdk_compat import (
    run_ctrader_demo_sdk_compat_probe,
)
from qore.kernel.result import Failure, Success

_ACCOUNT_ID = 7_654_321
_SYMBOL_ID = 1_234


def _inputs() -> CTraderDemoOperationalProbeInputs:
    return CTraderDemoOperationalProbeInputs(
        run_key="290-2",
        instrument="EURUSD",
        started_at=datetime(2026, 8, 12, 13, 7, tzinfo=UTC),
    )


def _observation(*, bridge_has_more: bool = False) -> CTraderDemoOperationalObservation:
    return CTraderDemoOperationalObservation(
        permission_scope=CTraderClientPermissionScope.VIEW,
        permission_scope_explicit=True,
        granted_accounts=(
            CTraderGrantedAccount(
                account_id=_ACCOUNT_ID,
                is_live=False,
                is_live_explicit=True,
            ),
        ),
        authorized_account_id=_ACCOUNT_ID,
        light_symbols=(
            CTraderLightSymbolObservation(
                symbol_id=_SYMBOL_ID,
                symbol_name="EUR/USD",
                enabled=True,
                symbol_name_explicit=True,
                enabled_explicit=True,
            ),
        ),
        full_symbol=CTraderFullSymbolObservation(
            symbol_id=_SYMBOL_ID,
            digits=5,
        ),
        trendbars_response=CTraderTrendbarsResponseObservation(
            account_id=_ACCOUNT_ID,
            symbol_id=_SYMBOL_ID,
            symbol_id_explicit=True,
            period_code=5,
            trendbars=(
                CTraderTrendbar(
                    low_relative=110_000,
                    delta_open=10,
                    delta_high=50,
                    delta_close=25,
                    utc_timestamp_in_minutes=29_775_660,
                ),
            ),
            trendbar_fields_explicit=True,
            has_more=bridge_has_more,
        ),
    )


def test_sdk_092_absent_has_more_is_preserved_as_absent_evidence() -> None:
    result = run_ctrader_demo_sdk_compat_probe(
        _inputs(),
        _observation(),
        provider_has_more_explicit=False,
        provider_has_more=None,
    )

    assert isinstance(result, Success)
    evidence = result.value
    assert evidence.provider_has_more_explicit is False
    assert evidence.provider_has_more is None
    payload = evidence.public_payload()
    assert payload["provider_has_more_explicit"] is False
    assert payload["provider_has_more"] is None
    assert payload["schema"] == "qore.ctrader-demo.sdk-closed-m5-evidence.v1"


def test_future_sdk_explicit_false_has_more_is_preserved() -> None:
    result = run_ctrader_demo_sdk_compat_probe(
        _inputs(),
        _observation(),
        provider_has_more_explicit=True,
        provider_has_more=False,
    )

    assert isinstance(result, Success)
    assert result.value.provider_has_more_explicit is True
    assert result.value.provider_has_more is False


def test_future_sdk_explicit_true_has_more_fails_closed() -> None:
    result = run_ctrader_demo_sdk_compat_probe(
        _inputs(),
        _observation(bridge_has_more=True),
        provider_has_more_explicit=True,
        provider_has_more=True,
    )

    assert isinstance(result, Failure)


def test_absent_has_more_cannot_bridge_to_true() -> None:
    result = run_ctrader_demo_sdk_compat_probe(
        _inputs(),
        _observation(bridge_has_more=True),
        provider_has_more_explicit=False,
        provider_has_more=None,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoOperationalProbeValidationError)


def test_has_more_explicitness_and_value_must_match() -> None:
    result = run_ctrader_demo_sdk_compat_probe(
        _inputs(),
        _observation(),
        provider_has_more_explicit=True,
        provider_has_more=True,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoOperationalProbeValidationError)


def test_sdk_compat_evidence_is_deterministic() -> None:
    first = run_ctrader_demo_sdk_compat_probe(
        _inputs(),
        _observation(),
        provider_has_more_explicit=False,
        provider_has_more=None,
    )
    second = run_ctrader_demo_sdk_compat_probe(
        _inputs(),
        _observation(),
        provider_has_more_explicit=False,
        provider_has_more=None,
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value == second.value
    assert first.value.to_json() == second.value.to_json()
