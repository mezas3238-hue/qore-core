import pytest

from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_demo_lab_vt08_v2_probe import (
    select_vt08_provider_symbol_name,
)


def test_explicit_index_aliases_resolve_without_fuzzy_matching() -> None:
    observed = (("USTEC", True), ("US500", True), ("US30", True), ("EURUSD", True))
    assert select_vt08_provider_symbol_name("NAS100", observed) == "USTEC"
    assert select_vt08_provider_symbol_name("SP500", observed) == "US500"
    assert select_vt08_provider_symbol_name("US30", observed) == "US30"


def test_fx_exact_or_separated_suffix_is_supported() -> None:
    assert select_vt08_provider_symbol_name("EURUSD", (("EURUSD", True),)) == "EURUSD"
    assert select_vt08_provider_symbol_name("GBPJPY", (("GBPJPY.c", True),)) == "GBPJPY.c"


def test_substring_alias_is_not_accepted() -> None:
    with pytest.raises(CTraderDemoLabProbeError):
        select_vt08_provider_symbol_name("NAS100", (("MYUSTECINDEX", True),))


def test_multiple_suffixes_at_same_root_fail_closed() -> None:
    with pytest.raises(CTraderDemoLabProbeError):
        select_vt08_provider_symbol_name(
            "EURUSD", (("EURUSD.a", True), ("EURUSD.b", True))
        )
