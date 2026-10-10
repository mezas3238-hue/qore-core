"""Decision-time feature atlas for V50 prequential cognition.

For every V49 development candidate, capture only features knowable at its entry timestamp and
join the terminal outcome strictly as a separate label for offline/prequential simulation.

Decision features:
- V50 cognitive state-family tokens,
- H1 age / M15->M1 delay / session runway,
- stop-to-M1-noise geometry,
- target ladder availability,
- execution-stop availability,
- current trigger and H1 basis.

Outcome fields are carried only as labels and are explicitly marked invisible to the current
decision. This atlas grants no rule promotion or deployment authority.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import iter_cibo_m1
from qore.infrastructure.trader_lab.capitalizer_experience_memory import (
    CapitalizerExperienceMemory,
)
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    _aggregate,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_metacognition_v2 import (
    CapitalizerEpistemicReadiness,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_opportunity import (
    build_v50_cognitive_snapshot,
)

IDENTITY = "QORE_CAPITALIZER_V50_COGNITIVE_FEATURE_ATLAS"


@dataclass(frozen=True, slots=True)
class V50CognitiveFeatureRow:
    identity: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    exit_at: str
    state_family_id: str
    observation_tokens: tuple[str, ...]
    structural_disposition: str
    h1_freshness: str
    execution_freshness: str
    session_runway: str
    stop_noise_state: str
    stop_to_noise_ratio: str
    destination_state: str
    current_destination_room_r: str | None
    target_candidate_count: int
    target_has_one_r: bool
    target_has_two_r: bool
    execution_stop_available: bool
    execution_vs_thesis_ratio: str | None
    trigger_family: str
    h1_basis: str
    candidate_ordinal_in_session_day: int
    realized_gross_r: str
    exit_reason: str
    current_outcome_visible_to_decision: bool = False
    future_bars_visible_to_decision: bool = False
    rule_promotion_allowed: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("unexpected V50 feature atlas identity")
        if self.current_outcome_visible_to_decision or self.future_bars_visible_to_decision:
            raise ValueError("V50 feature atlas leaked future information")
        if self.rule_promotion_allowed:
            raise ValueError("V50 feature atlas cannot promote rules")


def _load_opportunities(root: Path) -> tuple[V49Opportunity, ...]:
    paths = sorted(root.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    if len(paths) != 1:
        raise ValueError("V50 feature atlas requires one market opportunity ledger")
    rows: list[V49Opportunity] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(V49Opportunity(**json.loads(line)))
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                datetime.fromisoformat(item.m1_trigger_confirmed_at),
                item.symbol,
            ),
        )
    )


def _load_outcomes(root: Path) -> dict[tuple[str, str], V49EconomicTrade]:
    paths = sorted(root.rglob("capitalizer-*-v49-development-economics-trades.jsonl"))
    if len(paths) != 1:
        raise ValueError("V50 feature atlas requires one market economic ledger")
    result: dict[tuple[str, str], V49EconomicTrade] = {}
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            trade = V49EconomicTrade(**json.loads(line))
            key = (trade.symbol, trade.entry_at)
            if key in result:
                raise ValueError("duplicate V49 economic outcome key")
            result[key] = trade
    return result


def build_feature_atlas(
    *,
    capacity_root: Path,
    economic_root: Path,
    m1_root: Path,
) -> tuple[dict[str, object], tuple[V50CognitiveFeatureRow, ...]]:
    opportunities = _load_opportunities(capacity_root)
    outcomes = _load_outcomes(economic_root)
    if not opportunities:
        raise ValueError("V50 feature atlas requires opportunities")
    symbol = opportunities[0].symbol
    if any(item.symbol != symbol for item in opportunities):
        raise ValueError("V50 feature atlas is market-local")

    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if DEV_WINDOW_START <= bar.opened_at < DEV_WINDOW_END
    )
    if not bars or any(bar.symbol != symbol for bar in bars):
        raise ValueError("V50 feature atlas M1 market mismatch")
    h1 = _aggregate(bars, minutes=60)

    ordinal: Counter[tuple[str, str]] = Counter()
    rows: list[V50CognitiveFeatureRow] = []
    for opportunity in opportunities:
        key = (opportunity.symbol, opportunity.m1_trigger_confirmed_at)
        outcome = outcomes.get(key)
        if outcome is None:
            raise ValueError("V50 feature atlas missing economic outcome label")

        session_day = (opportunity.session, opportunity.operating_date)
        ordinal[session_day] += 1
        slot = ordinal[session_day]

        snapshot = build_v50_cognitive_snapshot(
            opportunity,
            m1_bars=bars,
            h1_bars=h1,
            experience_memory=CapitalizerExperienceMemory(),
            metacognitive_readiness=CapitalizerEpistemicReadiness.WELL_SUPPORTED,
            session_slot_ordinal=slot,
        )
        state = snapshot.cognitive.state
        ladder = snapshot.target_ladder
        dual = snapshot.dual_invalidation
        rows.append(
            V50CognitiveFeatureRow(
                identity=IDENTITY,
                symbol=opportunity.symbol,
                session=opportunity.session,
                operating_date=opportunity.operating_date,
                entry_at=opportunity.m1_trigger_confirmed_at,
                exit_at=outcome.exit_at,
                state_family_id=state.state_family_id,
                observation_tokens=state.observation_tokens,
                structural_disposition=snapshot.cognitive.disposition.value,
                h1_freshness=state.h1_freshness.value,
                execution_freshness=state.execution_freshness.value,
                session_runway=state.session_runway.value,
                stop_noise_state=state.stop_noise_state.value,
                stop_to_noise_ratio=str(state.stop_to_noise_ratio),
                destination_state=state.destination_state.value,
                current_destination_room_r=(
                    None
                    if state.destination_room_r is None
                    else str(state.destination_room_r)
                ),
                target_candidate_count=len(ladder.candidates),
                target_has_one_r=ladder.has_one_r_destination,
                target_has_two_r=ladder.has_two_r_destination,
                execution_stop_available=dual.execution_anchor_available,
                execution_vs_thesis_ratio=(
                    None
                    if dual.execution_vs_thesis_ratio is None
                    else str(dual.execution_vs_thesis_ratio)
                ),
                trigger_family=opportunity.m1_trigger_family,
                h1_basis=opportunity.h1_state_basis,
                candidate_ordinal_in_session_day=slot,
                realized_gross_r=outcome.realized_gross_r,
                exit_reason=outcome.exit_reason,
            )
        )

    result = tuple(rows)
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": opportunities[0].session,
        "window_start": DEV_WINDOW_START.isoformat(),
        "window_end_exclusive": DEV_WINDOW_END.isoformat(),
        "rows": len(result),
        "outcome_visible_to_decision": False,
        "future_bars_visible_to_decision": False,
        "features_known_by_entry": True,
        "rule_promotion_allowed": False,
        "reserved_holdout_reopened": False,
        "fresh_holdout_used": False,
    }, result


def write_feature_atlas(
    report: dict[str, object],
    rows: tuple[V50CognitiveFeatureRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v50-cognitive-feature-atlas"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("capacity_root", type=Path)
    parser.add_argument("economic_root", type=Path)
    parser.add_argument("m1_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, rows = build_feature_atlas(
        capacity_root=args.capacity_root,
        economic_root=args.economic_root,
        m1_root=args.m1_root,
    )
    write_feature_atlas(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
