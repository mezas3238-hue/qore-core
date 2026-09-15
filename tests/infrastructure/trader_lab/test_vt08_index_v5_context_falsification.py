from qore.infrastructure.trader_lab.vt08_index_v5_context_falsification import analyze


def _row(alignment: str, sweep: str, side: str, outcome: str) -> dict[str, str]:
    return {
        "previous_source_day_body_alignment": alignment,
        "previous_day_sweep_type": sweep,
        "side": side,
        "outcome_r": outcome,
        "window_id": "2022_23",
        "symbol": "NAS100",
        "anchor": "02",
    }


def test_analysis_keeps_all_rows_and_separates_proxy_from_closure() -> None:
    rows = [
        _row("opposed", "low_reclaim", "long", "2"),
        _row("opposed", "high_breakout", "short", "-1"),
        _row("aligned", "inside", "long", "2"),
    ]
    report = analyze(rows)
    assert report["sample"] == 3
    assert report["resolvable_sample"] == 2
    assert report["opposed_reversal_agreement"] == "0.5"
    assert report["by_context_side_relation"]["inconclusive"]["sample"] == 1
    assert report["by_context_side_relation"]["with_side"]["sample"] == 1
    assert report["by_context_side_relation"]["against_side"]["sample"] == 1


def test_outcomes_do_not_change_context_classification() -> None:
    base = _row("opposed", "low_reclaim", "long", "2")
    changed = dict(base, outcome_r="-1")
    a = analyze([base])["rows"][0]
    b = analyze([changed])["rows"][0]
    assert a["v5_previous_closed_day_context"] == b["v5_previous_closed_day_context"]
    assert a["v5_context_side_relation"] == b["v5_context_side_relation"]
