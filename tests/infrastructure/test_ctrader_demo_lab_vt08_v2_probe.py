from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_demo_lab_vt08_v2_probe import (
    _parse_d1_bar,
    select_vt08_provider_symbol_name,
)


def _native_d1() -> SimpleNamespace:
    return SimpleNamespace(
        low=100000,
        deltaOpen=50,
        deltaHigh=100,
        deltaClose=75,
        utcTimestampInMinutes=30_000_000,
    )


def test_explicit_provider_aliases_remain_fail_closed() -> None:
    observed = (("USTEC", True), ("US500", True), ("EURUSD", True))
    assert select_vt08_provider_symbol_name("NAS100", observed) == "USTEC"
    assert select_vt08_provider_symbol_name("SP500", observed) == "US500"
    with pytest.raises(CTraderDemoLabProbeError):
        select_vt08_provider_symbol_name("NAS100", (("MYUSTECINDEX", True),))


def test_private_native_d1_parser_does_not_widen_shared_lab_period_contract() -> None:
    checked = datetime(2030, 1, 1, tzinfo=UTC)
    parsed = _parse_d1_bar(_native_d1(), digits=5, checked_at=checked)
    assert parsed is not None
    assert parsed.payload()["period"] == "D1"
