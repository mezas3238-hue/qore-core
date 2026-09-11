import pytest

from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_demo_lab_vt08_v2_probe import (
    _NATIVE_M15_PERIOD,
    _PRIMARY_SOURCE_SHA256,
    select_vt08_provider_symbol_name,
)


def test_explicit_provider_aliases_remain_fail_closed() -> None:
    observed = (("USTEC", True), ("US500", True), ("EURUSD", True))
    assert select_vt08_provider_symbol_name("NAS100", observed) == "USTEC"
    assert select_vt08_provider_symbol_name("SP500", observed) == "US500"
    with pytest.raises(CTraderDemoLabProbeError):
        select_vt08_provider_symbol_name("NAS100", (("MYUSTECINDEX", True),))


def test_source_faithful_probe_collects_m15_without_invented_d1_gate() -> None:
    assert _NATIVE_M15_PERIOD == 7
    assert (
        _PRIMARY_SOURCE_SHA256
        == "bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271"
    )


def test_provider_suffix_ambiguity_still_fails_closed() -> None:
    with pytest.raises(CTraderDemoLabProbeError):
        select_vt08_provider_symbol_name(
            "EURUSD", (("EURUSD.a", True), ("EURUSD.b", True))
        )