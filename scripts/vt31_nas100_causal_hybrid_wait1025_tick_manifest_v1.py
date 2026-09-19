"""Exact tick manifest for the causal-hybrid WAIT_1025_B060 policy.

Consumed-evidence research only.

This enumerates only intrabar ambiguity actually reached by the causal hybrid
after CORE reasoning and authorization timing. It is narrower than the generic
OCO manifest because SECONDARY/SCOUT orders may activate later.

The manifest does not resolve ambiguity, change economics, or open a holdout.
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
from typing import Any, cast

import vt31_nas100_causal_hybrid_replay_v1 as v1
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

SCHEMA = "qore.vt31.nas100.causal_hybrid_wait1025_tick_manifest.v1"
MARKET = "NAS100"
PROVIDER = "USTEC"
WAIT_RELEASE_MINUTE = 10 * 60 + 25
MONTHLY_ALT_BUDGET = Decimal("0.60")
SECONDARY_RISK = Decimal("0.05")
SCOUT_RISK = Decimal("0.02")
VARIANT = "WAIT_1025_B060"


def _ms(value: datetime) -> int:
    return int(value.astimezone(UTC).timestamp() * 1000)


def _window_id(payload: dict[str, object]) -> str:
    encoded=json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()[:24]


def _order_payload(setup: Vt31R22ExecutableSetup) -> dict[str, object]:
    return {
        "family": setup.selected_family.value,
        "side": setup.side.value,
        "entry": format(setup.entry_price, "f"),
        "initial_stop": format(setup.stop_price, "f"),
        "target": format(setup.target_price, "f"),
        "activation_at": setup.decision_at.astimezone(UTC).isoformat(),
        "activation_ms": _ms(setup.decision_at),
    }


def _fill_candidates_after(
    day_bars: tuple[object, ...],
    timeline: oco.SourceTimeline,
    policy: Vt31R22ExecutionPolicy,
    *,
    authorization_at: datetime,
) -> tuple[list[tuple[int, Vt31R22ExecutableSetup]], bool]:
    candidates: list[tuple[int, Vt31R22ExecutableSetup]] = []
    censored_second_side = False
    for evidence in timeline.candidates:
        raw_setup=oco._candidate_order(timeline.source, evidence, policy)
        if raw_setup is None:
            continue
        setup=v1._activation_setup(raw_setup, authorization_at)
        fill_index, reason=v1._fill_after_authorization(
            day_bars,
            setup,
            authorization_at=authorization_at,
            both_sides_swept_at=timeline.both_sides_swept_at,
        )
        if reason == "censored-same-bar-fill-vs-second-side-sweep":
            censored_second_side = True
        if fill_index is not None:
            candidates.append((fill_index, setup))
    return candidates, censored_second_side


def build(
    evidence_path: Path,
    *,
    partition: str,
) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider=(
        load_market_evidence(evidence_path)
    )
    if provider != PROVIDER:
        raise ValueError(f"expected provider {PROVIDER}, got {provider}")
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("causal-hybrid tick manifest requires NAS100")

    raw: dict[date, list[object]]=defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day={
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }
    context_by_day=specialist._context_map(by_day)
    policy=Vt31R22ExecutionPolicy()

    current_month: str | None=None
    alt_budget=Decimal(0)
    windows: list[dict[str, object]]=[]
    status: Counter[str]=Counter()

    for local_day in sorted(by_day):
        month=local_day.isoformat()[:7]
        if month != current_month:
            current_month=month
            alt_budget=MONTHLY_ALT_BUDGET

        day_bars=by_day[local_day]
        reference=specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session=specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        timeline=oco._timeline(day_bars, evidence_fingerprint=evidence)
        prefix=list(reference)
        (
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
        )=context_by_day[local_day]

        core_selected: Vt31R22ExecutableSetup | None=None
        core_state: dict[str, object] | None=None
        alt_authorized_at: datetime | None=None
        alt_reason: str | None=None
        alt_tier: str | None=None
        alt_risk: Decimal | None=None
        saw_wait=False
        source_invalidated=False

        for bar in session:
            prefix.append(bar)
            closed_at=cast(datetime, getattr(bar, "closed_at"))
            evaluation=evaluate_vt31_r2_2_source(
                instrument=getattr(bar, "instrument"),
                as_of=closed_at,
                m1_candles=cast(Any, tuple(prefix)),
                evidence_fingerprint=evidence,
            )
            if evaluation.setup is None:
                if saw_wait and evaluation.both_sides_swept:
                    source_invalidated=True
                    status["core-invalidated-after-wait"] += 1
                    break
                continue

            executable, _=make_executable_setup(evaluation.setup, policy)
            if executable is None:
                alt_authorized_at=closed_at
                alt_reason="CORE_SOURCE_NOT_SINGLE_ROUTE_EXECUTABLE"
                alt_tier="SECONDARY"
                alt_risk=SECONDARY_RISK
                status["secondary-authorized-source-router"] += 1
                break

            session_prefix=tuple(
                item
                for item in prefix
                if (10, 0, 0)
                <= _wall(getattr(item, "opened_at"))
                < (11, 0, 0)
            )
            state=specialist._state_snapshot(
                day_bars,
                previous_path_range,
                prior_ref_median,
                prior_admitted_day_bars,
                session_prefix,
                evaluation.setup,
                executable,
                closed_at,
            )
            action=cast(str, state["action"])
            if action == "WAIT":
                saw_wait=True
                status["core-wait-observation"] += 1
                if specialist.baseline._local_minute(bar) >= WAIT_RELEASE_MINUTE:
                    alt_authorized_at=closed_at
                    alt_reason=f"CORE_PERSISTENT_WAIT_{WAIT_RELEASE_MINUTE}"
                    alt_tier="SCOUT"
                    alt_risk=SCOUT_RISK
                    status["scout-authorized-persistent-wait"] += 1
                    break
                continue
            if action == "ABSTAIN":
                alt_authorized_at=closed_at
                alt_reason="CORE_CAUSAL_ABSTAIN"
                alt_tier="SECONDARY"
                alt_risk=SECONDARY_RISK
                status["secondary-authorized-core-abstain"] += 1
                break
            if action != "EXECUTE":
                raise ValueError(action)
            core_selected=v1._activation_setup(executable, closed_at)
            core_state=state
            break

        if core_selected is not None and core_state is not None:
            outcome=specialist._simulate_selected_plan(
                day_bars,
                core_selected,
                core_state,
            )
            status[f"core-{outcome['status']}"] += 1
            continue

        if (
            source_invalidated
            or alt_authorized_at is None
            or alt_risk is None
            or alt_tier is None
        ):
            status["no-alt-authorization"] += 1
            continue
        if timeline is None:
            status["alt-no-oco-timeline"] += 1
            continue
        if (
            timeline.both_sides_swept_at is not None
            and timeline.both_sides_swept_at <= alt_authorized_at
        ):
            status["alt-source-invalidated-before-authorization"] += 1
            continue
        if alt_budget < alt_risk:
            status["alt-monthly-budget-exhausted"] += 1
            continue

        candidates, censored_second_side=_fill_candidates_after(
            day_bars,
            timeline,
            policy,
            authorization_at=alt_authorized_at,
        )
        if not candidates:
            status[
                "alt-censored-second-side-fill-ambiguity"
                if censored_second_side
                else "alt-no-causal-fill"
            ] += 1
            continue

        earliest_index=min(index for index, _ in candidates)
        first=[
            setup
            for index, setup in candidates
            if index == earliest_index
        ]
        fill_bar=day_bars[earliest_index]
        opened_at=cast(datetime, getattr(fill_bar, "opened_at"))
        closed_at=cast(datetime, getattr(fill_bar, "closed_at"))
        prices={setup.entry_price for setup in first}

        if len(prices) > 1:
            base: dict[str, object]={
                "classification":"HYBRID_ALT_MULTI_PRICE_FIRST_FILL",
                "variant":VARIANT,
                "partition":partition,
                "market":MARKET,
                "provider":PROVIDER,
                "ny_date":local_day.isoformat(),
                "tier":alt_tier,
                "authorization_reason":cast(str, alt_reason),
                "requested_risk_r":format(alt_risk, "f"),
                "authorization_at":alt_authorized_at.astimezone(UTC).isoformat(),
                "authorization_ms":_ms(alt_authorized_at),
                "side":first[0].side.value,
                "tick_window_open_ms":_ms(opened_at),
                "tick_window_close_ms":_ms(closed_at)-1,
                "fill_bar_opened_at":opened_at.astimezone(UTC).isoformat(),
                "fill_bar_closed_at":closed_at.astimezone(UTC).isoformat(),
                "orders":[
                    _order_payload(item)
                    for item in sorted(
                        first,
                        key=lambda item:(
                            item.decision_at,
                            item.selected_family.value,
                            item.entry_price,
                        ),
                    )
                ],
            }
            base["window_id"]=_window_id(base)
            windows.append(base)
            status["alt-censored-same-bar-multi-price-oco-fill"] += 1
            continue

        selected=sorted(
            first,
            key=lambda item:(
                item.decision_at,
                item.selected_family.value,
            ),
        )[0]
        outcome=specialist.baseline._simulate(day_bars, selected)
        status[f"alt-outcome-{outcome['status']}"] += 1
        if outcome.get("status") == "terminal":
            alt_budget -= alt_risk
            continue
        if outcome.get("status") != "censored-fill-bar-path":
            continue

        high=Decimal(str(getattr(fill_bar, "high")))
        low=Decimal(str(getattr(fill_bar, "low")))
        base={
            "classification":"HYBRID_ALT_FILL_BAR_PATH",
            "variant":VARIANT,
            "partition":partition,
            "market":MARKET,
            "provider":PROVIDER,
            "ny_date":local_day.isoformat(),
            "tier":alt_tier,
            "authorization_reason":cast(str, alt_reason),
            "requested_risk_r":format(alt_risk, "f"),
            "authorization_at":alt_authorized_at.astimezone(UTC).isoformat(),
            "authorization_ms":_ms(alt_authorized_at),
            "side":selected.side.value,
            "tick_window_open_ms":_ms(opened_at),
            "tick_window_close_ms":_ms(closed_at)-1,
            "fill_bar_opened_at":opened_at.astimezone(UTC).isoformat(),
            "fill_bar_closed_at":closed_at.astimezone(UTC).isoformat(),
            "entry":format(selected.entry_price, "f"),
            "initial_stop":format(selected.stop_price, "f"),
            "target":format(selected.target_price, "f"),
            "activation_at":selected.decision_at.astimezone(UTC).isoformat(),
            "activation_ms":_ms(selected.decision_at),
            "family":selected.selected_family.value,
            "m1_high":format(high, "f"),
            "m1_low":format(low, "f"),
        }
        base["window_id"]=_window_id(base)
        windows.append(base)
        status["hybrid-alt-fill-bar-manifested"] += 1

    payload: dict[str, object]={
        "schema":SCHEMA,
        "research_only":True,
        "opens_new_holdout":False,
        "candidate_status":"RESEARCH_NOT_CERTIFIED",
        "variant":VARIANT,
        "partition":partition,
        "market":MARKET,
        "provider":PROVIDER,
        "source_evidence":{
            "account_fingerprint":account,
            "evidence_fingerprint":evidence,
            "evidence_software_sha":evidence_sha,
            "checked_at":checked.astimezone(UTC).isoformat(),
        },
        "window_count":len(windows),
        "classification_counts":dict(
            sorted(Counter(str(row["classification"]) for row in windows).items())
        ),
        "status_counts":dict(sorted(status.items())),
        "windows":sorted(
            windows,
            key=lambda row:(
                cast(int, row["tick_window_open_ms"]),
                cast(str, row["window_id"]),
            ),
        ),
        "governance":{
            "core_reasoning_replayed_causally":True,
            "authorization_timestamp_respected":True,
            "monthly_alt_budget_respected":True,
            "terminal_pnl_used_to_form_window":False,
            "future_bars_used_to_authorize_entry":False,
            "policy_promoted":False,
            "live_authorized":False,
            "production_authorized":False,
        },
    }
    encoded=json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    payload["sha256"]=hashlib.sha256(encoded).hexdigest()
    return payload


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args=parser.parse_args()
    payload=build(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2)+"\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "partition":payload["partition"],
        "variant":payload["variant"],
        "window_count":payload["window_count"],
        "classification_counts":payload["classification_counts"],
        "sha256":payload["sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
