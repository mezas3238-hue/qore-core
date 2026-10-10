"""Lossless post-hoc admission waterfall for V49 source -> V50-G replay ledgers.

Research-only *reader*. It does not rerun, rank or alter opportunities, stops,
targets, costs, orders, cognition, or policy. A1 cognitive trace is joined
strictly by its stable predecision source identifier. Without that trace only
aggregate market counts are auditable (and detail is explicitly UNKNOWN).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_economics import (
    POLICIES,
    V50GTrade,
    _portfolio,
)

IDENTITY = "QORE_SCALPER_V49_TO_V50_G_ADMISSION_WATERFALL_V1"
A1_TRACE_ID = "QORE_SCALPER_V50_G_CAUSAL_TRACE_V1"
TRACE_NAME = "capitalizer-v50-g-cognitive-trace.jsonl"
PROVENANCE = "POST_HOC_REPLAY_LEDGER_AUDIT_NOT_EXECUTION"


def source_id(item: V49Opportunity) -> str:
    """The A1 source identity contract (exclude future-dated H1 active_until)."""
    parts = (
        item.symbol, item.session, item.operating_date,
        item.h1_state_from, item.h1_state_direction, item.h1_state_basis,
        item.m15_setup_confirmed_at, item.m15_protected_swing_price,
        item.m1_trigger_confirmed_at, item.m1_trigger_family,
        item.decision_reference_price, item.structural_target_witness_price,
    )
    return hashlib.sha256(
        json.dumps(parts, separators=(",", ":")).encode()
    ).hexdigest()


def _jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError(f"{path}:{line_number} expected JSON object")
            result.append(obj)
    return tuple(result)


def _strict_time(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("waterfall requires timezone-aware decision stamps")
    return dt


@dataclass(frozen=True, slots=True)
class OpportunityGateRow:
    source_opportunity_id: str
    symbol: str
    session: str
    operating_date: str
    decision_at: str
    trigger_family: str
    geometry_decision: str
    bridge_disposition: str
    geometry_reasons: tuple[str, ...]
    bridge_reasons: tuple[str, ...]
    geometry_policy_eligible: bool
    cognitive_policy_eligible: bool
    # No hindsight win/loss, future H1 active_until, P&L or trade outcome fields.
    outcome_visible_at_decision: bool = False
    master_frame_demonstrated: bool = False
    economic_execution_inferred_from_row: bool = False

    def __post_init__(self) -> None:
        _strict_time(self.decision_at)
        if (
            self.outcome_visible_at_decision
            or self.master_frame_demonstrated
            or self.economic_execution_inferred_from_row
        ):
            raise ValueError("gate row cannot claim full cognition/outcome/execution")
        if self.cognitive_policy_eligible and not self.geometry_policy_eligible:
            raise ValueError("cognitive policy must be a subset of geometry ready")


def _check_trace(
    opportunity: V49Opportunity, raw: dict[str, Any]
) -> OpportunityGateRow:
    decision = _strict_time(opportunity.m1_trigger_confirmed_at)
    h1 = _strict_time(opportunity.h1_state_from)
    m15 = _strict_time(opportunity.m15_setup_confirmed_at)
    if not h1 <= m15 <= decision:
        raise ValueError("future H1 or M15 source confirmation")
    expected = source_id(opportunity)
    if (
        raw.get("identity") != A1_TRACE_ID
        or raw.get("source_opportunity_id") != expected
        or raw.get("symbol") != opportunity.symbol
        or raw.get("session") != opportunity.session
        or raw.get("source_h1_from") != opportunity.h1_state_from
        or raw.get("source_m15_confirmed_at") != opportunity.m15_setup_confirmed_at
        or raw.get("source_m1_confirmed_at") != opportunity.m1_trigger_confirmed_at
        or raw.get("source_trigger_family") != opportunity.m1_trigger_family
        or _strict_time(str(raw.get("observed_at"))) != decision
    ):
        raise ValueError(f"A1 trace/source identity or time mismatch: {expected}")

    if (
        raw.get("outcome_visible_to_cognition") is not False
        or raw.get("capital_authority_granted") is not False
        or raw.get("master_frame_evaluated") is not False
        or raw.get("global_world_model_evaluated") is not False
        or raw.get("nine_market_competition_evaluated") is not False
        or raw.get("readiness_verified") is not False
        or raw.get("experience_memory_scope") != "PER_CANDIDATE_EMPTY_EXPERIENCE"
        or raw.get("readiness_origin") != "LEGACY_STATIC_WELL_SUPPORTED"
        or raw.get("experience_observations") != 0
    ):
        raise ValueError("V50-G legacy cognitive provenance must stay truthful")
    geometry = str(raw["geometry_decision"])
    disposition = str(raw["bridge_disposition"])
    only = raw.get("policy_geometry_only_eligible")
    cog = raw.get("policy_cognitive_geometry_eligible")
    if type(only) is not bool or type(cog) is not bool:
        raise ValueError("policy-eligibility flags must be real booleans")
    if only != (geometry == "READY") or (cog and not only):
        raise ValueError("geometry/cognitive eligibility contradiction")
    geometry_reasons = tuple(str(x) for x in raw["geometry_reasons"])
    bridge_reasons = tuple(str(x) for x in raw["bridge_reasons"])
    if not geometry_reasons or not bridge_reasons:
        raise ValueError("trace must include nonempty WHY for both gates")
    return OpportunityGateRow(
        source_opportunity_id=expected,
        symbol=opportunity.symbol,
        session=opportunity.session,
        operating_date=opportunity.operating_date,
        decision_at=opportunity.m1_trigger_confirmed_at,
        trigger_family=opportunity.m1_trigger_family,
        geometry_decision=geometry,
        bridge_disposition=disposition,
        geometry_reasons=geometry_reasons,
        bridge_reasons=bridge_reasons,
        geometry_policy_eligible=only,
        cognitive_policy_eligible=cog,
    )


def _count_pairs(value: object, *, field: str) -> Counter[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must contain [key, count] pairs")
    result: Counter[str] = Counter()
    for pair in value:
        if (
            not isinstance(pair, list) or len(pair) != 2
            or not isinstance(pair[0], str) or type(pair[1]) is not int
            or pair[1] < 0 or pair[0] in result
        ):
            raise ValueError(f"invalid or duplicate {field} count")
        result[pair[0]] = pair[1]
    return result


def build_waterfall(
    capacity_root: Path,
    v50_root: Path,
    *,
    expected_markets: int = 9,
    require_traces: bool = True,
) -> tuple[dict[str, Any], tuple[OpportunityGateRow, ...]]:
    """Fail-closed on missing/double inputs or arithmetic inconsistency."""

    if expected_markets < 1:
        raise ValueError("market coverage must be positive")
    source_paths = sorted(
        capacity_root.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl")
    )
    report_paths = sorted(v50_root.rglob("capitalizer-*-v50-g-report.json"))
    trade_paths = sorted(v50_root.rglob("capitalizer-*-v50-g-trades.jsonl"))
    if any(len(group) != expected_markets for group in (
        source_paths, report_paths, trade_paths,
    )):
        raise ValueError("missing/duplicate V49/V50-G inputs for market coverage")

    sources: dict[str, tuple[V49Opportunity, ...]] = {}
    for path in source_paths:
        opps = tuple(V49Opportunity(**row) for row in _jsonl(path))
        if not opps:
            raise ValueError(f"empty source opportunity ledger: {path}")
        symbol = opps[0].symbol
        if symbol in sources or any(item.symbol != symbol for item in opps):
            raise ValueError("duplicate or mixed market V49 opportunities")
        if path.name != f"capitalizer-{symbol.lower()}-v49-hf-capacity-opportunities.jsonl":
            raise ValueError("source ledger filename/market mismatch")
        sources[symbol] = opps
    reports: dict[str, tuple[dict[str, Any], Path]] = {}
    for path in report_paths:
        obj = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("market report must be an object")
        symbol = str(obj.get("symbol", ""))
        if symbol in reports or symbol not in sources:
            raise ValueError("duplicate/unmatched V50 market report")
        if path.name != f"capitalizer-{symbol.lower()}-v50-g-report.json":
            raise ValueError("V50-G report filename/market mismatch")
        reports[symbol] = (obj, path)

    trades: list[V50GTrade] = []
    seen_trade_markets: set[str] = set()
    for path in trade_paths:
        filename = path.name
        found = tuple(
            symbol for symbol in reports
            if filename == f"capitalizer-{symbol.lower()}-v50-g-trades.jsonl"
        )
        if len(found) != 1 or found[0] in seen_trade_markets:
            raise ValueError("duplicate or unmatched trade ledger")
        symbol = found[0]
        seen_trade_markets.add(symbol)
        market_trades = tuple(V50GTrade(**row) for row in _jsonl(path))
        if any(
            row.symbol != symbol or row.session != sources[symbol][0].session
            or row.policy not in POLICIES for row in market_trades
        ):
            raise ValueError("trades conflict with source market/session")
        trades.extend(market_trades)
    if set(sources) != set(reports) or seen_trade_markets != set(sources):
        raise ValueError("incomplete market source/replay pairing")

    all_gates: list[OpportunityGateRow] = []
    coverage: list[dict[str, Any]] = []
    all_trades = tuple(trades)
    for symbol in sorted(sources):
        opps = sources[symbol]
        report, report_path = reports[symbol]
        if len({item.session for item in opps}) != 1:
            raise ValueError("mixed sessions within source ledger")
        if report.get("session") != opps[0].session:
            raise ValueError("market report/session mismatch")
        if report.get("source_opportunities") != len(opps):
            raise ValueError("source opportunity count mismatch")
        geometry_counts = _count_pairs(
            report.get("geometry_decisions"), field="geometry_decisions"
        )
        bridge_counts = _count_pairs(
            report.get("cognitive_dispositions"), field="cognitive_dispositions"
        )
        if sum(geometry_counts.values()) != len(opps) or sum(
            bridge_counts.values()
        ) != len(opps):
            raise ValueError("source geometry/cognition denominators mismatch")
        ready = geometry_counts.get("READY", 0)
        if report.get("geometry_ready") != ready:
            raise ValueError("ready geometry count mismatch")
        reported_policies = report.get("policy_trade_rows_before_max3")
        if not isinstance(reported_policies, dict):
            raise ValueError("V50-G policy counts required")
        actual = Counter(
            trade.policy for trade in all_trades if trade.symbol == symbol
        )
        if (
            set(reported_policies) != set(POLICIES)
            or any(reported_policies[p] != actual[p] for p in POLICIES)
            or actual["GEOMETRY_ONLY"] > ready
            or actual["COGNITIVE_GEOMETRY"] > actual["GEOMETRY_ONLY"]
        ):
            raise ValueError("policy rows not reconciled to replay trade ledger")

        trace_path = report_path.parent / TRACE_NAME
        traces_available = trace_path.is_file()
        if require_traces and not traces_available:
            raise ValueError(f"A1 cognitive trace missing for {symbol}")
        local_gates: list[OpportunityGateRow] = []
        trace_ready_count: int | None = None
        trace_cognitive_count: int | None = None
        rejection_reasons: Counter[str] = Counter()
        cognitive_reasons: Counter[str] = Counter()
        if traces_available:
            raw_rows = _jsonl(trace_path)
            if len(raw_rows) != len(opps):
                raise ValueError("A1 trace must cover every source opportunity")
            source_lookup = {source_id(item): item for item in opps}
            trace_lookup = {str(row.get("source_opportunity_id")): row for row in raw_rows}
            if (
                len(source_lookup) != len(opps)
                or len(trace_lookup) != len(raw_rows)
                or set(source_lookup) != set(trace_lookup)
            ):
                raise ValueError("duplicate, missing or foreign A1 source IDs")
            for identifier in sorted(source_lookup):
                gate = _check_trace(source_lookup[identifier], trace_lookup[identifier])
                local_gates.append(gate)
                if not gate.geometry_policy_eligible:
                    rejection_reasons.update(gate.geometry_reasons)
                if gate.geometry_policy_eligible and not gate.cognitive_policy_eligible:
                    cognitive_reasons.update(gate.bridge_reasons)
            trace_ready_count = sum(item.geometry_policy_eligible for item in local_gates)
            trace_cognitive_count = sum(
                item.cognitive_policy_eligible for item in local_gates
            )
            if (
                Counter(item.geometry_decision for item in local_gates)
                != geometry_counts
                or Counter(item.bridge_disposition for item in local_gates)
                != bridge_counts
                or trace_ready_count != ready
                or trace_cognitive_count < actual["COGNITIVE_GEOMETRY"]
            ):
                raise ValueError("report and opportunity-level A1 traces disagree")
            missing_calc = (
                ready - actual["GEOMETRY_ONLY"]
                + trace_cognitive_count - actual["COGNITIVE_GEOMETRY"]
            )
            if report.get("missing_session_bars") != missing_calc:
                raise ValueError("missing-session-bars does not reconcile")
        if report.get("cognitive_trace_rows") not in (None, len(opps)):
            raise ValueError("V50 cognitive trace declared with wrong cardinality")
        coverage.append({
            "symbol": symbol,
            "session": report["session"],
            "source_opportunities": len(opps),
            "geometry_decisions": sorted(geometry_counts.items()),
            "cognitive_dispositions": sorted(bridge_counts.items()),
            "geometry_not_ready": len(opps) - ready,
            "geometry_ready": ready,
            "cognitive_allowed_with_geometry_ready": trace_cognitive_count,
            "cognitive_denied_among_geometry_ready": (
                ready - trace_cognitive_count if trace_cognitive_count is not None else None
            ),
            "geometry_policy_before_max3": actual["GEOMETRY_ONLY"],
            "cognitive_policy_before_max3": actual["COGNITIVE_GEOMETRY"],
            "missing_session_bars": report["missing_session_bars"],
            "geometry_reason_occurrences": sorted(rejection_reasons.items()),
            "bridge_reason_occurrences_on_geometry_ready": sorted(
                cognitive_reasons.items()
            ),
            "trace_covered": traces_available,
        })
        all_gates.extend(local_gates)

    post_by_policy = {
        policy: _portfolio(all_trades, policy=policy) for policy in POLICIES
    }
    postcounts: dict[tuple[str, str], int] = Counter(
        (row.policy, row.symbol)
        for policy in POLICIES for row in post_by_policy[policy]
    )
    pre_totals = Counter(row.policy for row in all_trades)
    post_totals = Counter(
        policy for policy in POLICIES for _ in post_by_policy[policy]
    )
    for row in coverage:
        symbol = str(row["symbol"])
        for policy in POLICIES:
            key = (
                "geometry" if policy == "GEOMETRY_ONLY" else "cognitive"
            )
            pre = int(row[f"{key}_policy_before_max3"])
            post = postcounts.get((policy, symbol), 0)
            if post > pre:
                raise ValueError("MAX3 cannot increase market trade count")
            row[f"{key}_policy_after_max3"] = post
            row[f"{key}_policy_removed_max3"] = pre - post

    result = {
        "identity": IDENTITY,
        "provenance": PROVENANCE,
        "source_market_count": len(sources),
        "market_coverage_required": expected_markets,
        "source_opportunities_total": sum(len(items) for items in sources.values()),
        "a1_trace_rows": len(all_gates),
        "all_markets_trace_covered": len(all_gates) == sum(
            len(items) for items in sources.values()
        ),
        "policy_rows_before_max3": {
            policy: pre_totals[policy] for policy in POLICIES
        },
        "policy_rows_after_max3": {
            policy: post_totals[policy] for policy in POLICIES
        },
        "policy_rows_removed_max3": {
            policy: pre_totals[policy] - post_totals[policy] for policy in POLICIES
        },
        "markets": coverage,
        "no_new_replay_executed": True,
        "no_terminal_outcomes_used_in_gate_trace": True,
        "no_automatic_methodology_promotion": True,
        "full_master_frame_evaluated": False,
        "trader_certified": False,
        "live_authorized": False,
    }
    return result, tuple(all_gates)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("capacity_root", type=Path)
    parser.add_argument("v50_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-markets", type=int, default=9)
    parser.add_argument("--allow-report-only", action="store_true")
    args = parser.parse_args()
    report, gates = build_waterfall(
        args.capacity_root,
        args.v50_root,
        expected_markets=args.expected_markets,
        require_traces=not args.allow_report_only,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "scalper-v49-v50-g-waterfall.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (args.output / "scalper-v49-v50-g-source-gates.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in gates:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    print(json.dumps({
        "identity": IDENTITY,
        "source_opportunities_total": report["source_opportunities_total"],
        "all_markets_trace_covered": report["all_markets_trace_covered"],
        "policy_rows_after_max3": report["policy_rows_after_max3"],
        "trader_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
