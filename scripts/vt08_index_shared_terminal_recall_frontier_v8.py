"""VT08 consumed-evidence frontier for expanding Shared terminal recall.

V8 does not change runtime or economics. It reuses the frozen V6 shadow ledger
and asks a narrower question: can a preregistered causal channel add materially
useful terminal-loss recall without increasing winner damage?

The families are intentionally small and interpretable. Outcome is used only
after each point-in-time candidate is selected, for research scoring.
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

IDENTITY = "QORE_SHARED_VT08_TERMINAL_RECALL_FRONTIER_V8"
SCHEMA = "qore.shared.vt08_terminal_recall_frontier.v8"


@dataclass(frozen=True, slots=True)
class CandidateResult:
    name: str
    predicted: int
    true_loss: int
    false_winner: int
    precision: Decimal
    additional_loss_recall: Decimal
    winner_mark_rate: Decimal
    median_lead_bars: Decimal | None
    status: str


def _ratio(n: int, d: int) -> Decimal:
    if d <= 0:
        return Decimal("0")
    return Decimal(n) / Decimal(d)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _first_match(
    trade: dict[str, Any],
    predicate: Callable[[dict[str, Any]], bool],
) -> dict[str, Any] | None:
    for row in trade["observations"]:
        if predicate(row):
            return row
    return None


def _channel_path_commitment(trade: dict[str, Any]) -> dict[str, Any] | None:
    """Late path transition: high precision expected, usefulness falsified by lead."""
    return _first_match(
        trade,
        lambda row: (
            row["recovery_challenge_state"] == "RECOVERY_FAILED"
            and row["path_state"] in {"ADVERSE_DOMINANCE", "FAILURE_RISK"}
            and _d(row["current_position_r"]) <= Decimal("-0.65")
            and int(row["target_hazard_proxy_bps"]) <= 4000
            and int(row["path_terminal_failure_risk_bps"]) >= 5500
        ),
    )


def _channel_contested_exhaustion(trade: dict[str, Any]) -> dict[str, Any] | None:
    """Contested path must remain terminal under two recovery-exhausted observations."""
    run = 0
    for row in trade["observations"]:
        qualifies = (
            row["recovery_challenge_state"] == "RECOVERY_FAILED"
            and row["path_state"] == "CONTESTED"
            and int(row["recovery_strength_bps"]) <= 500
            and int(row["path_terminal_failure_risk_bps"]) >= 6200
            and int(row["path_adverse_dominance_bps"]) >= 5000
            and int(row["target_hazard_proxy_bps"]) <= 3500
            and int(row["uncertainty_bps"]) <= 7000
        )
        if qualifies:
            run += 1
            if run >= 2:
                return row
        else:
            run = 0
    return None


def _channel_deterioration_sequence(trade: dict[str, Any]) -> dict[str, Any] | None:
    """Three-observation rising deterioration; intended to test earlier recall."""
    observations = trade["observations"]
    for idx in range(2, len(observations)):
        window = observations[idx - 2 : idx + 1]
        first = window[0]
        latest = window[-1]
        if (
            latest["recovery_challenge_state"] == "RECOVERY_FAILED"
            and latest["path_state"]
            in {"CONTESTED", "ADVERSE_DOMINANCE", "FAILURE_RISK"}
            and int(latest["path_terminal_failure_risk_bps"]) >= 5500
            and int(latest["path_adverse_dominance_bps"]) >= 4500
            and int(latest["target_hazard_proxy_bps"]) <= 3500
            and int(latest["recovery_strength_bps"]) <= 1500
            and _d(latest["current_position_r"]) <= Decimal("0.25")
            and (
                int(latest["path_terminal_failure_risk_bps"])
                - int(first["path_terminal_failure_risk_bps"])
                >= 300
            )
            and (
                int(latest["path_adverse_dominance_bps"])
                - int(first["path_adverse_dominance_bps"])
                >= 300
            )
        ):
            return latest
    return None


CHANNELS: tuple[tuple[str, Callable[[dict[str, Any]], dict[str, Any] | None]], ...] = (
    ("PATH_COMMITMENT_LATE", _channel_path_commitment),
    ("CONTESTED_RECOVERY_EXHAUSTION", _channel_contested_exhaustion),
    ("RISING_DETERIORATION_SEQUENCE", _channel_deterioration_sequence),
)


def _score_channel(
    *,
    name: str,
    selector: Callable[[dict[str, Any]], dict[str, Any] | None],
    trades: list[dict[str, Any]],
    losses: int,
    winners: int,
) -> CandidateResult:
    selected: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for trade in trades:
        if trade["first_terminal_confirmed"] is not None:
            continue
        row = selector(trade)
        if row is not None:
            selected.append((trade, row))

    true_loss = [
        (trade, row) for trade, row in selected if trade["actual"] == "LOSS"
    ]
    false_winner = [
        (trade, row) for trade, row in selected if trade["actual"] == "WIN"
    ]
    lead = [
        int(row["bars_before_canonical_exit"])
        for trade, row in true_loss
    ]
    precision = _ratio(len(true_loss), len(selected))
    recall = _ratio(len(true_loss), losses)
    winner_mark = _ratio(len(false_winner), winners)
    median_lead = None if not lead else Decimal(str(median(lead)))

    # Research admission is deliberately strict. Positive lead is required;
    # a perfectly precise signal at the stop bar is not useful DD intelligence.
    admitted = (
        bool(selected)
        and precision >= Decimal("0.95")
        and winner_mark <= Decimal("0.005")
        and recall > Decimal("0")
        and median_lead is not None
        and median_lead >= Decimal("1")
    )
    return CandidateResult(
        name=name,
        predicted=len(selected),
        true_loss=len(true_loss),
        false_winner=len(false_winner),
        precision=precision,
        additional_loss_recall=recall,
        winner_mark_rate=winner_mark,
        median_lead_bars=median_lead,
        status="ADMIT_FOR_ECONOMIC_SHADOW" if admitted else "REJECT",
    )


def run(v6_json: Path) -> dict[str, Any]:
    payload = json.loads(v6_json.read_text())
    windows: dict[str, Any] = {}
    for key in ("five_year", "recent_two_year", "r66_consumed_failed_holdout"):
        window = payload[key]
        trades = list(window["rows"])
        losses = sum(trade["actual"] == "LOSS" for trade in trades)
        winners = sum(trade["actual"] == "WIN" for trade in trades)
        current = window["competing_risk_diagnostics"]

        results = [
            _score_channel(
                name=name,
                selector=selector,
                trades=trades,
                losses=losses,
                winners=winners,
            )
            for name, selector in CHANNELS
        ]
        windows[key] = {
            "sample": len(trades),
            "losses": losses,
            "winners": winners,
            "control_terminal_confirmed_count": current["terminal_confirmed_count"],
            "control_terminal_precision": current[
                "terminal_confirmed_precision_for_diagnostics_only"
            ],
            "control_terminal_loss_recall": current["terminal_confirmed_loss_recall"],
            "control_terminal_winner_mark_rate": current[
                "terminal_confirmed_winner_mark_rate"
            ],
            "control_terminal_median_lead_bars": current[
                "median_terminal_confirmed_lead_bars"
            ],
            "channels": {
                result.name: {
                    "predicted": result.predicted,
                    "true_loss": result.true_loss,
                    "false_winner": result.false_winner,
                    "precision": str(result.precision),
                    "additional_loss_recall": str(result.additional_loss_recall),
                    "winner_mark_rate": str(result.winner_mark_rate),
                    "median_lead_bars": (
                        None
                        if result.median_lead_bars is None
                        else str(result.median_lead_bars)
                    ),
                    "status": result.status,
                }
                for result in results
            },
        }

    admitted_all = [
        name
        for name, _ in CHANNELS
        if all(
            windows[key]["channels"][name]["status"]
            == "ADMIT_FOR_ECONOMIC_SHADOW"
            for key in windows
        )
    ]
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": 36131607443,
        "source_shared_head": "1a534d0ae735efef4dcbc0c0be4b110ceaa80501",
        "research_only": True,
        "consumed_evidence_only": True,
        "runtime_actuation": False,
        "sizing_used": False,
        "trailing_used": False,
        "target_extension_used": False,
        "admitted_all_windows": admitted_all,
        "windows": windows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v6-json", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.v6_json)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
