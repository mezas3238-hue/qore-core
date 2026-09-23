"""R2-G same-parent Model #1 competition family for VT08 CRT PURE.

The CRT methodology remains frozen. This lab changes one engineering dimension only:
how multiple causal Model #1 hypotheses inside one parent C3 compete for a single
execution slot.

The family is declared in code before replay outcomes are observed. All policies use:
- the same parent CRT construction;
- the same close-unmitigated Model #1 source builder;
- the same body-close confirmation;
- next contiguous M15 open fill;
- source-candle structural stop;
- R1 C1 50% midpoint target control;
- R1 C3-close expiry control;
- STOP_FIRST same-M15 ambiguity;
- maximum one selected hypothesis / trade attempt per parent.

No policy may fall through to a later hypothesis after the selected hypothesis fails
risk geometry. This prevents geometry/PnL from becoming an implicit selector.

Research only. No demo/live/production/capital authority.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    END_EXCLUSIVE,
    FOLD_1_END,
    START,
    ReplayBar,
    load_two_year_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    Model1LabTrade,
    ParentCrt,
    _confirmation,
    _resolve_trade,
    _summary,
    aggregate_complete_m15,
    build_parent_crts,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    SourceObservation,
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2G_MODEL1_COMPETITION_FAMILY_001"
SCHEMA = "qore.vt08.crt_pure.r2g_model1_competition_family.v1"


class CompetitionPolicy(StrEnum):
    FIRST_SOURCE_ONLY_CONTROL = "FIRST_SOURCE_ONLY_CONTROL"
    FIRST_CONFIRMATION_WINS = "FIRST_CONFIRMATION_WINS"
    NEWEST_SUPERSEDES_CONFIRMATION_FIRST = "NEWEST_SUPERSEDES_CONFIRMATION_FIRST"
    NEWEST_SUPERSEDES_SOURCE_FIRST = "NEWEST_SUPERSEDES_SOURCE_FIRST"


POLICY_FAMILY: tuple[CompetitionPolicy, ...] = (
    CompetitionPolicy.FIRST_SOURCE_ONLY_CONTROL,
    CompetitionPolicy.FIRST_CONFIRMATION_WINS,
    CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST,
    CompetitionPolicy.NEWEST_SUPERSEDES_SOURCE_FIRST,
)
POLICY_FAMILY_MANIFEST = "|".join(policy.value for policy in POLICY_FAMILY)
POLICY_FAMILY_DIGEST = sha256(POLICY_FAMILY_MANIFEST.encode("utf-8")).hexdigest()


def _pair(
    observation: SourceObservation,
    c3_m15: tuple[M15Bar, ...],
) -> tuple[M15Bar, M15Bar] | None:
    source = observation.group.source_candle
    return _confirmation(
        source,
        c3_m15[observation.source_index + 1 :],
        # All observations are aligned to the parent direction by _aligned_sources.
        # Direction is irrelevant to indexing but required by _confirmation caller.
        # Patched by _candidate_pairs where parent direction is known.
        # This sentinel path is never called directly.
        None,  # type: ignore[arg-type]
    )


def _candidate_pairs(
    *,
    parent: ParentCrt,
    observations: tuple[SourceObservation, ...],
    c3_m15: tuple[M15Bar, ...],
) -> tuple[tuple[SourceObservation, M15Bar, M15Bar], ...]:
    candidates: list[tuple[SourceObservation, M15Bar, M15Bar]] = []
    for observation in observations:
        source = observation.group.source_candle
        pair = _confirmation(
            source,
            c3_m15[observation.source_index + 1 :],
            parent.direction,
        )
        if pair is None:
            continue
        confirmation, entry = pair
        candidates.append((observation, confirmation, entry))
    return tuple(candidates)


def _select_first_source(
    *,
    observations: tuple[SourceObservation, ...],
    candidates: tuple[tuple[SourceObservation, M15Bar, M15Bar], ...],
) -> tuple[SourceObservation, M15Bar, M15Bar] | None:
    if not observations:
        return None
    first = observations[0]
    return next((item for item in candidates if item[0] == first), None)


def _select_first_confirmation(
    candidates: tuple[tuple[SourceObservation, M15Bar, M15Bar], ...],
) -> tuple[SourceObservation, M15Bar, M15Bar] | None:
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda item: (
            item[1].closed_at,
            item[0].group.source_candle.closed_at,
            item[0].group.source_candle.opened_at,
        ),
    )


def _select_newest_supersedes(
    *,
    observations: tuple[SourceObservation, ...],
    candidates: tuple[tuple[SourceObservation, M15Bar, M15Bar], ...],
    confirmation_wins_same_close: bool,
) -> tuple[SourceObservation, M15Bar, M15Bar] | None:
    by_source = {item[0].group.source_candle.opened_at: item for item in candidates}
    ordered = tuple(
        sorted(
            observations,
            key=lambda item: (
                item.group.source_candle.closed_at,
                item.group.source_candle.opened_at,
            ),
        )
    )
    for index, observation in enumerate(ordered):
        candidate = by_source.get(observation.group.source_candle.opened_at)
        if candidate is None:
            continue
        _, confirmation, _ = candidate
        if index + 1 >= len(ordered):
            return candidate
        next_source_known_at = ordered[index + 1].group.source_candle.closed_at
        confirmation_known_at = confirmation.closed_at
        if confirmation_known_at < next_source_known_at:
            return candidate
        if confirmation_wins_same_close and confirmation_known_at == next_source_known_at:
            return candidate
    return None


def select_competing_hypothesis(
    *,
    policy: CompetitionPolicy,
    parent: ParentCrt,
    observations: tuple[SourceObservation, ...],
    c3_m15: tuple[M15Bar, ...],
) -> tuple[SourceObservation, M15Bar, M15Bar] | None:
    candidates = _candidate_pairs(
        parent=parent,
        observations=observations,
        c3_m15=c3_m15,
    )
    if policy is CompetitionPolicy.FIRST_SOURCE_ONLY_CONTROL:
        return _select_first_source(
            observations=observations,
            candidates=candidates,
        )
    if policy is CompetitionPolicy.FIRST_CONFIRMATION_WINS:
        return _select_first_confirmation(candidates)
    if policy is CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST:
        return _select_newest_supersedes(
            observations=observations,
            candidates=candidates,
            confirmation_wins_same_close=True,
        )
    if policy is CompetitionPolicy.NEWEST_SUPERSEDES_SOURCE_FIRST:
        return _select_newest_supersedes(
            observations=observations,
            candidates=candidates,
            confirmation_wins_same_close=False,
        )
    raise ValueError(f"unsupported competition policy: {policy.value}")


def _retag_trade(
    trade: Model1LabTrade,
    *,
    policy: CompetitionPolicy,
) -> Model1LabTrade:
    return Model1LabTrade(
        schema=SCHEMA,
        identity=f"{IDENTITY}:{policy.value}",
        market=trade.market,
        reference_policy=trade.reference_policy,
        reference_count=trade.reference_count,
        reference_ids=trade.reference_ids,
        parent_direction=trade.parent_direction,
        timing_triplet=trade.timing_triplet,
        c3_opened_at=trade.c3_opened_at,
        source_opened_at=trade.source_opened_at,
        confirmation_opened_at=trade.confirmation_opened_at,
        entry_opened_at=trade.entry_opened_at,
        entry_price_relative=trade.entry_price_relative,
        stop_price_relative=trade.stop_price_relative,
        target_price_relative=trade.target_price_relative,
        exit_price_relative=trade.exit_price_relative,
        exit_reason=trade.exit_reason,
        r_multiple=trade.r_multiple,
        research_only=True,
        promotion_forbidden_from_lab_pnl=True,
    )


def _fold(
    trades: tuple[Model1LabTrade, ...],
    start: datetime,
    end: datetime,
) -> tuple[Model1LabTrade, ...]:
    return tuple(
        trade
        for trade in trades
        if start <= datetime.fromisoformat(trade.entry_opened_at) < end
    )


def run_competition_family(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[CompetitionPolicy, tuple[Model1LabTrade, ...]], dict[str, Any]]:
    parents = build_parent_crts(market, bars)
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    trades: dict[CompetitionPolicy, list[Model1LabTrade]] = {
        policy: [] for policy in POLICY_FAMILY
    }
    counters: dict[CompetitionPolicy, Counter[str]] = {
        policy: Counter() for policy in POLICY_FAMILY
    }

    for parent in parents:
        c3_m15 = _c3_m15(parent, m15_by_time)
        observations = _aligned_sources(
            parent=parent,
            c3_m15=c3_m15,
            breaches=breaches,
        )
        for policy in POLICY_FAMILY:
            counter = counters[policy]
            counter["parent_count"] += 1
            counter["source_event_count"] += len(observations)
            selected = select_competing_hypothesis(
                policy=policy,
                parent=parent,
                observations=observations,
                c3_m15=c3_m15,
            )
            if selected is None:
                counter["no_selected_confirmed_hypothesis"] += 1
                continue

            observation, confirmation, entry = selected
            counter["selected_hypothesis"] += 1
            counter[f"selected_generation_{observation.source_index + 1}"] += 1
            if observation.source_index > 0:
                counter["selected_later_source"] += 1

            trade = _resolve_trade(
                parent=parent,
                group=observation.group,
                confirmation=confirmation,
                entry_bar=entry,
                c3_m15=c3_m15,
            )
            if trade is None:
                counter["selected_invalid_risk_geometry"] += 1
                continue
            counter["trade_created"] += 1
            trades[policy].append(_retag_trade(trade, policy=policy))

    frozen = {
        policy: tuple(sorted(rows, key=lambda item: item.entry_opened_at))
        for policy, rows in trades.items()
    }
    policy_reports: dict[str, Any] = {}
    for policy in POLICY_FAMILY:
        rows = frozen[policy]
        policy_reports[policy.value] = {
            "diagnostics": dict(counters[policy]),
            "full_2y": _summary(rows),
            "year_1": _summary(_fold(rows, START, FOLD_1_END)),
            "year_2": _summary(_fold(rows, FOLD_1_END, END_EXCLUSIVE)),
        }

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "single_changed_dimension": "SAME_PARENT_MODEL1_HYPOTHESIS_COMPETITION",
        "policy_family": [policy.value for policy in POLICY_FAMILY],
        "policy_family_manifest": POLICY_FAMILY_MANIFEST,
        "policy_family_digest": POLICY_FAMILY_DIGEST,
        "family_declared_before_replay_outcomes": True,
        "one_trade_attempt_max_per_parent": True,
        "selected_invalid_geometry_fallback_allowed": False,
        "source_availability": "M15_CLOSE",
        "confirmation_availability": "M15_CLOSE",
        "policies": policy_reports,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "automatic_winner_selection": False,
    }
    return frozen, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=[item.value for item in CrtPureMarket])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    family, report = run_competition_family(market, load_two_year_m5(market))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for policy in POLICY_FAMILY:
            for trade in family[policy]:
                row = asdict(trade)
                row["competition_policy"] = policy.value
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2G_COMPETITION_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
