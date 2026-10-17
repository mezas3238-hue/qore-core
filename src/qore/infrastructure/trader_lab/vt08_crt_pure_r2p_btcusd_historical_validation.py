"""R2-P historical validation of BTCUSD R2-M survivors.

The candidate family is frozen before the 2020-2022 validation outcomes are
observed. Definitions are reused unchanged from R2-J/R2-M.

Validation gate is the same binary gate used by R2-J:
- at least 24 trades;
- PF >= 1.05;
- total R > 0;
- max DD <= 12R;
- both 1Y halves > 0R.

No candidate ranking or combination is allowed.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
    _resolve_trade,
    _summary,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    select_competing_hypothesis,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2j_market_context_validation import (
    BASE_POLICY,
    CandidateContext,
    CandidateId,
    _accept,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    build_parent_crts_for_window,
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2P_BTCUSD_HISTORICAL_VALIDATION_001"
SCHEMA = "qore.vt08.crt_pure.r2p_btcusd_historical_validation.v1"
MARKET = CrtPureMarket.BTCUSD

VALIDATION_START = datetime(2020, 9, 21, 0, 0, tzinfo=UTC)
VALIDATION_FOLD = datetime(2021, 9, 21, 0, 0, tzinfo=UTC)
VALIDATION_END = datetime(2022, 9, 21, 0, 0, tzinfo=UTC)

MIN_TRADES = 24
MIN_PF = 1.05
MAX_DD_R = 12.0


class ValidationCandidate(StrEnum):
    CONTROL = "CONTROL"
    BTC_BEARISH = "BTC_BEARISH"
    BTC_BODY_GE_050 = "BTC_BODY_GE_050"
    BTC_REF2_PLUS = "BTC_REF2_PLUS"


CANDIDATE_FAMILY: tuple[ValidationCandidate, ...] = (
    ValidationCandidate.CONTROL,
    ValidationCandidate.BTC_BEARISH,
    ValidationCandidate.BTC_BODY_GE_050,
    ValidationCandidate.BTC_REF2_PLUS,
)

R2J_BINDING: dict[ValidationCandidate, CandidateId] = {
    ValidationCandidate.CONTROL: CandidateId.CONTROL,
    ValidationCandidate.BTC_BEARISH: CandidateId.BTC_BEARISH,
    ValidationCandidate.BTC_BODY_GE_050: CandidateId.BTC_BODY_GE_050,
    ValidationCandidate.BTC_REF2_PLUS: CandidateId.BTC_REF2_PLUS,
}
FAMILY_MANIFEST = "|".join(candidate.value for candidate in CANDIDATE_FAMILY)
FAMILY_DIGEST = sha256(FAMILY_MANIFEST.encode("utf-8")).hexdigest()


def _retag(
    trade: Model1LabTrade,
    candidate: ValidationCandidate,
) -> Model1LabTrade:
    return Model1LabTrade(
        schema=SCHEMA,
        identity=f"{IDENTITY}:{candidate.value}",
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


def _window(
    rows: tuple[Model1LabTrade, ...],
    start: datetime,
    end: datetime,
) -> tuple[Model1LabTrade, ...]:
    return tuple(
        row
        for row in rows
        if start <= datetime.fromisoformat(row.entry_opened_at) < end
    )


def _gate(
    full: dict[str, Any],
    year_1: dict[str, Any],
    year_2: dict[str, Any],
) -> tuple[bool, tuple[str, ...]]:
    failures: list[str] = []
    if int(full["trades"]) < MIN_TRADES:
        failures.append("MIN_TRADES")
    pf = full["profit_factor"]
    if pf is None or float(pf) < MIN_PF:
        failures.append("MIN_PF")
    if float(full["total_r"]) <= 0:
        failures.append("TOTAL_R")
    if float(full["max_drawdown_r"]) > MAX_DD_R:
        failures.append("MAX_DD")
    if float(year_1["total_r"]) <= 0:
        failures.append("YEAR1_R")
    if float(year_2["total_r"]) <= 0:
        failures.append("YEAR2_R")
    return not failures, tuple(failures)


def run_validation() -> tuple[
    dict[ValidationCandidate, tuple[Model1LabTrade, ...]],
    dict[str, Any],
]:
    bars = load_m5_window(
        MARKET,
        start=VALIDATION_START,
        end_exclusive=VALIDATION_END,
    )
    parents = build_parent_crts_for_window(
        MARKET,
        bars,
        start=VALIDATION_START,
        end_exclusive=VALIDATION_END,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    rows: dict[ValidationCandidate, list[Model1LabTrade]] = {
        candidate: [] for candidate in CANDIDATE_FAMILY
    }
    selected_count = 0
    invalid_geometry = 0

    for parent in parents:
        c3_m15 = _c3_m15(parent, m15_by_time)
        observations = _aligned_sources(
            parent=parent,
            c3_m15=c3_m15,
            breaches=breaches,
        )
        selected = select_competing_hypothesis(
            policy=BASE_POLICY,
            parent=parent,
            observations=observations,
            c3_m15=c3_m15,
        )
        if selected is None:
            continue
        selected_count += 1

        observation, confirmation, entry = selected
        context = CandidateContext(
            parent=parent,
            observation=observation,
            confirmation=confirmation,
            entry=entry,
            generation=observations.index(observation) + 1,
        )
        trade = _resolve_trade(
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry,
            c3_m15=c3_m15,
        )
        if trade is None:
            invalid_geometry += 1
            continue

        for candidate in CANDIDATE_FAMILY:
            if _accept(R2J_BINDING[candidate], context):
                rows[candidate].append(_retag(trade, candidate))

    frozen = {
        candidate: tuple(sorted(trades, key=lambda item: item.entry_opened_at))
        for candidate, trades in rows.items()
    }

    arms: dict[str, Any] = {}
    survivors: list[str] = []
    for candidate in CANDIDATE_FAMILY:
        trades = frozen[candidate]
        full = _summary(trades)
        year_1 = _summary(_window(trades, VALIDATION_START, VALIDATION_FOLD))
        year_2 = _summary(_window(trades, VALIDATION_FOLD, VALIDATION_END))
        survived, failures = _gate(full, year_1, year_2)
        if survived:
            survivors.append(candidate.value)
        arms[candidate.value] = {
            "full_2y": full,
            "year_1": year_1,
            "year_2": year_2,
            "survived_research_gate": survived,
            "gate_failures": list(failures),
        }

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "validation_start": VALIDATION_START.isoformat(),
        "validation_fold": VALIDATION_FOLD.isoformat(),
        "validation_end_exclusive": VALIDATION_END.isoformat(),
        "base_competition_policy": BASE_POLICY.value,
        "candidate_family": [candidate.value for candidate in CANDIDATE_FAMILY],
        "candidate_definitions_reused_unchanged": True,
        "family_manifest": FAMILY_MANIFEST,
        "family_digest": FAMILY_DIGEST,
        "family_frozen_before_validation_results": True,
        "research_gate_reused_from_r2j": True,
        "research_gate": {
            "min_trades": MIN_TRADES,
            "min_profit_factor": MIN_PF,
            "max_drawdown_r": MAX_DD_R,
            "total_r_must_be_positive": True,
            "each_half_total_r_must_be_positive": True,
        },
        "parent_crt_count": len(parents),
        "selected_confirmed_hypothesis_count": selected_count,
        "selected_invalid_geometry_count": invalid_geometry,
        "arms": arms,
        "survivors": survivors,
        "automatic_winner_ranking": False,
        "candidate_properties_combined": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return frozen, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    family, report = run_validation()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for candidate in CANDIDATE_FAMILY:
            for trade in family[candidate]:
                row = asdict(trade)
                row["candidate_id"] = candidate.value
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2P_BTC_VALIDATION_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
