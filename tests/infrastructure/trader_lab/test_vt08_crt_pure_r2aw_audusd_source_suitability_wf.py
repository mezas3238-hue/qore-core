from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_r2aw_audusd_source_suitability_wf import (
    ADVANCEMENT_MIN_PF,
    ADVANCEMENT_MIN_TRADES_PER_YEAR,
    IDENTITY,
    MIN_REMOVED_TRADES_PER_YEAR,
    MIN_RETENTION,
    SOURCE_DIMENSIONS,
    TRAINING_YEARS,
)


def test_r2aw_contract_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2AW_AUDUSD_SOURCE_SUITABILITY_WF_001"
    assert TRAINING_YEARS == 3
    assert MIN_RETENTION == Decimal("0.70")
    assert MIN_REMOVED_TRADES_PER_YEAR == 12


def test_r2aw_source_family_is_frozen() -> None:
    assert SOURCE_DIMENSIONS == (
        "source_generation",
        "source_reference_count",
        "confirmation_delay",
        "source_body_fraction",
        "source_range_to_c1",
        "source_penetration",
    )


def test_r2aw_advancement_gate_matches_frozen_gate() -> None:
    assert ADVANCEMENT_MIN_TRADES_PER_YEAR == Decimal("170")
    assert ADVANCEMENT_MIN_PF == Decimal("1.05")
