"""VT31 NAS100 structural rearm quality frontier V1.

Consumed-evidence tuning only.

The raw structural-rearm frontier proved that genuine post-exit source events
exist in sufficient quantity, but taking every rearm destroys drawdown. This
lab keeps the first genuine event and allows at most one post-exit rearm per
day when a predeclared causal quality score passes.

The score uses decision-time structure only:
- reference volatility;
- current-path state;
- H1 state;
- most recent causal structure;
- reclaim freshness;
- entry family;
- confirmation latency;
- stop/reference geometry.

Terminal PnL is attached only after authorization. No outcome field, date-level
oracle, or fold identity enters the quality score.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_specialist_r1_candidate as specialist
import vt31_nas100_structural_rearm_density_frontier_v1 as frontier

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    structurally_rearmed,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
)

SCHEMA = "qore.vt31.nas100.structural_rearm_quality_frontier.v1"
IDENTITY = "VT31_NAS100_STRUCTURAL_REARM_QUALITY_FRONTIER_V1"
MARKET = "NAS100"
FRICTION = Decimal("0.05")
THRESHOLDS = (3, 4, 5, 6, 7)


def _d(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _quality_score(
    state: dict[str, object],
    setup: Vt31R22ExecutableSetup,
) -> tuple[int, tuple[str, ...]]:
    score = 0
    reasons: list[str] = []

    ref = str(state["reference_volatility_state"])
    if ref == "compressed":
        score += 2
        reasons.append("REF_COMPRESSED:+2")
    elif ref == "expanded":
        score -= 1
        reasons.append("REF_EXPANDED:-1")

    path = _d(state["current_path_vs_previous"])
    if path is not None and path < Decimal("0.75"):
        score += 1
        reasons.append("PATH_COMPRESSED:+1")
    elif path is not None and path > Decimal("1.25"):
        score -= 1
        reasons.append("PATH_EXTENDED:-1")

    if state["h1_state"] == "mixed":
        score += 1
        reasons.append("H1_MIXED:+1")

    structure = str(state["last_structure_event_family"])
    if structure == "reference-liquidity-sweep":
        score += 2
        reasons.append("REF_LIQUIDITY_SWEEP:+2")
    elif structure == "breaker":
        score -= 1
        reasons.append("STRUCTURE_BREAKER:-1")

    reclaim_raw = state["reference_reclaim_age_minutes"]
    if reclaim_raw is None:
        score -= 1
        reasons.append("NO_RECLAIM:-1")
    else:
        reclaim = int(cast(int, reclaim_raw))
        if reclaim <= 7:
            score += 1
            reasons.append("RECLAIM_FRESH:+1")
        elif reclaim >= 15:
            score -= 1
            reasons.append("RECLAIM_OLD:-1")

    family = setup.selected_family.value
    if family == "fair-value-gap":
        score += 1
        reasons.append("FVG:+1")
    elif family == "breaker":
        score -= 1
        reasons.append("BREAKER_ENTRY:-1")

    latency = int(cast(int, state["confirmation_latency_minutes"]))
    if latency <= 2:
        score += 1
        reasons.append("FAST_CONFIRMATION:+1")
    elif latency >= 6:
        score -= 1
        reasons.append("SLOW_CONFIRMATION:-1")

    risk_ref = _d(state["risk_ref"])
    if risk_ref is not None and risk_ref <= Decimal("0.50"):
        score += 1
        reasons.append("COMPACT_RISK:+1")
    elif risk_ref is not None and risk_ref > Decimal("0.75"):
        score -= 1
        reasons.append("WIDE_RISK:-1")

    return score, tuple(reasons)


def _mc(
    rows: list[dict[str, object]],
    *,
    variant: str,
) -> dict[str, object]:
    values = [
        Decimal(cast(str, row["r_multiple"])) - FRICTION
        for row in rows
    ]
    n = len(values)
    if not n:
        return {
            "paths": 10000,
            "positive_terminal_probability": "0",
            "p95_max_drawdown_r": "0",
            "p99_max_drawdown_r": "0",
        }
    terminals: list[Decimal] = []
    drawdowns: list[Decimal] = []
    domain = IDENTITY.encode() + b":" + variant.encode()
    for path_index in range(10000):
        sampled: list[Decimal] = []
        block_index = 0
        while len(sampled) < n:
            digest = hashlib.sha256(
                domain
                + b":"
                + str(path_index).encode()
                + b":"
                + str(block_index).encode()
            ).digest()
            start = int.from_bytes(digest, "big") % n
            sampled.extend(
                values[(start + offset) % n]
                for offset in range(5)
            )
            block_index += 1
        equity = Decimal(0)
        peak = Decimal(0)
        max_dd = Decimal(0)
        for value in sampled[:n]:
            equity += value
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
        terminals.append(equity)
        drawdowns.append(max_dd)
    terminals.sort()
    drawdowns.sort()
    return {
        "paths": 10000,
        "block_length": 5,
        "positive_terminal_probability": format(
            Decimal(sum(value > 0 for value in terminals))
            / Decimal(10000),
            "f",
        ),
        "p05_terminal_r": format(
            terminals[(n - 1) * 5 // 100],
            "f",
        ),
        "p50_terminal_r": format(
            terminals[(n - 1) * 50 // 100],
            "f",
        ),
        "p95_max_drawdown_r": format(
            drawdowns[(n - 1) * 95 // 100],
            "f",
        ),
        "p99_max_drawdown_r": format(
            drawdowns[(n - 1) * 99 // 100],
            "f",
        ),
    }


def replay(
    evidence_path: Path,
    *,
    partition: str,
) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("rearm quality frontier requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)
    policy = Vt31R22ExecutionPolicy()

    base_rows: list[dict[str, object]] = []
    rearm_rows: list[dict[str, object]] = []
    status: Counter[str] = Counter()
    score_counts: Counter[int] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        first_selected = frontier._next_executable_after(
            reference=reference,
            session=session,
            after_at=cast(datetime, getattr(reference[-1], "closed_at")),
            evidence=evidence,
            policy=policy,
        )
        if first_selected is None:
            status["no-first-event"] += 1
            continue
        first_source, first_setup = first_selected
        first_outcome = frontier._terminal_trade(day_bars, first_setup)
        if first_outcome is None:
            status["first-nonterminal"] += 1
            continue
        first_row = dict(first_outcome)
        first_row.update(
            {
                "local_date": local_day.isoformat(),
                "event_index": 1,
                "quality_score": None,
                "quality_reasons": [],
                "authorized_by_quality": True,
            }
        )
        base_rows.append(first_row)
        status["first-terminal"] += 1

        first_exit = datetime.fromisoformat(
            cast(str, first_outcome["exit_at"])
        )
        if _wall(first_exit) >= (11, 0, 0):
            status["first-exit-after-source-window"] += 1
            continue

        second_selected = frontier._next_executable_after(
            reference=reference,
            session=session,
            after_at=first_exit,
            evidence=evidence,
            policy=policy,
        )
        if second_selected is None:
            status["no-second-event"] += 1
            continue
        second_source, second_setup = second_selected

        if not structurally_rearmed(
            protected_exit_at_epoch=int(first_exit.timestamp()),
            new_raid_at_epoch=int(second_source.structure.raid_at.timestamp()),
            new_confirmation_at_epoch=int(
                second_source.structure.confirmation_at.timestamp()
            ),
            new_decision_at_epoch=int(second_setup.decision_at.timestamp()),
        ):
            status["second-rearm-invariant-failed"] += 1
            continue

        (
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
        ) = context_by_day[local_day]
        observation_at = second_setup.decision_at
        session_prefix = tuple(
            bar
            for bar in session
            if cast(datetime, getattr(bar, "closed_at")) <= observation_at
        )
        state = specialist._state_snapshot(
            day_bars,
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
            session_prefix,
            second_source,
            second_setup,
            observation_at,
        )
        score, reasons = _quality_score(state, second_setup)
        score_counts[score] += 1

        second_outcome = frontier._terminal_trade(day_bars, second_setup)
        if second_outcome is None:
            status["second-nonterminal"] += 1
            continue
        row = dict(second_outcome)
        row.update(
            {
                "local_date": local_day.isoformat(),
                "event_index": 2,
                "quality_score": score,
                "quality_reasons": list(reasons),
                "reference_volatility_state": state[
                    "reference_volatility_state"
                ],
                "current_path_vs_previous": state[
                    "current_path_vs_previous"
                ],
                "h1_state": state["h1_state"],
                "h4_state": state["h4_state"],
                "last_structure_event_family": state[
                    "last_structure_event_family"
                ],
                "reference_reclaim_age_minutes": state[
                    "reference_reclaim_age_minutes"
                ],
                "confirmation_latency_minutes": state[
                    "confirmation_latency_minutes"
                ],
                "risk_ref": state["risk_ref"],
                "entry_family": second_setup.selected_family.value,
                "previous_exit_reason": first_outcome.get("exit_reason"),
                "previous_side": first_setup.side.value,
                "side_flip": first_setup.side.value != second_setup.side.value,
                "used_for_runtime_decision": False,
            }
        )
        rearm_rows.append(row)
        status["second-terminal"] += 1

    base_rows.sort(key=lambda row: cast(str, row["signal_at"]))
    rearm_rows.sort(key=lambda row: cast(str, row["signal_at"]))

    variants: dict[str, object] = {}
    for threshold in THRESHOLDS:
        selected_rearms = [
            row
            for row in rearm_rows
            if int(cast(int, row["quality_score"])) >= threshold
        ]
        rows = sorted(
            [*base_rows, *selected_rearms],
            key=lambda row: cast(str, row["signal_at"]),
        )
        metrics = _metrics(rows, friction=FRICTION)
        mc = _mc(rows, variant=f"Q{threshold}")
        variants[f"Q{threshold}"] = {
            "quality_threshold": threshold,
            "base_trade_count": len(base_rows),
            "authorized_rearm_count": len(selected_rearms),
            "trade_count": len(rows),
            "metrics": metrics,
            "monte_carlo": mc,
            "density": {
                "at_least_300": len(rows) >= 300,
                "inside_300_350": 300 <= len(rows) <= 350,
            },
        }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET,
        "partition": partition,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
        },
        "base_trade_count": len(base_rows),
        "second_event_terminal_count": len(rearm_rows),
        "score_distribution": {
            str(key): value for key, value in sorted(score_counts.items())
        },
        "variants": variants,
        "status_counts": dict(sorted(status.items())),
        "governance": {
            "quality_score_uses_terminal_pnl": False,
            "quality_score_uses_future_bars": False,
            "quality_score_uses_fold_identity": False,
            "one_rearm_max_per_day": True,
            "one_trade_max_per_source_event": True,
            "new_raid_confirmation_decision_required": True,
            "terminal_outcome_is_research_label_only": True,
            "consumed_evidence_only": True,
            "policy_promoted": False,
            "opens_new_holdout": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "base_trade_count": payload["base_trade_count"],
                "second_event_terminal_count": payload[
                    "second_event_terminal_count"
                ],
                "score_distribution": payload["score_distribution"],
                "variants": payload["variants"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
