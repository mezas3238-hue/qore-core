from __future__ import annotations

from qore.infrastructure.cibo_phase22_v5_source_receipt import (
    EXPECTED_SOURCE_KEYS,
    FROZEN_V5_ADVANCED_ELIGIBILITY_SHA256,
    FROZEN_V5_POLICY_BUNDLE_SHA256,
)


def test_v5_source_receipt_freezes_exact_source_surface_and_policy() -> None:
    assert EXPECTED_SOURCE_KEYS == (
        ("AUDJPY", "M5"),
        ("AUDUSD", "M5"),
        ("EURUSD", "M5"),
        ("GBPJPY", "M5"),
        ("GBPUSD", "M5"),
        ("NAS100", "M1"),
        ("NAS100", "M5"),
        ("USDCAD", "M5"),
        ("USDJPY", "M5"),
        ("XAUUSD", "M5"),
    )
    assert FROZEN_V5_POLICY_BUNDLE_SHA256 == (
        "sha256:4c2fbee5d9e6488c2c378eceda6da0a49a415f6af3b3aa29f673bfaa93ee54a4"
    )
    assert FROZEN_V5_ADVANCED_ELIGIBILITY_SHA256 == (
        "sha256:8101c287ba024032c81f97d1768c0380cb061e57de0cb87838e6b032074d610f"
    )
