"""Cross-fold forensics of VT31 NAS100 hypothesis replacement transitions.

This diagnostic follows the frozen Silver Bullet source through the FAMILY
maturity + market-at-maturity path from Hypothesis Lifecycle V1.  It labels
whether an executed hypothesis is the first accepted hypothesis of the day or
a replacement after one or more causally rejected hypotheses.

Runtime-eligible transition features are captured before authorization.  PnL
is used only after the fact to measure which transition states are robustly
positive/negative across the consumed folds.  No rule is promoted here.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_causal_hybrid_rearm_v1 as capital
import vt31_nas100_hypothesis_lifecycle_frontier_v1 as lifecycle
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders import vt31_silver_bullet_r2_2 as silver
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    Vt31R22SourceSetup,
)

SCHEMA = "qore.vt31.nas100.hypothesis_transition_forensics.v1"
IDENTITY = "VT31_NAS100_HYPOTHESIS_TRANSITION_FORENSICS_V1"
MARKET = "NAS100"
FRICTION = Decimal("0.05")
EXPECTED_SOURCE_SHA256 = lifecycle.EXPECTED_SOURCE_SHA256
EXPECTED_METHODOLOGY_ID = lifecycle.EXPECTED_METHODOLOGY_ID
MIN_STATE_SAMPLE = 10

FEATURE_FIELDS = (
    "execution_role",
    "replacement_depth_bucket",
    "current_family",
    "current_side",
    "confirmation_minute_bucket",
    "maturation_close_progress_bucket",
    "maturation_favorable_bucket",
    "maturation_adverse_bucket",
    "planned_target_r_bucket",
    "risk_ref_bucket",
    "prior_rejection_class",
    "prior_family_x_current_family",
    "prior_side_relation",
    "rejection_to_new_raid_bucket",
    "rejection_to_authorization_bucket",
    "role_x_family",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _ratio_bucket(value: Decimal) -> str:
    if value <= Decimal("0.05"):
        return "le_005"
    if value <= Decimal("0.10"):
        return "005_010"
    if value <= Decimal("0.25"):
        return "010_025"
    if value <= Decimal("0.50"):
        return "025_050"
    return "gt_050"


def _target_bucket(value: Decimal) -> str:
    if value <= Decimal(2):
        return "le_2R"
    if value <= Decimal(3):
        return "2_3R"
    if value <= Decimal(4):
        return "3_4R"
    return "gt_4R"


def _minute_bucket(value: int) -> str:
    if value < 10:
        return "00_09"
    if value < 20:
        return "10_19"
    if value < 30:
        return "20_29"
    if value < 40:
        return "30_39"
    return "40_59"


def _latency_bucket(minutes: int | None) -> str:
    if minutes is None:
        return "none"
    if minutes <= 2:
        return "0_2m"
    if minutes <= 5:
        return "3_5m"
    if minutes <= 10:
        return "6_10m"
    if minutes <= 20:
        return "11_20m"
    return "21m_plus"


def _replacement_depth_bucket(value: int) -> str:
    if value <= 0:
        return "0"
    if value == 1:
        return "1"
    if value == 2:
        return "2"
    return "3_plus"


def _rejection_class(status: str) -> str:
    if status == "NON_EXECUTABLE":
        return "NON_EXECUTABLE"
    if status == "INVALIDATED":
        return "EVENT_INVALIDATED"
    if status.startswith("REJECT_INVALIDATED"):
        return "MATURATION_INVALIDATED"
    if status.startswith("REJECT_WEAK_CLOSE"):
        return "WEAK_CLOSE"
    if status.startswith("REJECT_WEAK_FOLLOW"):
        return "WEAK_FOLLOW"
    if status.startswith("REJECT_EXCESSIVE"):
        return "EXCESSIVE_GIVEBACK"
    if status.startswith("REJECT_TARGET"):
        return "TARGET_EXHAUSTED"
    if status.startswith("REJECT_SESSION"):
        return "SESSION_EXHAUSTED"
    if status.startswith("REJECT_AMBIGUOUS"):
        return "AMBIGUOUS"
    return status


def _maturity_observed_at(
    session: tuple[object, ...],
    source: Vt31R22SourceSetup,
) -> datetime:
    bars_required, _, _, _ = lifecycle._maturity_contract(
        "breaker",
        "FAMILY",
    )
    # Family-specific count.
    family_setup = None
    # Caller always has an executable setup; this fallback is never used.
    del family_setup
    confirmation_index = next(
        index
        for index, bar in enumerate(session)
        if cast(datetime, getattr(bar, "closed_at"))
        == source.structure.confirmation_at
    )
    return cast(
        datetime,
        getattr(
            session[
                min(
                    len(session) - 1,
                    confirmation_index + bars_required,
                )
            ],
            "closed_at",
        ),
    )


def _rejection_decision_at(
    session: tuple[object, ...],
    source: Vt31R22SourceSetup,
    setup: Vt31R22ExecutableSetup,
) -> datetime:
    bars_required, _, _, _ = lifecycle._maturity_contract(
        setup.selected_family.value,
        "FAMILY",
    )
    confirmation_index = next(
        index
        for index, bar in enumerate(session)
        if cast(datetime, getattr(bar, "closed_at"))
        == source.structure.confirmation_at
    )
    return cast(
        datetime,
        getattr(
            session[
                min(
                    len(session) - 1,
                    confirmation_index + bars_required,
                )
            ],
            "closed_at",
        ),
    )


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {
            "sample": 0,
            "profit_factor": None,
            "mean_r": "0",
            "total_r": "0",
            "max_drawdown_r": "0",
            "max_losing_streak": 0,
        }
    return capital._capital_metrics(
        sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    )


def _feature_diagnostics(
    rows: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        for field in FEATURE_FIELDS:
            grouped[f"{field}={row[field]}"].append(row)
    return {
        state: {
            "sample": len(items),
            "metrics": _metrics(items),
        }
        for state, items in sorted(grouped.items())
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    if silver.SOURCE_SHA256 != EXPECTED_SOURCE_SHA256:
        raise AssertionError("Silver Bullet source SHA changed")
    if silver.METHODOLOGY_ID != EXPECTED_METHODOLOGY_ID:
        raise AssertionError("Silver Bullet methodology changed")

    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("transition forensics requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }

    policy = Vt31R22ExecutionPolicy()
    rows: list[dict[str, object]] = []
    status: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        cursor = cast(datetime, getattr(reference[-1], "closed_at"))
        executions = 0
        rejection_depth = 0
        prior_rejection: dict[str, object] | None = None

        for _ in range(lifecycle.MAX_SOURCE_CYCLES_PER_DAY):
            if executions >= lifecycle.MAX_EXECUTIONS_PER_DAY:
                status["execution-cap-reached"] += 1
                break

            event = lifecycle._next_source(
                reference=reference,
                session=session,
                after_at=cursor,
                evidence=evidence,
                policy=policy,
            )
            event_status = cast(str, event["status"])
            status[event_status] += 1
            if event_status == "NO_EVENT":
                break

            if event_status in {"INVALIDATED", "NON_EXECUTABLE"}:
                decision_at = cast(datetime, event["decision_at"])
                rejection_depth += 1
                prior_rejection = {
                    "status": event_status,
                    "decision_at": decision_at,
                    "family": None,
                    "side": None,
                }
                cursor = decision_at
                continue

            source = cast(Vt31R22SourceSetup, event["source"])
            setup = cast(Vt31R22ExecutableSetup, event["setup"])
            maturity = lifecycle._mature(
                session=session,
                source=source,
                setup=setup,
                mode="FAMILY",
            )
            maturity_status = cast(str, maturity["status"])
            status[maturity_status] += 1

            if maturity_status != "MATURED":
                decision_at = _rejection_decision_at(
                    session,
                    source,
                    setup,
                )
                rejection_depth += 1
                prior_rejection = {
                    "status": maturity_status,
                    "decision_at": decision_at,
                    "family": setup.selected_family.value,
                    "side": setup.side.value,
                }
                cursor = decision_at
                continue

            authorization_at = cast(datetime, maturity["authorization_at"])
            authorization_price = _d(maturity["authorization_price"])
            market_setup = lifecycle._market_setup(
                source,
                setup,
                authorization_at=authorization_at,
                authorization_price=authorization_price,
                variant=IDENTITY,
            )
            if market_setup is None:
                status["market-translation-invalid-geometry"] += 1
                rejection_depth += 1
                prior_rejection = {
                    "status": "MARKET_INVALID_GEOMETRY",
                    "decision_at": authorization_at,
                    "family": setup.selected_family.value,
                    "side": setup.side.value,
                }
                cursor = authorization_at
                continue

            outcome = lifecycle._simulate_market_at_close(
                day_bars,
                market_setup,
            )
            status[f"outcome-{outcome['status']}"] += 1
            if outcome.get("status") != "terminal":
                break

            family = market_setup.selected_family.value
            risk = lifecycle._risk_for(family, "FAMILY")
            capital_r = risk * (
                _d(outcome["r_multiple"]) - FRICTION
            )
            ref_width = source.reference.high - source.reference.low
            risk_ref = market_setup.initial_risk / ref_width
            target_r = abs(
                market_setup.target_price - market_setup.entry_price
            ) / market_setup.initial_risk
            minute = (
                authorization_at.astimezone(lifecycle.specialist.NY).hour * 60
                + authorization_at.astimezone(lifecycle.specialist.NY).minute
                - 10 * 60
            )

            prior_status = (
                "NONE"
                if prior_rejection is None
                else _rejection_class(cast(str, prior_rejection["status"]))
            )
            prior_family = (
                "none"
                if prior_rejection is None
                or prior_rejection["family"] is None
                else cast(str, prior_rejection["family"])
            )
            if (
                prior_rejection is None
                or prior_rejection["side"] is None
            ):
                side_relation = "none"
            else:
                side_relation = (
                    "same"
                    if cast(str, prior_rejection["side"])
                    == market_setup.side.value
                    else "flip"
                )
            rejection_at = (
                None
                if prior_rejection is None
                else cast(datetime, prior_rejection["decision_at"])
            )
            raid_latency = (
                None
                if rejection_at is None
                else int(
                    (
                        source.structure.raid_at - rejection_at
                    ).total_seconds()
                    // 60
                )
            )
            auth_latency = (
                None
                if rejection_at is None
                else int(
                    (authorization_at - rejection_at).total_seconds()
                    // 60
                )
            )
            execution_role = (
                "FIRST_MATURED"
                if rejection_depth == 0
                else "REPLACEMENT_MATURED"
            )

            row = dict(outcome)
            row.update(
                {
                    "partition": partition,
                    "local_date": local_day.isoformat(),
                    "capital_weighted_net_r": format(capital_r, "f"),
                    "requested_risk_r": format(risk, "f"),
                    "execution_role": execution_role,
                    "replacement_depth_bucket": (
                        _replacement_depth_bucket(rejection_depth)
                    ),
                    "current_family": family,
                    "current_side": market_setup.side.value,
                    "confirmation_minute_bucket": _minute_bucket(minute),
                    "maturation_close_progress_bucket": _ratio_bucket(
                        _d(maturity["close_progress_ref"])
                    ),
                    "maturation_favorable_bucket": _ratio_bucket(
                        _d(maturity["favorable_ref"])
                    ),
                    "maturation_adverse_bucket": _ratio_bucket(
                        _d(maturity["adverse_ref"])
                    ),
                    "planned_target_r_bucket": _target_bucket(target_r),
                    "risk_ref_bucket": _ratio_bucket(risk_ref),
                    "prior_rejection_class": prior_status,
                    "prior_family_x_current_family": (
                        f"{prior_family}|{family}"
                    ),
                    "prior_side_relation": side_relation,
                    "rejection_to_new_raid_bucket": _latency_bucket(
                        raid_latency
                    ),
                    "rejection_to_authorization_bucket": _latency_bucket(
                        auth_latency
                    ),
                    "role_x_family": f"{execution_role}|{family}",
                    "future_label_used_at_runtime": False,
                }
            )
            rows.append(row)
            executions += 1
            rejection_depth = 0
            prior_rejection = None

            exit_at = datetime.fromisoformat(cast(str, outcome["exit_at"]))
            cursor = exit_at
            if _wall(exit_at) >= (11, 0, 0):
                break

    rows.sort(key=lambda row: cast(str, row["signal_at"]))
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "partition": partition,
        "market": MARKET,
        "overall": _metrics(rows),
        "feature_diagnostics": _feature_diagnostics(rows),
        "status_counts": dict(sorted(status.items())),
        "trade_count": len(rows),
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "silver_bullet_modified": False,
            "diagnostic_only": True,
            "future_labels_runtime_forbidden": True,
            "terminal_pnl_used_at_runtime": False,
            "fold_identity_used_at_runtime": False,
            "h4_primary_causal_feature": False,
            "h1_primary_causal_feature": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
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
    print(json.dumps(
        {
            "partition": payload["partition"],
            "trade_count": payload["trade_count"],
            "overall": payload["overall"],
            "status_counts": payload["status_counts"],
        },
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
