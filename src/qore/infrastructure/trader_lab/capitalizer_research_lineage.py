"""Frozen consumed research lineage available to the QORE Capitalizer.

These datasets are development/forensic evidence only. They are explicitly consumed and may
never be relabeled as a fresh holdout for a candidate influenced by them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)

M5_RUN_ID = 35166210458
M5_GIT_SHA = "ab782b8e9f890f86a2b6500070f0556b4b685e3d"
JOURNEY_RUN_ID = 35175979474
JOURNEY_GIT_SHA = "9cc0f17a2f30846d61b242132547f39391909656"
TARGET_V2_RUN_ID = 35204892665
TARGET_V2_GIT_SHA = "2f510461b3360e91d5ee70a72716a76cd6561f16"

CONSUMED_START = datetime(2016, 9, 17, 0, 0, tzinfo=UTC)
CONSUMED_END_EXCLUSIVE = datetime(2026, 9, 17, 0, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class CapitalizerConsumedMarketLineage:
    symbol: str
    session: CapitalizerSession
    retained_m5_bars: int
    m5_artifact_id: int
    journey_artifact_id: int
    target_v2_artifact_id: int
    research_evidence_consumed: bool = True
    fresh_holdout_eligible: bool = False

    def __post_init__(self) -> None:
        if self.symbol not in allowed_markets(self.session):
            raise ValueError("lineage symbol must belong to its frozen research session")
        if self.retained_m5_bars <= 0:
            raise ValueError("retained_m5_bars must be positive")
        if min(
            self.m5_artifact_id,
            self.journey_artifact_id,
            self.target_v2_artifact_id,
        ) <= 0:
            raise ValueError("artifact ids must be positive")
        if not self.research_evidence_consumed:
            raise ValueError("Capitalizer inherited Atlas evidence is already consumed")
        if self.fresh_holdout_eligible:
            raise ValueError("consumed Atlas evidence cannot be fresh holdout")


CAPITALIZER_CONSUMED_LINEAGE: tuple[CapitalizerConsumedMarketLineage, ...] = (
    CapitalizerConsumedMarketLineage(
        symbol="AUDJPY",
        session=CapitalizerSession.ASIA,
        retained_m5_bars=745_468,
        m5_artifact_id=10_476_530_915,
        journey_artifact_id=10_478_492_762,
        target_v2_artifact_id=10_489_761_448,
    ),
    CapitalizerConsumedMarketLineage(
        symbol="AUDUSD",
        session=CapitalizerSession.ASIA,
        retained_m5_bars=745_283,
        m5_artifact_id=10_475_697_610,
        journey_artifact_id=10_478_605_512,
        target_v2_artifact_id=10_489_343_147,
    ),
    CapitalizerConsumedMarketLineage(
        symbol="GBPJPY",
        session=CapitalizerSession.ASIA,
        retained_m5_bars=745_478,
        m5_artifact_id=10_475_453_293,
        journey_artifact_id=10_478_660_375,
        target_v2_artifact_id=10_489_327_009,
    ),
    CapitalizerConsumedMarketLineage(
        symbol="USDJPY",
        session=CapitalizerSession.ASIA,
        retained_m5_bars=745_327,
        m5_artifact_id=10_475_389_415,
        journey_artifact_id=10_478_448_325,
        target_v2_artifact_id=10_488_914_954,
    ),
    CapitalizerConsumedMarketLineage(
        symbol="EURUSD",
        session=CapitalizerSession.LONDON,
        retained_m5_bars=745_458,
        m5_artifact_id=10_475_354_631,
        journey_artifact_id=10_478_790_247,
        target_v2_artifact_id=10_489_596_583,
    ),
    CapitalizerConsumedMarketLineage(
        symbol="GBPUSD",
        session=CapitalizerSession.LONDON,
        retained_m5_bars=745_274,
        m5_artifact_id=10_475_449_182,
        journey_artifact_id=10_478_775_834,
        target_v2_artifact_id=10_489_089_220,
    ),
    CapitalizerConsumedMarketLineage(
        symbol="NAS100",
        session=CapitalizerSession.NEW_YORK,
        retained_m5_bars=701_457,
        m5_artifact_id=10_476_153_072,
        journey_artifact_id=10_479_150_314,
        target_v2_artifact_id=10_489_955_740,
    ),
    CapitalizerConsumedMarketLineage(
        symbol="USDCAD",
        session=CapitalizerSession.NEW_YORK,
        retained_m5_bars=745_088,
        m5_artifact_id=10_475_972_108,
        journey_artifact_id=10_478_860_823,
        target_v2_artifact_id=10_489_119_067,
    ),
    CapitalizerConsumedMarketLineage(
        symbol="XAUUSD",
        session=CapitalizerSession.NEW_YORK,
        retained_m5_bars=707_716,
        m5_artifact_id=10_476_557_530,
        journey_artifact_id=10_478_795_395,
        target_v2_artifact_id=10_489_343_458,
    ),
)


def validate_consumed_lineage_coverage() -> None:
    """Require exact coverage of the frozen Capitalizer research universe."""

    observed = {
        (item.session, item.symbol)
        for item in CAPITALIZER_CONSUMED_LINEAGE
    }
    expected = {
        (session, symbol)
        for session in CapitalizerSession
        for symbol in allowed_markets(session)
    }
    if observed != expected:
        missing = sorted(f"{session.value}:{symbol}" for session, symbol in expected - observed)
        extra = sorted(f"{session.value}:{symbol}" for session, symbol in observed - expected)
        raise ValueError(f"consumed lineage coverage mismatch missing={missing} extra={extra}")
