"""Read-only V3/G-M4 Atlas M5 G2/G7 point-in-time diagnostic (preregistered).

Never changes frozen V3 source nor G-M4 lifecycle. Two H4 references are a
BOUNDED sensitivity witness, not an exhaustive old-CRT reference inventory.
G7 uses censored prior terminal observations and never authorizes reentry.
No execution, sizing, PnL, broker, live capital, or certification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.trader_lab.vt08_crt_pure_original_atlas_reader import (
    load_atlas_vt08_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_three_source_candidate_v1 import (
    _direction,
)
from qore.infrastructure.trader_lab.vt08_crt_three_source_v1_full_h4_census import (
    H4,
    M5,
    _aggregate,
)
from qore.infrastructure.trader_lab.vt08_crt_three_source_v3_confirmed_h4_census import (
    full_utc_h4_v3_census,
)
from qore.infrastructure.trader_lab.vt08_crt_three_source_v3_gm4_lifecycle import (
    replay_v3_gm4,
)
from qore.infrastructure.traders.crt_pure_gm1_g2_g7_causal_audit import (
    CrtGm1CausalVerdict,
    CrtGm1Reference,
    CrtGm1SourceEvent,
    audit_g2_reference_conflicts,
    audit_g7_rearm,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

SCHEMA = "qore.vt08.crt.g2_g7_real_atlas_pit_bridge.research_only.v1"
HISTORY_WINDOW = H4 + H4 + H4


def _utc(t: str) -> datetime:
    clock = datetime.fromisoformat(t)
    if clock.tzinfo is None or clock.utcoffset() is None:
        raise ValueError("PIT clock without timezone")
    return clock.astimezone(UTC)


def _evidence_digest(
    market: CrtPureMarket, parent: str, name: str,
    payload: dict[str, Any], c2: dict[str, Any],
) -> str:
    # Only H4 candles already closed when the source decision is made.
    body = json.dumps({
        "market": market.value, "parent": parent, "reference": name,
        "ohlc_reference": payload, "ohlc_closed_c2": c2,
    }, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(body).hexdigest()


def _reference(
    market: CrtPureMarket,
    parent: str,
    reference_started: datetime,
    payload: dict[str, Any],
    c2: dict[str, Any],
    c2_close: datetime,
    direction: str,
) -> CrtGm1Reference:
    reference_close = reference_started + H4
    return CrtGm1Reference(
        market=market,
        reference_id=f"{market.value}|{reference_started.isoformat()}",
        parent_id=parent,
        direction=CrtPureCandidateDirection(direction),
        closed_at=reference_close,
        discovered_at=c2_close,
        evidence_sha256=_evidence_digest(
            market, parent, reference_started.isoformat(), payload, c2
        ),
    )


def _closed_h4(
    bars: dict[datetime, ReplayBar], started: datetime,
) -> dict[str, Any] | None:
    window = tuple(bars.get(started + i * M5) for i in range(48))
    if any(bar is None for bar in window):
        return None
    return _aggregate(tuple(bar for bar in window if bar is not None))


def audit_v3_g2_g7_ledgers(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
    source_rows: tuple[dict[str, Any], ...],
    gm4_rows: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Pure checker; untrusted unit fixtures are never authenticated evidence."""
    if market not in (CrtPureMarket.AUDUSD, CrtPureMarket.USDJPY):
        raise ValueError("BTCUSD frozen in original Atlas sample")
    if not bars:
        raise ValueError("original M5 not supplied")
    indexed: dict[datetime, ReplayBar] = {}
    for bar in bars:
        if bar.opened_at.tzinfo is None or bar.opened_at.utcoffset() is None:
            raise ValueError("original M5 clock timezone absent")
        started = bar.opened_at.astimezone(UTC)
        if started in indexed:
            raise ValueError("duplicate original M5 time")
        if started.minute % 5 or started.second or started.microsecond:
            raise ValueError("original M5 time not aligned")
        indexed[started] = bar
    if len({x["source_event_id"] for x in source_rows}) != len(source_rows):
        raise ValueError("duplicate V3 source identity")
    gm4 = {x["source_event_id"]: x for x in gm4_rows}
    if len(gm4) != len(gm4_rows) or set(gm4) != {
        x["source_event_id"] for x in source_rows
    }:
        raise ValueError("V3/G-M4 identity set mismatch")
    ordered = sorted(source_rows, key=lambda x: x["decision_clock_utc"])
    history: list[CrtGm1SourceEvent] = []
    records: list[dict[str, Any]] = []
    summaries = Counter[str]()
    if len({x["c3_H4_opened_at_utc"] for x in ordered}) != len(ordered):
        raise ValueError("more than one V3 source per H4 parent")

    for i, source in enumerate(ordered):
        if (
            source["market"] != market.value
            or source["conceptual_state"] != "CONCEPTUAL_CANDIDATE_V3"
            or source["source_authority_adjudicated"] is not False
            or source["independent_method_review_complete"] is not False
            or source["not_a_trade"] is not True
            or source["no_sizing_or_capital_authority"] is not True
        ):
            raise ValueError("V3 source not admissible or falsely approved")
        event_id = source["source_event_id"]
        decision = _utc(source["decision_clock_utc"])
        c3_start = _utc(source["c3_H4_opened_at_utc"])
        if not c3_start < decision < c3_start + H4:
            raise ValueError("source decision outside H4 parent window")
        c2_start = c3_start - H4
        c1_start = c3_start - 2 * H4
        c0_start = c3_start - HISTORY_WINDOW
        c0 = _closed_h4(indexed, c0_start)
        c1 = _closed_h4(indexed, c1_start)
        c2 = _closed_h4(indexed, c2_start)
        if c1 is None or c2 is None:
            raise ValueError("V3 claims parent but true closed H4 M5 missing")
        parent = f"{market.value}|{c3_start.isoformat()}"
        direction = _direction(c1, c2)
        if direction != source["parent_direction"] or direction is None:
            raise ValueError("frozen V3 parent direction disagrees with raw M5")
        c2_close = c3_start
        if c2_close > decision:
            raise ValueError("C2 not closed by decision")
        refs = [_reference(
            market, parent, c1_start, c1, c2, c2_close, direction
        )]
        rival_direction = _direction(c0, c2) if c0 is not None else None
        if c0 is not None and rival_direction is not None:
            refs.append(_reference(
                market, parent, c0_start, c0, c2, c2_close, rival_direction
            ))
        # Explicitly do NOT call the dual H4 bounded census "complete".
        # There could be still older live CRT references.
        g2 = audit_g2_reference_conflicts(
            market=market, parent_id=parent,
            decision_at=decision, references=tuple(refs),
            inventory_complete=False,
        )
        if g2.verdict is not CrtGm1CausalVerdict.WAIT:
            raise ValueError("bounded G2 inventory falsely promoted to method PASS")

        path = gm4[event_id]
        if (
            path["source_event_id"] != event_id
            or path["market"] != market.value
            or _utc(path["source_decision_clock_utc"]) != decision
            or _utc(path["parent_c3_utc"]) != c3_start
            or path["initial_cognitive_action"] != "ABSTAIN"
            or path["gm5_router_blocked_at_decision"] is not True
            or path["not_a_trade"] is not True
            or path["no_PnL_or_sizing"] is not True
            or path["G_M4_PASS"] is not False
        ):
            raise ValueError("G-M4/source identity, risk or chronology mismatch")
        proven = path["terminal_observation_proven"]
        if type(proven) is not bool:
            raise ValueError("G-M4 terminal witness is not boolean")
        raw_terminal = path["terminal_observed_at_utc"]
        if proven != (raw_terminal is not None):
            raise ValueError("G-M4 terminal and clock contradict each other")
        actual_terminal = _utc(raw_terminal) if raw_terminal is not None else None
        if actual_terminal is not None and actual_terminal < decision:
            raise ValueError("G-M4 terminal precedes source decision")

        proposal = CrtGm1SourceEvent(
            market=market, parent_id=parent, source_event_id=event_id,
            hypothesis_id=f"{market.value}|V3_HYP|{event_id}",
            event_generation=i + 1, observed_at=decision, decision_at=decision,
        )
        # Source's current post-decision terminal does NOT enter initial
        # decision. For prior events, mask both UNKNOWN and any terminal not
        # observed by this decision time. No price result enters G7.
        prior = tuple(CrtGm1SourceEvent(
            market=h.market,
            parent_id=h.parent_id,
            source_event_id=h.source_event_id,
            hypothesis_id=h.hypothesis_id,
            event_generation=h.event_generation,
            observed_at=h.observed_at,
            decision_at=h.decision_at,
            terminal_observed_at=(
                h.terminal_observed_at
                if (h.terminal_observed_at is not None
                    and h.terminal_observed_at <= decision)
                else None
            ),
        ) for h in history)
        if history and history[-1].decision_at >= decision:
            raise ValueError("source decisions not strictly increasing")
        g7 = audit_g7_rearm(proposal=proposal, observed_history=prior)
        if g7.grants_rearm_authority or g7.grants_execution_authority:
            raise ValueError("research G7 unexpectedly authorized entry")
        if g7.verdict not in (
            CrtGm1CausalVerdict.PROVISIONAL, CrtGm1CausalVerdict.WAIT,
            CrtGm1CausalVerdict.ABSTAIN,
        ):
            raise ValueError("unexpected G7 status")
        # Append source for FUTURE diagnoses only; never look ahead in record.
        history.append(CrtGm1SourceEvent(
            market=proposal.market, parent_id=proposal.parent_id,
            source_event_id=proposal.source_event_id,
            hypothesis_id=proposal.hypothesis_id,
            event_generation=proposal.event_generation,
            observed_at=proposal.observed_at,
            decision_at=proposal.decision_at,
            terminal_observed_at=actual_terminal,
        ))
        row = {
            "schema": SCHEMA,
            "market": market.value,
            "source_event_id": event_id,
            "parent_c3_utc": c3_start.isoformat(),
            "decision_clock_utc": decision.isoformat(),
            "previous_sources": len(prior),
            "reference_C0_complete": c0 is not None,
            "reference_C0_rival_eligible": rival_direction is not None,
            "reference_C0_rival_opposes_C1": (
                rival_direction is not None and rival_direction != direction
            ),
            "reference_C0_rival_same_as_C1": (
                rival_direction is not None and rival_direction == direction
            ),
            "bounded_references_observed": len(refs),
            "reference_evidence_sha256": tuple(r.evidence_sha256 for r in refs),
            "G2_verdict": g2.verdict.value,
            "G2_complete_inventory_proven": False,
            "G7_verdict": g7.verdict.value,
            "G7_prior_terminals_causally_known": sum(
                h.terminal_observed_at is not None for h in prior
            ),
            "G7_prior_terminals_censored": sum(
                h.terminal_observed_at is None for h in prior
            ),
            "G7_generation_research_ordinal": proposal.event_generation,
            "source_authorized": False,
            "not_a_trade": True,
            "no_sizing": True,
            "not_fresh_OOS": True,
            "G_M1_PASS": False,
            "G_M4_PASS": False,
            "G_M5_ISSUED": False,
            "GLOBAL_CERTIFIED": False,
        }
        records.append(row)
        summaries["G2_" + g2.verdict.value] += 1
        summaries["G7_" + g7.verdict.value] += 1
        summaries["C0_MISSING"] += int(c0 is None)
        summaries["C0_COMPETING"] += int(rival_direction is not None)
        summaries["C0_OPPOSING"] += int(
            rival_direction is not None and rival_direction != direction
        )
        summaries["C0_SAME"] += int(
            rival_direction is not None and rival_direction == direction
        )
        summaries["GM4_UNKNOWN"] += int(not proven)

    return {
        "schema": SCHEMA,
        "market": market.value,
        "original_M5": len(bars),
        "V3_cases": len(source_rows),
        "GM4_cases_reconciled": len(gm4_rows),
        "counts": dict(sorted(summaries.items())),
        "G2_full_reference_inventory_proven": False,
        "G7_runtime_ledger_authenticated": False,
        "OOS_new": False,
        "G_M1_PASS": False, "G_M4_PASS": False,
        "G_M5_ISSUED": False, "GLOBAL_CERTIFIED": False,
        "no_sizing": True, "no_orders": True,
    }, tuple(records)


