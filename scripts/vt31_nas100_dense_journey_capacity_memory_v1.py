"""Dense OCO journey-capacity memory for VT31_NAS100.

Consumed-evidence research only. Labels are structural, not PnL:
- maximum DOL rank reached before methodological invalidation/lifecycle;
- DOL1/DOL2/DOL3+ reach;
- MFE/MAE before invalidation;
- time to invalidation and journey depth.

The entry is supplied by the causal OCO router. Pre-entry context is captured
from the causal Situation Model. This lab is designed to teach target depth and
protection behavior without turning historical R into an entry oracle.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import cast

import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_high_density_management_intelligence_v1 as management
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutionPolicy,
)

SCHEMA = "qore.vt31.nas100.dense_journey_capacity_memory.v1"
MARKET = "NAS100"


def _rate(n: int, d: int) -> str | None:
    return None if d == 0 else format(Decimal(n) / Decimal(d), "f")


def _median_decimal(values: list[Decimal]) -> str | None:
    if not values:
        return None
    return format(Decimal(str(median(values))), "f")


def _group_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    usable = [
        row
        for row in rows
        if row["capacity_status"] == "labeled"
    ]
    ranks = [int(cast(int, row["max_dol_rank"])) for row in usable]
    mfe = [
        Decimal(cast(str, row["mfe_r_before_invalidation"]))
        for row in usable
    ]
    mae = [
        Decimal(cast(str, row["mae_r_before_invalidation"]))
        for row in usable
    ]
    return {
        "observations": len(rows),
        "labeled": len(usable),
        "dol1_reached": sum(rank >= 1 for rank in ranks),
        "dol2_reached": sum(rank >= 2 for rank in ranks),
        "dol3_plus_reached": sum(rank >= 3 for rank in ranks),
        "dol1_rate": _rate(sum(rank >= 1 for rank in ranks), len(usable)),
        "dol2_rate": _rate(sum(rank >= 2 for rank in ranks), len(usable)),
        "dol3_plus_rate": _rate(
            sum(rank >= 3 for rank in ranks),
            len(usable),
        ),
        "invalidated": sum(
            row["invalidated_at"] is not None for row in usable
        ),
        "invalidation_rate": _rate(
            sum(row["invalidated_at"] is not None for row in usable),
            len(usable),
        ),
        "median_max_dol_rank": (
            None if not ranks else str(median(ranks))
        ),
        "median_mfe_r_before_invalidation": _median_decimal(mfe),
        "median_mae_r_before_invalidation": _median_decimal(mae),
    }


def replay(evidence_path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("dense capacity memory requires NAS100 evidence")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        day: tuple(sorted(items, key=lambda bar: getattr(bar, "opened_at")))
        for day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)
    policy = Vt31R22ExecutionPolicy()

    rows: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            continue

        timeline = oco._timeline(
            day_bars,
            evidence_fingerprint=evidence,
        )
        if timeline is None:
            continue
        selected, selection_status = oco._select_oco(
            day_bars,
            timeline,
            policy,
        )
        status_counts[f"oco-{selection_status}"] += 1
        if selected is None:
            continue

        (
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
        ) = context_by_day[local_day]
        observation_at = selected.decision_at
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
            timeline.source,
            selected,
            observation_at,
        )
        context = management._context_state(state)
        capacity = specialist._journey_capacity_label(day_bars, selected)
        capacity_status = str(capacity.get("status"))
        status_counts[f"capacity-{capacity_status}"] += 1

        row: dict[str, object] = {
            "local_date": local_day.isoformat(),
            "decision_at": observation_at.astimezone(UTC).isoformat(),
            "side": selected.side.value,
            "entry_family": selected.selected_family.value,
            "management_context": context,
            "reference_volatility_state": state[
                "reference_volatility_state"
            ],
            "current_path_compressed": state["current_path_compressed"],
            "h1_state": state["h1_state"],
            "h4_state": state["h4_state"],
            "premarket_state": state["premarket_state"],
            "cash_open_state": state["cash_open_state"],
            "prior_day_state": state["prior_day_state"],
            "last_structure_event_family": state[
                "last_structure_event_family"
            ],
            "reference_reclaim_age_minutes": state[
                "reference_reclaim_age_minutes"
            ],
            "risk_ref": state["risk_ref"],
            "decision_minute_ny": state["decision_minute_ny"],
            "capacity_status": (
                "labeled" if capacity_status == "labeled" else capacity_status
            ),
            "max_dol_rank": capacity.get(
                "max_distinct_active_dol_rank_touched_before_invalidation"
            ),
            "mfe_r_before_invalidation": capacity.get(
                "max_favorable_r_before_invalidation"
            ),
            "mae_r_before_invalidation": capacity.get(
                "max_adverse_r_before_invalidation"
            ),
            "invalidated_at": (
                capacity.get("journey_end_at")
                if capacity.get("journey_end_reason")
                == "methodological-invalidation"
                else None
            ),
            "used_for_runtime_decision": False,
        }
        rows.append(row)

    dimensions = (
        "management_context",
        "entry_family",
        "side",
        "reference_volatility_state",
        "h1_state",
        "h4_state",
        "premarket_state",
        "cash_open_state",
        "prior_day_state",
        "last_structure_event_family",
    )
    by_dimension: dict[str, dict[str, object]] = {}
    for dimension in dimensions:
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            grouped[str(row[dimension])].append(row)
        by_dimension[dimension] = {
            key: _group_summary(values)
            for key, values in sorted(grouped.items())
        }

    return {
        "schema": SCHEMA,
        "market": MARKET,
        "candidate_contract_fingerprint": specialist.contract_fingerprint(),
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
            "first_opened_at": getattr(series[0], "opened_at")
            .astimezone(UTC)
            .isoformat(),
            "last_closed_at": getattr(series[-1], "closed_at")
            .astimezone(UTC)
            .isoformat(),
        },
        "summary": _group_summary(rows),
        "by_dimension": by_dimension,
        "status_counts": dict(sorted(status_counts.items())),
        "rows": rows,
        "governance": {
            "label_is_pnl": False,
            "label_is_structural_journey_capacity": True,
            "post_outcome_label_used_at_runtime": False,
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
    print(
        json.dumps(
            {
                "summary": payload["summary"],
                "management_context": payload["by_dimension"][
                    "management_context"
                ],
                "entry_family": payload["by_dimension"]["entry_family"],
                "status_counts": payload["status_counts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
