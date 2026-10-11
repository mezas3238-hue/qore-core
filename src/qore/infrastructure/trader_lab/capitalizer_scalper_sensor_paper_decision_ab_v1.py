"""Causal entry-sensor→trader decision→PAPER portfolio A/B evidence.

Never mutates a V49 source, trade, SL, TP, fill or trade R. All choices are
read-only AS-OF decisions made before the economic book is joined. Only a
genuinely supplied cognitive decision trace can activate the COGNITIVE lane.
Shadow sensor-identity disagreement is a forensic stress, NOT proof of edge.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_winner_retention_v1 import (
    _origin,
    _source_table,
    compare_winner_mass,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _metrics,
    _portfolio_select,
    _read_trades,
)

IDENTITY = "QORE_SCALPER_A2_SENSOR_TO_PAPER_TRADER_AB_V1"


@dataclass(frozen=True, slots=True)
class CognitiveEntryVerdict:
    """Independent A1 Master-Frame evaluation, never invented by A2.

    Every source opportunity must be evaluated at EXACTLY its entry timestamp.
    A WAIT means no entry for that source, NOT an invented later fill.
    """

    source_opportunity_id: str
    symbol: str
    observed_at: str
    disposition: Literal["ACCEPT", "WAIT", "ABSTAIN"]
    why: str
    cognitive_engine_identity: str
    master_frame_artifact_sha256: str
    master_frame_evaluated: bool
    sensor_evidence_evaluated: bool
    outcome_visible: bool = False
    used_future_h1_expiry: bool = False
    authorization_is_live: bool = False

    def __post_init__(self) -> None:
        if (
            not self.source_opportunity_id or not self.symbol or not self.why
            or not self.cognitive_engine_identity
            or len(self.master_frame_artifact_sha256) != 64
            or not self.master_frame_evaluated
            or not self.sensor_evidence_evaluated
            or self.outcome_visible
            or self.used_future_h1_expiry
            or self.authorization_is_live
        ):
            raise ValueError("requires independently evidenced causal A1 Master Frame")
        at = datetime.fromisoformat(self.observed_at)
        if at.utcoffset() is None:
            raise ValueError("A1 cognitive verdict timestamp must be timezone aware")


def _source_root(root: Path) -> tuple[V49Opportunity, ...]:
    paths = sorted(root.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    if len(paths) != 9:
        raise ValueError("A/B requires nine original V49 source files")
    return tuple(V49Opportunity(**x) for path in paths for x in _jsonl(path))


def _sensor_rows(root: Path) -> dict[str, dict[str, Any]]:
    files = sorted(root.rglob("scalper-entry-sensors-rows.jsonl"))
    if len(files) != 9:
        raise ValueError("A/B requires full nine-market original sensor evidence")
    rows = [r for path in files for r in _jsonl(path)]
    if len(rows) != 2876:
        raise ValueError("sensor-to-paper bridge requires all original 2876 rows")
    out = {r["source_opportunity_id"]: r for r in rows}
    if len(out) != len(rows):
        raise ValueError("duplicate source identity in sensor input")
    for row in rows:
        if (row["execution_authorized"] or row["hard_entry_gate_added"]
                or row["trader_certified"] or row["live_authorized"]):
            raise ValueError("sensor evidence illegally granted trading authority")
    return out


def _cognitive_verdicts(
    root: Path | None,
    sources: dict[str, V49Opportunity],
) -> dict[str, CognitiveEntryVerdict] | None:
    if root is None:
        return None
    files = sorted(root.rglob("scalper-a1-master-sensor-decision.jsonl"))
    if len(files) != 9:
        raise ValueError("A1 cognition requires nine source-specific decision ledgers")
    rows = tuple(CognitiveEntryVerdict(**r) for p in files for r in _jsonl(p))
    if len(rows) != len(sources):
        raise ValueError("A1 cognition did NOT cover all 2876 source opportunities")
    out = {r.source_opportunity_id: r for r in rows}
    if len(out) != len(sources) or set(out) != set(sources):
        raise ValueError("A1 cognition must provide exactly the same source IDs")
    for identifier, verdict in out.items():
        source = sources[identifier]
        if (
            verdict.symbol != source.symbol
            or datetime.fromisoformat(verdict.observed_at)
            != datetime.fromisoformat(source.m1_trigger_confirmed_at)
        ):
            raise ValueError("A1 Master Frame decision mismatched original timestamp")
    return out


def _select_with_max3(
    trades: tuple[V49EconomicTrade, ...],
) -> tuple[V49EconomicTrade, ...]:
    return tuple(trade for _, trade in _portfolio_select(trades))


def _score(
    selected: tuple[V49EconomicTrade, ...],
) -> dict[str, Any]:
    if not selected:
        return {
            "trades": 0, "total_r": "0", "max_drawdown_r": None,
            "profit_factor": None, "wins": 0,
        }
    m = _metrics(selected)
    return {
        "trades": m.trades,
        "wins": m.wins,
        "losses": m.losses,
        "total_r": m.total_r,
        "gross_profit_r": m.gross_profit_r,
        "gross_loss_r": m.gross_loss_r,
        "profit_factor": m.profit_factor,
        "max_drawdown_r": m.max_drawdown_r,
    }


def build_paper_ab(
    source_root: Path,
    trade_root: Path,
    sensor_root: Path,
    *,
    cognitive_root: Path | None = None,
) -> dict[str, Any]:
    """Filter candidate ORIGINAL trades only AFTER independent as-of decisions.

    POLICY CANDIDATE: preserve MAX3 by session/date and refill vacated slots
    chronologically from original opportunities, NEVER by their future R.
    The V49 economic outcomes are fixed. This is only an admission study;
    any actual delayed entry, new stop/target or live cost needs fresh replay.
    """

    source_rows = _source_root(source_root)
    source_map = {source_id(s): s for s in source_rows}
    if len(source_rows) != 2876 or len(source_map) != 2876:
        raise ValueError("not exactly 2876 unique frozen V49 sources")
    sensors = _sensor_rows(sensor_root)
    if set(sensors) != set(source_map):
        raise ValueError("missing/mismatched V49 original sensor source IDs")
    for sid, row in sensors.items():
        source = source_map[sid]
        if (
            row["symbol"] != source.symbol
            or row["original_entry_at"] != source.m1_trigger_confirmed_at
            or row["original_trigger_family"] != source.m1_trigger_family
        ):
            raise ValueError("sensor frame does not belong to source entry")
    all_trades = _read_trades(trade_root)
    source_table = _source_table(source_rows)
    trade_id = {_origin(trade, source_table): trade for trade in all_trades}
    if len(all_trades) != 2876 or len(trade_id) != 2876:
        raise ValueError("trade/source one-to-one matching failed")
    cognitive = _cognitive_verdicts(cognitive_root, source_map)
    control = _select_with_max3(all_trades)
    control_ids = {_origin(t, source_table) for t in control}
    if len(control) != 2020 or len(control_ids) != 2020:
        raise ValueError("original 2020 MAX3 control invalid")
    if sum(Decimal(t.realized_gross_r)>0 for t in control) != 1167:
        raise ValueError("original 1167 winner population not preserved")
    original_r = sum((Decimal(t.realized_gross_r) for t in control), Decimal(0))
    if abs(original_r - Decimal("-233.2693270763665099166092077")) > Decimal("1e-15"):
        raise ValueError("baseline original economic control changed")

    # Shadow research stress: does a sensor timestamp/route contradiction
    # predict DD? This is NOT a full cognitive trader and is NOT eligible
    # for rule promotion or certification from in-sample evidence.
    def matched(trade: V49EconomicTrade) -> bool:
        return bool(sensors[_origin(trade, source_table)]["sensor_source_identity_match"])

    arms: dict[str, tuple[V49EconomicTrade, ...]] = {
        "FROZEN_V49_CONTROL": control,
        "NOOP_SENSORS_OBSERVED": _select_with_max3(all_trades),
        "RESEARCH_SOURCE_SENSOR_CONSISTENCY_ONLY": _select_with_max3(
            tuple(trade for trade in all_trades if matched(trade))
        ),
    }
    if cognitive is not None:
        arms["A1_FULL_COGNITIVE_SENSORS_PAPER"] = _select_with_max3(
            tuple(
                t for t in all_trades
                if cognitive[_origin(t, source_table)].disposition == "ACCEPT"
            )
        )
    baseline_winning_r = {
        sid: Decimal(trade_id[sid].realized_gross_r) for sid in control_ids
    }
    results: dict[str, Any] = {}
    for name, chosen in arms.items():
        ids = {_origin(t, source_table) for t in chosen}
        retention = compare_winner_mass(
            baseline_winning_r,
            {sid: Decimal(trade_id[sid].realized_gross_r) for sid in ids},
        )
        metrics = _score(chosen)
        results[name] = {
            **metrics, "retention": retention,
            "original_winners_preserved": retention["retained_baseline_winning_source_ids"],
            "passed_retention_934_count": (
                retention["retained_baseline_winning_source_ids"] >= 934
            ),
            "passed_retention_415_75_r": (
                Decimal(retention["preserved_original_winner_r"]) >= Decimal("415.75")
            ),
            "gross_drawdown_change_vs_control_r": (
                str(Decimal(metrics["max_drawdown_r"])
                    - Decimal(_score(control)["max_drawdown_r"]))
                if metrics["max_drawdown_r"] is not None else None
            ),
            "source_entries_preserved": len(ids & control_ids),
            "newly_selected_after_slots_freed": len(ids - control_ids),
        }
    if arms["FROZEN_V49_CONTROL"] != arms["NOOP_SENSORS_OBSERVED"]:
        raise ValueError("no-op sensor bridge modified original trades")
    mismatch = sum(not row["sensor_source_identity_match"] for row in sensors.values())
    decisions: Counter[str] = Counter(
        v.disposition for v in cognitive.values()
    ) if cognitive is not None else Counter()
    return {
        "identity": IDENTITY, "mode": "DEVELOPMENT_PAPER_POSTHOC",
        "markets": 9, "original_source_opportunities": 2876,
        "original_max3_selected": 2020,
        "sensor_source_mismatch": mismatch,
        "a1_full_master_frame_attested": cognitive is not None,
        "a1_cognitive_dispositions": dict(sorted(decisions.items())),
        "scorecard": results,
        "case_study_sensor_mismatch_only_not_cognitive": True,
        "abstentions_are_not_delayed_fills": True,
        "original_v49_entry_exit_stops_targets_unchanged": True,
        "broker_bid_ask_commission_slippage_simulated": False,
        "outcomes_used_for_decisions": False,
        "research_only": True,
        "trader_certified": False, "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("original_sources", type=Path)
    parser.add_argument("original_trades", type=Path)
    parser.add_argument("sensor_evidence", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--a1-full-frame-decisions", type=Path)
    args = parser.parse_args()
    result = build_paper_ab(
        args.original_sources, args.original_trades, args.sensor_evidence,
        cognitive_root=args.a1_full_frame_decisions,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "scalper-sensors-to-trader-paper-ab.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "sensor_conflicts": result["sensor_source_mismatch"],
        "full_master_frame_connected": result["a1_full_master_frame_attested"],
        "paper_arms": {
            name: {
                "trades": x["trades"], "profit_factor": x["profit_factor"],
                "max_drawdown_r": x["max_drawdown_r"],
                "original_winners_preserved": x["original_winners_preserved"],
            } for name, x in result["scorecard"].items()
        },
    }, sort_keys=True))


if __name__ == "__main__":
    main()
