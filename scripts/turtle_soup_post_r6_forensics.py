"""Post-R6 diagnostic forensics for Turtle Soup rejected research evidence."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from statistics import median

POLICIES = ("C_TRAIL1_H3", "C_TRAIL1_H6", "C_TRAIL2_H3", "C_TRAIL2_H6")
WF_START = datetime(2024, 9, 1, tzinfo=timezone.utc)
OOS_START = datetime(2026, 3, 1, tzinfo=timezone.utc)


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def num(value: object) -> float | None:
    return None if value is None else float(value)


def pf(values: list[float]) -> float | None:
    gains = sum(x for x in values if x > 0)
    losses = -sum(x for x in values if x < 0)
    return None if losses == 0 else gains / losses


def digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return sha256(raw).hexdigest()


def closed(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [row for row in rows if row["decision"] == "closed"]


def enrich(row: dict[str, object]) -> dict[str, object]:
    out = dict(row)
    for key in (
        "entry", "stop", "gross_r", "net_1bp_r", "net_2bp_r",
        "mfe_lower_bound_r", "mae_lower_bound_r",
    ):
        out[key] = num(out.get(key))
    entry = float(out["entry"])
    stop = float(out["stop"])
    out["fill_at_dt"] = dt(str(out["fill_at"]))
    out["risk_abs"] = abs(entry - stop)
    out["risk_bps"] = float(out["risk_abs"]) / entry * 10000
    gross = out["gross_r"]
    net = out["net_1bp_r"]
    out["cost_1bp_r"] = None if gross is None else float(gross) - float(net)
    return out


def metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    rows = closed(rows)
    net = [float(r["net_1bp_r"]) for r in rows]
    gross = [float(r["gross_r"]) for r in rows]
    winners = [r for r in rows if float(r["net_1bp_r"]) > 0]
    losers = [r for r in rows if float(r["net_1bp_r"]) < 0]
    return {
        "closed": len(rows),
        "wins": len(winners),
        "losses": len(losers),
        "net_total_r": sum(net),
        "gross_total_r": sum(gross),
        "net_pf": pf(net),
        "gross_pf": pf(gross),
        "win_rate": len(winners) / len(rows) if rows else None,
        "median_risk_bps": median(float(r["risk_bps"]) for r in rows) if rows else None,
        "median_cost_1bp_r": median(float(r["cost_1bp_r"]) for r in rows) if rows else None,
        "cost_ge_0_5r_share": (
            sum(float(r["cost_1bp_r"]) >= 0.5 for r in rows) / len(rows) if rows else None
        ),
        "loser_mfe_ge_0_25_share": (
            sum(float(r["mfe_lower_bound_r"]) >= 0.25 for r in losers) / len(losers)
            if losers else None
        ),
        "loser_mfe_ge_1_share": (
            sum(float(r["mfe_lower_bound_r"]) >= 1 for r in losers) / len(losers)
            if losers else None
        ),
        "loser_mfe_ge_2_share": (
            sum(float(r["mfe_lower_bound_r"]) >= 2 for r in losers) / len(losers)
            if losers else None
        ),
    }


def concentration(rows: list[dict[str, object]]) -> dict[str, object]:
    positive = sorted(
        (float(r["net_1bp_r"]) for r in closed(rows) if float(r["net_1bp_r"]) > 0),
        reverse=True,
    )
    total = sum(positive)

    def share(n: int) -> float | None:
        return sum(positive[:n]) / total if total > 0 else None

    return {
        "positive_count": len(positive),
        "positive_total_r": total,
        "top1_share": share(1),
        "top3_share": share(3),
        "top5_share": share(5),
        "top10_share": share(10),
        "largest_winner_r": positive[0] if positive else None,
    }


def grouped(rows: list[dict[str, object]], key: str) -> dict[str, object]:
    groups: defaultdict[object, list[dict[str, object]]] = defaultdict(list)
    for row in closed(rows):
        groups[row[key]].append(row)
    return {str(name): metrics(values) for name, values in sorted(groups.items(), key=lambda x: str(x[0]))}


def quarter_stats(rows: list[dict[str, object]]) -> dict[str, object]:
    groups: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in closed(rows):
        when = row["fill_at_dt"]
        if not isinstance(when, datetime):
            raise TypeError("fill_at_dt must be datetime")
        if WF_START <= when < OOS_START:
            q = f"{when.year}Q{((when.month - 1) // 3) + 1}"
            groups[q].append(row)
    result: dict[str, object] = {}
    for q, values in sorted(groups.items()):
        item = metrics(values)
        item["stop_or_gap_share"] = (
            sum(r["exit_reason"] in {"stop", "gap-stop"} for r in values) / len(values)
        )
        result[q] = item
    return result


def exit_forensics(rows: list[dict[str, object]]) -> dict[str, object]:
    groups: defaultdict[object, list[dict[str, object]]] = defaultdict(list)
    for row in closed(rows):
        groups[row["exit_reason"]].append(row)
    return {str(reason): metrics(values) for reason, values in sorted(groups.items(), key=lambda x: str(x[0]))}


def analyze_policy(rows: list[dict[str, object]], source_fill_count: int) -> dict[str, object]:
    enriched = [enrich(row) for row in rows]
    attempt1 = enriched[:source_fill_count]
    attempt2 = enriched[source_fill_count:]
    all_closed = closed(enriched)
    pre = [r for r in all_closed if r["fill_at_dt"] < WF_START]
    wf = [r for r in all_closed if WF_START <= r["fill_at_dt"] < OOS_START]
    losses = [r for r in all_closed if float(r["net_1bp_r"]) < 0]
    return {
        "attempt1": metrics(attempt1),
        "attempt2": metrics(attempt2),
        "combined": metrics(enriched),
        "pre_walk_forward": metrics(pre),
        "walk_forward": metrics(wf),
        "exit_reason_counts": dict(Counter(str(r["exit_reason"]) for r in all_closed)),
        "exit_reason_metrics": exit_forensics(enriched),
        "positive_gain_concentration": concentration(enriched),
        "attempt1_positive_gain_concentration": concentration(attempt1),
        "side": grouped(enriched, "side"),
        "market": grouped(enriched, "market"),
        "walk_forward_quarters": quarter_stats(enriched),
        "failed_reversal_after_recovery_share_of_losses": (
            sum(
                r["exit_reason"] == "stop" and float(r["mfe_lower_bound_r"]) >= 0.25
                for r in losses
            ) / len(losses)
            if losses else None
        ),
    }


def payoff(rows: list[dict[str, object]]) -> dict[str, float]:
    wins = [float(r["net_1bp_r"]) for r in rows if float(r["net_1bp_r"]) > 0]
    losses = [float(r["net_1bp_r"]) for r in rows if float(r["net_1bp_r"]) < 0]
    avg_win = sum(wins) / len(wins)
    avg_loss = sum(losses) / len(losses)
    return {
        "avg_win_r": avg_win,
        "avg_loss_r": avg_loss,
        "actual_win_rate": len(wins) / len(rows),
        "breakeven_win_rate_from_payoffs": (-avg_loss) / (avg_win - avg_loss),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r6-report", type=Path, required=True)
    parser.add_argument("--r6-trades", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    r6 = json.loads(args.r6_report.read_text(encoding="utf-8"))
    trades = json.loads(args.r6_trades.read_text(encoding="utf-8"))
    assert r6["final_verdict"] == "R6_REENTRY_EXPERIMENT_REJECTED"
    assert r6["fresh_oos_consumed"] is False
    assert r6["candidate_freeze"] is None
    assert r6["r5_source_fills"] == 290
    assert tuple(sorted(trades)) == tuple(sorted(POLICIES))

    policies = {
        policy: analyze_policy(trades[policy], int(r6["r5_source_fills"]))
        for policy in POLICIES
    }
    invariants = {
        "attempt1_gross_negative_all_policies": all(
            float(p["attempt1"]["gross_total_r"]) < 0 for p in policies.values()
        ),
        "attempt2_gross_negative_all_policies": all(
            float(p["attempt2"]["gross_total_r"]) < 0 for p in policies.values()
        ),
        "walk_forward_gross_negative_all_policies": all(
            float(p["walk_forward"]["gross_total_r"]) < 0 for p in policies.values()
        ),
        "every_walk_forward_quarter_net_negative_all_policies": all(
            all(float(q["net_total_r"]) < 0 for q in p["walk_forward_quarters"].values())
            for p in policies.values()
        ),
    }

    anchor_rows = [enrich(row) for row in trades["C_TRAIL2_H3"]]
    anchor_closed = closed(anchor_rows)
    pre_rows = [r for r in anchor_closed if r["fill_at_dt"] < WF_START]
    wf_rows = [r for r in anchor_closed if WF_START <= r["fill_at_dt"] < OOS_START]

    report: dict[str, object] = {
        "schema": "qore.trader_lab.turtle_soup_post_r6_forensics.v1",
        "source_r6_report_digest": r6["report_digest_sha256"],
        "source_r6_software_sha": r6["software_sha"],
        "fresh_oos_consumed": False,
        "candidate_selection_authorized": False,
        "forensics_only": True,
        "policies": policies,
        "cross_policy_invariants": invariants,
        "anchor_policy_diagnostic_only": "C_TRAIL2_H3",
        "anchor_payoff_regime_shift": {
            "pre_walk_forward": payoff(pre_rows),
            "walk_forward": payoff(wf_rows),
        },
        "root_cause_ranking": [
            {
                "rank": 1,
                "code": "REVERSAL_PERSISTENCE_FAILURE",
                "finding": "Most losses are stops after favorable recovery; the setup often creates a bounce but not a durable reversal.",
            },
            {
                "rank": 2,
                "code": "RIGHT_TAIL_INSTABILITY",
                "finding": "Pre-Walk-Forward viability depends on rare very large winners whose magnitude collapses in forward folds.",
            },
            {
                "rank": 3,
                "code": "INITIAL_STOP_COST_GEOMETRY",
                "finding": "Attempt-1 risk is often so small that 1bp cost consumes a large fraction of R; gross PF is also below 1, so costs amplify rather than create failure.",
            },
            {
                "rank": 4,
                "code": "MARKET_SIDE_NON_STATIONARITY",
                "finding": "Positive-looking market/side pockets are concentrated and do not survive Walk Forward broadly; this is diagnostic, not permission to filter.",
            },
        ],
        "forensic_verdict": "STRUCTURAL_EDGE_FAILURE_NOT_MANAGEMENT_ONLY",
    }
    report["report_digest_sha256"] = digest(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "forensic_verdict": report["forensic_verdict"],
        "report_digest_sha256": report["report_digest_sha256"],
        "cross_policy_invariants": invariants,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
