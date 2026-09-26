"""Score bound VT31 NAS100 V4 Phase-18 evidence with generic CIBO replay."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_chronological_replay import (
    CiboChronologicalReplayTrade,
    CiboReplayCausalTrade,
    CiboReplayOutcome,
    ReplayEconomicsStatus,
    ReplaySignalFingerprintOrigin,
    reconstructed_signal_fingerprint,
    score_legacy_replay,
)

EXPECTED_TRADES = 806
EXPECTED_PF = Decimal("3.455321118486999415676978877")
EXPECTED_TOTAL_R = Decimal("61.38049535416448786455402411")
EXPECTED_DD_R = Decimal("3.70898490728154195122908861")


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def score(*, bound_path: Path, output_path: Path) -> dict[str, Any]:
    rows = _jsonl(bound_path)
    evidence_ids = (
        "github-actions:r8:10402199719",
        "github-actions:r6:10389112524",
        "github-actions:r5:10380044761",
        "github-actions:vt31-v4:10610673464",
    )

    trades: list[CiboChronologicalReplayTrade] = []
    for row in rows:
        signal_at = datetime.fromisoformat(str(row["signal_at"]))
        entry_at = datetime.fromisoformat(str(row["entry_at"]))
        exit_at = datetime.fromisoformat(str(row["exit_at"]))
        entry = Decimal(str(row["entry_price"]))
        stop = Decimal(str(row["structural_stop"]))
        target = Decimal(str(row["technical_target"]))
        legacy_risk = Decimal(str(row["legacy_vt31_requested_risk_r"]))
        legacy_net = Decimal(
            str(row["legacy_vt31_capital_weighted_net_r"])
        )
        per_unit_net = Decimal(
            str(row["legacy_vt31_net_r_per_requested_r"])
        )

        fingerprint = reconstructed_signal_fingerprint(
            trader_id=TraderLineage.VT31_NAS100,
            qore_symbol="NAS100",
            side=str(row["side"]),
            signal_at=signal_at,
            entry_at=entry_at,
            entry_price=entry,
            structural_stop=stop,
            technical_target=target,
            source_evidence_ids=evidence_ids,
        )
        causal = CiboReplayCausalTrade(
            trader_id=TraderLineage.VT31_NAS100,
            signal_fingerprint=fingerprint,
            signal_fingerprint_origin=(
                ReplaySignalFingerprintOrigin.PHASE18_RECONSTRUCTED
            ),
            qore_symbol="NAS100",
            side=str(row["side"]),
            signal_at=signal_at,
            entry_at=entry_at,
            entry_price=entry,
            structural_stop=stop,
            technical_target=target,
            legacy_risk_scale=legacy_risk,
            minimum_execution_steps=1,
            pre_trade_state=(),
            source_evidence_ids=evidence_ids,
            economics_status=ReplayEconomicsStatus.R_DENOMINATED_ONLY,
        )
        outcome = CiboReplayOutcome(
            exit_at=exit_at,
            raw_outcome_r=Decimal(str(row["r_multiple"])),
            net_outcome_r=per_unit_net,
            exit_reason=str(row["exit_reason"]),
        )
        trades.append(
            CiboChronologicalReplayTrade(
                causal=causal,
                outcome=outcome,
                legacy_net_outcome_r=legacy_net,
            )
        )

    metrics = score_legacy_replay(tuple(trades))
    if metrics.trades != EXPECTED_TRADES:
        raise ValueError("VT31 V4 generic trade-count drift")
    if metrics.profit_factor != EXPECTED_PF:
        raise ValueError("VT31 V4 generic PF drift")
    if metrics.total_r != EXPECTED_TOTAL_R:
        raise ValueError("VT31 V4 generic total-R drift")
    if metrics.max_drawdown_r != EXPECTED_DD_R:
        raise ValueError("VT31 V4 generic drawdown drift")

    report: dict[str, Any] = {
        "schema": "qore.cibo.phase18.generic_legacy_score.v1",
        "trader_id": TraderLineage.VT31_NAS100.value,
        "trades": metrics.trades,
        "profit_factor": str(metrics.profit_factor),
        "total_r": str(metrics.total_r),
        "max_drawdown_r": str(metrics.max_drawdown_r),
        "max_loss_streak": metrics.max_loss_streak,
        "stop_count": metrics.stop_count,
        "provider_economics_status": "R_DENOMINATED_ONLY",
        "usd_cibo_sizing_comparison_authorized": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bound", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            score(bound_path=args.bound, output_path=args.output),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
