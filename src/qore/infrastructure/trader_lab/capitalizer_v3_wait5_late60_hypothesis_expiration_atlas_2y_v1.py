"""Outcome-free H1 hypothesis-expiration atlas for rejected WAIT5_LATE60.

This atlas joins two already-completed structural diagnostics:
- next-H1 supersession census;
- M5 carry-context census.

The join is structural only. Realized R, exits, target/stop outcomes and PnL are not read.
It does not admit trades, reject trades, alter WAIT5, or promote LATE60.

Purpose:
distinguish a physically intact stop from a causally unchanged hypothesis before
any future economic candidate is frozen.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

IDENTITY = "QORE_CAPITALIZER_V3_WAIT5_LATE60_HYPOTHESIS_EXPIRATION_ATLAS_2Y_V1"
EXPECTED_SUPERSESSION_ROWS = 376
EXPECTED_CARRY_ROWS = 365

NO_NEW_H1_SWEEP = "NO_NEW_H1_SWEEP"
NEW_H1_SWEEP_PENDING = "NEW_H1_SWEEP_PENDING"
NEW_H1_CLOSEBACK_PENDING = "NEW_H1_CLOSEBACK_PENDING"
OPPOSED_NEW_H1_MSS = "OPPOSED_NEW_H1_MSS"
SAME_SIDE_NEW_H1_MSS = "SAME_SIDE_NEW_H1_MSS"
NEW_H1_MSS_RELATION_UNKNOWN = "NEW_H1_MSS_RELATION_UNKNOWN"


@dataclass(frozen=True, slots=True)
class HypothesisExpirationRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str
    original_deadline: str
    h1_supersession_state: str
    h1_new_mss_side_relation: str | None
    continuity_state: str
    deadline_m5_state: str
    entry_m5_state: str
    m5_state_transition: str
    any_aligned_since_deadline: bool
    any_opposed_since_deadline: bool
    new_completed_m5_evidence: bool


def _load_jsonl(root: Path, pattern: str) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob(pattern))
    if len(paths) != 9:
        raise ValueError(f"expiration atlas requires 9 ledgers for {pattern}, got {len(paths)}")
    rows: list[dict[str, Any]] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("expiration atlas row must be object")
                rows.append(raw)
    return tuple(rows)


def _supersession_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row["symbol"]),
        str(row["session"]),
        str(row["operating_date"]),
        str(row["old_side"]),
        str(row["late_fill_at"]),
    )


def _carry_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row["symbol"]),
        str(row["session"]),
        str(row["operating_date"]),
        str(row["side"]),
        str(row["entry_at"]),
    )


def _continuity_state(row: dict[str, Any]) -> str:
    state = str(row["new_state"])
    if state == "NO_NEW_SWEEP":
        return NO_NEW_H1_SWEEP
    if state == "NEW_SWEEP_ONLY":
        return NEW_H1_SWEEP_PENDING
    if state == "NEW_CLOSEBACK_NO_MSS":
        return NEW_H1_CLOSEBACK_PENDING
    if state != "NEW_MSS":
        raise ValueError(f"unknown supersession state: {state}")

    relation = row.get("new_mss_side_relation")
    if relation == "OPPOSED_SIDE":
        return OPPOSED_NEW_H1_MSS
    if relation == "SAME_SIDE":
        return SAME_SIDE_NEW_H1_MSS
    return NEW_H1_MSS_RELATION_UNKNOWN


def build_atlas(
    supersession_root: Path,
    carry_root: Path,
) -> tuple[dict[str, Any], tuple[HypothesisExpirationRow, ...]]:
    supersession = _load_jsonl(
        supersession_root,
        "capitalizer-*-v3-source-first-late60-supersession-census-2y-v1-rows.jsonl",
    )
    carry = _load_jsonl(
        carry_root,
        "capitalizer-*-v3-wait5-late60-carry-context-forensics-2y-v1-rows.jsonl",
    )

    if len(supersession) != EXPECTED_SUPERSESSION_ROWS:
        raise ValueError("supersession control mismatch")
    if len(carry) != EXPECTED_CARRY_ROWS:
        raise ValueError("carry-context control mismatch")

    supersession_by_key = {_supersession_key(row): row for row in supersession}
    carry_by_key = {_carry_key(row): row for row in carry}
    if len(supersession_by_key) != len(supersession):
        raise ValueError("duplicate supersession structural key")
    if len(carry_by_key) != len(carry):
        raise ValueError("duplicate carry-context structural key")

    unmatched_carry = sorted(set(carry_by_key) - set(supersession_by_key))
    unmatched_supersession = sorted(set(supersession_by_key) - set(carry_by_key))
    if unmatched_carry:
        raise ValueError("carry row missing supersession provenance")

    rows: list[HypothesisExpirationRow] = []
    for key, carry_row in carry_by_key.items():
        supersession_row = supersession_by_key[key]
        rows.append(
            HypothesisExpirationRow(
                symbol=str(carry_row["symbol"]),
                session=str(carry_row["session"]),
                operating_date=str(carry_row["operating_date"]),
                side=str(carry_row["side"]),
                entry_at=str(carry_row["entry_at"]),
                original_deadline=str(carry_row["original_deadline"]),
                h1_supersession_state=str(supersession_row["new_state"]),
                h1_new_mss_side_relation=(
                    None
                    if supersession_row.get("new_mss_side_relation") is None
                    else str(supersession_row["new_mss_side_relation"])
                ),
                continuity_state=_continuity_state(supersession_row),
                deadline_m5_state=str(carry_row["deadline_state"]),
                entry_m5_state=str(carry_row["entry_state"]),
                m5_state_transition=str(carry_row["state_transition"]),
                any_aligned_since_deadline=bool(
                    carry_row["any_aligned_since_deadline"]
                ),
                any_opposed_since_deadline=bool(
                    carry_row["any_opposed_since_deadline"]
                ),
                new_completed_m5_evidence=bool(
                    carry_row["new_completed_m5_evidence"]
                ),
            )
        )

    ordered = tuple(sorted(rows, key=lambda item: (item.entry_at, item.symbol)))
    continuity = Counter(item.continuity_state for item in ordered)
    deadline_states = Counter(item.deadline_m5_state for item in ordered)
    entry_states = Counter(item.entry_m5_state for item in ordered)
    transitions = Counter(item.m5_state_transition for item in ordered)

    deadline_by_continuity: dict[str, Counter[str]] = defaultdict(Counter)
    entry_by_continuity: dict[str, Counter[str]] = defaultdict(Counter)
    transition_by_continuity: dict[str, Counter[str]] = defaultdict(Counter)
    per_session: dict[str, Counter[str]] = defaultdict(Counter)
    per_market: dict[str, Counter[str]] = defaultdict(Counter)

    for item in ordered:
        deadline_by_continuity[item.continuity_state][item.deadline_m5_state] += 1
        entry_by_continuity[item.continuity_state][item.entry_m5_state] += 1
        transition_by_continuity[item.continuity_state][item.m5_state_transition] += 1
        per_session[item.session][item.continuity_state] += 1
        per_session[item.session]["TOTAL"] += 1
        per_market[item.symbol][item.continuity_state] += 1
        per_market[item.symbol]["TOTAL"] += 1

    report = {
        "identity": IDENTITY,
        "supersession_rows": len(supersession),
        "carry_rows": len(carry),
        "joined_rows": len(ordered),
        "unmatched_carry_rows": len(unmatched_carry),
        "unmatched_supersession_rows": len(unmatched_supersession),
        "continuity_states": dict(sorted(continuity.items())),
        "deadline_m5_states": dict(sorted(deadline_states.items())),
        "entry_m5_states": dict(sorted(entry_states.items())),
        "m5_state_transitions": dict(sorted(transitions.items())),
        "deadline_m5_by_continuity": {
            key: dict(sorted(value.items()))
            for key, value in sorted(deadline_by_continuity.items())
        },
        "entry_m5_by_continuity": {
            key: dict(sorted(value.items()))
            for key, value in sorted(entry_by_continuity.items())
        },
        "transition_by_continuity": {
            key: dict(sorted(value.items()))
            for key, value in sorted(transition_by_continuity.items())
        },
        "per_session": {
            key: dict(sorted(value.items()))
            for key, value in sorted(per_session.items())
        },
        "per_market": {
            key: dict(sorted(value.items()))
            for key, value in sorted(per_market.items())
        },
        "any_aligned_since_deadline": sum(
            item.any_aligned_since_deadline for item in ordered
        ),
        "any_opposed_since_deadline": sum(
            item.any_opposed_since_deadline for item in ordered
        ),
        "new_completed_m5_evidence": sum(
            item.new_completed_m5_evidence for item in ordered
        ),
        "structural_only": True,
        "outcome_fields_read": False,
        "outcome_used_for_classification": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_claimed": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return report, ordered


def write_atlas(
    report: dict[str, Any],
    rows: tuple[HypothesisExpirationRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-nine-market-v3-wait5-late60-hypothesis-expiration-atlas-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("supersession_root", type=Path)
    parser.add_argument("carry_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, rows = build_atlas(
        args.supersession_root,
        args.carry_root,
    )
    write_atlas(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
