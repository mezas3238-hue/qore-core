"""Score VT08 R3.15 FundedNext legacy policy replay with generic Phase 18."""

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


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def score(
    *,
    bound_path: Path,
    policy_report_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    rows = _jsonl(bound_path)
    policy_report = json.loads(policy_report_path.read_text(encoding="utf-8"))
    expected = policy_report["canonical_result"]["entry_order_metrics"]
    evidence_ids = (
        "github-actions:vt08-r315:10318827002",
        "github-actions:vt08-r312-risk:10309794877",
    )

    trades: list[CiboChronologicalReplayTrade] = []
    for row in rows:
        signal_at = datetime.fromisoformat(str(row["signal_at"]))
        entry_at = datetime.fromisoformat(str(row["entry_at"]))
        exit_at = datetime.fromisoformat(str(row["exit_at"]))
        entry = Decimal(str(row["entry_price"]))
        stop = Decimal(str(row["structural_stop"]))
        target = Decimal(str(row["technical_target"]))
        fingerprint = reconstructed_signal_fingerprint(
            trader_id=TraderLineage.VT08_FOREX,
            qore_symbol=str(row["symbol"]),
            side=str(row["side"]),
            signal_at=signal_at,
            entry_at=entry_at,
            entry_price=entry,
            structural_stop=stop,
            technical_target=target,
            source_evidence_ids=evidence_ids,
        )
        causal = CiboReplayCausalTrade(
            trader_id=TraderLineage.VT08_FOREX,
            signal_fingerprint=fingerprint,
            signal_fingerprint_origin=(
                ReplaySignalFingerprintOrigin.PHASE18_RECONSTRUCTED
            ),
            qore_symbol=str(row["symbol"]),
            side=str(row["side"]),
            signal_at=signal_at,
            entry_at=entry_at,
            entry_price=entry,
            structural_stop=stop,
            technical_target=target,
            legacy_risk_scale=Decimal(str(row["legacy_risk_scale_r25"])),
            minimum_execution_steps=1,
            pre_trade_state=(
                ("provider_profile", str(row["profile_id"])),
                (
                    "legacy_regime_risk_bps",
                    str(row["legacy_regime_risk_bps"]),
                ),
                (
                    "legacy_authorized_risk_bps_pre_broker",
                    str(row["legacy_authorized_risk_bps_pre_broker"]),
                ),
            ),
            source_evidence_ids=evidence_ids,
            economics_status=ReplayEconomicsStatus.R_DENOMINATED_ONLY,
        )
        outcome = CiboReplayOutcome(
            exit_at=exit_at,
            raw_outcome_r=Decimal(str(row["raw_outcome_r"])),
            net_outcome_r=Decimal(str(row["raw_outcome_r"])),
            exit_reason=str(row["exit_reason"]),
        )
        trades.append(
            CiboChronologicalReplayTrade(
                causal=causal,
                outcome=outcome,
                legacy_net_outcome_r=Decimal(
                    str(row["legacy_net_outcome_r25"])
                ),
            )
        )

    metrics = score_legacy_replay(tuple(trades))
    checks = {
        "trades": (metrics.trades, int(expected["trades"])),
        "profit_factor": (
            None if metrics.profit_factor is None else str(metrics.profit_factor),
            expected["profit_factor"],
        ),
        "total_r25": (str(metrics.total_r), expected["total_r25"]),
        "max_drawdown_r25_entry_order": (
            str(metrics.max_drawdown_r),
            expected["max_drawdown_r25_entry_order"],
        ),
        "max_losing_streak_entry_order": (
            metrics.max_loss_streak,
            int(expected["max_losing_streak_entry_order"]),
        ),
    }
    for label, (actual, wanted) in checks.items():
        if actual != wanted:
            raise ValueError(
                f"VT08 generic Phase-18 {label} drift: {actual!r} != {wanted!r}"
            )

    report: dict[str, Any] = {
        "schema": "qore.cibo.phase18.generic_legacy_score.v1",
        "trader_id": TraderLineage.VT08_FOREX.value,
        "unit": "R25",
        "trades": metrics.trades,
        "profit_factor": (
            None if metrics.profit_factor is None else str(metrics.profit_factor)
        ),
        "total_r25": str(metrics.total_r),
        "max_drawdown_r25_entry_order": str(metrics.max_drawdown_r),
        "max_loss_streak": metrics.max_loss_streak,
        "stop_count": metrics.stop_count,
        "provider_profile": policy_report["canonical_profile"],
        "provider_economics_status": "R_DENOMINATED_ONLY",
        "pre_broker_capital_policy_only": True,
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
    parser.add_argument("--policy-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(score(
        bound_path=args.bound,
        policy_report_path=args.policy_report,
        output_path=args.output,
    ), sort_keys=True))


if __name__ == "__main__":
    main()
