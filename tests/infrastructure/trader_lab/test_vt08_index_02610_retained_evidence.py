from __future__ import annotations

import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.vt08_index_02610_retained_evidence import (
    SOURCE_SOFTWARE_SHA,
    Vt08Index02610EvidenceError,
    build_report,
)


def _write_market(
    root: Path,
    *,
    market: str,
    provider: str,
    counts: tuple[int, int, int],
    close_values: tuple[str, str, str],
) -> Path:
    root.mkdir(parents=True)
    total = sum(counts)
    scope = {
        "futures_h4_anchors": [2, 6, 10],
        "timezone": "America/New_York",
    }
    summary = {
        "software_sha": SOURCE_SOFTWARE_SHA,
        "symbol": market,
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "human_owner_operating_scope": scope,
    }
    characterization = {
        "decision_funnel": {
            "mechanical_candidates": total,
            "automatic_setups": 0,
            "filled": 0,
            "source_judgment_required": total,
        },
        "by_h4_anchor_hour_new_york": {
            label: {
                "candidate_count": count,
                "mean_mae_r_descriptive_only": "1.0",
                "mean_mfe_r_descriptive_only": "2.0",
                "mean_post_signal_h4_close_r_descriptive_only": close_value,
            }
            for label, count, close_value in zip(
                ("02:00", "06:00", "10:00"),
                counts,
                close_values,
                strict=True,
            )
        },
    }
    market_evidence = {
        "software_sha": SOURCE_SOFTWARE_SHA,
        "canonical_symbol": market,
        "provider_symbol_name": provider,
        "owner_operating_scope": {
            "futures_h4_opens": [2, 6, 10],
            "timezone": "America/New_York",
        },
        "coverage": {
            "bar_count": 100,
            "first_opened_at": "2024-01-01T00:00:00+00:00",
            "last_closed_at": "2026-01-01T00:00:00+00:00",
        },
    }
    (root / "research-summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (root / "characterization.json").write_text(
        json.dumps(characterization), encoding="utf-8"
    )
    (root / "market-evidence.json").write_text(
        json.dumps(market_evidence), encoding="utf-8"
    )
    return root


def test_build_report_aggregates_without_manufacturing_trades(tmp_path: Path) -> None:
    nas = _write_market(
        tmp_path / "NAS100",
        market="NAS100",
        provider="USTEC",
        counts=(10, 20, 30),
        close_values=("0.1", "-0.2", "0.3"),
    )
    spx = _write_market(
        tmp_path / "SP500",
        market="SP500",
        provider="US500",
        counts=(20, 10, 10),
        close_values=("0.2", "-0.1", "0.0"),
    )
    dow = _write_market(
        tmp_path / "US30",
        market="US30",
        provider="US30",
        counts=(30, 30, 20),
        close_values=("0.3", "-0.3", "0.1"),
    )

    report = build_report(nas100=nas, sp500=spx, us30=dow)
    aggregate = report["aggregate"]
    assert isinstance(aggregate, dict)
    assert aggregate["mechanical_candidate_count"] == 180
    assert aggregate["automatic_setup_count"] == 0
    assert aggregate["filled_count"] == 0
    assert aggregate["source_judgment_required"] == 180

    anchors = aggregate["by_anchor_new_york"]
    assert isinstance(anchors, dict)
    assert anchors["02:00"]["candidate_count"] == 60
    assert anchors["06:00"]["candidate_count"] == 60
    assert anchors["10:00"]["candidate_count"] == 60
    assert (
        anchors["02:00"]["mean_post_signal_h4_close_r_descriptive_only"]
        == "0.2333333333333333333333333333"
    )

    adjudication = report["adjudication"]
    assert isinstance(adjudication, dict)
    assert adjudication["executable_economic_sample_available"] is False
    assert adjudication["win_loss_pf_claim_authorized"] is False
    assert adjudication["schedule_selection_from_descriptive_paths_authorized"] is False


def test_build_report_fails_closed_on_anchor_drift(tmp_path: Path) -> None:
    nas = _write_market(
        tmp_path / "NAS100",
        market="NAS100",
        provider="USTEC",
        counts=(1, 1, 1),
        close_values=("0", "0", "0"),
    )
    spx = _write_market(
        tmp_path / "SP500",
        market="SP500",
        provider="US500",
        counts=(1, 1, 1),
        close_values=("0", "0", "0"),
    )
    dow = _write_market(
        tmp_path / "US30",
        market="US30",
        provider="US30",
        counts=(1, 1, 1),
        close_values=("0", "0", "0"),
    )

    summary_path = nas / "research-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["human_owner_operating_scope"]["futures_h4_anchors"] = [1, 5, 9]
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    with pytest.raises(Vt08Index02610EvidenceError, match="anchors drifted"):
        build_report(nas100=nas, sp500=spx, us30=dow)


def test_build_report_fails_closed_on_provider_alias_drift(tmp_path: Path) -> None:
    nas = _write_market(
        tmp_path / "NAS100",
        market="NAS100",
        provider="NAS100",
        counts=(1, 1, 1),
        close_values=("0", "0", "0"),
    )
    spx = _write_market(
        tmp_path / "SP500",
        market="SP500",
        provider="US500",
        counts=(1, 1, 1),
        close_values=("0", "0", "0"),
    )
    dow = _write_market(
        tmp_path / "US30",
        market="US30",
        provider="US30",
        counts=(1, 1, 1),
        close_values=("0", "0", "0"),
    )

    with pytest.raises(Vt08Index02610EvidenceError, match="provider symbol mapping drifted"):
        build_report(nas100=nas, sp500=spx, us30=dow)
