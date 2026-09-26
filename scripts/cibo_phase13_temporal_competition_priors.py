"""Bind Phase-19 chronology evidence into Phase-13 temporal priors.

Input is the sealed chronology-only report. The report contains no PnL,
historical USD arithmetic or allocation outcome. This script converts only the
observed cross-Trader overlap distribution into frozen descriptive priors.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_empirical_temporal_interactions import (
    HistoricalTemporalCompetitionPrior,
)

EXPECTED_IDENTITY = "CIBO_PHASE19_INTEGRATED_CHRONOLOGY_REPLAY_V1"
EXPECTED_STATUS = "CHRONOLOGY_GREEN_USD_PROVIDER_ECONOMICS_BLOCKED"
EXPECTED_CROSS_OVERLAPS = 250
EXPECTED_TOTAL_ROWS = 855


def build_priors(
    *,
    phase19_report: dict[str, Any],
    evidence_id: str,
) -> tuple[HistoricalTemporalCompetitionPrior, ...]:
    if phase19_report.get("identity") != EXPECTED_IDENTITY:
        raise ValueError("unexpected Phase-19 chronology identity")
    if phase19_report.get("status") != EXPECTED_STATUS:
        raise ValueError("Phase-19 chronology is not sealed GREEN evidence")
    if phase19_report.get("total_common_window_rows") != EXPECTED_TOTAL_ROWS:
        raise ValueError("Phase-19 common-window population drift")
    if phase19_report.get("cross_trader_overlapping_pairs") != EXPECTED_CROSS_OVERLAPS:
        raise ValueError("Phase-19 cross-Trader overlap count drift")

    readiness = phase19_report["readiness"]
    if readiness["chronology_replay_authorized"] is not True:
        raise ValueError("Phase-19 chronology is not authorized")
    if readiness["usd_portfolio_replay_authorized"] is not False:
        raise ValueError("Phase-19 temporal priors must not consume USD replay")
    if readiness["cross_trader_r_aggregation_authorized"] is not False:
        raise ValueError("Phase-19 temporal priors must not consume cross-Trader R")

    governance = phase19_report["governance"]
    if governance["usd_capital_arithmetic_performed"] is not False:
        raise ValueError("Phase-19 report unexpectedly contains USD arithmetic")
    if governance["cross_trader_r_aggregation_performed"] is not False:
        raise ValueError("Phase-19 report unexpectedly aggregates Trader R")
    if governance["provider_economics_fabricated"] is not False:
        raise ValueError("Phase-19 provider economics provenance drift")

    common = phase19_report["common_window"]
    start = datetime.fromisoformat(str(common["start"]))
    end = datetime.fromisoformat(str(common["end"]))
    counts = phase19_report["cross_trader_pair_overlap_counts"]
    if not isinstance(counts, dict) or not counts:
        raise ValueError("Phase-19 pair-overlap evidence missing")
    if sum(int(value) for value in counts.values()) != EXPECTED_CROSS_OVERLAPS:
        raise ValueError("Phase-19 pair-overlap decomposition drift")

    priors: list[HistoricalTemporalCompetitionPrior] = []
    for pair_key, count in sorted(counts.items()):
        parts = str(pair_key).split("|")
        if len(parts) != 2:
            raise ValueError("invalid Phase-19 Trader-pair key")
        left = TraderLineage(parts[0])
        right = TraderLineage(parts[1])
        if left.value >= right.value:
            raise ValueError("Phase-19 pair key is not canonical")
        priors.append(
            HistoricalTemporalCompetitionPrior(
                left_trader=left,
                right_trader=right,
                overlap_pairs=int(count),
                total_cross_trader_overlap_pairs=EXPECTED_CROSS_OVERLAPS,
                observed_window_start=start,
                observed_window_end=end,
                evidence_id=evidence_id,
            )
        )
    return tuple(priors)


def run(
    *,
    report_path: Path,
    evidence_id: str,
    output_path: Path,
) -> dict[str, Any]:
    phase19 = json.loads(report_path.read_text(encoding="utf-8"))
    priors = build_priors(
        phase19_report=phase19,
        evidence_id=evidence_id,
    )
    share_total = sum((item.competition_share for item in priors), start=0)
    if share_total != 1:
        raise ValueError("temporal competition shares must sum exactly to one")

    payload: dict[str, Any] = {
        "schema": "qore.cibo.phase13.temporal_competition_priors.v1",
        "identity": "CIBO_PHASE13_TEMPORAL_COMPETITION_PRIORS_V1",
        "status": "EMPIRICAL_TEMPORAL_PRIORS_GREEN",
        "source": {
            "phase19_identity": phase19["identity"],
            "phase19_status": phase19["status"],
            "evidence_id": evidence_id,
            "window_start": phase19["common_window"]["start"],
            "window_end": phase19["common_window"]["end"],
            "common_window_rows": phase19["total_common_window_rows"],
            "cross_trader_overlap_pairs": EXPECTED_CROSS_OVERLAPS,
        },
        "priors": [
            {
                "left_trader": item.left_trader.value,
                "right_trader": item.right_trader.value,
                "overlap_pairs": item.overlap_pairs,
                "competition_share": str(item.competition_share),
            }
            for item in priors
        ],
        "invariants": {
            "pair_count": len(priors),
            "competition_share_total": str(share_total),
            "pnl_consumed": False,
            "outcome_consumed": False,
            "usd_capital_arithmetic_consumed": False,
            "cross_trader_r_consumed": False,
            "historical_prior_is_allocation_authority": False,
            "historical_prior_is_risk_authority": False,
            "historical_prior_is_execution_authority": False,
        },
        "governance": {
            "research_only": True,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
            "merge_authorized": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--evidence-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                report_path=args.report,
                evidence_id=args.evidence_id,
                output_path=args.output,
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
