"""R2-J market-specific context candidates on historical validation evidence.

Candidate arms were frozen from R2-I development forensics before this module's
historical-validation workflow was executed.

Methodology remains fixed. Each candidate is a simple single-factor engineering
gate applied to the same R2-G NEWEST competition model.

Historical validation window:
    2022-09-21T00:00Z -> 2024-09-21T00:00Z

This window is not used to define the candidate family. Candidate survival is
binary under a predeclared research gate; there is no automatic winner ranking.

Research only. No demo/live/production/capital authority.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    Model1LabTrade,
    ParentCrt,
    _resolve_trade,
    _summary,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    SourceObservation,
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    CompetitionPolicy,
    select_competing_hypothesis,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2i_context_forensics import (
    _delay_bars,
    _source_body_fraction,
    _source_range_to_c1,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    build_parent_crts_for_window,
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

IDENTITY = "VT08_CRT_PURE_R2J_MARKET_CONTEXT_VALIDATION_001"
SCHEMA = "qore.vt08.crt_pure.r2j_market_context_validation.v1"

VALIDATION_START = datetime(2022, 9, 21, 0, 0, tzinfo=UTC)
VALIDATION_END = datetime(2024, 9, 21, 0, 0, tzinfo=UTC)
VALIDATION_FOLD = datetime(2023, 9, 21, 0, 0, tzinfo=UTC)

BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST

MIN_VALIDATION_TRADES = 24
MIN_VALIDATION_PF = 1.05
MAX_VALIDATION_DD_R = 12.0


class CandidateId(StrEnum):
    CONTROL = "CONTROL"

    AUD_G1 = "AUD_G1"
    AUD_REF2_PLUS = "AUD_REF2_PLUS"
    AUD_SOURCE_RANGE_GE_030_C1 = "AUD_SOURCE_RANGE_GE_030_C1"
    AUD_T1_BULLISH = "AUD_T1_BULLISH"

    USD_T1 = "USD_T1"
    USD_D2 = "USD_D2"
    USD_BODY_050_TO_075 = "USD_BODY_050_TO_075"

    BTC_REF2_PLUS = "BTC_REF2_PLUS"
    BTC_BODY_GE_050 = "BTC_BODY_GE_050"
    BTC_BEARISH = "BTC_BEARISH"
    BTC_D2 = "BTC_D2"
    BTC_T1_BEARISH = "BTC_T1_BEARISH"


CANDIDATE_FAMILY: dict[CrtPureMarket, tuple[CandidateId, ...]] = {
    CrtPureMarket.AUDUSD: (
        CandidateId.CONTROL,
        CandidateId.AUD_G1,
        CandidateId.AUD_REF2_PLUS,
        CandidateId.AUD_SOURCE_RANGE_GE_030_C1,
        CandidateId.AUD_T1_BULLISH,
    ),
    CrtPureMarket.USDJPY: (
        CandidateId.CONTROL,
        CandidateId.USD_T1,
        CandidateId.USD_D2,
        CandidateId.USD_BODY_050_TO_075,
    ),
    CrtPureMarket.BTCUSD: (
        CandidateId.CONTROL,
        CandidateId.BTC_REF2_PLUS,
        CandidateId.BTC_BODY_GE_050,
        CandidateId.BTC_BEARISH,
        CandidateId.BTC_D2,
        CandidateId.BTC_T1_BEARISH,
    ),
}
FAMILY_MANIFEST = "|".join(
    f"{market.value}:{','.join(item.value for item in candidates)}"
    for market, candidates in CANDIDATE_FAMILY.items()
)
FAMILY_DIGEST = sha256(FAMILY_MANIFEST.encode("utf-8")).hexdigest()


class CandidateContext:
    __slots__ = (
        "parent",
        "observation",
        "confirmation",
        "entry",
        "generation",
        "delay_bars",
        "body_fraction",
        "source_range_to_c1",
    )

    def __init__(
        self,
        *,
        parent: ParentCrt,
        observation: SourceObservation,
        confirmation: M15Bar,
        entry: M15Bar,
        generation: int,
    ) -> None:
        self.parent = parent
        self.observation = observation
        self.confirmation = confirmation
        self.entry = entry
        self.generation = generation
        self.delay_bars = _delay_bars(
            observation.group.source_candle,
            confirmation,
        )
        self.body_fraction = _source_body_fraction(observation.group.source_candle)
        self.source_range_to_c1 = _source_range_to_c1(
            parent,
            observation.group.source_candle,
        )


def _accept(candidate: CandidateId, context: CandidateContext) -> bool:
    if candidate is CandidateId.CONTROL:
        return True
    if candidate is CandidateId.AUD_G1:
        return context.generation == 1
    if candidate is CandidateId.AUD_REF2_PLUS:
        return len(context.observation.group.references) >= 2
    if candidate is CandidateId.AUD_SOURCE_RANGE_GE_030_C1:
        return context.source_range_to_c1 >= Decimal("0.30")
    if candidate is CandidateId.AUD_T1_BULLISH:
        return (
            context.parent.triplet == "1"
            and context.parent.direction is CrtPureCandidateDirection.BULLISH
        )

    if candidate is CandidateId.USD_T1:
        return context.parent.triplet == "1"
    if candidate is CandidateId.USD_D2:
        return context.delay_bars == 2
    if candidate is CandidateId.USD_BODY_050_TO_075:
        return Decimal("0.50") <= context.body_fraction < Decimal("0.75")

    if candidate is CandidateId.BTC_REF2_PLUS:
        return len(context.observation.group.references) >= 2
    if candidate is CandidateId.BTC_BODY_GE_050:
        return context.body_fraction >= Decimal("0.50")
    if candidate is CandidateId.BTC_BEARISH:
        return context.parent.direction is CrtPureCandidateDirection.BEARISH
    if candidate is CandidateId.BTC_D2:
        return context.delay_bars == 2
    if candidate is CandidateId.BTC_T1_BEARISH:
        return (
            context.parent.triplet == "1"
            and context.parent.direction is CrtPureCandidateDirection.BEARISH
        )
    raise ValueError(f"candidate not supported: {candidate.value}")


def _retag(trade: Model1LabTrade, candidate: CandidateId) -> Model1LabTrade:
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


def _fold(
    rows: tuple[Model1LabTrade, ...],
    start: datetime,
    end: datetime,
) -> tuple[Model1LabTrade, ...]:
    return tuple(
        row
        for row in rows
        if start <= datetime.fromisoformat(row.entry_opened_at) < end
    )


def _survives(
    *,
    full: dict[str, Any],
    year_1: dict[str, Any],
    year_2: dict[str, Any],
) -> tuple[bool, tuple[str, ...]]:
    failures: list[str] = []
    if int(full["trades"]) < MIN_VALIDATION_TRADES:
        failures.append("MIN_TRADES")
    pf = full["profit_factor"]
    if pf is None or float(pf) < MIN_VALIDATION_PF:
        failures.append("MIN_PF")
    if float(full["total_r"]) <= 0:
        failures.append("TOTAL_R")
    if float(full["max_drawdown_r"]) > MAX_VALIDATION_DD_R:
        failures.append("MAX_DD")
    if float(year_1["total_r"]) <= 0:
        failures.append("YEAR1_R")
    if float(year_2["total_r"]) <= 0:
        failures.append("YEAR2_R")
    return not failures, tuple(failures)


def run_candidate_family(
    market: CrtPureMarket,
) -> tuple[dict[CandidateId, tuple[Model1LabTrade, ...]], dict[str, Any]]:
    bars = load_m5_window(
        market,
        start=VALIDATION_START,
        end_exclusive=VALIDATION_END,
    )
    parents = build_parent_crts_for_window(
        market,
        bars,
        start=VALIDATION_START,
        end_exclusive=VALIDATION_END,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    candidates = CANDIDATE_FAMILY[market]
    trades: dict[CandidateId, list[Model1LabTrade]] = {
        candidate: [] for candidate in candidates
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

        for candidate in candidates:
            if _accept(candidate, context):
                trades[candidate].append(_retag(trade, candidate))

    frozen = {
        candidate: tuple(sorted(rows, key=lambda row: row.entry_opened_at))
        for candidate, rows in trades.items()
    }
    arms: dict[str, Any] = {}
    survivors: list[str] = []
    for candidate in candidates:
        rows = frozen[candidate]
        full = _summary(rows)
        y1 = _summary(_fold(rows, VALIDATION_START, VALIDATION_FOLD))
        y2 = _summary(_fold(rows, VALIDATION_FOLD, VALIDATION_END))
        survived, failures = _survives(full=full, year_1=y1, year_2=y2)
        if survived:
            survivors.append(candidate.value)
        arms[candidate.value] = {
            "full_2y": full,
            "year_1": y1,
            "year_2": y2,
            "survived_research_gate": survived,
            "gate_failures": list(failures),
        }

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "validation_start": VALIDATION_START.isoformat(),
        "validation_end_exclusive": VALIDATION_END.isoformat(),
        "validation_fold": VALIDATION_FOLD.isoformat(),
        "base_competition_policy": BASE_POLICY.value,
        "family_manifest": FAMILY_MANIFEST,
        "family_digest": FAMILY_DIGEST,
        "family_frozen_before_validation_results": True,
        "research_gate": {
            "min_trades": MIN_VALIDATION_TRADES,
            "min_profit_factor": MIN_VALIDATION_PF,
            "max_drawdown_r": MAX_VALIDATION_DD_R,
            "total_r_must_be_positive": True,
            "each_half_total_r_must_be_positive": True,
        },
        "parent_crt_count": len(parents),
        "selected_confirmed_hypothesis_count": selected_count,
        "selected_invalid_geometry_count": invalid_geometry,
        "arms": arms,
        "survivors": survivors,
        "automatic_winner_ranking": False,
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
    parser.add_argument("market", choices=[item.value for item in CrtPureMarket])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    family, report = run_candidate_family(market)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for candidate in CANDIDATE_FAMILY[market]:
            for trade in family[candidate]:
                row = asdict(trade)
                row["candidate_id"] = candidate.value
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2J_VALIDATION_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
