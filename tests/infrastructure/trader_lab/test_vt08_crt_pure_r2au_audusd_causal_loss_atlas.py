from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    TargetArm,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2au_audusd_causal_loss_atlas import (
    ARM,
    END,
    IDENTITY,
    INTERACTIONS,
    MARKET,
    MIN_ANNUAL_SUPPORT,
    MIN_BUCKET_TRADES,
    START,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def test_r2au_identity_and_market_are_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2AU_AUDUSD_CAUSAL_LOSS_ATLAS_001"
    assert MARKET is CrtPureMarket.AUDUSD
    assert ARM is TargetArm.FIXED_1_5R


def test_r2au_window_and_support_are_frozen() -> None:
    assert START.year == 2016
    assert END.year == 2026
    assert MIN_BUCKET_TRADES == 60
    assert MIN_ANNUAL_SUPPORT == 5


def test_r2au_interaction_family_is_frozen() -> None:
    assert ("timing_triplet", "source_generation") in INTERACTIONS
    assert ("manipulation_depth", "source_penetration") in INTERACTIONS
    assert ("c1_body_fraction", "source_body_fraction") in INTERACTIONS
