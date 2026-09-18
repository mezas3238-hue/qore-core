"""R5 causal forensics for stale pending CORE entries.

Research-only. It asks:
If the intelligent CORE emits EXECUTE but its selected entry still has not
filled after a predeclared causal latency, can the same VT31 source event
recover through the already-defined OCO route at tiny scout risk?

Latency is grounded in consumed CIBO journey timing:
- 6m: median last-structure-touch -> departure neighborhood.
- 12m: conservative sensitivity near the upper central distribution.

No terminal outcome is used to authorize the fallback. The fallback is
authorized strictly from: CORE_EXECUTE + elapsed pending time + still-valid
source event.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_causal_hybrid_replay_v1 as causal
import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

MARKET = "NAS100"
SCOUT_RISK = Decimal("0.02")
FRICTION = Decimal("0.05")
LATENCIES = (6, 12)


def _core_selection(
    day_bars: tuple[object, ...],
    context: tuple[Decimal | None, Decimal | None, tuple[object, ...]],
    *,
    evidence: str,
) -> tuple[Vt31R22ExecutableSetup | None, dict[str, object] | None]:
    reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
    session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
    if len(reference) != 60 or len(session) != 60:
        return None, None

    previous_path_range, prior_ref_median, prior_admitted = context
    policy = Vt31R22ExecutionPolicy()
    prefix = list(reference)
    saw_wait = False
    for bar in session:
        prefix.append(bar)
        closed_at = cast(datetime, getattr(bar, "closed_at"))
        evaluation = evaluate_vt31_r2_2_source(
            instrument=getattr(bar, "instrument"),
            as_of=closed_at,
            m1_candles=cast(Any, tuple(prefix)),
            evidence_fingerprint=evidence,
        )
        if evaluation.setup is None:
            if saw_wait and evaluation.both_sides_swept:
                return None, None
            continue
        executable, _ = make_executable_setup(evaluation.setup, policy)
        if executable is None:
            return None, None
        session_prefix = tuple(
            item
            for item in prefix
            if (10, 0, 0)
            <= _wall(getattr(item, "opened_at"))
            < (11, 0, 0)
        )
        state = specialist._state_snapshot(
            day_bars,
            previous_path_range,
            prior_ref_median,
            prior_admitted,
            session_prefix,
            evaluation.setup,
            executable,
            closed_at,
        )
        action = cast(str, state["action"])
        if action == "WAIT":
            saw_wait = True
            continue
        if action == "ABSTAIN":
            return None, None
        if action != "EXECUTE":
            raise ValueError(action)
        return causal._activation_setup(executable, closed_at), state
    return None, None


def replay(path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        day: tuple(sorted(rows, key=lambda x: getattr(x, "opened_at")))
        for day, rows in raw.items()
    }
    context_by_day = specialist._context_map(by_day)
    policy = Vt31R22ExecutionPolicy()

    rows_by_latency: dict[int, list[dict[str, object]]] = {
        latency: [] for latency in LATENCIES
    }
    status: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        core, core_state = _core_selection(
            day_bars,
            context_by_day[local_day],
            evidence=evidence,
        )
        if core is None or core_state is None:
            continue
        outcome = specialist._simulate_selected_plan(
            day_bars,
            core,
            core_state,
        )
        if outcome.get("status") != "no-fill":
            continue
        status["core-execute-no-fill"] += 1

        timeline = oco._timeline(day_bars, evidence_fingerprint=evidence)
        if timeline is None:
            status["no-timeline"] += 1
            continue

        for latency in LATENCIES:
            authorization_at = core.decision_at + timedelta(minutes=latency)
            if authorization_at >= core.pending_expires_at:
                status[f"{latency}m-after-expiry"] += 1
                continue
            selected, selection_status = causal._select_secondary_after(
                day_bars,
                timeline,
                policy,
                authorization_at=authorization_at,
            )
            status[f"{latency}m-{selection_status}"] += 1
            if selected is None:
                continue
            recovered = specialist.baseline._simulate(day_bars, selected)
            if recovered.get("status") != "terminal":
                status[f"{latency}m-outcome-{recovered['status']}"] += 1
                continue
            gross = Decimal(cast(str, recovered["r_multiple"]))
            rows_by_latency[latency].append(
                {
                    "local_date": local_day.isoformat(),
                    "authorization_at": authorization_at.astimezone(UTC).isoformat(),
                    "selected_family": selected.selected_family.value,
                    "raw_r": format(gross, "f"),
                    "capital_weighted_net_r": format(
                        SCOUT_RISK * (gross - FRICTION),
                        "f",
                    ),
                }
            )

    return {
        "schema": "qore.vt31.nas100.core_pending_fallback_forensics.v1",
        "market": MARKET,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
        },
        "core_execute_no_fill_count": status["core-execute-no-fill"],
        "latencies": {
            str(latency): {
                "recovered_terminal_count": len(rows),
                "total_capital_weighted_net_r": format(
                    sum(
                        (
                            Decimal(cast(str, row["capital_weighted_net_r"]))
                            for row in rows
                        ),
                        Decimal(0),
                    ),
                    "f",
                ),
                "rows": rows,
            }
            for latency, rows in rows_by_latency.items()
        },
        "status_counts": dict(sorted(status.items())),
        "governance": {
            "authorization_uses_terminal_outcome": False,
            "authorization_is_elapsed_time_after_core_execute": True,
            "same_strategy_source_event": True,
            "scout_risk_r": format(SCOUT_RISK, "f"),
            "consumed_evidence_only": True,
            "policy_promoted": False,
            "opens_new_holdout": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "core_execute_no_fill_count": payload["core_execute_no_fill_count"],
        "latencies": {
            key: {
                "recovered_terminal_count": value["recovered_terminal_count"],
                "total_capital_weighted_net_r": value[
                    "total_capital_weighted_net_r"
                ],
            }
            for key, value in payload["latencies"].items()
        },
        "status_counts": payload["status_counts"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
