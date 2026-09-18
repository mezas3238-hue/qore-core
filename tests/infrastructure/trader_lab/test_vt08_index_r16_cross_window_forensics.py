from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r16_cross_window_forensics as mod


def test_r16_contract() -> None:
    assert mod.IDENTITY == "VT08_INDEX_R16_CROSS_WINDOW_FORENSICS_001"
    assert mod.STRESS == Decimal("0.05")


def test_stable_rows_requires_both_windows() -> None:
    five = {
        "x": {
            "sample": 10,
            "profit_factor": "1.30",
            "total_r": "2",
            "max_drawdown_r": "1",
            "wins": 5,
            "losses": 5,
            "flats": 0,
            "mean_r": "0.2",
            "max_losing_streak": 2,
        }
    }
    two = {
        "x": {
            "sample": 4,
            "profit_factor": "1.25",
            "total_r": "1",
            "max_drawdown_r": "1",
            "wins": 2,
            "losses": 2,
            "flats": 0,
            "mean_r": "0.25",
            "max_losing_streak": 1,
        }
    }
    row = mod._stable_rows(five, two)["x"]
    assert row["positive_both"] is True
    assert row["pf_above_1_both"] is True
    assert row["pf_above_1_2_both"] is True
