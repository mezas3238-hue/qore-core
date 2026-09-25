from datetime import UTC, datetime
from typing import cast

from qore.infrastructure.ctrader_demo_lab_vt08_index_v7_fresh_probe import (
    fixed_acquisition_window_utc,
)
from qore.infrastructure.trader_lab.vt08_index_v7_fresh_validation import validate_report
from qore.infrastructure.trader_lab.vt08_index_v7_ttrades_source_corrected import (
    CANDIDATE_ID,
    RULE_FINGERPRINT,
)


def _metrics(
    *,
    sample: int = 40,
    mean_r: str = "0.10",
    profit_factor: str = "1.50",
    max_drawdown_r: str = "5",
) -> dict[str, object]:
    return {
        "sample": sample,
        "wins": 24,
        "losses": 16,
        "flats": 0,
        "total_r": "4",
        "mean_r": mean_r,
        "profit_factor": profit_factor,
        "max_drawdown_r": max_drawdown_r,
        "max_losing_streak": 3,
        "stress_r_per_trade": "0.05",
    }


def _report() -> dict[str, object]:
    return {
        "candidate_id": CANDIDATE_ID,
        "rule_fingerprint": RULE_FINGERPRINT,
        "partition": {
            "start_date": "2018-09-15",
            "end_date_exclusive": "2020-09-15",
        },
        "metrics_primary_stress": _metrics(),
        "metrics_secondary_stress": _metrics(
            mean_r="0.05", profit_factor="1.20", max_drawdown_r="7"
        ),
        "halves_primary_stress": [_metrics(sample=20), _metrics(sample=20)],
        "quartile_mean_r_primary_stress": ["0.10", "0.20", "0.05", "0.15"],
        "by_market_primary_stress": {
            "NAS100": _metrics(sample=14, mean_r="0.05"),
            "SP500": _metrics(sample=13, mean_r="0.08"),
            "US30": _metrics(sample=13, mean_r="0.12"),
        },
        "by_side_primary_stress": {
            "long": _metrics(sample=20, mean_r="0.11"),
            "short": _metrics(sample=20, mean_r="0.09"),
        },
    }


def test_v7_fresh_validator_bound_to_executor() -> None:
    result = validate_report(_report())
    gates = cast(dict[str, bool], result["gates"])
    assert result["fresh_holdout_pass"] is True
    assert all(gates.values())


def test_v7_fresh_acquisition_is_fixed_and_pre_2020_09_15_only() -> None:
    opened, checked = fixed_acquisition_window_utc()
    assert opened == datetime(2018, 8, 1, 4, 0, tzinfo=UTC)
    assert checked == datetime(2020, 9, 15, 4, 0, tzinfo=UTC)
    assert opened < checked
