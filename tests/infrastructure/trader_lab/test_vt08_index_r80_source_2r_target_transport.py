from __future__ import annotations

from datetime import date
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r80_source_2r_target_transport as r80,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)


def test_r80_source_target_is_exact_v6_two_r() -> None:
    assert r80.SOURCE_TARGET_R == Decimal("2")
    assert r80.SOURCE_TARGET_R == v6.TARGET_R_MULTIPLE
    assert r80.CANONICAL_TARGET_R == Decimal("2.5")


def test_r80_r66_uses_official_two_blocks() -> None:
    boundaries = r80._boundaries(
        window_id="R66",
        start_date=date(2016, 9, 17),
        end_date=date(2018, 9, 15),
    )
    assert boundaries == (
        date(2016, 9, 17),
        date(2017, 9, 16),
        date(2018, 9, 15),
    )


def test_r80_five_year_uses_five_annual_blocks() -> None:
    boundaries = r80._boundaries(
        window_id="5Y",
        start_date=date(2018, 9, 15),
        end_date=date(2023, 9, 15),
    )
    assert boundaries == (
        date(2018, 9, 15),
        date(2019, 9, 15),
        date(2020, 9, 15),
        date(2021, 9, 15),
        date(2022, 9, 15),
        date(2023, 9, 15),
    )


def test_r80_baseline_contract_is_pinned() -> None:
    assert r80.EXPECTED_BASELINE_SECONDARY["5Y"]["sample"] == 2448
    assert r80.EXPECTED_BASELINE_SECONDARY["2Y"]["sample"] == 1017
    assert r80.EXPECTED_BASELINE_SECONDARY["R66"]["sample"] == 773


def test_r80_source_r79_evidence_is_pinned() -> None:
    assert r80.SOURCE_R79_RUN_ID == 35516202970
    assert r80.SOURCE_R79_ARTIFACT_ID == 10606254504
    assert r80.SOURCE_R79_ARTIFACT_DIGEST.startswith("sha256:")
