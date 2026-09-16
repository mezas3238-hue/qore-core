from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_index_deep_behavior_lab import (
    _drawdown_episodes,
    _funnel_summary,
    _row_metrics,
    _stop_taxonomy,
    combine_reports,
)
from qore.infrastructure.trader_lab.vt08_index_v7_ttrades_source_corrected import (
    CANDIDATE_ID,
    RULE_FINGERPRINT,
)


def _row(
    signal_at: str,
    primary_r: str,
    *,
    symbol: str = "NAS100",
) -> dict[str, object]:
    return {
        "signal_at": signal_at,
        "symbol": symbol,
        "side": "long",
        "anchor_hour_new_york": 10,
        "model_kind": "same-c2-intracandle",
        "poi_kind": "relevant-swing",
        "year": 2020,
        "year_quarter": "2020-Q1",
        "entry_timing_bucket": "q2_61_120",
        "prior_h4_range_regime": "normal",
        "peer_alignment_count": 1,
        "current_source_body_alignment": "aligned",
        "previous_source_body_alignment": "opposed",
        "raw_r": str(float(primary_r) + 0.05),
        "primary_r": primary_r,
        "secondary_r": str(float(primary_r) - 0.05),
        "mfe_r_conservative": "0.25" if primary_r.startswith("-") else "2",
        "stop_excursion_bucket": (
            "lt_0_5r" if primary_r.startswith("-") else "not-stop"
        ),
        "duration_bucket": "le_2h",
        "target_outcomes_raw_r": {
            "0.5": "0.5",
            "1.0": "1.0",
            "1.5": "1.5",
            "2.0": "2.0",
            "2.5": "-1.0",
            "3.0": "-1.0",
        },
    }


def test_row_metrics_and_drawdown_are_deterministic() -> None:
    rows = [
        _row("2020-01-01T14:00:00+00:00", "1.95"),
        _row("2020-01-02T14:00:00+00:00", "-1.05"),
        _row("2020-01-03T14:00:00+00:00", "-1.05"),
        _row("2020-01-04T14:00:00+00:00", "1.95"),
    ]
    metrics = _row_metrics(rows)
    assert metrics["sample"] == 4
    assert metrics["total_r"] == "1.80"
    assert metrics["max_drawdown_r"] == "2.10"
    episodes = _drawdown_episodes(rows)
    assert episodes
    assert episodes[0]["depth_r"] == "2.10"


def test_funnel_summary_tracks_conversion_and_failure_stages() -> None:
    observations = [
        {"symbol": "NAS100", "anchor_hour_new_york": 10, "stage": "signal"},
        {"symbol": "NAS100", "anchor_hour_new_york": 10, "stage": "no-cisd"},
        {"symbol": "SP500", "anchor_hour_new_york": 6, "stage": "signal"},
    ]
    summary = _funnel_summary(observations)
    overall = summary["overall"]
    assert isinstance(overall, dict)
    assert overall["opportunities"] == 3
    assert overall["signals"] == 2
    assert overall["conversion_rate"] == "0.6666666666666666666666666667"


def test_stop_taxonomy_is_market_specific() -> None:
    rows = [
        _row("2020-01-01T14:00:00+00:00", "-1.05", symbol="NAS100"),
        _row("2020-01-02T14:00:00+00:00", "-1.05", symbol="SP500"),
        _row("2020-01-03T14:00:00+00:00", "1.95", symbol="US30"),
    ]
    taxonomy = _stop_taxonomy(rows)
    assert taxonomy["sample"] == 2
    by_symbol = taxonomy["by_symbol"]
    assert isinstance(by_symbol, dict)
    assert by_symbol["NAS100"]["sample"] == 1
    assert by_symbol["SP500"]["sample"] == 1


def test_combined_report_is_diagnostic_only_and_bound_to_v7() -> None:
    report: dict[str, object] = {
        "window_id": "w1",
        "partition": {
            "start_date": "2020-01-01",
            "end_date_exclusive": "2020-07-01",
        },
        "metrics_primary": {
            "sample": 1,
            "mean_r": "1.95",
            "profit_factor": None,
            "max_drawdown_r": "0",
        },
        "opportunity_funnel": {
            "overall": {
                "opportunities": 2,
                "signals": 1,
                "stages": {"signal": 1, "no-cisd": 1},
            }
        },
        "trades": [_row("2020-01-01T14:00:00+00:00", "1.95")],
    }
    combined = combine_reports([report])
    assert combined["candidate_id"] == CANDIDATE_ID
    assert combined["rule_fingerprint"] == RULE_FINGERPRINT
    governance = combined["governance"]
    assert isinstance(governance, dict)
    assert governance["diagnostic_only"] is True
    assert governance["consumed_evidence_only"] is True
    assert governance["live_authorized"] is False
