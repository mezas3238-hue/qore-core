from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_dd_joint_forensics_2y_v1 as forensic,
)


def test_wait5_dd_joint_forensics_contract_is_frozen() -> None:
    assert forensic.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_DD_JOINT_FORENSICS_2Y_V1"
    )
    assert forensic.EXPECTED_MAX3 == 983
    assert forensic.EXPECTED_DD == Decimal("11.9420088471277198029814040")


def test_exact_timing_partition_is_causal() -> None:
    assert (
        forensic._exact_timing(
            "2026-01-01T10:00:00+00:00",
            "2026-01-01T10:00:00+00:00",
        )
        == "EXACT_ZERO"
    )
    assert (
        forensic._exact_timing(
            "2026-01-01T10:03:00+00:00",
            "2026-01-01T10:00:00+00:00",
        )
        == "GT0_TO_5M"
    )
