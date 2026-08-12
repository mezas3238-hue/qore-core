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
    CTraderDemoSdkOperationalEvidence,
    ctrader_historical_m5_query_window,
    run_ctrader_demo_sdk_compat_probe,
)
from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success

_ACCOUNT_ID = 7_654_321
_SYMBOL_ID = 1_234
_SDK_VERSION = "0.9.2"


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


def _run(
    *,
    observation: CTraderDemoOperationalObservation | None = None,
    sdk_package_version: str = _SDK_VERSION,
    provider_has_more_supported: bool = False,
    provider_has_more_explicit: bool = False,
    provider_has_more: bool | None = None,
) -> Result[CTraderDemoSdkOperationalEvidence, ExternalPortError]:
    return run_ctrader_demo_sdk_compat_probe(
        _inputs(),
        _observation() if observation is None else observation,
        sdk_package_version=sdk_package_version,
        provider_has_more_supported=provider_has_more_supported,
        provider_has_more_explicit=provider_has_more_explicit,
        provider_has_more=provider_has_more,
    )


def test_sdk_092_absent_has_more_is_preserved_as_absent_evidence() -> None:
    result = _run()

    assert isinstance(result, Success)
    evidence = result.value
    assert evidence.sdk_package_version == _SDK_VERSION
    assert evidence.provider_has_more_supported is False
    assert evidence.provider_has_more_explicit is False
    assert evidence.provider_has_more is None
    payload = evidence.public_payload()
    assert payload["sdk_package_version"] == _SDK_VERSION
    assert payload["provider_has_more_supported"] is False
    assert payload["provider_has_more_explicit"] is False
    assert payload["provider_has_more"] is None
    assert payload["schema"] == "qore.ctrader-demo.sdk-closed-m5-evidence.v1"


def test_uncertified_sdk_version_fails_closed() -> None:
    result = _run(sdk_package_version="0.9.3")

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoOperationalProbeValidationError)


def test_sdk_092_cannot_claim_has_more_support() -> None:
    result = _run(provider_has_more_supported=True)

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoOperationalProbeValidationError)


def test_sdk_092_cannot_claim_explicit_has_more() -> None:
    result = _run(provider_has_more_explicit=True, provider_has_more=False)

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoOperationalProbeValidationError)


def test_sdk_092_absent_has_more_must_retain_none() -> None:
    result = _run(provider_has_more=False)

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoOperationalProbeValidationError)


def test_absent_has_more_cannot_bridge_to_true() -> None:
    result = _run(observation=_observation(bridge_has_more=True))

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoOperationalProbeValidationError)


def test_historical_query_window_excludes_next_bar_open_by_one_millisecond() -> None:
    from_timestamp, to_timestamp = ctrader_historical_m5_query_window(
        datetime(2026, 8, 12, 13, 7, 42, tzinfo=UTC)
    )

    assert from_timestamp == 1_786_539_600_000
    assert to_timestamp == 1_786_539_899_999
    assert to_timestamp - from_timestamp + 1 == 300_000


def test_sdk_compat_evidence_is_deterministic() -> None:
    first = _run()
    second = _run()

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value == second.value
    assert first.value.to_json() == second.value.to_json()
