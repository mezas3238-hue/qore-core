"""Research-only causal source parity fixtures; no official L3/DEMO gate."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar
from scripts.vt31_l3_m1_source_parity_20261014 import (
    SPEED_FACTOR,
    canonical_hash,
    streaming_census,
)
from scripts.vt31_m4_m5_ttrades_census_20261014 import census

NY = ZoneInfo("America/New_York")


def bar(
    at: datetime, o: str = "100", h: str = "102",
    low: str = "98", c: str = "101",
) -> M1Bar:
    return M1Bar(
        at, at + timedelta(minutes=1),
        Decimal(o), Decimal(h), Decimal(low), Decimal(c),
    )


def day_blocks(month: int = 7, *, valid_mss: bool = False):
    start = datetime(2025, month, 15, 9, tzinfo=NY).astimezone(UTC)
    nine = tuple(bar(start + timedelta(minutes=i)) for i in range(60))
    ten = tuple(
        bar(start + timedelta(minutes=60+i)) for i in range(60)
    )
    if valid_mss:
        mutable9 = list(nine)
        mutable9[10] = bar(nine[10].opened_at, h="130")
        mutable9[20] = bar(nine[20].opened_at, low="90")
        mutable9[57] = bar(nine[57].opened_at, h="104")
        nine = tuple(mutable9)
        mutable10 = list(ten)
        mutable10[0] = bar(ten[0].opened_at, c="100")
        mutable10[1] = bar(
            ten[1].opened_at, "96", "99", "89", "95",
        )
        mutable10[2] = bar(
            ten[2].opened_at, "94", "106", "93", "105",
        )
        mutable10[3] = bar(
            ten[3].opened_at, "105", "108", "104", "107",
        )
        ten = tuple(mutable10)
    return nine, ten


def cases():
    summer9, summer10 = day_blocks(7, valid_mss=True)
    winter9, winter10 = day_blocks(1, valid_mss=False)
    return {
        "2025-01-15": {9: winter9, 10: winter10},
        "2025-07-15": {9: summer9, 10: summer10},
    }


def test_1x_32x_same_reference_and_data_hash():
    groups = cases()
    original = census(groups)
    slow = streaming_census(groups, factor=1)
    fast = streaming_census(groups, factor=SPEED_FACTOR)
    for field in (
        "baseline_days_total",
        "baseline_M2_M3_state_counts",
        "M2_M3_cognitive_contexts",
        "M4_source_state_counts",
        "M5_hypothetical_source_path_counts",
        "cognitive_case_evidence",
    ):
        assert original[field] == slow[field] == fast[field], field
    assert slow["observation_events"] == fast["observation_events"] == 240
    assert slow["event_instants_sha256"] == fast["event_instants_sha256"]
    assert slow["explicit_wall_advance_microseconds"] == (
        32 * fast["explicit_wall_advance_microseconds"]
    )
    assert original["M2_M3_cognitive_contexts"] == 1
    assert original["M4_source_state_counts"] == {
        "FVG_GEOMETRY_ATTESTED_NOT_EXECUTABLE": 1,
    }
    assert fast["cognitive_case_evidence"][0]["m4_m5_source_only"][
        "filled"
    ] is False
    assert not fast["cognitive_case_evidence"][0]["m4_m5_source_only"][
        "execution_authorized"
    ]


def test_dst_effect_in_ny_schedule_is_preserved():
    groups = cases()
    first_winter = groups["2025-01-15"][9][0].opened_at
    first_summer = groups["2025-07-15"][9][0].opened_at
    assert first_winter.hour == 14
    assert first_summer.hour == 13
    result = streaming_census(groups, factor=32)
    assert result["observation_events"] == 240


def test_unregistered_factor_rejected():
    with pytest.raises(ValueError, match="PREREGISTERED_FACTOR"):
        streaming_census(cases(), factor=16)


def test_missing_middle_m1_never_mints_candidate():
    groups = cases()
    summer = groups["2025-07-15"]
    groups["2025-07-15"] = {
        9: summer[9], 10: summer[10][:11] + summer[10][12:],
    }
    out = streaming_census(groups, factor=32)
    assert out["baseline_M2_M3_state_counts"] == {
        "INCOMPLETE_M1_HOURS": 1,
        "NO_SWEEP": 1,
    }
    assert out["M2_M3_cognitive_contexts"] == 0
    assert out["M4_source_state_counts"] == {}


def test_duplicate_or_out_of_order_m1_fails_closed():
    groups = cases()
    summer = groups["2025-07-15"]
    original = summer[10]
    groups["2025-07-15"] = {
        9: summer[9],
        10: original[:11] + (original[10],) + original[12:],
    }
    res = streaming_census(groups, factor=1)
    assert res["baseline_M2_M3_state_counts"][
        "INCOMPLETE_M1_HOURS"
    ] == 1
    assert res["M2_M3_cognitive_contexts"] == 0


def test_no_future_candle_passes_to_cog_or_m4(monkeypatch):
    from scripts import vt31_l3_m1_source_parity_20261014 as module

    orig_cog = module.propose_ttrades_am_cognition
    orig_m4 = module.first_fvg_and_source_path
    observed = {"cog": 0, "m4": 0}

    def check_cog(*, as_of, history):
        assert history[-1].closed_at == as_of
        assert all(row.closed_at <= as_of for row in history)
        observed["cog"] += 1
        return orig_cog(as_of=as_of, history=history)

    def check_m4(*, nine, ten, cognition):
        assert ten[-1].closed_at >= cognition.observed_at
        assert len(ten) <= 60
        observed["m4"] += 1
        return orig_m4(nine=nine, ten=ten, cognition=cognition)

    monkeypatch.setattr(module, "propose_ttrades_am_cognition", check_cog)
    monkeypatch.setattr(module, "first_fvg_and_source_path", check_m4)
    accelerated = streaming_census(cases(), factor=32)
    assert observed["cog"] > 0
    assert observed["m4"] > 0
    assert accelerated["M2_M3_cognitive_contexts"] == 1


def test_canonical_hash_detects_one_changed_price_and_json_key_order():
    a = {"observed": [{"price": "100", "time": "2025-07-15"}]}
    b = {"observed": [{"time": "2025-07-15", "price": "100"}]}
    changed = {"observed": [{"price": "101", "time": "2025-07-15"}]}
    assert canonical_hash(a) == canonical_hash(b)
    assert canonical_hash(a) != canonical_hash(changed)
