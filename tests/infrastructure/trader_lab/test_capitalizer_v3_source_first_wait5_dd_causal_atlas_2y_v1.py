from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_dd_causal_atlas_2y_v1 as atlas,
)


def test_wait5_dd_causal_atlas_contract_is_frozen() -> None:
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_DD_CAUSAL_ATLAS_2Y_V1"
    )
    assert atlas.EXPECTED_MAX3 == 983
    assert atlas.EXPECTED_DD == Decimal("11.9420088471277198029814040")


def test_wait5_dd_bucket_contracts_are_deterministic() -> None:
    assert atlas._bucket_minutes(5) == "01_05M"
    assert atlas._bucket_minutes(16) == "16_30M"
    assert atlas._body_bucket(Decimal("0.75")) == "0.70_TO_LT_0.80"
    assert atlas._ratio_bucket(Decimal("2.5")) == "2.00_TO_LT_3.00"
    assert atlas._stop_atr_bucket(Decimal("1.75")) == "1.50_TO_LT_2.00"
