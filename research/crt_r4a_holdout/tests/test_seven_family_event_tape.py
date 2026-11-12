"""Source-event lineage audit tests: not certified trading or Pine parity."""
from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from research.crt_r4a_holdout.causal_crt_m5_engine import (
    CausalCRTM5,
    Evidence,
)
from research.crt_r4a_holdout.secondary_family_mss import AuxiliaryMssEvent
from research.crt_r4a_holdout.secondary_family_observer import ObservedFamily
from research.crt_r4a_holdout.seven_family_contract import Family
from research.crt_r4a_holdout.seven_family_event_tape import (
    build_event_tape,
    write_event_tape,
)

T = datetime(2024, 2, 1, 1, tzinfo=UTC)
HOUR = timedelta(hours=1)
MINUTE = timedelta(minutes=1)


def base() -> Evidence:
    return Evidence(
        "EURUSD|A_2C|C1", "EURUSD", "A_2C_MSS15", "LONG",
        T, T + 4 * HOUR + 15 * MINUTE, T + 8 * HOUR,
        T + 6 * HOUR, T + 8 * HOUR, 120.0, 100.0, 115.0, 98.0,
        108.0,
    )


def own() -> AuxiliaryMssEvent:
    return AuxiliaryMssEvent(
        Family.INSIDE_RETURN, "EURUSD", "EURUSD|INSIDE|C1",
        "LONG", T, T + 8 * HOUR + 15 * MINUTE,
        T + 7 * HOUR + 30 * MINUTE, 109.0,
        T + 8 * HOUR + 30 * MINUTE,
        T + 12 * HOUR, T + 12 * HOUR,
        c1_high=120.0, c1_low=100.0,
        terminal_high=118.0, terminal_low=96.0,
        terminal_close=110.0,
    )


def retest(parent_id: str = "EURUSD|A_2C|C1") -> ObservedFamily:
    return ObservedFamily(
        Family.M15_RETEST, T, T + 8 * HOUR + 15 * MINUTE,
        1, parent_id, True, False, 0,
        112.0, 106.0, 109.0, T + 8 * HOUR + 15 * MINUTE,
    )


def engine_with_lineage() -> CausalCRTM5:
    engine = CausalCRTM5("EURUSD", family="forex")
    engine.evidence.append(base())
    engine.secondary_mss.events.append(own())
    engine.secondary.events.extend((
        ObservedFamily(
            Family.INSIDE_RETURN, T, T + 12 * HOUR, 1
        ),
        retest(),
    ))
    return engine


class StructuralEventTapeQA(unittest.TestCase):
    def test_01_three_distinct_source_owners_and_linked_retest(self) -> None:
        rows = build_event_tape(
            engine_with_lineage(),
            provider_cohort="ICMARKETS_DEMO_CONFIRMED",
        )
        self.assertEqual(len(rows), 3)
        by_family = {r["family"]: r for r in rows}
        self.assertEqual(
            by_family[Family.M15_RETEST.value]["parent_event_id"],
            "EURUSD|A_2C|C1",
        )
        self.assertEqual(
            by_family[Family.M15_RETEST.value]["geometry"]["retest_close"],
            "109.0",
        )
        self.assertEqual(
            by_family[Family.INSIDE_RETURN.value]["geometry"]["c1_high"],
            "120.0",
        )
        self.assertEqual(
            by_family[Family.TWO_C_MSS_C2.value]["geometry"]["sweep_low"],
            "98.0",
        )
        self.assertTrue(all(not r["economic_ready"] for r in rows))
        self.assertTrue(all(r["broker_orders_executed"] == 0 for r in rows))

    def test_02_deterministic_sha_and_rows_from_research_source(self) -> None:
        e = engine_with_lineage()
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "events.jsonl"
            first = write_event_tape(
                path, engine=e, provider_cohort="ICMARKETS_DEMO_CONFIRMED"
            )
            second = write_event_tape(
                path, engine=e, provider_cohort="ICMARKETS_DEMO_CONFIRMED"
            )
            self.assertEqual(first, second)
            self.assertEqual(first["rows"], 3)
            self.assertFalse(first["price_backtest_certified"])
            self.assertEqual(
                len(path.read_text(encoding="utf-8").splitlines()), 3
            )
            self.assertTrue(all(
                not json.loads(line)["economic_ready"]
                for line in path.read_text(encoding="utf-8").splitlines()
            ))

    def test_03_retest_foreign_parent_fails_closed(self) -> None:
        e = engine_with_lineage()
        e.secondary.events[-1] = retest("another-cycle")
        with self.assertRaisesRegex(ValueError, "parent"):
            build_event_tape(e, provider_cohort="ICMARKETS_DEMO_CONFIRMED")

    def test_04_missing_own_h4_evidence_fails_closed(self) -> None:
        e = engine_with_lineage()
        e.secondary_mss.events[0] = replace(own(), c1_high=None)
        with self.assertRaisesRegex(ValueError, "missing own H4"):
            build_event_tape(e, provider_cohort="ICMARKETS_DEMO_CONFIRMED")

    def test_05_provider_identity_restricted(self) -> None:
        with self.assertRaisesRegex(ValueError, "provider"):
            build_event_tape(
                engine_with_lineage(), provider_cohort="CERTIFIED_IC"
            )

    def test_06_missing_m15_close_disallows_retest_export(self) -> None:
        e = engine_with_lineage()
        e.secondary.events[-1] = replace(
            retest(), retest_closed_at=None
        )
        with self.assertRaisesRegex(ValueError, "M15 retest"):
            build_event_tape(e, provider_cohort="ICMARKETS_DEMO_CONFIRMED")

    def test_07_duplicate_source_event_fails(self) -> None:
        e = engine_with_lineage()
        e.evidence.append(base())
        with self.assertRaisesRegex(ValueError, "duplicate primary"):
            build_event_tape(e, provider_cohort="ICMARKETS_DEMO_CONFIRMED")

    def test_08_observer_mss_ownership_mismatch_fails(self) -> None:
        e = engine_with_lineage()
        e.secondary.events.pop(0)
        with self.assertRaisesRegex(ValueError, "no independently matched"):
            build_event_tape(e, provider_cohort="ICMARKETS_DEMO_CONFIRMED")

    def test_09_bare_geometry_is_not_an_executable_entry(self) -> None:
        e = engine_with_lineage()
        e.secondary.events.append(
            ObservedFamily(Family.MULTI4, T, T + 16 * HOUR, 1)
        )
        rows = build_event_tape(
            e, provider_cohort="ICMARKETS_DEMO_CONFIRMED"
        )
        self.assertEqual(len(rows), 3)
        self.assertNotIn(
            Family.MULTI4.value, {row["family"] for row in rows}
        )

    def test_10_raw_provider_alias_preserves_lineage(self) -> None:
        e = CausalCRTM5("NAS100", family="index")
        rows = build_event_tape(
            e, provider_cohort="ATLAS_DEMO_BROKER_UNVERIFIED"
        )
        self.assertEqual(rows, [])
