"""VT31 NAS100 causal OCO entry-intelligence lab.

Research-only consumed-evidence experiment.

The source methodology can expose Breaker, Order Block and FVG entry evidence
inside the same AM Silver Bullet source event. The legacy execution policy
selects only the earliest formed family. This lab tests a causal OCO router:

- each valid family becomes a pending order only after that evidence has formed;
- at most one order may fill for the source event;
- the first uniquely filled order wins and the others are cancelled;
- if two different entry prices first fill on the same M1 bar, the path is
  censored because intrabar order is unknown;
- a second-side reference sweep before fill cancels the source event.

This changes execution routing, not Strategy Identity. It does not open a
holdout and does not promote the policy automatically.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_specialist_r1_candidate as specialist

import qore.infrastructure.traders.vt31_silver_bullet_r2_2 as source_model
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22EntryEvidence,
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    Vt31R22SourceSetup,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.entry_intelligence_oco_lab.v1"
MARKET = "NAS100"


@dataclass(frozen=True, slots=True)
class SourceTimeline:
    source: Vt31R22SourceSetup
    candidates: tuple[Vt31R22EntryEvidence, ...]
    both_sides_swept_at: datetime | None


def _candidate_key(candidate: Vt31R22EntryEvidence) -> tuple[str, ...]:
    return (
        candidate.family.value,
        candidate.formed_at.astimezone(UTC).isoformat(),
        format(candidate.zone_lower, "f"),
        format(candidate.zone_upper, "f"),
    )


def _source_key(source: Vt31R22SourceSetup) -> tuple[str, ...]:
    return (
        source.side.value,
        source.structure.raid_at.astimezone(UTC).isoformat(),
        source.structure.confirmation_at.astimezone(UTC).isoformat(),
        format(source.structure.swing_extreme, "f"),
        format(source.target_price, "f"),
    )


def _timeline(
    day_bars: tuple[object, ...],
    *,
    evidence_fingerprint: str,
) -> SourceTimeline | None:
    reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
    session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
    if len(reference) != 60 or len(session) != 60:
        return None

    prefix = list(reference)
    first_source: Vt31R22SourceSetup | None = None
    key: tuple[str, ...] | None = None
    candidates: dict[tuple[str, ...], Vt31R22EntryEvidence] = {}
    both_sides_at: datetime | None = None

    for bar in session:
        prefix.append(bar)
        closed_at = cast(datetime, getattr(bar, "closed_at"))
        evaluation = evaluate_vt31_r2_2_source(
            instrument=getattr(bar, "instrument"),
            as_of=closed_at,
            m1_candles=cast(Any, tuple(prefix)),
            evidence_fingerprint=evidence_fingerprint,
        )
        if evaluation.both_sides_swept:
            if first_source is not None:
                both_sides_at = closed_at
                break
            continue
        if evaluation.setup is None:
            continue
        source = evaluation.setup
        current_key = _source_key(source)
        if first_source is None:
            first_source = source
            key = current_key
        elif current_key != key:
            raise ValueError("source event identity drift within AM session")
        for candidate in source.candidates:
            candidates[_candidate_key(candidate)] = candidate

    if first_source is None:
        return None
    ordered = tuple(
        candidates[item]
        for item in sorted(
            candidates,
            key=lambda item: (
                datetime.fromisoformat(item[1]),
                item[0],
                item[2],
                item[3],
            ),
        )
    )
    return SourceTimeline(
        source=first_source,
        candidates=ordered,
        both_sides_swept_at=both_sides_at,
    )


def _candidate_order(
    source: Vt31R22SourceSetup,
    candidate: Vt31R22EntryEvidence,
    policy: Vt31R22ExecutionPolicy,
) -> Vt31R22ExecutableSetup | None:
    entry = source_model._execution_price(candidate, policy)
    stop = source.structure.swing_extreme
    target = source.target_price
    if source.side.value == "short":
        if not target < entry < stop:
            return None
        three_r = entry - (stop - entry) * Decimal(3)
    else:
        if not stop < entry < target:
            return None
        three_r = entry + (entry - stop) * Decimal(3)
    return Vt31R22ExecutableSetup(
        side=source.side,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        three_r_price=three_r,
        selected_family=candidate.family,
        candidate_families=(candidate.family,),
        decision_at=candidate.formed_at,
        pending_expires_at=source.pending_expires_at,
        source_setup=source,
        execution_policy_fingerprint=policy.fingerprint(),
    )


def _fill_index(
    day_bars: tuple[object, ...],
    setup: Vt31R22ExecutableSetup,
) -> int | None:
    return v2b._fill_index(day_bars, setup)


def _fill_before_invalidation(
    day_bars: tuple[object, ...],
    setup: Vt31R22ExecutableSetup,
    both_sides_swept_at: datetime | None,
) -> tuple[int | None, str | None]:
    index = _fill_index(day_bars, setup)
    if index is None:
        return None, None
    bar = day_bars[index]
    opened_at = cast(datetime, getattr(bar, "opened_at"))
    closed_at = cast(datetime, getattr(bar, "closed_at"))
    if both_sides_swept_at is None:
        return index, None
    if closed_at < both_sides_swept_at:
        return index, None
    if opened_at >= both_sides_swept_at:
        return None, "cancelled-before-fill-by-second-side-sweep"
    return None, "censored-same-bar-fill-vs-second-side-sweep"


def _select_oco(
    day_bars: tuple[object, ...],
    timeline: SourceTimeline,
    policy: Vt31R22ExecutionPolicy,
) -> tuple[Vt31R22ExecutableSetup | None, str]:
    candidates: list[tuple[int, Vt31R22ExecutableSetup]] = []
    censored = False
    for evidence in timeline.candidates:
        setup = _candidate_order(timeline.source, evidence, policy)
        if setup is None:
            continue
        fill_index, reason = _fill_before_invalidation(
            day_bars,
            setup,
            timeline.both_sides_swept_at,
        )
        if reason == "censored-same-bar-fill-vs-second-side-sweep":
            censored = True
        if fill_index is not None:
            candidates.append((fill_index, setup))
    if not candidates:
        return (
            None,
            (
                "censored-second-side-fill-ambiguity"
                if censored
                else "no-fill"
            ),
        )

    earliest_index = min(item[0] for item in candidates)
    first = [
        setup for index, setup in candidates if index == earliest_index
    ]
    prices = {setup.entry_price for setup in first}
    if len(prices) > 1:
        return None, "censored-same-bar-multi-price-oco-fill"
    selected = sorted(
        first,
        key=lambda item: (
            item.decision_at,
            item.selected_family.value,
        ),
    )[0]
    return selected, "selected"


def _simulate(
    day_bars: tuple[object, ...],
    setup: Vt31R22ExecutableSetup,
) -> dict[str, object]:
    return specialist.baseline._simulate(day_bars, setup)


def replay(evidence_path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("OCO entry lab requires NAS100 evidence")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        day: tuple(sorted(rows, key=lambda item: getattr(item, "opened_at")))
        for day, rows in raw.items()
    }

    policy = Vt31R22ExecutionPolicy()
    status: Counter[str] = Counter()
    candidate_family_counts: Counter[str] = Counter()
    selected_family_counts: Counter[str] = Counter()
    baseline_terminal: list[dict[str, object]] = []
    oco_terminal: list[dict[str, object]] = []
    oco_rows: list[dict[str, object]] = []

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue
        timeline = _timeline(
            day_bars,
            evidence_fingerprint=evidence,
        )
        if timeline is None:
            status["no-source-timeline"] += 1
            continue
        status["source-timeline"] += 1
        for item in timeline.candidates:
            candidate_family_counts[item.family.value] += 1

        baseline_setup, baseline_reason = make_executable_setup(
            timeline.source,
            policy,
        )
        if baseline_setup is None:
            status[f"baseline-{baseline_reason}"] += 1
        else:
            outcome = _simulate(day_bars, baseline_setup)
            status[f"baseline-{outcome['status']}"] += 1
            if outcome.get("status") == "terminal":
                baseline_terminal.append(outcome)

        selected, selection_status = _select_oco(
            day_bars,
            timeline,
            policy,
        )
        status[f"oco-{selection_status}"] += 1
        if selected is None:
            continue
        selected_family_counts[selected.selected_family.value] += 1
        outcome = _simulate(day_bars, selected)
        status[f"oco-outcome-{outcome['status']}"] += 1
        row = {
            "local_date": local_day.isoformat(),
            "selected_family": selected.selected_family.value,
            "candidate_families_seen": [
                item.family.value for item in timeline.candidates
            ],
            "candidate_count": len(timeline.candidates),
            "decision_at": selected.decision_at.astimezone(UTC).isoformat(),
            "entry": format(selected.entry_price, "f"),
            "stop": format(selected.stop_price, "f"),
            "target": format(selected.target_price, "f"),
            "outcome_status": outcome["status"],
            "r_multiple": outcome.get("r_multiple"),
            "used_for_runtime_decision": False,
        }
        oco_rows.append(row)
        if outcome.get("status") == "terminal":
            oco_terminal.append(outcome)

    baseline_metrics = _metrics(
        baseline_terminal,
        friction=specialist.FRICTION,
    )
    oco_metrics = _metrics(
        oco_terminal,
        friction=specialist.FRICTION,
    )
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
        "market_days": len(by_day),
        "status_counts": dict(sorted(status.items())),
        "candidate_family_counts": dict(sorted(candidate_family_counts.items())),
        "oco_selected_family_counts": dict(
            sorted(selected_family_counts.items())
        ),
        "baseline_terminal_count": len(baseline_terminal),
        "oco_terminal_count": len(oco_terminal),
        "terminal_density_gain": len(oco_terminal) - len(baseline_terminal),
        "baseline_metrics": baseline_metrics,
        "oco_metrics": oco_metrics,
        "target_density_250_300": {
            "at_least_250": len(oco_terminal) >= 250,
            "at_most_300": len(oco_terminal) <= 300,
            "inside_target_band": 250 <= len(oco_terminal) <= 300,
        },
        "oco_rows": oco_rows,
        "governance": {
            "consumed_evidence_only": True,
            "one_trade_max_per_source_event": True,
            "orders_activate_only_after_evidence_forms": True,
            "same_bar_multi_price_fill_censored": True,
            "strategy_identity_changed": False,
            "operating_policy_selection_allowed": False,
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
                "baseline_terminal_count": payload[
                    "baseline_terminal_count"
                ],
                "oco_terminal_count": payload["oco_terminal_count"],
                "terminal_density_gain": payload["terminal_density_gain"],
                "baseline_metrics": payload["baseline_metrics"],
                "oco_metrics": payload["oco_metrics"],
                "target_density_250_300": payload[
                    "target_density_250_300"
                ],
                "selected_family_counts": payload[
                    "oco_selected_family_counts"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
