"""Build honest nine-market cognition PERCEPTION/REGIME/CROSS inputs from native M1.

Attests timestamps, market coverage, provider provenance and exact M1 closure.
Never upgrades OHLC to BID/ASK, quote freshness, completed microstructure,
session-clock proof, named regimes, causal cross-market direction, positions,
executions or an authorized full Master Frame. Missing bars remain explicit.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from itertools import combinations
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_a1_native_nine_market_bar_witness_v1 import (
    A1NativeMarketObservation,
)
from qore.infrastructure.trader_lab.capitalizer_confidence import (
    CapitalizerKnowledgeState,
)
from qore.infrastructure.trader_lab.capitalizer_cross_market_causality import (
    CapitalizerCrossMarketCausalGraph,
    CapitalizerCrossMarketEdge,
    CapitalizerCrossMarketRelation,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    NINE_MARKET_UNIVERSE,
)
from qore.infrastructure.trader_lab.capitalizer_perception_integrity import (
    CapitalizerMarketPerceptionSnapshot,
    CapitalizerPerceptionFacts,
    CapitalizerPerceptionStatus,
    assess_perception_integrity,
)
from qore.infrastructure.trader_lab.capitalizer_regime_intelligence import (
    CapitalizerRegimeHypothesis,
    CapitalizerRegimeResolution,
    assess_regime,
)

IDENTITY = "QORE_SCALPER_A1_NATIVE_M1_NINE_MARKET_EPISTEMIC_INPUT_V1"


def _dt(s: str) -> datetime:
    value = datetime.fromisoformat(s)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("native witness timestamps require a timezone")
    return value


@dataclass(frozen=True, slots=True)
class A1NineMarketNativeCognitiveInputs:
    """Raw market evidence encoded for the ACTUAL Master Frame contracts."""

    observed_at: datetime
    observations: tuple[A1NativeMarketObservation, ...]
    perceptions: tuple[CapitalizerMarketPerceptionSnapshot, ...]
    regimes: tuple[CapitalizerRegimeHypothesis, ...]
    cross_market_graph: CapitalizerCrossMarketCausalGraph
    complete_exact_native_m1: bool
    broker_quotes_proven: bool = False
    session_clock_proven: bool = False
    nine_market_world_model_proven: bool = False
    portfolio_ledger_proven: bool = False
    full_cognitive_frame_executed: bool = False
    live_authorized: bool = False

    def __post_init__(self) -> None:
        expected = set(NINE_MARKET_UNIVERSE)
        if (
            len(self.observations) != 9
            or {x.symbol for x in self.observations} != expected
            or len(self.perceptions) != 9
            or {x.symbol for x in self.perceptions} != expected
            or len(self.regimes) != 9
            or {x.symbol for x in self.regimes} != expected
            or len({x.symbol for x in self.observations}) != 9
            or len({x.symbol for x in self.perceptions}) != 9
            or len({x.symbol for x in self.regimes}) != 9
        ):
            raise ValueError("must preserve one provider-native snapshot per nine markets")
        if any(
            _dt(x.decision_at) != self.observed_at
            for x in self.observations
        ) or any(
            p.observed_at != self.observed_at for p in self.perceptions
        ) or any(r.observed_at != self.observed_at for r in self.regimes):
            raise ValueError("all nine market cognition inputs must be same as-of instant")
        if self.cross_market_graph.observed_at != self.observed_at:
            raise ValueError("market relation graph contains different snapshot time")
        if self.complete_exact_native_m1 != all(
            x.has_exact_predecision_m1 for x in self.observations
        ):
            raise ValueError("nine-market exact native closure was invented")
        if any((
            self.broker_quotes_proven,
            self.session_clock_proven,
            self.nine_market_world_model_proven,
            self.portfolio_ledger_proven,
            self.full_cognitive_frame_executed,
            self.live_authorized,
        )):
            raise ValueError("OHLC witness cannot attest missing full cognition inputs")
        if any(
            p.assessment.status is CapitalizerPerceptionStatus.GOOD
            for p in self.perceptions
        ):
            raise ValueError("native OHLC cannot certify GOOD without BID/ASK quotes")
        if any(
            assess_regime(r).resolution is not CapitalizerRegimeResolution.UNRESOLVED
            for r in self.regimes
        ):
            raise ValueError("regime classification must not be fabricated from M1 close")
        if any(
            edge.relation is not CapitalizerCrossMarketRelation.UNKNOWN
            for edge in self.cross_market_graph.edges
        ):
            raise ValueError("simultaneous close is not cross-market causality")


def build_epistemic_inputs(
    *, observations: tuple[A1NativeMarketObservation, ...],
) -> A1NineMarketNativeCognitiveInputs:
    """Use real market M1 witnesses; mark all unproven feed dimensions unavailable."""
    if len(observations) != 9:
        raise ValueError("one native market observation required per frozen market")
    by_symbol = {x.symbol: x for x in observations}
    if set(by_symbol) != set(NINE_MARKET_UNIVERSE):
        raise ValueError("nine native markets must be exact and unduplicated")
    at = _dt(observations[0].decision_at)
    if any(_dt(x.decision_at) != at for x in observations):
        raise ValueError("simultaneous nine-market snapshot may not mix timestamps")
    ordered = tuple(by_symbol[s] for s in sorted(NINE_MARKET_UNIVERSE))
    perceptions: list[CapitalizerMarketPerceptionSnapshot] = []
    regimes: list[CapitalizerRegimeHypothesis] = []
    for x in ordered:
        if not x.provider_native_m1 or x.synthetic_data_used:
            raise ValueError("non-provider-native market observation must be rejected")
        valid_asof = (
            x.last_native_m1_closed_at is None
            or _dt(x.last_native_m1_closed_at) <= at
        )
        if not valid_asof:
            raise ValueError("future market M1 candle cannot enter cognition")
        # IMPORTANT: session_clock_valid is False. A timezone-aware instant
        # does NOT prove the source author's NY session clock, and an OHLC
        # candle does not prove quote freshness or complete microstructure.
        assessment = assess_perception_integrity(CapitalizerPerceptionFacts(
            quote_fresh=False,
            bars_complete=x.has_exact_predecision_m1,
            timestamps_ordered=valid_asof,
            session_clock_valid=False,
            provenance_valid=x.provider_native_m1,
            microstructure_complete=False,
        ))
        perceptions.append(CapitalizerMarketPerceptionSnapshot(
            symbol=x.symbol, observed_at=at, assessment=assessment,
        ))
        regimes.append(CapitalizerRegimeHypothesis(
            symbol=x.symbol, observed_at=at, family_id=None,
            causal_evidence=(
                "PROVIDER_NATIVE_LAST_M1_ASOF=" +
                (x.last_native_m1_closed_at or "NOT_AVAILABLE"),
            ),
            contradictions=(),
            knowledge=CapitalizerKnowledgeState.UNKNOWN,
        ))
    pairs = tuple(
        CapitalizerCrossMarketEdge(
            left_symbol=left,
            right_symbol=right,
            relation=CapitalizerCrossMarketRelation.UNKNOWN,
            observed_at=at, causal_tokens=(),
        )
        for left, right in combinations(sorted(NINE_MARKET_UNIVERSE), 2)
    )
    return A1NineMarketNativeCognitiveInputs(
        observed_at=at, observations=ordered,
        perceptions=tuple(perceptions), regimes=tuple(regimes),
        cross_market_graph=CapitalizerCrossMarketCausalGraph(
            observed_at=at, edges=pairs,
        ),
        complete_exact_native_m1=all(
            x.has_exact_predecision_m1 for x in ordered
        ),
    )


def audit_pinned_nine_market_inputs(root: Path, target: Path) -> dict[str, object]:
    """Build causal Master-compatible evidence for ALL original 2822 barriers."""
    paths = sorted(root.rglob("scalper-a1-native-market-witness.jsonl"))
    if len(paths) != 9:
        raise ValueError("requires nine pinned provider-native M1 witness books")
    per_symbol: dict[str, tuple[A1NativeMarketObservation, ...]] = {}
    for path in paths:
        rows = tuple(
            A1NativeMarketObservation(**json.loads(line))
            for line in path.read_text().splitlines() if line.strip()
        )
        if not rows or len({r.symbol for r in rows}) != 1:
            raise ValueError("empty or mixed provider market book")
        symbol = rows[0].symbol
        if symbol in per_symbol:
            raise ValueError("duplicated provider market")
        per_symbol[symbol] = rows
    if set(per_symbol) != set(NINE_MARKET_UNIVERSE):
        raise ValueError("all nine original Market Brain symbols required")
    n = len(next(iter(per_symbol.values())))
    if n != 2822 or any(len(rows) != n for rows in per_symbol.values()):
        raise ValueError("same frozen 2822 original M1 barrier instants required")
    ordered_symbols = tuple(sorted(per_symbol))
    counts: Counter[str] = Counter()
    previous: datetime | None = None
    target.mkdir(parents=True, exist_ok=True)
    with (target / "scalper-a1-native-nine-market-epistemic-barriers.jsonl").open("w") as f:
        for i in range(n):
            evidence = build_epistemic_inputs(
                observations=tuple(per_symbol[s][i] for s in ordered_symbols)
            )
            if previous is not None and evidence.observed_at <= previous:
                raise ValueError("provider cognition barriers unsorted/duplicated")
            previous = evidence.observed_at
            complete = evidence.complete_exact_native_m1
            counts["ALL_NINE_EXACT_CLOSED_NATIVE_M1:" + str(complete)] += 1
            for p in evidence.perceptions:
                counts["PERCEPTION:" + p.assessment.status.value] += 1
            for r in evidence.regimes:
                counts["REGIME:" + assess_regime(r).resolution.value] += 1
            if len(evidence.cross_market_graph.edges) != 36:
                raise ValueError("nine markets need 36 explicitly unknown relations")
            f.write(json.dumps({
                "identity": IDENTITY,
                "observed_at": evidence.observed_at.isoformat(),
                "all_nine_exact_native_m1": complete,
                "perceptions": [{
                    "symbol": p.symbol,
                    "status": p.assessment.status.value,
                    "reasons": p.assessment.reasons,
                } for p in evidence.perceptions],
                "regimes": [{
                    "symbol": r.symbol,
                    "resolution": assess_regime(r).resolution.value,
                    "source_native_last_m1": r.causal_evidence[0],
                } for r in evidence.regimes],
                "cross_market_unknown_relations": 36,
                "broker_quotes_attested": False,
                "session_clock_attested": False,
                "portfolio_ledger_attested": False,
                "full_master_frame_executed": False,
                "source_entries_filtered": 0,
                "live_authorized": False,
            },sort_keys=True)+"\n")
    summary: dict[str, object] = {
        "identity": IDENTITY, "markets": 9,
        "original_decision_instants": n,
        "original_source_opportunities": 2876,
        "counts": dict(sorted(counts.items())),
        "genuine_perception_snapshots_constructed": n * 9,
        "genuine_unresolved_regime_hypotheses_constructed": n * 9,
        "unknown_causal_pair_edges_represented": n * 36,
        "broker_quotes_attested": False,
        "session_clock_attested": False,
        "capitalizer_global_world_model_completed": False,
        "portfolio_ledger_completed": False,
        "full_historical_master_frame_replay": False,
        "cognitive_profit_factor": None,
        "cognitive_drawdown_r": None,
        "source_entries_filtered": 0,
        "trader_certified": False,
        "live_authorized": False,
    }
    (target / "scalper-a1-nine-market-epistemic-inputs-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)+"\n"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("nine_provider_market_books", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(
        audit_pinned_nine_market_inputs(args.nine_provider_market_books, args.output),
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
