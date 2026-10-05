from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_edge_certification_cli_filters_nas100_and_never_certifies(
    tmp_path: Path,
) -> None:
    source = tmp_path / "replay.json"
    output = tmp_path / "report.json"
    source.write_text(
        json.dumps(
            {
                "trades": [
                    {
                        "market": "NAS100",
                        "trade_id": "n1",
                        "signal_at": "2024-01-02T15:00:00+00:00",
                        "r_multiple": "2",
                        "requested_risk_r": "999",
                        "capital_weighted_net_r": "999999",
                    },
                    {
                        "market": "NAS100",
                        "trade_id": "n2",
                        "signal_at": "2024-01-03T15:00:00+00:00",
                        "r_multiple": "-1",
                        "requested_risk_r": "0.0001",
                        "capital_weighted_net_r": "-0.0001",
                    },
                    {
                        "market": "SP500",
                        "trade_id": "s1",
                        "signal_at": "2024-01-04T15:00:00+00:00",
                        "r_multiple": "100",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/vt31_nas100_edge_certification_v1.py",
            str(source),
            "--output",
            str(output),
            "--monte-carlo-paths",
            "50",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(completed.stdout)
    report = json.loads(output.read_text(encoding="utf-8"))

    assert summary["source_trade_count"] == 2
    assert report["metrics"]["profit_factor"] == "2"
    assert report["source_market_filter"] == "NAS100"
    assert report["capital_fields_used_for_edge_metrics"] == []
    assert report["candidate_certified"] is False
    assert report["opens_new_holdout"] is False
    assert report["live_authorized"] is False
