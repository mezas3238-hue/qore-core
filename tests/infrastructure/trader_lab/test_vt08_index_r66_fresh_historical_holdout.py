from __future__ import annotations

from datetime import date
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r59_candidate_freeze as freeze,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r66_fresh_historical_holdout as r66,
)


def test_r66_binds_exact_frozen_r58_identity() -> None:
    assert r66.freeze.CANDIDATE_ID == freeze.CANDIDATE_ID
    assert (
        r66.freeze.CANDIDATE_RULE_FINGERPRINT
        == freeze.CANDIDATE_RULE_FINGERPRINT
    )
    assert r66.freeze.FREEZE_ID == freeze.FREEZE_ID


def test_r66_holdout_is_full_available_disjoint_pre5y_region() -> None:
    assert r66.START_DATE == date(2016, 9, 17)
    assert r66.BLOCK_BOUNDARY == date(2017, 9, 16)
    assert r66.END_DATE_EXCLUSIVE == date(2018, 9, 15)
    assert (r66.END_DATE_EXCLUSIVE - r66.START_DATE).days == 728
    assert (r66.BLOCK_BOUNDARY - r66.START_DATE).days == 364
    assert (r66.END_DATE_EXCLUSIVE - r66.BLOCK_BOUNDARY).days == 364


def test_r66_preregistered_economic_floor_is_frozen() -> None:
    assert r66.MIN_TRADES == 1000
    assert r66.PRIMARY_STRESS == Decimal("0.05")
    assert r66.SECONDARY_STRESS == Decimal("0.10")
    assert r66.PRIMARY_PF_MIN == Decimal("1.50")
    assert r66.SECONDARY_PF_MIN == Decimal("1.30")
    assert r66.PORTFOLIO_DD_MAX_R == Decimal("6")


def test_r66_atlas_lineage_is_fixed_before_execution() -> None:
    assert r66.ATLAS_TARGET_START == "2016-09-17T00:00:00+00:00"
    assert r66.ATLAS_TARGET_END_EXCLUSIVE == "2026-09-17T00:00:00+00:00"
    assert r66.ATLAS_SOURCE_RUN_ID == 35166210458
    assert r66.ATLAS_SOURCE_HEAD == (
        "ab782b8e9f890f86a2b6500070f0556b4b685e3d"
    )
