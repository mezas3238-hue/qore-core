"""Proof of totally independent clean-room VT31 OPS and COG interface."""
from __future__ import annotations

import ast
import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    CognitiveDecision,
    M1Bar,
    MethodologyDecision,
    SessionId,
    Side,
    window_bounds,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.operations import IctSilverBulletOperations

NY = ZoneInfo("America/New_York")


def bar(base: datetime, i: int, h: str, low: str, c: str) -> M1Bar:
    t = base + timedelta(minutes=i)
    return M1Bar(
        t, t + timedelta(minutes=1),
        Decimal(c), Decimal(h), Decimal(low), Decimal(c)
    )


def decision(at: datetime, session: SessionId, side: Side = Side.SHORT) -> CognitiveDecision:
    return CognitiveDecision(
        session=session, side=side, observed_at=at,
        draw_target=Decimal("80") if side is Side.SHORT else Decimal("140"),
        draw_family="PREVIOUS_DAY_LOW" if side is Side.SHORT else "PREVIOUS_DAY_HIGH",
        draw_level_observed_at=at - timedelta(minutes=20),
        structure_level=Decimal("105") if side is Side.SHORT else Decimal("106"),
        structure_level_confirmed_at=at-timedelta(minutes=5),
        structure_break_confirmed_at=at,
        source_provenance="COG_CLEANROOM_TEST_PRODUCER",
        cognitive_version="cleanroom-cog-interface-v1"
    )


class TestCleanroom(unittest.TestCase):
    def setUp(self) -> None:
        self.t = datetime(2025, 7, 7, 7, tzinfo=UTC)  # London 03 NY
        self.session = SessionId.LONDON

    def test_original_source_clocks_across_dst(self) -> None:
        for dt in (
            datetime(2026, 3, 2, 12, tzinfo=UTC),
            datetime(2026, 3, 10, 12, tzinfo=UTC),
            datetime(2026, 3, 30, 12, tzinfo=UTC),
            datetime(2026, 10, 26, 12, tzinfo=UTC),
            datetime(2026, 11, 2, 12, tzinfo=UTC),
        ):
            for sess, hour in (
                (SessionId.LONDON, 3),
                (SessionId.NY_AM, 10),
                (SessionId.NY_PM, 14),
            ):
                start, end = window_bounds(dt, sess)
                self.assertEqual(start.astimezone(NY).hour, hour)
                self.assertEqual(end-start, timedelta(hours=1))

    def _pending(self) -> IctSilverBulletOperations:
        ops = IctSilverBulletOperations(session=self.session, day=self.t)
        self.assertEqual(
            ops.on_closed_m1(bar(self.t, 0, "110", "106", "108"), cognition=None),
            MethodologyDecision.AWAIT_COGNITION
        )
        self.assertEqual(
            ops.on_closed_m1(bar(self.t, 1, "109", "105", "106"), cognition=None),
            MethodologyDecision.AWAIT_COGNITION
        )
        t3 = self.t + timedelta(minutes=3)
        self.assertEqual(
            ops.on_closed_m1(
                bar(self.t, 2, "103", "100", "102"),
                cognition=decision(t3, self.session)
            ), MethodologyDecision.RESEARCH_PENDING_CE
        )
        self.assertEqual(ops.first_suitable.consequent_encroachment, Decimal("104.5"))
        self.assertFalse(ops.snapshot()["actual_mt5_fill_proven"])
        self.assertFalse(ops.snapshot()["trading_authorized"])
        return ops

    def test_source_first_fvg_and_research_touch_not_broker_fill(self) -> None:
        ops = self._pending()
        original = ops.snapshot()["fvg"]
        phase = ops.on_closed_m1(
            bar(self.t, 3, "105", "103", "104"),
            cognition=decision(self.t + timedelta(minutes=4), self.session)
        )
        self.assertEqual(phase, MethodologyDecision.RESEARCH_TOUCH_NOT_FILL)
        self.assertEqual(original, ops.snapshot()["fvg"])
        self.assertFalse(ops.snapshot()["actual_mt5_fill_proven"])

    def test_same_bar_touch_and_invalidation_is_ambiguous(self) -> None:
        ops = self._pending()
        phase = ops.on_closed_m1(
            bar(self.t, 3, "110", "103", "108"), cognition=None
        )
        self.assertEqual(phase, MethodologyDecision.AMBIGUOUS_PRICE_PATH)
        self.assertFalse(ops.snapshot()["actual_mt5_fill_proven"])

    def test_no_future_cognition(self) -> None:
        ops = IctSilverBulletOperations(session=self.session, day=self.t)
        with self.assertRaises(ValueError):
            ops.on_closed_m1(
                bar(self.t, 0, "110", "106", "108"),
                cognition=decision(self.t+timedelta(minutes=2), self.session)
            )
        self.assertIsNone(ops.last_closed)

    def test_no_duplicate_or_out_of_order(self) -> None:
        ops = IctSilverBulletOperations(session=self.session, day=self.t)
        sample = bar(self.t, 0, "110", "106", "108")
        ops.on_closed_m1(sample, cognition=None)
        with self.assertRaises(ValueError):
            ops.on_closed_m1(sample, cognition=None)

    def test_other_session_not_accepted(self) -> None:
        ops = IctSilverBulletOperations(session=self.session, day=self.t)
        with self.assertRaises(ValueError):
            ops.on_closed_m1(
                bar(self.t, 0, "110", "106", "108"),
                cognition=decision(self.t+timedelta(minutes=1), SessionId.NY_AM)
            )

    def test_cognitive_timestamp_guards(self) -> None:
        at = self.t + timedelta(minutes=4)
        obj = decision(at, self.session)
        with self.assertRaises(ValueError):
            CognitiveDecision(
                session=obj.session, side=obj.side, observed_at=obj.observed_at,
                draw_target=obj.draw_target, draw_family=obj.draw_family,
                draw_level_observed_at=obj.observed_at+timedelta(minutes=1),
                structure_level=obj.structure_level,
                structure_level_confirmed_at=obj.structure_level_confirmed_at,
                structure_break_confirmed_at=obj.structure_break_confirmed_at,
                source_provenance=obj.source_provenance,
                cognitive_version=obj.cognitive_version,
            )

    def test_no_legacy_source_imports(self) -> None:
        root = (
            Path(__file__).resolve().parents[2]
            / "src/qore/infrastructure/traders/vt31_ict_cleanroom"
        )
        self.assertTrue(root.is_dir())
        for name in ("__init__.py", "contracts.py", "operations.py"):
            syntax = ast.parse((root / name).read_text())
            for node in ast.walk(syntax):
                if isinstance(node, ast.Import):
                    for entry in node.names:
                        self.assertNotIn("vt31_", entry.name)
                        self.assertNotIn("ttrades", entry.name.lower())
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    self.assertFalse(
                        "vt31_nas100_" in module or
                        "vt31_silver_bullet" in module or
                        "ttrades" in module.lower(),
                        f"legacy module imported: {module}"
                    )


if __name__ == "__main__":
    unittest.main()