def real_atlas_g2_g7_bridge(
    market: CrtPureMarket, bars: tuple[ReplayBar, ...],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Real entry point: recompute BOTH frozen V3 and G-M4 from verified M5."""
    source_manifest, all_v3 = full_utc_h4_v3_census(market, bars)
    gm4_manifest, gm4 = replay_v3_gm4(market, bars)
    selected = tuple(
        row for row in all_v3
        if row["conceptual_state"] == "CONCEPTUAL_CANDIDATE_V3"
    )
    if (
        source_manifest["state_counts"].get("CONCEPTUAL_CANDIDATE_V3", 0)
        != len(selected)
        or gm4_manifest["v3_confirmed_source_count"] != len(selected)
        or gm4_manifest["v3_gm4_cases_reconciled"] != len(selected)
    ):
        raise ValueError("frozen V3/G-M4 manifests do not reconcile")
    summary, rows = audit_v3_g2_g7_ledgers(market, bars, selected, gm4)
    summary["frozen_V3_policy_id"] = source_manifest["policy_id"]
    summary["frozen_GM4_schema"] = gm4_manifest["schema"]
    return summary, rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=("AUDUSD", "USDJPY"))
    parser.add_argument("atlas_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    market = CrtPureMarket(args.market)
    bars, provenance = load_atlas_vt08_m5(market, args.atlas_root)
    summary, ledger = real_atlas_g2_g7_bridge(market, bars)
    summary["original_atlas_provenance"] = provenance
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "g2-g7-real-atlas-pit-summary.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n"
    )
    with (args.output / "g2-g7-real-atlas-pit-ledger.jsonl").open("w") as out:
        for row in ledger:
            out.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({
        k: v for k, v in summary.items() if k != "original_atlas_provenance"
    }, sort_keys=True))


if __name__ == "__main__":
    main()
