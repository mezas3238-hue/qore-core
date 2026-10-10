"""Original ICT Silver Bullet: M1 IS the operative execution chart."""
from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    CognitiveDecision,
    M1Bar,
    MethodologyDecision,
    SessionId,
    Side,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.m1_execution import (
    confirmed_m1_fvg,
    required_timeframe_contract,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.operations import (
    IctSilverBulletOperations,
)

NY = ZoneInfo("America/New_York")


def candle(start: datetime, i: int, high: str, low: str, close: str) -> M1Bar:
    begin = start + timedelta(minutes=i)
    return M1Bar(
        opened_at=begin,
        closed_at=begin + timedelta(minutes=1),
        open=Decimal(close), high=Decimal(high),
        low=Decimal(low), close=Decimal(close),
    )


def proof(time: datetime) -> CognitiveDecision:
    return CognitiveDecision(
        session=SessionId.NY_AM, side=Side.SHORT, observed_at=time,
        draw_target=Decimal("80"), draw_family="RESEARCH_LIQUIDITY_POOL_LOW",
        draw_level_observed_at=time - timedelta(minutes=30),
        structure_level=Decimal("105"),
        structure_level_confirmed_at=time - timedelta(minutes=3),
        structure_break_confirmed_at=time,
        source_provenance="COG_CLOSED_M1_MSS_TEST_SOURCE",
        cognitive_version="TEST_M1_ONLY",
    )


class TestOriginalIctM1Execution(unittest.TestCase):
    def setUp(self) -> None:
        self.start = datetime(2026, 3, 10, 14, tzinfo=UTC)
        self.assertEqual(self.start.astimezone(NY).hour, 10)
        self.a = candle(self.start, 0, "110", "106", "108")
        self.b = candle(self.start, 1, "109", "105", "106")
        self.c = candle(self.start, 2, "103", "100", "102")

    def test_m1_only_contract_is_shared_with_architect_cog(self) -> None:
        t = required_timeframe_contract()
        self.assertEqual(t["trader_id"], "VT31")
        self.assertEqual(t["session_models"], ("LONDON", "NEW_YORK"))
        self.assertEqual(t["primary_execution_timeframe"], "M1")
        self.assertEqual(t["mss_and_displacement_execution_timeframe"], "M1")
        self.assertEqual(t["fvg_creation_timeframe"], "M1")
        self.assertEqual(t["source_candle_size_seconds"], 60)
        self.assertEqual(t["htf_context_only"], ("M15", "H1", "H4"))
        self.assertFalse(t["m15_h1_h4_are_entry_triggers"])
        self.assertFalse(t["intrabar_m1_touch_proves_broker_fill"])
        self.assertFalse(t["live_authorized"])

    def test_gap_is_confirmed_only_after_3_real_closed_m1(self) -> None:
        gap = confirmed_m1_fvg(
            session=SessionId.NY_AM,
            first=self.a, middle=self.b, third=self.c,
        )
        assert gap is not None
        self.assertEqual(gap.entry_timeframe, "M1")
        self.assertEqual(gap.side, Side.SHORT)
        self.assertEqual(gap.confirmed_at, self.start + timedelta(minutes=3))
        self.assertEqual(gap.zone_low, Decimal("103"))
        self.assertEqual(gap.zone_high, Decimal("106"))
        self.assertEqual(gap.consequent_encroachment, Decimal("104.5"))

    def test_cannot_pass_m5_candle_to_m1_source(self) -> None:
        with self.assertRaises(ValueError):
            M1Bar(
                opened_at=self.start, closed_at=self.start + timedelta(minutes=5),
                open=Decimal("100"), high=Decimal("105"),
                low=Decimal("99"), close=Decimal("101"),
            )

    def test_cannot_pass_m15_or_h1_sources_as_trigger_bars(self) -> None:
        with self.assertRaises(TypeError):
            confirmed_m1_fvg(
                session=SessionId.NY_AM,
                first=self.a, middle={"timeframe": "M15"}, third=self.c,
            )

    def test_missing_m1_rejected_not_synthesized(self) -> None:
        c = candle(self.start, 3, "103", "100", "102")
        with self.assertRaises(ValueError):
            confirmed_m1_fvg(
                session=SessionId.NY_AM, first=self.a, middle=self.b, third=c,
            )

    def test_crossing_ny_10am_first_candle_rejected_as_research_boundary(self) -> None:
        a = candle(self.start, -1, "110", "106", "108")
        b = candle(self.start, 0, "109", "105", "106")
        c = candle(self.start, 1, "103", "100", "102")
        self.assertIsNone(confirmed_m1_fvg(
            session=SessionId.NY_AM, first=a, middle=b, third=c,
        ))

    def test_actual_ops_entry_cannot_precede_third_closed_m1(self) -> None:
        ops = IctSilverBulletOperations(session=SessionId.NY_AM, day=self.start)
        self.assertEqual(
            ops.on_closed_m1(self.a, cognition=None),
            MethodologyDecision.AWAIT_COGNITION,
        )
        self.assertIsNone(ops.first_suitable)
        self.assertEqual(
            ops.on_closed_m1(self.b, cognition=None),
            MethodologyDecision.AWAIT_COGNITION,
        )
        self.assertIsNone(ops.first_suitable)
        result = ops.on_closed_m1(
            self.c,
            cognition=proof(self.start + timedelta(minutes=3)),
        )
        self.assertEqual(result, MethodologyDecision.RESEARCH_PENDING_CE)
        assert ops.first_suitable is not None
        self.assertEqual(ops.first_suitable.formed_at, self.c.closed_at)
        snap = ops.snapshot()
        self.assertEqual(snap["execution_timeframe"], "M1")
        self.assertEqual(snap["structure_execution_timeframe"], "M1")
        self.assertEqual(snap["fvg_timeframe"], "M1")
        self.assertEqual(snap["higher_timeframes_role"], "CONTEXT_ONLY")
        self.assertTrue(snap["fvg"]["formed_by_closed_m1"])
        self.assertFalse(snap["actual_mt5_fill_proven"])
        self.assertFalse(snap["trading_authorized"])

    def test_live_tick_remains_separate_from_m1_candle_replay(self) -> None:
        self.assertTrue(
            required_timeframe_contract()["broker_bid_ask_tick_or_ack_needed_for_fill"]
        )


if __name__ == "__main__":
    unittest.main()
