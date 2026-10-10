"""Pre-registered 2x2 stop/noise factorial on identical native-M1 V49 source.

Factor: M15 thesis stop vs causally confirmed M1 pivot stop.
Factor: M1 local-noise 4..8x HARD VETO vs NO veto.
All four arms keep the SAME V49 H1 target, time, MAX3 and replay mechanics.
A V50-G historical *comparison* is NOT identical to the isolated M1 arm
because V50-G also changes its H1 target ladder and cognitive decisions.

Research only, no permission to trade, size, merge, or tune from outcomes.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEFAULT_LOOKBACK,
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_trader_v49 import (
    materialize_trade_intent,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_winner_retention_v1 import (
    _key,
    _origin,
    _source_table,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _metrics,
    _portfolio_select,
    _replay_one,
    _session_bars,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_opportunity import (
    _recent_range_ticks,
)
from qore.infrastructure.trader_lab.capitalizer_v50_target_stop_intelligence import (
    build_dual_invalidation,
)

IDENTITY = "QORE_SCALPER_A2_PRE_REGISTERED_STOP_NOISE_2X2_V1"
MIN_NOISE = Decimal("4")
MAX_NOISE = Decimal("8")


class Arm(StrEnum):
    M15_NOISE_OFF = "M15_NOISE_OFF"
    M15_NOISE_VETO = "M15_NOISE_VETO"
    M1_NOISE_OFF = "M1_NOISE_OFF"
    M1_NOISE_VETO = "M1_NOISE_VETO"


@dataclass(frozen=True, slots=True)
class StopNoiseSourceGate:
    source_opportunity_id: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    entry_price: str
    trigger_family: str
    h1_state_basis: str
    thesis_stop_price: str
    unchanged_h1_target_price: str
    m1_anchor_available: bool
    m1_anchor_price: str | None
    m1_anchor_confirmed_at: str | None
    m1_stop_to_recent_m1_range: str | None
    m1_noise_reason: str
    eligible_arms: tuple[str, ...]
    outcome_used_for_admission: bool = False
    full_master_frame_evaluated: bool = False
    entry_authorized: bool = False

    def __post_init__(self) -> None:
        if self.outcome_used_for_admission or self.entry_authorized or self.full_master_frame_evaluated:
            raise ValueError("factorial gate has no outcome, trade or Master Frame authority")
        if Arm.M15_NOISE_OFF not in self.eligible_arms:
            raise ValueError("all source-complete V49 opportunities need M15 baseline")
        if self.m1_anchor_available != (self.m1_anchor_price is not None):
            raise ValueError("M1 stop availability/price mismatch")


def _aware(value: str) -> datetime:
    t = datetime.fromisoformat(value)
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("factorial requires timezone-aware source stamps")
    return t


def analyze_source_geometry(
    source: V49Opportunity,
    m1: tuple[CapitalizerM1Bar, ...],
    opened: tuple[datetime, ...],
) -> StopNoiseSourceGate:
    """Read only completed bars at the decision; never use exit or future M1."""

    at = _aware(source.m1_trigger_confirmed_at)
    m15_at = _aware(source.m15_setup_confirmed_at)
    h1_at = _aware(source.h1_state_from)
    if h1_at > m15_at or m15_at > at:
        raise ValueError("H1/M15/M1 source confirmations out of order")
    right = bisect.bisect_left(opened, at)
    left = bisect.bisect_left(opened, m15_at)
    completed = m1[left:right]
    if any(bar.opened_at < m15_at or bar.closed_at > at for bar in completed):
        raise ValueError("leaked uncompleted or pre-M15 M1 bar")
    if right < 15 or not completed:
        raise ValueError("M1 history insufficient to form causal stop and range")
    recent = m1[right - 15:right]
    if recent[-1].closed_at > at or any(
        bar.symbol != source.symbol for bar in recent
    ):
        raise ValueError("M1 recent-range observations not complete as-of")
    entry = Decimal(source.decision_reference_price)
    thesis = Decimal(source.m15_protected_swing_price)
    side = CapitalizerSide.LONG if source.h1_state_direction == "BULLISH" else CapitalizerSide.SHORT
    stop_info = build_dual_invalidation(
        completed,
        side=side,
        setup_confirmed_at=m15_at,
        decision_at=at,
        entry_price=entry,
        thesis_stop_price=thesis,
    )
    noise_ticks = _recent_range_ticks(recent, decision_at=at)
    tick = Decimal(1).scaleb(-recent[-1].digits)
    range_price = noise_ticks * tick
    ratio = (
        None
        if stop_info.execution_risk_price is None
        else stop_info.execution_risk_price / range_price
    )
    if ratio is None:
        reason = "M1_PIVOT_UNAVAILABLE"
    elif ratio < MIN_NOISE:
        reason = "M1_EXECUTION_STOP_INSIDE_LOCAL_NOISE"
    elif ratio > MAX_NOISE:
        reason = "M1_EXECUTION_STOP_TOO_WIDE_FOR_SCALP"
    else:
        reason = "M1_EXECUTION_STOP_NOISE_4_TO_8_PASS"
    approved: list[str] = [Arm.M15_NOISE_OFF.value]
    if stop_info.execution_anchor_available:
        approved.append(Arm.M1_NOISE_OFF.value)
        if reason == "M1_EXECUTION_STOP_NOISE_4_TO_8_PASS":
            approved.extend((
                Arm.M15_NOISE_VETO.value,
                Arm.M1_NOISE_VETO.value,
            ))
    return StopNoiseSourceGate(
        source_opportunity_id=source_id(source),
        symbol=source.symbol,
        session=source.session,
        operating_date=source.operating_date,
        entry_at=source.m1_trigger_confirmed_at,
        entry_price=source.decision_reference_price,
        trigger_family=source.m1_trigger_family,
        h1_state_basis=source.h1_state_basis,
        thesis_stop_price=source.m15_protected_swing_price,
        unchanged_h1_target_price=source.structural_target_witness_price,
        m1_anchor_available=stop_info.execution_anchor_available,
        m1_anchor_price=(
            str(stop_info.execution_stop_price)
            if stop_info.execution_stop_price is not None else None
        ),
        m1_anchor_confirmed_at=(
            stop_info.execution_anchor_confirmed_at.isoformat()
            if stop_info.execution_anchor_confirmed_at else None
        ),
        m1_stop_to_recent_m1_range=str(ratio) if ratio is not None else None,
        m1_noise_reason=reason,
        eligible_arms=tuple(approved),
    )


def build_market(
    sources_root: Path,
    native_m1_root: Path,
    baseline_root: Path,
) -> tuple[dict[str, Any], tuple[StopNoiseSourceGate, ...], dict[Arm, tuple[V49EconomicTrade, ...]]]:
    source_paths = sorted(sources_root.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    trade_paths = sorted(baseline_root.rglob("capitalizer-*-v49-development-economics-trades.jsonl"))
    if len(source_paths) != 1 or len(trade_paths) != 1:
        raise ValueError("one market needs one frozen V49 source and trade ledger")
    sources = tuple(V49Opportunity(**data) for data in _jsonl(source_paths[0]))
    control = tuple(V49EconomicTrade(**data) for data in _jsonl(trade_paths[0]))
    if not sources or len(sources) != len(control):
        raise ValueError("frozen V49 source/trade cardinality mismatch")
    symbol = sources[0].symbol
    session = sources[0].session
    if any(s.symbol != symbol or s.session != session for s in sources):
        raise ValueError("mixed markets in source file")

    # The same M1 dev window + lookback as original V49 census. No outside-market bars.
    start = DEV_WINDOW_START - DEFAULT_LOOKBACK
    bars = tuple(
        bar for bar in iter_cibo_m1(native_m1_root)
        if start <= bar.opened_at < DEV_WINDOW_END
    )
    if not bars or any(bar.symbol != symbol for bar in bars):
        raise ValueError("native-M1 asset mismatch")
    opened = tuple(bar.opened_at for bar in bars)
    src_table = _source_table(sources)
    original = {_origin(t, src_table): t for t in control}
    if len(original) != len(sources):
        raise ValueError("duplicated original V49 trade keys")

    gates: list[StopNoiseSourceGate] = []
    rows: dict[Arm, list[V49EconomicTrade]] = {arm: [] for arm in Arm}
    for source in sources:
        identity = source_id(source)
        gate = analyze_source_geometry(source, bars, opened)
        gates.append(gate)
        intent = materialize_trade_intent(source)
        session_bars = _session_bars(bars, opened, intent=intent)
        thesis_fill = _replay_one(session_bars, intent)
        if thesis_fill is None or thesis_fill != original[identity]:
            raise ValueError("unchanged M15 arm disagrees with frozen 9-market V49 control")
        rows[Arm.M15_NOISE_OFF].append(thesis_fill)
        if Arm.M15_NOISE_VETO.value in gate.eligible_arms:
            rows[Arm.M15_NOISE_VETO].append(thesis_fill)

        if Arm.M1_NOISE_OFF.value in gate.eligible_arms:
            if gate.m1_anchor_price is None:
                raise ValueError("M1 fill missing decision-time pivot")
            refined_intent = replace(
                intent, stop_price=Decimal(gate.m1_anchor_price)
            )
            refined_fill = _replay_one(session_bars, refined_intent)
            if refined_fill is None:
                raise ValueError("M1 pivot eligible but no execution session bars")
            rows[Arm.M1_NOISE_OFF].append(refined_fill)
            if Arm.M1_NOISE_VETO.value in gate.eligible_arms:
                rows[Arm.M1_NOISE_VETO].append(refined_fill)
    if len({g.source_opportunity_id for g in gates}) != len(sources):
        raise ValueError("duplicate per-source factorial gate")
    by_arm = {arm: tuple(records) for arm, records in rows.items()}
    return ({
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session,
        "source_opportunities": len(sources),
        "baseline_trades_replayed_and_identical": len(rows[Arm.M15_NOISE_OFF]),
        "m1_noise_reasons": sorted(Counter(g.m1_noise_reason for g in gates).items()),
        "pre_max3_by_arm": {arm.value: len(rows[arm]) for arm in Arm},
        "same_h1_target_all_arms": True,
        "outcomes_used_for_gate": False,
        "full_master_frame_evaluated": False,
        "trader_certified": False,
        "live_authorized": False,
    }, tuple(gates), by_arm)


def write_market(
    report: dict[str, Any],
    gates: tuple[StopNoiseSourceGate, ...],
    arms: dict[Arm, tuple[V49EconomicTrade, ...]],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "scalper-stop-noise-market.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (output / "scalper-stop-noise-source-gates.jsonl").open("w", encoding="utf-8") as f:
        for gate in gates:
            f.write(json.dumps(asdict(gate), sort_keys=True) + "\n")
    for arm in Arm:
        with (output / f"scalper-stop-noise-{arm.value}-trades.jsonl").open(
            "w", encoding="utf-8"
        ) as f:
            for trade in arms[arm]:
                f.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def aggregate(root: Path) -> dict[str, Any]:
    reports = tuple(
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(root.rglob("scalper-stop-noise-market.json"))
    )
    if len(reports) != 9 or len({r.get("symbol") for r in reports}) != 9:
        raise ValueError("factorial requires all 9 distinct original markets")
    gate_paths = sorted(root.rglob("scalper-stop-noise-source-gates.jsonl"))
    if len(gate_paths) != 9:
        raise ValueError("per-source causal gates missing")
    all_gates = tuple(
        StopNoiseSourceGate(**raw)
        for path in gate_paths for raw in _jsonl(path)
    )
    if len(all_gates) != 2876 or len({g.source_opportunity_id for g in all_gates}) != 2876:
        raise ValueError("factorial source population must be identical to frozen V49")
    sources = {
        _key(g.symbol,g.session,g.operating_date,g.entry_at,g.entry_price,
             g.trigger_family,g.h1_state_basis): g
        for g in all_gates
    }
    if len(sources) != len(all_gates):
        raise ValueError("ambiguous source-to-trade identity in factorial")

    def trade_gate(t: V49EconomicTrade) -> StopNoiseSourceGate:
        k = _key(t.symbol,t.session,t.operating_date,t.entry_at,t.entry_price,
                 t.trigger_family,t.h1_state_basis)
        if k not in sources:
            raise ValueError("factorial trade lacks V49 source")
        return sources[k]

    selected_by_arm: dict[Arm, tuple[V49EconomicTrade, ...]] = {}
    per_arm: dict[str, dict[str, Any]] = {}
    for arm in Arm:
        paths = sorted(root.rglob(f"scalper-stop-noise-{arm.value}-trades.jsonl"))
        if len(paths) != 9:
            raise ValueError("one market's factorial arm is missing")
        trades = tuple(
            V49EconomicTrade(**row) for path in paths for row in _jsonl(path)
        )
        ids: set[str] = set()
        for trade in trades:
            gate = trade_gate(trade)
            if arm.value not in gate.eligible_arms:
                raise ValueError("economic trade contradicts observed gate eligibility")
            if gate.source_opportunity_id in ids:
                raise ValueError("duplicate trade for one source/arm")
            ids.add(gate.source_opportunity_id)
            if Decimal(trade.target_price) != Decimal(gate.unchanged_h1_target_price):
                raise ValueError("target changed across the stop/noise experiment")
            desired_stop = (
                gate.thesis_stop_price
                if arm in (Arm.M15_NOISE_OFF, Arm.M15_NOISE_VETO)
                else gate.m1_anchor_price
            )
            if desired_stop is None or Decimal(trade.stop_price) != Decimal(desired_stop):
                raise ValueError("stop changed from preregistered causal anchor")
        selected = tuple(t for _, t in _portfolio_select(trades))
        selected_by_arm[arm] = selected
        by_reason: dict[str, dict[str, Any]] = {}
        by_session: dict[str, dict[str, Any]] = {}
        for reason in sorted({x.trigger_family for x in selected}):
            metrics = _metrics(tuple(t for t in selected if t.trigger_family == reason))
            by_reason[reason] = asdict(metrics)
        for session in sorted({x.session for x in selected}):
            metrics = _metrics(tuple(t for t in selected if t.session == session))
            by_session[session] = asdict(metrics)
        per_arm[arm.value] = {
            "pre_max3": len(trades),
            "post_max3": len(selected),
            "max3_censored": len(trades) - len(selected),
            "gross": asdict(_metrics(selected)) if selected else None,
            "by_family": by_reason,
            "by_session": by_session,
        }

    baseline = selected_by_arm[Arm.M15_NOISE_OFF]
    base_r = {
        trade_gate(t).source_opportunity_id: Decimal(t.realized_gross_r)
        for t in baseline
    }
    winners = {k: v for k, v in base_r.items() if v > 0}
    positive_r = sum(winners.values(), Decimal(0))
    if len(baseline) != 2020 or len(winners) != 1167:
        raise ValueError("preregistered V49 baseline winner denominator changed")
    for arm in Arm:
        selected = selected_by_arm[arm]
        candidate = {
            trade_gate(t).source_opportunity_id: Decimal(t.realized_gross_r)
            for t in selected
        }
        positive_common = [
            k for k, val in winners.items()
            if candidate.get(k, Decimal(0)) > 0
        ]
        preserved = sum((winners[k] for k in positive_common), Decimal(0))
        per_arm[arm.value]["baseline_winners_still_positive"] = len(positive_common)
        per_arm[arm.value]["original_winner_r_preserved"] = str(preserved)
        per_arm[arm.value]["winner_count_retention"] = str(
            Decimal(len(positive_common))/len(winners)
        )
        per_arm[arm.value]["original_winner_mass_retention"] = str(
            preserved/positive_r
        )

    reasons = dict(Counter(g.m1_noise_reason for g in all_gates))
    return {
        "identity": IDENTITY,
        "source_market_count": 9,
        "source_opportunities": 2876,
        "original_baseline_selected": 2020,
        "original_baseline_winners": len(winners),
        "original_baseline_gross_winning_r": str(positive_r),
        "predecision_m1_noise_reasons": reasons,
        "same_h1_target_all_arms": True,
        "identical_causal_source_ids": True,
        "all_policies_research_only": True,
        "neither_master_frame_nor_real_broker_costs_tested": True,
        "arms": per_arm,
        "trader_certified": False,
        "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    m = sub.add_parser("market")
    m.add_argument("v49_source", type=Path)
    m.add_argument("native_m1", type=Path)
    m.add_argument("v49_control", type=Path)
    m.add_argument("output", type=Path)
    a = sub.add_parser("matrix")
    a.add_argument("market_artifacts", type=Path)
    a.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.mode == "market":
        report, gates, arms = build_market(
            args.v49_source,args.native_m1,args.v49_control
        )
        write_market(report,gates,arms,args.output)
        print(json.dumps(report, sort_keys=True))
    else:
        result = aggregate(args.market_artifacts)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "scalper-stop-noise-factorial-matrix.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps({
            "identity": IDENTITY,
            "source_opportunities": 2876,
            "m1_noise_reasons": result["predecision_m1_noise_reasons"],
            "arms": {
                arm: {
                    k: v for k,v in row.items()
                    if k in ("pre_max3","post_max3","gross",
                             "baseline_winners_still_positive","original_winner_r_preserved")
                }
                for arm,row in result["arms"].items()
            },
            "trader_certified": False,
        }, sort_keys=True))


if __name__ == "__main__":
    main()
